"""Tickets 03, 04, 06, 07, 09: Baseline A core, before the Spec 1 contracts exist.

Readings go in one at a time (indicator, value, unit, t in seconds); Alerts, Reading states,
Status and the briefing text come out. The golden replay tests are added once Spec 1's
crew replays exist; these use a synthetic crew member with a known planted change.
"""
import numpy as np
import pytest

from backend.baseline_a import BaselineA, Thresholds, briefing, status, urgency

DAY = 86_400.0
ANCHOR = {"resting_hr": {"mean": 60.0, "sd": 2.0}}
# Test values only; the real ones are team values kept in content/.
TH = Thresholds(cusum_k=0.5, drift_amber=5.0, drift_red=10.0, acute_amber=3.5, acute_red=4.5, min_window=7)


def crew(expected_shift=None) -> BaselineA:
    return BaselineA("C001", ANCHOR, TH, expected_shift or {})


def feed(a, values, start=0, tag=None):
    out = []
    for i, v in enumerate(values):
        out.append(a.process("resting_hr", v, "bpm", (start + i) * DAY))
        if tag:
            a.label(tag, (start + i) * DAY + 1)
    return out


def normal_days(n, seed=0):
    return list(60 + np.random.default_rng(seed).normal(0, 1.5, n))


def alerts(out, kind=None):
    return [al for o in out for al in o["alerts"] if kind in (None, al["kind"])]


# --- Ticket 03: Drift alert from the Anchor -------------------------------------------------

def test_planted_drift_raises_a_drift_alert_before_the_emergency():
    drift = [v + 0.3 * i for i, v in enumerate(normal_days(40, seed=1))]  # +0.3 bpm a day from day 60
    found = alerts(feed(crew(), normal_days(60) + drift), "drift")
    assert found, "no drift alert"
    assert 60 < found[0]["t"] / DAY < 100  # emergency at day 100
    assert (found[0]["crew"], found[0]["indicator"]) == ("C001", "resting_hr")
    assert {"sigma", "cusum"} <= set(found[0]["deviation"])
    assert [al["status"] for al in found][:2] == ["amber", "red"]


def test_normal_days_raise_no_alert():
    assert not alerts(feed(crew(), normal_days(120, seed=3)))


def test_expected_space_shift_is_not_a_drift():
    assert not alerts(feed(crew({"resting_hr": 8.0}), [v + 8 for v in normal_days(90, seed=4)]), "drift")


# --- Ticket 04: Acute alert from the 28-day Adaptive baseline -----------------------------

def test_sudden_jump_raises_a_red_acute_alert_at_once():
    out = feed(crew(), normal_days(40) + [85.0])
    acute = alerts(out[-1:], "acute")
    assert acute and acute[0]["status"] == "red" and acute[0]["t"] == 40 * DAY


def test_adaptive_baseline_forgets_after_28_days():
    a = crew()
    feed(a, normal_days(40))
    feed(a, [v + 5 for v in normal_days(30, seed=5)], start=40, tag="normal")  # crew says the new level is normal
    assert a.adaptive_mean("resting_hr") == pytest.approx(65, abs=1.0)


# --- Ticket 07: Quarantine -----------------------------------------------------------------

def test_readings_during_an_open_alert_are_held_and_never_update_the_baseline():
    a = crew()
    feed(a, normal_days(40))
    out = [a.process("resting_hr", v, "bpm", 40 * DAY + h * 3600) for h, v in ((0, 85.0), (2, 84.0))]
    assert [o["state"] for o in out] == ["quarantined", "quarantined"]
    assert a.adaptive_mean("resting_hr") < 61  # 85 and 84 are not in the baseline


def test_false_alarm_tag_releases_held_readings_into_the_baseline():
    a = crew()
    feed(a, normal_days(40))
    before = a.adaptive_mean("resting_hr")
    feed(a, [85.0], start=40)
    released = a.label("false alarm", 40.5 * DAY)
    assert [r["state"] for r in released] == ["released"]
    assert a.adaptive_mean("resting_hr") > before
    assert feed(a, [60.0], start=41)[0]["state"] == "released"


