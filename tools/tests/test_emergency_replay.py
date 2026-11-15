"""Ticket 05 (Spec 1 task 1.5): emergency replay from Pulse.

Spec: stepwise stroke-volume drop, sinus tachycardia, unstable VT, VF, arrest, CPR.
Chest pain is crew-reported, not simulated. Labelled "estimate, not validated" (stories 5, 6).
Stroke-volume drop: StrokeVolumeMultiplier steps (user decision 2026-11-14, option A).
Test (a): the replay validates against its schema.
"""
import csv
import io
import json
import os
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "contracts"))

import emergency_replay as er  # noqa: E402
from validate import validate  # noqa: E402

BUNDLE = ROOT / "data" / "pulse" / "PulseExplorer-3.3.0-Windows-AMD64"

HEADER = ["Time(s)", "HeartRate(1/min)", "HeartStrokeVolume(mL)", "SystolicArterialPressure(mmHg)",
          "DiastolicArterialPressure(mmHg)", "MeanArterialPressure(mmHg)", "CardiacOutput(L/min)",
          "OxygenSaturation", "RespirationRate(1/min)", "EndTidalCarbonDioxidePressure(mmHg)", "Unused(x)",
          "CoreTemperature(degC)"]


def fixture_csv(seconds=6, dt=0.5):
    """Synthetic test CSV (not physiology): value = column index * 100 + time."""
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(HEADER)
    n = int(seconds / dt) + 1
    for i in range(n):
        t = round(i * dt, 2)
        w.writerow([t] + [c * 100 + t for c in range(1, len(HEADER))])
    return out.getvalue()


SMALL_PHASES = [  # test phases on a short timeline
    {"t": 0, "action": "baseline"},
    {"t": 1, "action": "stroke_volume", "multiplier": 0.9, "chest_pain": True},
    {"t": 2, "action": "rhythm", "rhythm": "SinusTachycardia"},
    {"t": 3, "action": "rhythm", "rhythm": "UnstableVentricularTachycardia"},
    {"t": 4, "action": "rhythm", "rhythm": "CoarseVentricularFibrillation"},
    {"t": 5, "action": "compressions"},
    {"t": 6, "action": "end"},
]


def replay_from_fixture(**kw):
    return er.build_replay(er.read_csv(fixture_csv()), SMALL_PHASES, **kw)


# ---- the Pulse scenario ------------------------------------------------------------

def actions_of(kind, scenario):
    return [a for a in scenario["AnyAction"] if kind in json.dumps(a)]


def test_default_phases_follow_the_spec_order():
    order = [p["action"] if p["action"] != "rhythm" else p["rhythm"] for p in er.PHASES]
    assert order == ["baseline", "stroke_volume", "stroke_volume", "stroke_volume", "SinusTachycardia",
                     "UnstableVentricularTachycardia", "CoarseVentricularFibrillation", "compressions", "end"]
    assert [p["multiplier"] for p in er.PHASES if p["action"] == "stroke_volume"] == [0.9, 0.8, 0.7]
    assert [p["t"] for p in er.PHASES] == sorted(p["t"] for p in er.PHASES)


def test_scenario_steps_stroke_volume_with_the_cardiovascular_modifier():
    sc = er.build_scenario(er.PHASES)
    mods = actions_of("StrokeVolumeMultiplier", sc)
    values = [a["PatientAction"]["CardiovascularMechanicsModification"]["Modifiers"]["StrokeVolumeMultiplier"]
              ["ScalarUnsigned"]["Value"] for a in mods]
    assert values == [0.9, 0.8, 0.7]


def test_scenario_rhythms_then_kitware_compressions():
    sc = er.build_scenario(er.PHASES)
    rhythms = [a["PatientAction"]["Arrhythmia"]["Rhythm"] for a in actions_of("Arrhythmia", sc)]
    assert rhythms == ["SinusTachycardia", "UnstableVentricularTachycardia", "CoarseVentricularFibrillation"]
    cpr = actions_of("ChestCompressionAutomated", sc)[0]["PatientAction"]["ChestCompressionAutomated"]
    assert cpr["Depth"]["ScalarLength"] == {"Value": 6, "Unit": "cm"}
    assert cpr["CompressionFrequency"]["ScalarFrequency"] == {"Value": 100, "Unit": "1/min"}
    assert cpr["AppliedForceFraction"]["Scalar0To1"] == {"Value": 0.8}


