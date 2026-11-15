"""Emergency replay for crew B from the Pulse Physiology Engine (Spec 1 task 1.5).

Episode (spec order): stepwise stroke-volume drop, sinus tachycardia, unstable VT, VF, arrest, CPR.
- Stroke-volume drop: Pulse CardiovascularMechanicsModification / StrokeVolumeMultiplier steps
  (user decision 2026-11-14, option A). Step sizes and all phase timings are team values.
- Rhythms: Pulse Arrhythmia action. Arrest is Pulse's own CardiacArrest event.
- Compressions: ChestCompressionAutomated with the settings from Kitware's
  ChestCompressionAutomatedVaried.json scenario.
- Chest pain is crew-reported (a crew_report event), never simulated.
Every physiological value is Pulse model output, labelled "estimate, not validated".

Readings are taken from the Pulse CSV at every whole second, values copied unchanged.
Pulse's CSV has no rhythm column, so cardiac_rhythm readings come from the scenario's own
Arrhythmia actions (NormalSinus until the first one).

Usage:
  python tools/emergency_replay.py --bundle data/pulse/PulseExplorer-3.3.0-Windows-AMD64   # run Pulse, then build
  python tools/emergency_replay.py --csv run.csv --log run.log                             # build from a saved run
Output (default replay/generated/): emergency-crew-<crew>.json and .source.json
"""
import argparse
import csv
import datetime as dt
import hashlib
import io
import json
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"
LABEL = "estimate, not validated"
ENGINE = "Pulse Physiology Engine 4.3.1 (Kitware PulseExplorer-3.3.0-Windows-AMD64 bundle), Apache 2.0"

# Timeline in seconds. Multipliers and timings are team values (see NOTES).
PHASES = [
    {"t": 0, "action": "baseline"},
    {"t": 60, "action": "stroke_volume", "multiplier": 0.9, "chest_pain": True},
    {"t": 120, "action": "stroke_volume", "multiplier": 0.8},
    {"t": 180, "action": "stroke_volume", "multiplier": 0.7},
    {"t": 240, "action": "rhythm", "rhythm": "SinusTachycardia"},
    {"t": 300, "action": "rhythm", "rhythm": "UnstableVentricularTachycardia"},
    {"t": 360, "action": "rhythm", "rhythm": "CoarseVentricularFibrillation"},
    {"t": 420, "action": "compressions"},
    {"t": 540, "action": "end"},
]

# Pulse CSV column -> indicator (unit taken from the column header)
COLUMNS = {
    "HeartRate(1/min)": "heart_rate",
    "HeartStrokeVolume(mL)": "stroke_volume",
    "SystolicArterialPressure(mmHg)": "systolic_bp",
    "DiastolicArterialPressure(mmHg)": "diastolic_bp",
    "MeanArterialPressure(mmHg)": "mean_arterial_pressure",
    "CardiacOutput(L/min)": "cardiac_output",
    "OxygenSaturation": "spo2",
    "RespirationRate(1/min)": "respiration_rate",
    "EndTidalCarbonDioxidePressure(mmHg)": "etco2",
    "CoreTemperature(degC)": "body_temperature",  # added 2026-11-15 (Spec 2 card, Spec 5 request)
}
UNITLESS = {"OxygenSaturation": "fraction"}  # Pulse reports SpO2 as a 0-1 fraction with no unit in the header

KITWARE_COMPRESSIONS = {
    "PatientAction": {"Action": {"Comment": "Settings from Kitware ChestCompressionAutomatedVaried.json"}},
    "Depth": {"ScalarLength": {"Value": 6, "Unit": "cm"}},
    "CompressionFrequency": {"ScalarFrequency": {"Value": 100, "Unit": "1/min"}},
    "AppliedForceFraction": {"Scalar0To1": {"Value": 0.8}},
}

NOTES = [
    f"All physiological values are Pulse model output: {LABEL}.",
    "Stroke-volume multipliers (0.9, 0.8, 0.7) and every phase time are team values, not published values.",
    "Chest pain is crew-reported (crew_report event), not simulated; Pulse has no ischemia model.",
    "Compression settings copied from Kitware's ChestCompressionAutomatedVaried.json scenario.",
    "cardiac_rhythm readings come from the scenario's Arrhythmia actions; Pulse's CSV has no rhythm column.",
    "Readings sampled at whole seconds from Pulse's 0.02 s output, values copied unchanged.",
    "Pulse re-stabilises for about 600 s of simulated time after each stroke-volume modifier step; "
    "phase times in the replay are the times Pulse actually applied each action (from its log), not the plan.",
    "confidence = 1: model output has no measurement quality score; it is not a validated quality measure.",
]


