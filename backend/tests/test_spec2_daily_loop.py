"""Spec 2 daily loop through the habitat service: an alert opens a cited plan; a replay where the drift reverses
closes it; one where it does not escalates to ESCALATE_TO_GROUND carrying the plans tried and their results.
"""
import pytest
from spec2_helpers import DAY, of_type, play, reading, record, replay

from validate import validate

FOLLOW_UP_RHR_H = 72  # content/plans/daily-loop.json follow_up_h.resting_heart_rate
LEARNING_LABEL = "learns per person; demonstrated on simulated response, not proven"


def rhr_replay(raise_day=20, back_day=None, days=30, sleep=450):
    ev = []
    for d in range(days):
        up = d >= raise_day and (back_day is None or d < back_day)
        ev.append(reading("A", "resting_heart_rate", 72 if up else 60, "bpm", d * DAY + 7 * 3600))
        ev.append(reading("A", "sleep_duration", sleep, "min", d * DAY + 6 * 3600))
    return replay("A", ev)


def test_a_drift_alert_opens_one_cited_plan_with_a_follow_up(tmp_path):
    _, got = play(tmp_path, [rhr_replay()])
    first_alert = next(m["payload"] for m in of_type(got, "alert") if m["payload"]["indicator"] == "resting_heart_rate")
    plans = [m["payload"] for m in of_type(got, "plan")]
    assert len(plans) == 1, "amber then red on the same indicator is one plan, not two"
    plan = plans[0]
    assert plan["alert_id"] == first_alert["id"] and plan["crew"] == "A" and plan["indicator"] == "resting_heart_rate"
    assert plan["follow_up_due_t"] == pytest.approx(first_alert["t"] + FOLLOW_UP_RHR_H * 3600)
    assert plan["action"] in {"hydration", "sleep-timing", "exercise-countermeasure", "co2-check", "crew-check-in"}
    assert plan["steps"] and all(s["source"]["guideline"] and s["source"]["section"] for s in plan["steps"])
    assert plan["approval"]["status"]  # draft until the team approves (Spec 1 workflow)
    assert plan["learning_label"] == LEARNING_LABEL
    assert plan["label"] == "suggestion, not diagnosis"


def test_the_plan_addresses_the_likely_driver(tmp_path):
    _, got = play(tmp_path, [rhr_replay(sleep=300)])  # 2 h short every night: 360 min debt over 3 days
    plan = of_type(got, "plan")[0]["payload"]
    assert any(d["name"] == "sleep_debt" for d in plan["drivers"])
    assert all(d["label"] == "likely driver: suggestion, not diagnosis" for d in plan["drivers"])


def test_a_drift_that_reverses_closes_the_plan(tmp_path):
    _, got = play(tmp_path, [rhr_replay(raise_day=20, back_day=22)])
    results = [m["payload"] for m in of_type(got, "plan_result")]
    assert [r["result"] for r in results] == ["reversed"]
    assert not [m for m in of_type(got, "alert") if m["payload"]["urgency"] == "ESCALATE_TO_GROUND"]


def test_a_drift_that_does_not_reverse_escalates_to_ground_with_what_was_tried(tmp_path):
    _, got = play(tmp_path, [rhr_replay()])
    plan = of_type(got, "plan")[0]["payload"]
    assert [m["payload"]["result"] for m in of_type(got, "plan_result")] == ["not reversed"]
    esc = [m for m in of_type(got, "alert") if m["payload"]["urgency"] == "ESCALATE_TO_GROUND"]
    assert len(esc) == 1, "one escalation, not one per later reading"
    alert = esc[0]["payload"]
    validate("Alert", alert)
    assert alert["kind"] == "drift" and alert["indicator"] == "resting_heart_rate"
    assert alert["t"] >= plan["follow_up_due_t"]
    tried = alert["escalation"]["plans_tried"]
    assert [(p["plan_id"], p["action"], p["result"]) for p in tried] == [(plan["id"], plan["action"], "not reversed")]
    assert alert["escalation"]["reason"] == "home-side actions failed"
    assert esc[0]["hot_summary"]["crew"] == "A"


def test_learning_happens_per_person(tmp_path):
    """Each crew member has their own bandit: A's failed plan does not change B's choice."""
    svc, _ = play(tmp_path, [rhr_replay()], records=[record("A"), record("B")])
    loop = svc.detection
    assert loop.bandit_state("A")["updates"] == 1
    assert loop.bandit_state("A")["last_reward"] == 0
    assert loop.bandit_state("B")["updates"] == 0
    assert loop.bandit_state("A")["label"] == LEARNING_LABEL
