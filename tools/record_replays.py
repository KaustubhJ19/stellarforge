"""Record replays: play ReplayFiles through detection (Spec 3) and Forecast B, and write the output back
into each file, so the home screen (Spec 2) can run from files with the service stopped.

Added events, each right after the event that caused it:
  alert, trigger      Alert / Trigger contracts
  reading_state       Reading contract, with its new state (quarantined, released, event)
  forecast            provisional Forecast schema (contracts/provisional/forecast.schema.json)
An added event's t is the time of the event that caused it, so the file stays in time order; a Reading
released later keeps its own time in the payload.

Replays of one crew are played in the order given through one detection, so an emergency replay is
judged against that crew's normal days. Forecasts use a model trained on PMData people other than the
crew's own participant. Status: "estimate, not validated".

Usage (needs the git-ignored PMData download for forecasts; without --pmdata, no forecasts):
  python tools/record_replays.py --pmdata <pmdata/extracted> replay/crew-A.json replay/crew-B.json \
      replay/emergency-crew-B.json replay/crew-C.json replay/crew-D.json
Output: replay/recorded/<input file name>.
"""
import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from backend.detection import Detection, load_content  # noqa: E402
from backend.forecast_b import FEATURES, daily_pairs, forecast, load_pmdata, train  # noqa: E402

DAY = 86_400
NO_LABEL = "estimate, not validated"  # the forecast's own label is empty on a normal day


def record(replays: list[dict], records: list[dict], cutoffs: dict, bounds: list[dict], forecaster=None) -> list[dict]:
    """Recorded copies of the replays; input events are kept unchanged and in order."""
    det, out = Detection(records, cutoffs, bounds), []
    for rp in replays:
        events = []
        for e in rp["events"]:
            events.append(e)
            produced = det.on_message({**e, "payload": {"schema_version": rp["schema_version"], **e["payload"]}})
            if forecaster and e["type"] == "reading":
                produced += forecaster.on_reading(e["payload"])
            events += [{**m, "t": e["t"]} for m in produced]  # the cause's time keeps the file in order
        out.append({**rp, "events": events})
    return out


class CrewForecaster:
    """One forecast per crew per day, once all of that day's FEATURES have arrived."""

    def __init__(self, models: dict, min_days: int, remeasure_width: float, forecast_fn=forecast):
        self.models, self.min_days, self.width, self.fn = models, min_days, remeasure_width, forecast_fn
        self.days: dict[str, dict[int, dict]] = {}

    def on_reading(self, p: dict) -> list[dict]:
        name = "sleep_duration_h" if p["indicator"] == "sleep_duration" else p["indicator"]
        if name not in FEATURES or p["crew"] not in self.models or not isinstance(p["value"], (int, float)):
            return []
        days = self.days.setdefault(p["crew"], {})
        day = int(p["t"] // DAY)
        today = days.setdefault(day, {})
        if len(today) == len(FEATURES):
            return []  # already forecast today
        today[name] = p["value"] / 60 if name == "sleep_duration_h" else p["value"]  # replay sleep is in minutes
        if len(today) < len(FEATURES):
            return []
        history = pd.DataFrame([{**days[d], "target": days[d + 1]["readiness"]} for d in sorted(days)
                                if d < day and len(days[d]) == len(FEATURES) and "readiness" in days.get(d + 1, {})],
                               columns=[*FEATURES, "target"])
        res = self.fn(self.models[p["crew"]], history, pd.Series(today)[FEATURES], self.min_days, self.width)
        payload = {"crew": p["crew"], "t": p["t"], "label": res["label"] or NO_LABEL,
                   **{k: res[k] for k in ("value", "low", "high", "population", "personal_correction", "base")},
                   "drivers": res["drivers"]}
        return [{"t": p["t"], "type": "forecast", "payload": payload}]


def train_models(pmdata: Path, mapping: dict[str, str]) -> dict:
    """Per crew: a model trained without that crew's own PMData participant (as in evaluate_held_out)."""
    pairs = daily_pairs(load_pmdata(pmdata))
    models = {}
    for crew, own in mapping.items():
        rest = sorted(set(pairs["person"]) - {own})
        calib = rest[::4]
        model = train(pairs[pairs.person.isin(set(rest) - set(calib))], pairs[pairs.person.isin(calib)])
        models[crew] = model | {"people": rest}
    return models


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("replays", nargs="+", type=Path)
    ap.add_argument("--records", type=Path, default=ROOT / "replay/crew-records.json")
    ap.add_argument("--pmdata", type=Path, help="PMData extracted folder; forecasts are skipped without it")
    ap.add_argument("--out", type=Path, default=ROOT / "replay/recorded")
    args = ap.parse_args(argv)
    cutoffs, bounds = load_content()
    replays = [json.loads(p.read_text()) for p in args.replays]
    forecaster = None
    if args.pmdata:
        mapping = json.loads((ROOT / "replay/crew-replays.source.json").read_text())["mapping"]
        crews = {rp["crew"] for rp in replays}
        forecaster = CrewForecaster(train_models(args.pmdata, {c: p for c, p in mapping.items() if c in crews}),
                                    cutoffs["forecast_min_days"], cutoffs["forecast_remeasure_width"])
    out = record(replays, json.loads(args.records.read_text()), cutoffs, bounds, forecaster)
    args.out.mkdir(parents=True, exist_ok=True)
    for path, rp in zip(args.replays, out):
        (args.out / path.name).write_text(json.dumps(rp, separators=(",", ":")))
        counts = pd.Series([e["type"] for e in rp["events"]]).value_counts().to_dict()
        print(f"{path.name}: {counts}")


if __name__ == "__main__":
    main()
