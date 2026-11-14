"""Crew replays from PMData (Spec 1 task 1.4).

Four synthetic crew (A-D) from the four most complete PMData participants: about five
months of normal days each. Earth wearable data shaped to look like a crew; values copied
unchanged except crew A's planted drift. Lead Mission profile: Mars transit.

Daily indicators (PMData file -> indicator, unit, Reading.source):
  fitbit/resting_heart_rate.json  resting_heart_rate  bpm          sensor  (0 means no reading)
  fitbit/sleep.json               sleep_duration      min          sensor  (main sleep minutesAsleep)
  fitbit/steps.json               steps               steps        sensor  (per-minute steps summed per day)
  fitbit/sleep_score.csv          sleep_score         score 0-100  sensor  (overall_score)
  pmsys/wellness.csv              fatigue, mood, sleep_quality, stress (score 1-5), readiness (score 0-10)  manual
Scales from the PMData page: 1-5 with 3 normal; readiness 0-10.

Planted drift (crew A, team-planted): over the last 9 days with a resting heart rate, resting HR
rises linearly to +6 bpm and sleep falls linearly to -90 min; those readings get source "sim".
Anchor: mean and sample standard deviation per indicator over each crew's first 14 days.
t = whole days since the earliest first date among the four, at 07:00 mission time.

Usage: python tools/crew_replays.py --pmdata data/pmdata --sex p01=male,p02=female,...
       (or --overview data/pmdata/participant-overview.xlsx to read sex from PMData)
Output (default replay/generated/): crew-A..D.json, crew-records.json, crew-replays.source.json
"""
import argparse
import csv
import datetime as dt
import json
import random
import re
import statistics
import sys
import zipfile
from collections import defaultdict
from pathlib import Path
from xml.etree import ElementTree

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"
DAY = 86400
READ_AT = 7 * 3600
CREW_IDS = "ABCD"
DRIFT = {"crew": "A", "days": 9, "resting_heart_rate": 6.0, "sleep_duration": -90.0}

# indicator -> (unit, Reading.source), in output order
INDICATORS = {
    "resting_heart_rate": ("bpm", "sensor"),
    "sleep_duration": ("min", "sensor"),
    "steps": ("steps", "sensor"),
    "sleep_score": ("score 0-100", "sensor"),
    "fatigue": ("score 1-5", "manual"),
    "mood": ("score 1-5", "manual"),
    "readiness": ("score 0-10", "manual"),
    "sleep_quality": ("score 1-5", "manual"),
    "stress": ("score 1-5", "manual"),
}
WELLNESS = ("fatigue", "mood", "readiness", "sleep_quality", "stress")

NOTES = [
    "Earth wearable data (PMData, Fitbit Versa 2 and PMSys) shaped to look like a crew; no open astronaut wearable stream exists.",
    "Values copied unchanged except crew A's planted drift (source 'sim'); steps are per-minute values summed per day.",
    "Planted drift: linear ramp to +6 bpm resting HR and -90 min sleep over the last 9 days (spec example; ramp shape is a team value).",
    "Planted sleep is floored at 0 min (a short tracked night minus the drift cannot go negative).",
    "Anchor window 14 days and the 07:00 reading time are team values.",
    "confidence = 1: PMData gives no per-reading quality score; it is not a validated quality measure.",
]


def parse_date(text):
    return dt.date.fromisoformat(text[:10])


def _number(text):
    try:
        value = float(text)
    except (TypeError, ValueError):
        return None
    return int(value) if value == int(value) else value


