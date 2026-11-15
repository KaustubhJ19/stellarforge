"""Spec 2: the HotSummary matches a recomputation from full history, and its update is constant time.

Seam: the habitat service plays a real shared crew replay (PMData crew A) merged with the shared synthetic
history (glucose, meals, EVA, locations) and the ISS cabin replay; the snapshot is compared with numbers
recomputed here straight from the replay events with numpy (independent of the running sums).
"""
import time

import numpy as np
import pytest
from spec2_helpers import DAY, ROOT, load, play, replay

from backend.daily_loop import build_loop
from synthetic_history import events as synthetic_events

HOUR = 3600


def merged_replay(days):
    crew = load(ROOT / "replay" / "crew-A.json")
    cabin = load(ROOT / "replay" / "iss-cabin-dose-RR-1.json")
    ev = [e for e in crew["events"] if e["t"] < days * DAY]
    ev += [e for e in cabin["events"] if e["t"] < days * DAY and e["payload"]["indicator"] in ("radiation_dose_total", "cabin_pco2_1h")]
    ev += synthetic_events("A", days)
    return replay("A", ev), ev


def brute_slope(ev, ind, now, span):
    pts = [(e["t"] / DAY, e["payload"]["value"]) for e in ev
           if e["type"] == "reading" and e["payload"]["crew"] == "A" and e["payload"]["indicator"] == ind and e["t"] > now - span]
    if len(pts) < 2 or len({x for x, _ in pts}) < 2:
        return None
    x, y = np.array(pts).T
    return float(np.polyfit(x, y, 1)[0])


def exposure(ev, now, limit=3.0):
    """Piecewise-constant cabin values; A is in the habitat except on EVA (synthetic timeline)."""
    where, rate, above = "habitat", 0.0, False
    last, dose, co2 = None, 0.0, []
    for e in sorted(ev, key=lambda e: e["t"]):
        p = e["payload"]
        changes = (e["type"] == "location" and p["crew"] == "A") or (e["type"] == "reading" and p["crew"] == "habitat"
                                                                     and p["indicator"] in ("radiation_dose_total", "cabin_pco2_1h"))
        if not changes:
            continue
        if last is not None and where == "habitat":
            dose += rate * (e["t"] - last) / DAY
            if above:
                co2.append((e["t"], (e["t"] - last) / HOUR))
        last = e["t"]
        if e["type"] == "location":
            where = p["cabin"]
        elif p["indicator"] == "radiation_dose_total":
            rate = p["value"]
        else:
            above = p["value"] > limit
    if last is not None and where == "habitat":
        dose += rate * (now - last) / DAY
    return dose, sum(h for t, h in co2 if t > now - DAY)


def test_snapshot_matches_recomputation_from_full_history(tmp_path):
    rp, ev = merged_replay(30)
    rec = load(ROOT / "replay" / "crew-records.json")
    svc, _ = play(tmp_path, [rp], records=[r for r in rec if r["id"] == "A"])
    snap = svc.hot_summary("A", requester="A")
    now = max(e["t"] for e in ev)
    assert snap["t"] == now and snap["mission_day"] == int(now // DAY) + 1

    for ind in ("resting_heart_rate", "sleep_duration", "mood", "glucose"):
        for w, span in (("24h", DAY), ("72h", 3 * DAY), ("7d", 7 * DAY)):
            got, want = snap["indicators"][ind]["slope_per_day"][w], brute_slope(ev, ind, now, span)
            assert (got is None) == (want is None), (ind, w)
            if want is not None:
                assert got == pytest.approx(want, rel=1e-6, abs=1e-6), (ind, w)

    sleeps = [e["payload"]["value"] for e in ev if e["type"] == "reading" and e["payload"]["indicator"] == "sleep_duration"
              and e["t"] > now - 3 * DAY]
    assert snap["context"]["sleep_debt_3d_min"] == pytest.approx(sum(max(0, 420 - v) for v in sleeps))

    dose, co2_h = exposure(ev, now)
    assert snap["context"]["dose_mission_mGy"] == pytest.approx(dose, rel=1e-9)
    assert snap["context"]["co2_above_limit_h_24h"] == pytest.approx(co2_h, abs=1e-9)
    assert dose > 0

    evas = [e["payload"]["answers"]["eva_end_t"] for e in ev if e["type"] == "form" and e["payload"]["form"] == "post_eva"]
    assert snap["context"]["hours_since_eva"] == pytest.approx((now - max(evas)) / HOUR)
    meals = [e for e in ev if e["type"] == "form" and e["payload"]["form"] == "meal"]
    assert snap["context"]["last_meal_t"] == meals[-1]["t"]

    a = next(r for r in rec if r["id"] == "A")["anchor"]["resting_heart_rate"]
    last_rhr = snap["indicators"]["resting_heart_rate"]["value"]
    floor = 3  # min_anchor_sd for resting_heart_rate (content/profiles/detection-cut-offs.json)
    assert snap["indicators"]["resting_heart_rate"]["z_anchor"] == pytest.approx((last_rhr - a["mean"]) / max(a["sd"], floor))


def _per_message_seconds(days):
    _, ev = merged_replay(days)
    rec = [r for r in load(ROOT / "replay" / "crew-records.json") if r["id"] == "A"]
    loop = build_loop(rec)
    msgs = [{"t": e["t"], "type": e["type"], "payload": {"schema_version": "1.0.0", **e["payload"]}} for e in ev]
    tail = msgs[-500:]  # time the last messages: with a growing history, constant time means they cost the same
    for m in msgs[:-500]:
        loop.on_message(m)
    start = time.perf_counter()
    for m in tail:
        loop.on_message(m)
        loop.hot_summary("A")
    return (time.perf_counter() - start) / len(tail)


def test_hot_summary_update_is_constant_time_as_history_grows():
    short, long = min(_per_message_seconds(30) for _ in range(3)), min(_per_message_seconds(120) for _ in range(3))
    assert long < 2.5 * short, f"per-message cost grew {long / short:.1f}x for 4x the history"  # both past the joint training days
