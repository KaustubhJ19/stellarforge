"""Golden replays (Spec 3 Seam): a ReplayFile goes into the real habitat service; the Alerts, Triggers and
Reading states that come out are checked at set times. Detection listens like a window
(service.subscribe) until the service hook lands. Cut-offs and Safety bounds come from content/.

Scenarios (one crew each, daily readings at 07:00 Mission time):
  G  calm normal days, then +10 bpm resting heart rate over 9 days, then the emergency button  (03, 08, 09)
  J  normal days, then a sudden jump; the crew tags "false alarm"                              (04, 07)
  K  same jump; the crew confirms an event                                                      (07)
  H  a person whose own normal heart rate is high; one reading crosses the Safety bound         (06)
"""
import json
import re
import sys
from pathlib import Path

from backend.detection import Detection, load_content

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "contracts"))
from service import HabitatService  # noqa: E402
from validate import validate  # noqa: E402

DAY, AM7 = 86_400, 7 * 3_600
NOISE = [0.0, 1.5, -1.5, 0.75, -0.75, 1.0, -1.0]  # fixed day-to-day wobble
CONTRACT = {"alert": "Alert", "trigger": "Trigger", "reading_state": "Reading"}


def record(crew, indicator, mean, sd):
    return {"schema_version": "1.0.0", "id": crew, "sex": "female", "missionProfile": "mars_transit",
            "anchor": {indicator: {"mean": mean, "sd": sd}}}


def reading(crew, indicator, value, unit, day):
    t = day * DAY + AM7
    return {"t": t, "type": "reading", "payload": {"crew": crew, "indicator": indicator, "value": value, "unit": unit,
                                                   "t": t, "source": "sim", "confidence": 0.9, "state": "released"}}


def replay(crew, events):
    return {"schema_version": "1.0.0", "crew": crew, "profile": "mars_transit", "events": events}


def daily(crew, indicator, unit, normal, days):
    return [reading(crew, indicator, normal + NOISE[d % len(NOISE)], unit, d) for d in range(days)]


def play(tmp_path, replays, records, labels=()):
    """Play every replay through the service; labels: (day, crew, note) posted at that Mission time."""
    cutoffs, bounds = load_content()
    det, out = Detection(records, cutoffs, bounds), []
    svc = HabitatService(tmp_path / "golden.sqlite", replays, records)
    svc.subscribe("ground", lambda m: out.extend(det.on_message(m)))
    pending = sorted(labels)
    try:
        while svc.skip() is not None:
            svc.tick()
            now = svc.clock_status()["t"]
            while pending and pending[0][0] * DAY + AM7 <= now:
                day, crew, note = pending.pop(0)
                label = {"crew": crew, "t": day * DAY + AM7 + 60, "note": note}
                svc.post_label(label)
                out.extend(det.on_label(label))
    finally:
        svc.close()
    for m in out:
        validate(CONTRACT[m["type"]], m["payload"])
    return det, out


def alerts(out, crew, kind=None):
    return [m["payload"] for m in out if m["type"] == "alert" and m["payload"]["crew"] == crew
            and kind in (None, m["payload"]["kind"])]


def scenario_g():
    events = daily("G", "resting_heart_rate", "bpm", 60, 60)
    events += [reading("G", "resting_heart_rate", 60 + 10 * (i + 1) / 9 + NOISE[i % 7], "bpm", 60 + i) for i in range(9)]
    t = 70 * DAY + AM7
    events.append({"t": t, "type": "trigger", "payload": {"kind": "manual", "crew": "G", "t": t, "reason": "Emergency button"}})
    return replay("G", events), record("G", "resting_heart_rate", 60, 1.0)


def jump(crew):
    events = daily(crew, "resting_heart_rate", "bpm", 60, 30) + [reading(crew, "resting_heart_rate", 85, "bpm", 30)]
    events += [reading(crew, "resting_heart_rate", 60, "bpm", 30 + d) for d in (1, 2)]
    return replay(crew, events), record(crew, "resting_heart_rate", 60, 1.0)