def test_held_readings_are_released_after_24_hours_without_an_event():
    a = crew()
    feed(a, normal_days(40))
    feed(a, [85.0], start=40)
    out = a.process("resting_hr", 60.0, "bpm", 41 * DAY + 1)
    assert out["state"] == "released"
    assert [r["state"] for r in out["released"]] == ["released"]


def test_confirmed_event_moves_held_readings_to_the_event_store():
    a = crew()
    feed(a, normal_days(40))
    for h, v in ((0, 85.0), (2, 86.0)):
        a.process("resting_hr", v, "bpm", 40 * DAY + h * 3600)
    moved = a.label("confirmed event", 40.5 * DAY)
    assert [r["state"] for r in moved] == ["event", "event"]
    assert [r["value"] for r in a.event_store] == [85.0, 86.0]
    a.process("resting_hr", 60.0, "bpm", 43 * DAY)  # well past 24 h: nothing left to release
    assert a.adaptive_mean("resting_hr") < 61  # 85 and 86 never joined the baseline


# --- Ticket 06: Status and urgency from one rule -------------------------------------------

BOUND = {"indicator": "resting_hr", "low": 40, "high": 100, "label": "Earth reference, no space data", "source": "test"}


@pytest.mark.parametrize("level,value,expected", [
    ("green", 70, "green"), ("amber", 70, "amber"), ("red", 70, "red"),
    ("green", 120, "red"),  # safety limit wins even when the baseline has drifted up to it
    ("amber", 35, "red"),
])
def test_status_is_the_worse_of_baseline_level_and_safety_bound(level, value, expected):
    s = status(level, value, BOUND)
    assert s["status"] == expected
    assert s["text"]  # never colour alone


def test_status_without_a_bound_uses_the_baseline_level():
    assert status("amber", 70, None)["status"] == "amber"


@pytest.mark.parametrize("kind,level,expected", [
    ("emergency", "red", "ACT_NOW"), ("acute", "red", "ESCALATE_TO_GROUND"),
    ("acute", "amber", "MONITOR"), ("drift", "amber", "MONITOR"), (None, "green", "ROUTINE"),
])
def test_urgency_rule(kind, level, expected):
    assert urgency(kind, level) == expected


def test_alerts_carry_the_alert_contract_fields():
    al = alerts(feed(crew(), normal_days(40) + [85.0])[-1:], "acute")[0]
    assert al["urgency"] == "ESCALATE_TO_GROUND"
    assert set(al) == {"id", "kind", "crew", "indicator", "deviation", "status", "urgency", "likely_causes", "t"}


# --- Ticket 09: Daily briefing text ----------------------------------------------------------

def test_briefing_names_the_drifting_indicator_with_size_and_duration():
    a = crew()
    feed(a, [60.0] * 60 + [66.0] * 9)  # flat normal days: with noise the start date is only approximate
    assert "resting hr +6 bpm over 9 days" in briefing(a)


def test_briefing_on_a_normal_day_says_so():
    a = crew()
    feed(a, normal_days(30))
    assert briefing(a) == ["All indicators within your normal."]


# --- Clearing a Status (Spec 2 request): a green Alert when a tier returns to green ----------

def test_return_to_green_sends_one_green_routine_alert_that_holds_nothing():
    out = feed(crew(), normal_days(30) + [80.0, 60.0, 60.5])
    cleared = [al for al in alerts(out[31:], "acute") if al["status"] == "green"]
    assert len(cleared) == 1 and cleared[0]["urgency"] == "ROUTINE" and cleared[0]["t"] == 31 * DAY
    assert out[31]["state"] == out[32]["state"] == "released"  # a green Alert is no reason to hold


def test_no_green_alert_without_an_earlier_alert():
    assert not [al for al in alerts(feed(crew(), normal_days(60, seed=5))) if al["status"] == "green"]