def build_scenario(phases):
    actions = []
    for phase, nxt in zip(phases, phases[1:] + [None]):
        kind = phase["action"]
        if kind == "stroke_volume":
            actions.append({"PatientAction": {"CardiovascularMechanicsModification": {"Modifiers": {
                "StrokeVolumeMultiplier": {"ScalarUnsigned": {"Value": phase["multiplier"]}}}}}})
        elif kind == "rhythm":
            actions.append({"PatientAction": {"Arrhythmia": {"Rhythm": phase["rhythm"]}}})
        elif kind == "compressions":
            actions.append({"PatientAction": {"ChestCompressionAutomated": json.loads(json.dumps(KITWARE_COMPRESSIONS))}})
        if nxt is not None:
            actions.append({"AdvanceTime": {"Time": {"ScalarTime": {"Value": nxt["t"] - phase["t"], "Unit": "s"}}}})
    return {
        "Description": "StellarForge emergency episode for crew B: " + LABEL,
        "PatientConfiguration": {"PatientFile": "StandardMale.json"},
        "DataRequestFile": ["StandardDataRequests.json", "ACLSDataRequests.json"],
        "AnyAction": actions,
    }


def rhythm_timeline(phases):
    timeline = [(phases[0]["t"], "NormalSinus")]
    timeline += [(p["t"], p["rhythm"]) for p in phases if p["action"] == "rhythm"]
    return timeline


def read_csv(text):
    reader = csv.reader(io.StringIO(text))
    header = next(reader)
    return {"header": header, "rows": [row for row in reader if row]}


def _unit(column):
    if column in UNITLESS:
        return UNITLESS[column]
    match = re.search(r"\(([^)]*)\)$", column)
    return match.group(1) if match else ""


def build_replay(data, phases, crew="B", profile="mars_transit", offset=0):
    header = data["header"]
    missing = _missing_columns(header)
    if missing:
        raise KeyError(f"Pulse CSV is missing columns: {missing}")
    index = {name: header.index(name) for name in COLUMNS}
    by_time = {round(float(row[0]), 3): row for row in data["rows"]}
    rhythms = rhythm_timeline(phases)
    events = []
    for second in range(int(phases[0]["t"]), int(phases[-1]["t"]) + 1):
        row = by_time.get(float(second))
        if row is None:
            continue
        t = second + offset
        for column, indicator in COLUMNS.items():
            value = float(row[index[column]])
            value = int(value) if value == int(value) else value
            events.append(_reading(crew, indicator, value, _unit(column), t))
        rhythm = [name for start, name in rhythms if start <= second][-1]
        events.append(_reading(crew, "cardiac_rhythm", rhythm, "rhythm", t))
    for phase in phases:
        if phase.get("chest_pain"):
            t = phase["t"] + offset
            events.append({"t": t, "type": "crew_report",
                           "payload": {"crew": crew, "t": t, "report": "chest pain", "source": "crew-reported"}})
    events.sort(key=lambda e: e["t"])  # stable
    return {"schema_version": SCHEMA_VERSION, "crew": crew, "profile": profile, "events": events}


def _reading(crew, indicator, value, unit, t):
    return {"t": t, "type": "reading", "payload": {"crew": crew, "indicator": indicator, "value": value, "unit": unit,
                                                   "t": t, "source": "sim", "confidence": 1, "state": "released"}}


def _missing_columns(header):
    return [c for c in COLUMNS if c not in header]