# --- 03, 08, 09 -------------------------------------------------------------------------------

def test_planted_drift_raises_a_drift_alert_before_the_emergency(tmp_path):
    rp, rec = scenario_g()
    _, out = play(tmp_path, [rp], [rec])
    drift = alerts(out, "G", "drift")
    emergency = alerts(out, "G", "emergency")
    assert drift and emergency
    assert 60 * DAY <= drift[0]["t"] < emergency[0]["t"]
    assert not [a for a in alerts(out, "G") if a["t"] < 60 * DAY]  # no alert on the normal days


def test_likely_causes_appear_after_the_trigger_and_carry_the_label(tmp_path):
    rp, rec = scenario_g()
    _, out = play(tmp_path, [rp], [rec])
    causes = alerts(out, "G", "emergency")[0]["likely_causes"]
    assert causes[0]["indicator"] == "resting_heart_rate" and causes[0]["direction"] == "up"
    assert all("suggestion, not diagnosis" in c["note"] for c in causes)


def test_briefing_names_the_drift_with_size_and_duration(tmp_path):
    rp, rec = scenario_g()
    det, _ = play(tmp_path, [rp], [rec])
    assert any(re.fullmatch(r"resting heart rate \+\d+ bpm over \d+ days", line) for line in det.briefing("G"))


# --- 04, 07 -------------------------------------------------------------------------------------

def test_sudden_jump_raises_an_acute_alert_at_that_time(tmp_path):
    rp, rec = jump("J")
    _, out = play(tmp_path, [rp], [rec])
    acute = alerts(out, "J", "acute")
    assert acute and acute[0]["t"] == 30 * DAY + AM7 and acute[0]["status"] == "red"


def test_false_alarm_tag_releases_the_held_reading(tmp_path):
    rp, rec = jump("J")
    _, out = play(tmp_path, [rp], [rec], labels=[(30, "J", "false alarm")])
    states = [(m["payload"]["t"], m["payload"]["state"]) for m in out if m["type"] == "reading_state"]
    assert (30 * DAY + AM7, "quarantined") in states and (30 * DAY + AM7, "released") in states


def test_held_reading_is_released_after_24_hours_without_an_event(tmp_path):
    rp, rec = jump("J")
    _, out = play(tmp_path, [rp], [rec])
    released = [m["payload"] for m in out if m["type"] == "reading_state" and m["payload"]["state"] == "released"]
    assert released and released[0]["value"] == 85


def test_confirmed_event_moves_held_readings_to_the_event_store(tmp_path):
    rp, rec = jump("K")
    det, out = play(tmp_path, [rp], [rec], labels=[(30, "K", "confirmed event")])
    states = [m["payload"]["state"] for m in out if m["type"] == "reading_state"]
    assert "event" in states and [r["value"] for r in det.baselines["K"].event_store] == [85]
    assert det.baselines["K"].adaptive_mean("resting_heart_rate") < 62  # 85 never joined the baseline


# --- 06 -----------------------------------------------------------------------------------------

def test_safety_limit_turns_red_even_when_the_persons_own_normal_is_high(tmp_path):
    events = daily("H", "heart_rate", "1/min", 140, 30) + [reading("H", "heart_rate", 155, "1/min", 30)]
    _, out = play(tmp_path, [replay("H", events)], [record("H", "heart_rate", 140, 5.0)])
    safety = [a for a in alerts(out, "H") if "bound" in a["deviation"]]  # the baseline may flag it too
    assert len(safety) == 1 and safety[0]["status"] == "red" and safety[0]["t"] == 30 * DAY + AM7
    assert safety[0]["deviation"]["bound"]["label"] == "Earth reference, no space data"
    assert not [a for a in alerts(out, "H") if a["t"] < 30 * DAY]  # 140 is this person's normal: no alert before


def test_content_file_has_a_label_and_source_for_every_value():
    doc = json.loads((ROOT / "content" / "profiles" / "detection-cut-offs.json").read_text())
    for item in doc["cutoffs"] + doc["safety_bounds"]:
        assert item["label"] and item["source"]