def test_scenario_time_advances_add_up_to_the_end_phase():
    sc = er.build_scenario(er.PHASES)
    total = sum(a["AdvanceTime"]["Time"]["ScalarTime"]["Value"] for a in sc["AnyAction"] if "AdvanceTime" in a)
    assert total == er.PHASES[-1]["t"]
    assert sc["DataRequestFile"] == ["StandardDataRequests.json", "ACLSDataRequests.json"]
    assert sc["PatientConfiguration"] == {"PatientFile": "StandardMale.json"}


def test_rhythm_timeline_starts_in_normal_sinus():
    assert er.rhythm_timeline(SMALL_PHASES) == [
        (0, "NormalSinus"), (2, "SinusTachycardia"), (3, "UnstableVentricularTachycardia"),
        (4, "CoarseVentricularFibrillation")]


# ---- CSV -> ReplayFile ------------------------------------------------------------------

def test_a_replay_validates_and_every_reading_is_a_valid_reading():
    replay = replay_from_fixture()
    validate("ReplayFile", replay)
    for e in replay["events"]:
        if e["type"] == "reading":
            validate("Reading", {"schema_version": replay["schema_version"], **e["payload"]})


def test_readings_are_taken_every_whole_second_with_values_copied_exactly():
    readings = [e["payload"] for e in replay_from_fixture()["events"] if e["type"] == "reading"]
    hr = [(r["t"], r["value"]) for r in readings if r["indicator"] == "heart_rate"]
    assert hr == [(t, 100 + t) for t in range(0, 7)]  # column 1 value = 100 + time


def test_indicators_and_units_come_from_the_csv_header():
    readings = [e["payload"] for e in replay_from_fixture()["events"] if e["type"] == "reading"]
    units = {r["indicator"]: r["unit"] for r in readings}
    assert units == {
        "heart_rate": "1/min", "stroke_volume": "mL", "systolic_bp": "mmHg", "diastolic_bp": "mmHg",
        "mean_arterial_pressure": "mmHg", "cardiac_output": "L/min", "spo2": "fraction",
        "respiration_rate": "1/min", "etco2": "mmHg", "cardiac_rhythm": "rhythm",
        "body_temperature": "degC",  # Pulse CoreTemperature (Spec 2/5 request 2026-11-15)
    }


def test_rhythm_readings_follow_the_scenario_actions():
    readings = [e["payload"] for e in replay_from_fixture()["events"] if e["type"] == "reading"]
    rhythm = {r["t"]: r["value"] for r in readings if r["indicator"] == "cardiac_rhythm"}
    assert rhythm == {0: "NormalSinus", 1: "NormalSinus", 2: "SinusTachycardia", 3: "UnstableVentricularTachycardia",
                      4: "CoarseVentricularFibrillation", 5: "CoarseVentricularFibrillation", 6: "CoarseVentricularFibrillation"}


def test_chest_pain_is_a_crew_report_not_a_reading():
    events = replay_from_fixture()["events"]
    reports = [e for e in events if e["type"] == "crew_report"]
    assert reports == [{"t": 1, "type": "crew_report",
                        "payload": {"crew": "B", "t": 1, "report": "chest pain", "source": "crew-reported"}}]
    assert not any(e["type"] == "reading" and "pain" in e["payload"]["indicator"] for e in events)


def test_readings_are_simulated_and_released_for_crew_b():
    r = next(e["payload"] for e in replay_from_fixture()["events"] if e["type"] == "reading")
    assert (r["crew"], r["source"], r["state"]) == ("B", "sim", "released")


def test_events_are_ordered_and_offset_and_crew_are_settable():
    replay = replay_from_fixture(crew="Bee", offset=1000)
    assert replay["crew"] == "Bee"
    times = [e["t"] for e in replay["events"]]
    assert times == sorted(times) and times[0] == 1000
    assert all(e["payload"]["crew"] == "Bee" for e in replay["events"])


def test_same_input_gives_identical_output():
    assert json.dumps(replay_from_fixture()) == json.dumps(replay_from_fixture())


def test_missing_csv_column_fails_loudly():
    text = fixture_csv().replace("HeartRate(1/min)", "Something(else)")
    with pytest.raises(KeyError):
        er.build_replay(er.read_csv(text), SMALL_PHASES)


# ---- log + source record ------------------------------------------------------------------

LOG = "[INFO] [89.74(s)] [Event Tachycardia 1]  x\n[INFO] [180.24(s)] [Event CardiacArrest 1]  y\n[INFO] [225.2(s)] [Event CardiogenicShock 1] z\n"


def action_log(entries, final):
    """Synthetic Pulse log in the driver's format: (time, action JSON) pairs."""
    out = []
    for t, action in entries:
        out.append(f"[INFO] [{t}(s)] [Action]\n{json.dumps(action, indent=1)}\n")
    out.append(f"[INFO] [{final}(s)] [Final SimTime] {final}(s)\n")
    return "".join(out)


