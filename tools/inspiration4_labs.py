"""Inspiration4 blood values as source = lab Readings (Spec 1 task 1.7).

Source: NASA OSDR study OSD-569, file LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv
(processed, public). Real values from the four de-identified Inspiration4 crew (C001-C004).

"A few" values: five headline complete-blood-count analytes (ANALYTES). Rows labelled
"(FEMALE)" map to the same indicator. Values and units are copied unchanged.
Crew field: "I4-<SUBJECT_ID>" (real astronauts, kept separate from the synthetic crew),
unless --map C001=B assigns a subject to a crew ID.
Time: TEST_DATE L-n = n days before launch; R+n = n days after return; Inspiration4 flew
3 days (launch 16 SEP 21, splashdown 18 SEP 21), so R+n = 3 + n days after launch.
t = 0 at the earliest sample (L-92), readings at 07:00; --offset shifts everything.
The lab's reference ranges (Earth clinical ranges) go into the source record, per sex.

Usage: python tools/inspiration4_labs.py --input data/inspiration4/LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv
Output (default replay/generated/): inspiration4-labs-<crew>.json and inspiration4-labs.source.json
"""
import argparse
import csv
import hashlib
import io
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCHEMA_VERSION = "1.0.0"
DAY = 86400
READ_AT = 7 * 3600
FLIGHT_DAYS = 3
ANALYTES = ("WHITE BLOOD CELL COUNT", "RED BLOOD CELL COUNT", "HEMOGLOBIN", "HEMATOCRIT", "PLATELET COUNT")
NOTES = [
    "Real Inspiration4 crew values (de-identified C001-C004), copied unchanged from OSDR OSD-569 LSDS-7.",
    "R+n is converted with a 3-day flight (launch 16 SEP 21, splashdown 18 SEP 21).",
    "Reference ranges are the testing lab's Earth clinical reference ranges, not space-specific limits.",
    "Readings placed at 07:00 on their test day (team value); confidence = 1 (no per-value quality score given).",
]


def _indicator(analyte):
    return re.sub(r"[^a-z0-9]+", "_", analyte.replace(" (FEMALE)", "").lower()).strip("_")


def _number(text):
    value = float(text)  # ValueError for non-numeric values: fail loudly
    return int(value) if value == int(value) else value


def read_rows(text):
    return list(csv.DictReader(io.StringIO(text.lstrip("﻿"))))


def days_from_launch(label):
    match = re.fullmatch(r"([LR])([+-])(\d+)", label.strip())
    if not match:
        raise ValueError(f"Unknown TEST_DATE {label!r}")
    side, sign, n = match.groups()
    n = int(n) * (1 if sign == "+" else -1)
    return n if side == "L" else FLIGHT_DAYS + n


def _chosen(rows):
    return [r for r in rows if r["ANALYTE"].replace(" (FEMALE)", "") in ANALYTES]


def build_replays(rows, crew_map=None, offset=0, profile="mars_transit"):
    crew_map = crew_map or {}
    chosen = _chosen(rows)
    if not chosen:
        return {}
    first_day = min(days_from_launch(r["TEST_DATE"]) for r in chosen)
    order = {a: i for i, a in enumerate(ANALYTES)}
    events = {}
    for r in sorted(chosen, key=lambda r: (days_from_launch(r["TEST_DATE"]), order[r["ANALYTE"].replace(" (FEMALE)", "")])):
        crew = crew_map.get(r["SUBJECT_ID"], f"I4-{r['SUBJECT_ID']}")
        t = (days_from_launch(r["TEST_DATE"]) - first_day) * DAY + READ_AT + offset
        events.setdefault(crew, []).append({"t": t, "type": "reading", "payload": {
            "crew": crew, "indicator": _indicator(r["ANALYTE"]), "value": _number(r["VALUE"]), "unit": r["UNITS"],
            "t": t, "source": "lab", "confidence": 1, "state": "released"}})
    return {crew: {"schema_version": SCHEMA_VERSION, "crew": crew, "profile": profile, "events": evs}
            for crew, evs in sorted(events.items())}


def source_record(rows, raw_bytes, downloaded):
    ranges = {}  # indicator -> sex -> every distinct range in the file, with how many rows use it
    for r in _chosen(rows):
        found = ranges.setdefault(_indicator(r["ANALYTE"]), {}).setdefault(r["SEX"], [])
        rng = {"min": _number(r["RANGE_MIN"]), "max": _number(r["RANGE_MAX"]), "unit": r["UNITS"]}
        match = next((x for x in found if {k: x[k] for k in rng} == rng), None)
        if match:
            match["rows"] += 1
        else:
            found.append(dict(rng, rows=1))
    inconsistencies = [f"{ind} {sex}: {len(lst)} different reference ranges in the source file"
                       for ind, by_sex in ranges.items() for sex, lst in by_sex.items() if len(lst) > 1]
    return {
        "dataset": "NASA OSDR Inspiration4, Complete Blood Count (processed, public)",
        "study": "OSD-569",
        "file": "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv",
        "url": "https://osdr.nasa.gov/geode-py/ws/studies/OSD-569/download?source=datamanager&file="
               "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv",
        "paper": "https://pmc.ncbi.nlm.nih.gov/articles/PMC11094041",
        "downloaded": downloaded,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "analytes": list(ANALYTES),
        "launch_day_mapping": {"L-n": "n days before launch", "R+n": f"{FLIGHT_DAYS} + n days after launch"},
        "reference_ranges": ranges,
        "range_inconsistencies": inconsistencies,
        "notes": NOTES,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--input", default=str(ROOT / "data" / "inspiration4" /
                                               "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv"))
    parser.add_argument("--out-dir", default=str(ROOT / "replay" / "generated"))
    parser.add_argument("--map", help="C001=B,C004=C to attach subjects to crew ids")
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--downloaded", default="unknown")
    args = parser.parse_args(argv)
    raw = Path(args.input).read_bytes()
    rows = read_rows(raw.decode("utf-8-sig"))
    crew_map = dict(item.split("=") for item in args.map.split(",")) if args.map else {}
    replays = build_replays(rows, crew_map=crew_map, offset=args.offset)
    sys.path.insert(0, str(ROOT / "contracts"))
    from validate import validate
    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    for crew, replay in replays.items():
        validate("ReplayFile", replay)
        (out / f"inspiration4-labs-{crew}.json").write_text(json.dumps(replay, indent=1), encoding="utf-8")
    record = dict(source_record(rows, raw, args.downloaded), map=crew_map, offset=args.offset,
                  readings=sum(len(r["events"]) for r in replays.values()))
    (out / "inspiration4-labs.source.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Wrote {len(replays)} lab replays ({record['readings']} readings) to {out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
