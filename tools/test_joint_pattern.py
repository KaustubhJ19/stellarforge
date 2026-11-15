"""Joint-pattern detector vs today's detector on the shared PMData crew replays (Spec 2 Testing Decisions).

Clean replays -> false alerts per crew-day. Injected combined small drifts (resting heart rate up, sleep down,
mood down; each `size` sd of that crew's first 28 days, ramped in over 7 days from day 60) -> detection day for:
  today:  any non-green drift or acute Alert from Detection (backend/detection.py) on an injected indicator
Only alerts the clean replay does not also raise (same indicator, within a day) count as detections.
  joint:  a non-green Alert with pattern "joint" (backend/joint_anomaly.py, team values in content/plans/daily-loop.json)
Earth wearable data (PMData, CC BY 4.0), injected drifts: a measure of the method, not of astronauts.
Report: PYTHONPATH=. python tools/test_joint_pattern.py
"""
import copy
import json
import statistics
from pathlib import Path

import pytest

from backend.daily_loop import load_values
from backend.detection import Detection, load_content
from backend.joint_anomaly import JointAnomaly

ROOT = Path(__file__).resolve().parents[1]
CREWS = "ABCD"
DAY = 86_400
INJECT = {"resting_heart_rate": +1, "sleep_duration": -1, "mood": -1}
START_DAY, RAMP_DAYS, SIZE = 60, 7, 1.0


def load(crew):
    rp = json.loads((ROOT / "replay" / f"crew-{crew}.json").read_text(encoding="utf-8"))
    rec = next(r for r in json.loads((ROOT / "replay" / "crew-records.json").read_text(encoding="utf-8")) if r["id"] == crew)
    return [{"t": e["t"], "type": e["type"], "payload": {"schema_version": "1.0.0", **e["payload"]}} for e in rp["events"]], rec


def inject(events, size=SIZE, start_day=START_DAY):
    sd = {}
    for ind in INJECT:
        vals = [e["payload"]["value"] for e in events if e["payload"]["indicator"] == ind and e["t"] < 28 * DAY]
        sd[ind] = statistics.stdev(vals)
    out = copy.deepcopy(events)
    for e in out:
        p, day = e["payload"], e["t"] / DAY
        if p["indicator"] in INJECT and day >= start_day:
            p["value"] += INJECT[p["indicator"]] * size * sd[p["indicator"]] * min((day - start_day) / RAMP_DAYS, 1.0)
    return out


def run(events, rec, joint_values=None):
    """(today's Alerts, joint Alerts) as (day, indicator) lists, non-green only."""
    cutoffs, bounds = load_content()
    det = Detection([rec], cutoffs, bounds)
    joint = JointAnomaly([rec["id"]], **(joint_values or load_values()["joint"]))
    today, jt = [], []
    for m in events:
        for out in det.on_message(m):
            a = out["payload"]
            if out["type"] == "alert" and a["status"] != "green" and a["kind"] in ("drift", "acute"):
                today.append((a["t"] / DAY, a["indicator"]))
        for out in joint.on_message(m):
            if out["payload"]["status"] != "green":
                jt.append((out["payload"]["t"] / DAY, out["payload"]["indicator"]))
    return today, jt


def report(joint_values=None, size=SIZE):
    rows, fa_today, fa_joint, crew_days = [], 0, 0, 0
    train = (joint_values or load_values()["joint"])["train_days"]
    for crew in CREWS:
        events, rec = load(crew)
        days = events[-1]["t"] / DAY - train  # joint is silent while learning; count both after training
        today, jt = run(events, rec, joint_values)
        fa_today += sum(d > train for d, _ in today)
        fa_joint += sum(d > train for d, _ in jt)
        crew_days += days
        today_i, jt_i = run(inject(events, size), rec, joint_values)

        def first(alerts, clean, inds):
            """First alert after the start that the clean replay does not also have (same indicator, within 1 day)."""
            new = [d for d, i in alerts if d >= START_DAY and (inds is None or i in inds)
                   and not any(abs(d - dc) <= 1 and (inds is None or i == ic) for dc, ic in clean)]
            return min(new, default=None)
        rows.append({"crew": crew, "today_day": first(today_i, today, set(INJECT)), "joint_day": first(jt_i, jt, None)})
    return {"false_alerts_per_crew_day": {"today": fa_today / crew_days, "joint": fa_joint / crew_days},
            "crew_days": round(crew_days), "detection_day_after_start": [
                {k: (v - START_DAY if isinstance(v, float) else v) for k, v in r.items()} for r in rows]}


@pytest.fixture(scope="module")
def result():
    return report()


def test_joint_false_alerts_stay_rare_on_clean_replays(result):
    fa = result["false_alerts_per_crew_day"]
    assert fa["joint"] <= 0.02  # about one false joint alert per 7 weeks per crew
    assert fa["joint"] * 5 <= fa["today"], fa  # much quieter than today's per-indicator detector


def test_joint_catches_combined_small_drifts_on_most_crews(result):
    rows = result["detection_day_after_start"]
    caught = [r for r in rows if r["joint_day"] is not None and r["joint_day"] <= 21]
    assert len(caught) >= 3, rows


if __name__ == "__main__":
    print(json.dumps(report(), indent=1))
