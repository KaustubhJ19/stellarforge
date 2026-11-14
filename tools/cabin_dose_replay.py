"""Cabin and dose replay from the NASA OSDR Environmental Data App (Spec 1 task 1.6).

Reads one EDA mission dashboard page (it embeds the mission's telemetry and radiation
data as JSON) and writes a ReplayFile of Readings plus a source record for traceability.

Only the ISS series are used (cabin temperature, relative humidity, CO2) and the
radiation dose series (GCR, SAA, total, accumulated). Ground-control series are left out.
Values are copied unchanged; missing values are skipped, never filled.
Units come from the EDA chart axis labels; accumulated dose is the running sum of the
daily total dose (EDA tooltip), so its unit is mGy.

t = seconds since the first telemetry sample (+ optional offset). EDA timestamps carry no
time zone; they are treated as UTC.

Usage:
  python tools/cabin_dose_replay.py --fetch RR-1                       # download into data/osdr-eda/, then build
  python tools/cabin_dose_replay.py --input data/osdr-eda/dashboard_RR-1.html
Output (default replay/generated/): iss-cabin-dose-<mission>.json and .source.json
"""
import argparse
import datetime as dt
import hashlib
import json
import re
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
EDA_URL = "https://visualization.osdr.nasa.gov/eda/dashboard_{mission}"
SCHEMA_VERSION = "1.0.0"

# EDA series -> (indicator, unit)
INDICATORS = {
    "temperature_iss": ("cabin_temperature", "degC"),
    "rh_iss": ("cabin_relative_humidity", "%"),
    "co2_iss": ("cabin_co2", "ppm"),
    "gcr": ("radiation_dose_gcr", "mGy/day"),
    "saa": ("radiation_dose_saa", "mGy/day"),
    "total": ("radiation_dose_total", "mGy/day"),
    "accumulated": ("radiation_dose_accumulated", "mGy"),
}
CONFIDENCE = 1  # EDA provides no quality score; see source record note
NOTES = [
    "Values copied unchanged from the EDA; missing values skipped, never filled.",
    "Units from the EDA chart axis labels; accumulated dose is the running sum of daily total dose (EDA tooltip), unit mGy.",
    "EDA timestamps have no time zone; treated as UTC.",
    "confidence = 1 because the EDA gives no quality score; it is not a validated quality measure.",
    "Telemetry is from ISS cabin sensors recorded during this Rodent Research mission; ground-control series excluded.",
]


def parse_dashboard(page):
    """Return {mission, title, link, telemetry, radiation} from an EDA dashboard page."""
    match = re.search(r'<script[^>]*id="data"[^>]*>(.*?)</script>', page, re.S)
    if not match:
        raise ValueError("No embedded EDA data block found")
    data = json.loads(match.group(1))
    return {
        "mission": data["mission"],
        "title": data.get("mission_title"),
        "link": data.get("mission_link"),
        "telemetry": json.loads(data["telemetry_data"]),
        "radiation": json.loads(data["radiation_data"]),
    }


def _parse_time(text):
    fmt = "%Y-%m-%d %H:%M:%S" if " " in text else "%Y-%m-%d"
    return dt.datetime.strptime(text, fmt).replace(tzinfo=dt.timezone.utc)


def _number(value):
    return isinstance(value, (int, float)) and not isinstance(value, bool) and value == value  # excludes NaN


def build_replay(data, crew="habitat", profile="mars_transit", offset=0):
    t0 = _parse_time(data["telemetry"]["time"][0])
    events = []
    for block in ("telemetry", "radiation"):
        series = data[block]
        for i, stamp in enumerate(series["time"]):
            t = (_parse_time(stamp) - t0).total_seconds() + offset
            t = int(t) if t == int(t) else t
            for key, (indicator, unit) in INDICATORS.items():
                if key not in series or not _number(series[key][i]):
                    continue
                payload = {"crew": crew, "indicator": indicator, "value": series[key][i], "unit": unit, "t": t,
                           "source": "sensor", "confidence": CONFIDENCE, "state": "released"}
                events.append({"t": t, "type": "reading", "payload": payload})
    events.sort(key=lambda e: e["t"])  # stable: keeps series order within one time
    return {"schema_version": SCHEMA_VERSION, "crew": crew, "profile": profile, "events": events}


def source_record(data, raw_bytes, url, downloaded):
    return {
        "dataset": "NASA OSDR Environmental Data App (EDA)",
        "mission": data["mission"],
        "mission_title": data.get("title"),
        "mission_link": data.get("link"),
        "url": url,
        "downloaded": downloaded,
        "sha256": hashlib.sha256(raw_bytes).hexdigest(),
        "t0_utc": data["telemetry"]["time"][0],
        "units": {indicator: unit for indicator, unit in INDICATORS.values()},
        "citation": "NASA OSDR Environmental Data App, https://visualization.osdr.nasa.gov/eda/ ; "
                    "radiation data cited as visualization (not a primary dataset).",
        "terms": "https://www.nasa.gov/reference/osdr-help-terms-and-conditions/",
        "notes": NOTES,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    src = parser.add_mutually_exclusive_group(required=True)
    src.add_argument("--input", help="saved EDA dashboard page")
    src.add_argument("--fetch", metavar="MISSION", help="download the EDA dashboard for this mission, e.g. RR-1")
    parser.add_argument("--out-dir", default=str(ROOT / "replay" / "generated"))
    parser.add_argument("--crew", default="habitat")
    parser.add_argument("--profile", default="mars_transit")
    parser.add_argument("--offset", type=float, default=0)
    parser.add_argument("--downloaded", help="download date (YYYY-MM-DD); defaults to today for --fetch")
    args = parser.parse_args(argv)

    if args.fetch:
        url = EDA_URL.format(mission=args.fetch)
        with urllib.request.urlopen(url, timeout=120) as resp:
            raw = resp.read()
        raw_path = ROOT / "data" / "osdr-eda" / f"dashboard_{args.fetch}.html"
        raw_path.parent.mkdir(parents=True, exist_ok=True)
        raw_path.write_bytes(raw)
        downloaded = args.downloaded or dt.date.today().isoformat()
    else:
        raw_path = Path(args.input)
        raw = raw_path.read_bytes()
        downloaded = args.downloaded or "unknown"
    data = parse_dashboard(raw.decode("utf-8"))
    url = EDA_URL.format(mission=data["mission"])

    offset = int(args.offset) if args.offset == int(args.offset) else args.offset
    replay = build_replay(data, crew=args.crew, profile=args.profile, offset=offset)
    sys.path.insert(0, str(ROOT / "contracts"))
    from validate import validate
    validate("ReplayFile", replay)

    out = Path(args.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    stem = f"iss-cabin-dose-{data['mission']}"
    (out / f"{stem}.json").write_text(json.dumps(replay, separators=(",", ":")), encoding="utf-8")
    record = dict(source_record(data, raw, url, downloaded), readings=len(replay["events"]),
                  crew=args.crew, profile=args.profile, offset=offset)
    (out / f"{stem}.source.json").write_text(json.dumps(record, indent=2), encoding="utf-8")
    print(f"Wrote {out / (stem + '.json')} ({len(replay['events'])} readings)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