def test_actual_phase_times_come_from_the_pulse_log():
    sc = er.build_scenario(SMALL_PHASES)
    # Pulse took 600 s extra after the stroke-volume modifier (re-stabilising)
    shifted = {1: 1, 2: 602, 3: 603, 4: 604, 5: 605}
    entries, k = [], 0
    for a in sc["AnyAction"]:
        if "AdvanceTime" in a:
            continue
        k += 1
        entries.append((shifted[k], a))
    phases = er.actual_phases(SMALL_PHASES, action_log(entries, 606.0))
    assert [p["t"] for p in phases] == [0, 1, 602, 603, 604, 605, 606]
    assert phases[1]["multiplier"] == 0.9 and phases[1]["chest_pain"]


def test_actual_phases_fail_loudly_when_the_log_does_not_match_the_plan():
    with pytest.raises(ValueError):
        er.actual_phases(SMALL_PHASES, action_log([], 10.0))


def test_arrest_time_is_read_from_the_pulse_log():
    assert er.arrest_time(LOG) == 180.24
    assert er.arrest_time("no arrest here") is None


def test_source_record_carries_the_label_and_traceability():
    rec = er.source_record(er.PHASES, LOG, csv_bytes=b"abc", run_date="2026-11-14")
    assert rec["label"] == "estimate, not validated"
    assert rec["engine"] == "Pulse Physiology Engine 4.3.1 (Kitware PulseExplorer-3.3.0-Windows-AMD64 bundle), Apache 2.0"
    assert rec["arrest_t"] == 180.24
    assert rec["csv_sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert rec["scenario"] == er.build_scenario(er.PHASES)
    assert any("team value" in n for n in rec["notes"])
    assert any("crew-reported" in n for n in rec["notes"])


def test_command_line_builds_from_saved_csv_and_log(tmp_path):
    csv_path = tmp_path / "run.csv"
    csv_path.write_text(fixture_csv(seconds=600, dt=1.0), encoding="utf-8")
    log_path = tmp_path / "run.log"
    planned = [(p["t"], a) for p, a in zip(
        [p for p in er.PHASES if p["action"] in ("stroke_volume", "rhythm", "compressions")],
        [a for a in er.build_scenario(er.PHASES)["AnyAction"] if "AdvanceTime" not in a])]
    log_path.write_text(action_log(planned, 540.0) + LOG, encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "emergency_replay.py"), "--csv", str(csv_path),
                             "--log", str(log_path), "--out-dir", str(out), "--run-date", "2026-11-14"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    replay = json.loads((out / "emergency-crew-B.json").read_text(encoding="utf-8"))
    validate("ReplayFile", replay)
    rec = json.loads((out / "emergency-crew-B.source.json").read_text(encoding="utf-8"))
    assert rec["label"] == "estimate, not validated" and rec["events"] == len(replay["events"])


@pytest.mark.skipif(not (BUNDLE / "PulseScenarioDriver.exe").exists() or os.environ.get("STELLARFORGE_RUN_PULSE") != "1",
                    reason="slow real Pulse run: needs the bundle in data/pulse and STELLARFORGE_RUN_PULSE=1")
def test_real_pulse_run_produces_the_episode(tmp_path):
    csv_text, log_text = er.run_pulse(BUNDLE, er.build_scenario(er.PHASES))
    phases = er.actual_phases(er.PHASES, log_text)
    replay = er.build_replay(er.read_csv(csv_text), phases)
    validate("ReplayFile", replay)
    at = {p.get("rhythm", p["action"]): p["t"] for p in phases}
    arrest = er.arrest_time(log_text)
    assert arrest is not None and arrest >= at["CoarseVentricularFibrillation"]
    readings = [e["payload"] for e in replay["events"] if e["type"] == "reading"]
    sv = {r["t"]: r["value"] for r in readings if r["indicator"] == "stroke_volume"}
    hr = {r["t"]: r["value"] for r in readings if r["indicator"] == "heart_rate"}
    steps = [int(p["t"]) for p in phases if p["action"] == "stroke_volume"]
    # each stroke-volume step: an immediate drop right after it is applied
    assert all(sv[t + 3] < sv[t - 1] for t in steps)
    # stepwise overall: lower before the tachycardia than at baseline
    assert sv[int(at["SinusTachycardia"]) - 1] < sv[steps[0] - 1]
    # heart rate rises during the tachycardias
    assert hr[int(at["CoarseVentricularFibrillation"]) - 5] > hr[steps[0] - 1] + 30