def actual_phases(phases, log_text):
    """Phases with the times Pulse actually applied each action, read from the driver log.

    Pulse re-stabilises after a CardiovascularMechanicsModification (about 600 s of simulated
    time per step), so planned and actual times differ. The end phase takes the final sim time.
    """
    applied = [(float(t), block) for t, block in re.findall(
        r"\[([0-9.]+)\(s\)\] \[Action\]\n(.*?)(?=\n\[(?:INFO|WARN|ERROR)\]|\Z)", log_text, re.S)
        if "AdvanceTime" not in block]
    planned = [p for p in phases if p["action"] in ("stroke_volume", "rhythm", "compressions")]
    if len(applied) != len(planned):
        raise ValueError(f"Pulse log shows {len(applied)} actions; the plan has {len(planned)}")
    final = re.search(r"\[Final SimTime\] ([0-9.]+)\(s\)", log_text)
    if not final:
        raise ValueError("Pulse log has no Final SimTime")
    marker = {"stroke_volume": lambda p: "CardiovascularMechanicsModification",
              "rhythm": lambda p: p["rhythm"], "compressions": lambda p: "ChestCompressionAutomated"}
    times = iter(applied)
    out = []
    for phase in phases:
        phase = dict(phase)
        if phase["action"] in marker:
            t, block = next(times)
            if marker[phase["action"]](phase) not in block:
                raise ValueError(f"Pulse log action at {t} s does not match planned {phase}")
            phase["t"] = _tidy(t)
        elif phase["action"] == "end":
            phase["t"] = _tidy(float(final.group(1)))
        out.append(phase)
    return out


def _tidy(t):
    return int(t) if t == int(t) else t


def arrest_time(log_text):
    match = re.search(r"\[([0-9.]+)\(s\)\] \[Event CardiacArrest 1\]", log_text)
    return float(match.group(1)) if match else None


def source_record(phases, log_text, csv_bytes, run_date, applied_phases=None):
    return {
        "label": LABEL,
        "engine": ENGINE,
        "run_date": run_date,
        "csv_sha256": hashlib.sha256(csv_bytes).hexdigest(),
        "arrest_t": arrest_time(log_text),
        "phases": phases,
        "applied_phases": applied_phases,
        "scenario": build_scenario(phases),
        "notes": NOTES,
    }


def run_pulse(bundle, scenario, name="StellarForgeEmergency"):
    """Run the scenario with the bundle's PulseScenarioDriver. Returns (csv_text, log_text)."""
    bundle = Path(bundle)
    folder = bundle / "scenarios" / "stellarforge"  # data-request files resolve from the scenarios folder
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / f"{name}.json"
    path.write_text(json.dumps(scenario, indent=1), encoding="utf-8")
    env = dict(os.environ, PATH=os.environ.get("PATH", "") + os.pathsep + str(bundle / "bin"))
    result = subprocess.run([str(bundle / "PulseScenarioDriver.exe"), f"scenarios/stellarforge/{name}.json"],
                            cwd=bundle, env=env, capture_output=True, text=True, timeout=900)
    if result.returncode != 0:
        raise RuntimeError(f"Pulse failed ({result.returncode}): {result.stderr[-500:]}")
    csv_text = (folder / f"{name}Results.csv").read_text(encoding="utf-8")
    log_file = folder / f"{name}.log"
    log_text = log_file.read_text(encoding="utf-8") if log_file.exists() else result.stdout
    return csv_text, log_text


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--bundle", help="Pulse Explorer bundle folder (runs Pulse)")
    src.add_argument("--csv", help="saved Pulse CSV (use with --log)")
    parser.add_argument("--log", help="saved Pulse log")
    parser.add_argument("--out-dir", default=str(ROOT / "replay" / "generated"))
    parser.add_argument("--crew", default="B")
    parser.add_argument("--profile", default="mars_transit")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--run-date", default=dt.date.today().isoformat())
    args = parser.parse_args(argv)

    if args.bundle:
        csv_text, log_text = run_pulse(args.bundle, build_scenario(PHASES))
    else:
        if not args.log:
            parser.error("--csv needs --log")
        csv_text = Path(args.csv).read_text(encoding="utf-8")
        log_text = Path(args.log).read_text(encoding="utf-8")
    data = read_csv(csv_text)
    missing = _missing_columns(data["header"])
    if missing:
        raise SystemExit(f"Pulse CSV is missing columns: {missing}")
    applied = actual_phases(PHASES, log_text)
    replay = build_replay(data, applied, crew=args.crew, profile=args.profile, offset=args.offset)
    sys.path.insert(0, str(ROOT / "contracts"))
    from validate import validate
    validate("ReplayFile", replay)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"emergency-crew-{args.crew}"
    (out / f"{stem}.json").write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
    record = dict(source_record(PHASES, log_text, csv_text.encode("utf-8"), args.run_date, applied),
                  events=len(replay["events"]), crew=args.crew, profile=args.profile, offset=args.offset)
    (out / f"{stem}.source.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Wrote {out / (stem + '.json')} ({len(replay['events'])} events; arrest at t={record['arrest_t']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