def read_person(folder):
    """date -> {indicator: value} for one PMData participant folder."""
    folder = Path(folder)
    daily = defaultdict(dict)
    fit, pms = folder / "fitbit", folder / "pmsys"
    for entry in json.loads((fit / "resting_heart_rate.json").read_text(encoding="utf-8")):
        value = (entry.get("value") or {}).get("value")
        if value:  # 0 or missing means Fitbit had no resting HR that day
            daily[entry["dateTime"][:10]]["resting_heart_rate"] = value
    asleep = defaultdict(int)
    for entry in json.loads((fit / "sleep.json").read_text(encoding="utf-8")):
        if entry.get("mainSleep"):
            asleep[entry["dateOfSleep"]] += entry["minutesAsleep"]
    for date, minutes in asleep.items():
        daily[date]["sleep_duration"] = minutes
    if (fit / "steps.json").exists():
        steps = defaultdict(int)
        for entry in json.loads((fit / "steps.json").read_text(encoding="utf-8")):
            steps[entry["dateTime"][:10]] += int(entry["value"])
        for date, total in steps.items():
            daily[date]["steps"] = total
    if (fit / "sleep_score.csv").exists():
        with open(fit / "sleep_score.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                value = _number(row.get("overall_score"))
                if value is not None:
                    daily[row["timestamp"][:10]].setdefault("sleep_score", value)
    if (pms / "wellness.csv").exists():
        with open(pms / "wellness.csv", newline="", encoding="utf-8") as f:
            for row in csv.DictReader(f):
                for name in WELLNESS:
                    value = _number(row.get(name))
                    if value is not None:
                        daily[row["effective_time_frame"][:10]].setdefault(name, value)
    return dict(sorted(daily.items()))


def _participants(root):
    return sorted(p.name for p in Path(root).iterdir()
                  if p.is_dir() and (p / "fitbit" / "resting_heart_rate.json").exists())


def choose_people(root, n=4):
    """The n participants with the most days of resting HR, then of main sleep (the drift and Anchor
    indicators); ties keep id order. Independent of which optional files (e.g. steps) are present."""
    def coverage(pid):
        daily = read_person(Path(root) / pid)
        return (sum("resting_heart_rate" in v for v in daily.values()),
                sum("sleep_duration" in v for v in daily.values()))
    scores = {pid: coverage(pid) for pid in _participants(root)}
    return sorted(scores, key=lambda pid: (-scores[pid][0], -scores[pid][1], pid))[:n]


def assign_crew(people, seed):
    shuffled = list(people)
    random.Random(seed).shuffle(shuffled)
    return dict(zip(CREW_IDS, shuffled))


def _anchor(daily, days):
    values = defaultdict(list)
    for date in sorted(daily)[:days]:
        for name, value in daily[date].items():
            values[name].append(value)
    return {name: {"mean": statistics.fmean(vals), "sd": statistics.stdev(vals)}
            for name, vals in values.items() if len(vals) >= 2}


def _events(crew, daily, start, planted):
    events = []
    for date, values in daily.items():
        t = (parse_date(date) - start).days * DAY + READ_AT
        for name, (unit, source) in INDICATORS.items():
            if name not in values:
                continue
            value, src = values[name], source
            if (date, name) in planted:
                value, src = planted[(date, name)], "sim"
            events.append({"t": t, "type": "reading", "payload": {
                "crew": crew, "indicator": name, "value": value, "unit": unit, "t": t,
                "source": src, "confidence": 1, "state": "released"}})
    return events


def _plant_drift(daily):
    dates = [d for d in daily if "resting_heart_rate" in daily[d]][-DRIFT["days"]:]
    planted = {}
    for i, date in enumerate(dates, start=1):
        share = i / DRIFT["days"]
        for name in ("resting_heart_rate", "sleep_duration"):
            if name in daily[date]:
                planted[(date, name)] = max(0.0, daily[date][name] + DRIFT[name] * share)  # sleep cannot be negative
    return planted


def build_all(root, seed=1, sexes=None, n=4, anchor_days=14, profile="mars_transit"):
    root = Path(root)
    chosen = choose_people(root, n=n)
    mapping = assign_crew(chosen, seed)
    data = {crew: read_person(root / pid) for crew, pid in mapping.items()}
    start = min(parse_date(min(d)) for d in data.values())
    sexes = sexes or {}
    replays, records = {}, []
    for crew, pid in mapping.items():
        if pid not in sexes:
            raise ValueError(f"No sex given for {pid} (crew {crew}); pass --sex or --overview")
        planted = _plant_drift(data[crew]) if crew == DRIFT["crew"] else {}
        replays[crew] = {"schema_version": SCHEMA_VERSION, "crew": crew, "profile": profile,
                         "events": _events(crew, data[crew], start, planted)}
        records.append({"schema_version": SCHEMA_VERSION, "id": crew, "sex": sexes[pid],
                        "anchor": _anchor(data[crew], anchor_days), "missionProfile": profile})
    b_last = (parse_date(max(data["B"])) - start).days
    source = {
        "dataset": "PMData (Simula Metropolitan Center), https://datasets.simula.no/pmdata/ , files from https://osf.io/vx4bk",
        "licence": "CC BY 4.0",
        "licence_url": "https://creativecommons.org/licenses/by/4.0/",
        "citation": "Thambawita V. et al., PMData: A Sports Logging Dataset, MMSys '20, doi:10.1145/3339825.3394926",
        "changes": "Daily values reshaped into StellarForge Readings; crew A has a planted drift.",
        "seed": seed, "mapping": mapping, "start_date": start.isoformat(), "anchor_days": anchor_days,
        "planted_drift": dict(DRIFT, shape="linear ramp over the last 9 days with a resting HR", source="sim"),
        "emergency_offset_suggestion": (b_last + 1) * DAY,
        "notes": NOTES,
    }
    return {"replays": replays, "crew_records": records, "mapping": mapping, "start_date": start.isoformat(),
            "source": source}


def read_overview_sexes(path):
    """participant id -> 'male'/'female' from PMData's participant-overview.xlsx (stdlib only)."""
    ns = {"m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
    with zipfile.ZipFile(path) as z:
        strings = []
        if "xl/sharedStrings.xml" in z.namelist():
            for si in ElementTree.fromstring(z.read("xl/sharedStrings.xml")).findall("m:si", ns):
                strings.append("".join(t.text or "" for t in si.iter(f"{{{ns['m']}}}t")))
        sheet = ElementTree.fromstring(z.read("xl/worksheets/sheet1.xml"))
    rows = []
    for row in sheet.iter(f"{{{ns['m']}}}row"):
        cells = []
        for c in row.findall("m:c", ns):
            v = c.find("m:v", ns)
            text = "" if v is None else (strings[int(v.text)] if c.get("t") == "s" else v.text)
            cells.append(text.strip())
        rows.append(cells)
    out = {}
    for cells in rows:
        pid = next((c.lower() for c in cells if re.fullmatch(r"p\d\d", c.lower())), None)
        sex = next((c.lower() for c in cells if c.lower() in ("male", "female")), None)
        if pid and sex:
            out[pid] = sex
    return out


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--pmdata", default=str(ROOT / "data" / "pmdata"))
    parser.add_argument("--out-dir", default=str(ROOT / "replay" / "generated"))
    parser.add_argument("--seed", type=int, default=1)
    parser.add_argument("--sex", help="p01=male,p02=female,...")
    parser.add_argument("--overview", help="PMData participant-overview.xlsx")
    args = parser.parse_args(argv)
    sexes = {}
    if args.overview:
        sexes.update(read_overview_sexes(args.overview))
    if args.sex:
        sexes.update(dict(item.split("=") for item in args.sex.split(",")))
    out = build_all(args.pmdata, seed=args.seed, sexes=sexes)
    sys.path.insert(0, str(ROOT / "contracts"))
    from validate import validate
    for replay in out["replays"].values():
        validate("ReplayFile", replay)
    for record in out["crew_records"]:
        validate("CrewRecord", record)
    dest = Path(args.out_dir)
    dest.mkdir(parents=True, exist_ok=True)
    for crew, replay in out["replays"].items():
        (dest / f"crew-{crew}.json").write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
    (dest / "crew-records.json").write_text(json.dumps(out["crew_records"], indent=2), encoding="utf-8")
    counts = {crew: len(r["events"]) for crew, r in out["replays"].items()}
    (dest / "crew-replays.source.json").write_text(json.dumps(dict(out["source"], readings=counts), indent=2),
                                                   encoding="utf-8")
    print(f"Wrote crew A-D to {dest} (readings {counts}; mapping {out['mapping']})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
