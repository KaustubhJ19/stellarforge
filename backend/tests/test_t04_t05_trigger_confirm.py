"""Tickets 04 (auto Trigger, same flow) and 05 (confirm questions, dismissal)."""
import pytest

from app import replay
from app.contracts import ContractError
from app.flow import FlowError
from sf_helpers import alert

REPO = replay.Path(__file__).resolve().parents[2]
MANUAL = {"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "button"}


def run(eng, *events, until=None):
    return replay.run(eng, {"id": "t", "events": list(events)}, until=until)


# ---- 04 ------------------------------------------------------------------
def test_golden_auto_trigger_opens_verdict_without_user_action(eng):
    replay.run(eng, replay.load(REPO / "replay/stub-auto-emergency.json"))
    trig = next(e for e in eng.events if e["type"] == "trigger")
    assert trig["kind"] == "auto"
    assert replay.screens(eng, "cmdr") == ["verdict"]
    assert eng.view("cmdr")["urgency_label"] == "ACT NOW"


def test_auto_and_manual_reach_the_same_first_screen():
    from app.runtime import build
    a, m = build(), build()
    replay.run(a, replay.load(REPO / "replay/stub-auto-emergency.json"))
    replay.run(m, replay.load(REPO / "replay/stub-manual-emergency.json"))
    va, vm = a.view("cmdr"), m.view("cmdr")
    assert va["screen"] == vm["screen"] == "verdict"
    assert va["questions"] == vm["questions"]
    assert set(va) == set(vm)  # same screen shape; only data (urgency) differs


def test_duplicate_auto_trigger_and_mixed_triggers_share_one_flow(eng):
    eng.ingest_alert(alert())
    first = eng.trigger({"schema_version": "1.0.0", "kind": "auto", "crew": "cmdr", "t": 0, "reason": "auto"})
    assert eng.trigger({"schema_version": "1.0.0", "kind": "auto", "crew": "cmdr", "t": 1, "reason": "auto"}) is first
    assert eng.trigger(MANUAL) is first
    assert len(eng.emergencies) == 1
    assert [e["kind"] for e in eng.events if e["type"] == "trigger_duplicate"] == ["auto", "manual"]


def test_auto_trigger_for_unknown_crew_rejected(eng, client):
    with pytest.raises(ContractError):
        eng.trigger({"schema_version": "1.0.0", "kind": "auto", "crew": "ghost", "t": 0, "reason": "x"})
    assert client.post("/api/stream/trigger", json={"schema_version": "1.0.0", "kind": "auto", "crew": "ghost", "t": 0, "reason": "x"}).status_code == 422


def test_stream_endpoints_accept_alert_and_auto_trigger(client):
    assert client.post("/api/stream/alert", json=alert()).status_code == 202
    assert client.post("/api/stream/trigger", json={"schema_version": "1.0.0", "kind": "auto", "crew": "cmdr", "t": 0, "reason": "x"}).status_code == 201
    assert client.get("/api/view", params={"crew": "cmdr"}).json()["urgency_label"] == "ACT NOW"


# ---- 05 ------------------------------------------------------------------
def test_confirm_screen_has_symptom_and_responsiveness_questions(eng):
    eng.trigger(MANUAL)
    qs = eng.view("cmdr")["questions"]
    assert 1 <= len(qs) <= 2 and {q["id"] for q in qs} == {"status", "chest_pain"}


def test_false_alarm_dismissed_with_reason(eng):
    e = eng.trigger(MANUAL)
    eng.answer("cmdr", "status", "false_alarm")
    assert e.status == "dismissed" and e.trigger["confirmed"] is False
    ev = next(x for x in eng.events if x["type"] == "false_alarm_dismissed")
    assert "false alarm" in ev["reason"]
    assert eng.view("cmdr")["screen"] == "idle"
    assert eng.active_for("cmdr") is None  # a new press starts a new emergency
    assert eng.trigger(MANUAL) is not e


def test_need_help_confirms_and_waits_for_a_crewmate_without_alarm(eng):
    e = eng.trigger(MANUAL)
    eng.answer("cmdr", "status", "need_help")
    assert e.trigger["confirmed"] is True and e.status == "help_requested"
    run(eng, until=60)
    assert "crew_alarm" not in replay.types(eng)
    assert eng.view("cmdr")["screen"] == "help_requested"
    assert eng.view("eng")["screen"] == "join" and eng.view("eng")["ring"] is False


def test_chest_pain_is_recorded_as_crew_reported(eng):
    e = eng.trigger(MANUAL)
    eng.answer("cmdr", "chest_pain", "yes")
    assert any(x.get("crew_reported") for x in e.timeline if x["event"] == "patient answer")


def test_no_answer_for_15s_emits_exactly_one_no_answer_event(eng):
    run(eng, {"t": 0, "type": "press_emergency", "data": {"crew": "cmdr"}}, until=40)
    ev = [x for x in eng.events if x["type"] == "no_answer"]
    assert len(ev) == 1 and ev[0]["t"] == 15


def test_answer_at_14_9_s_cancels_timer(eng):
    eng.trigger(MANUAL)
    eng.clock.advance(14.9)
    eng.tick()
    eng.answer("cmdr", "chest_pain", "no")
    eng.clock.advance(10)
    eng.tick()
    assert "no_answer" not in replay.types(eng)


def test_answer_after_alarm_is_recorded_but_does_not_change_flow(eng):
    run(eng, {"t": 0, "type": "press_emergency", "data": {"crew": "cmdr"}}, until=16)
    e = eng.active_for("cmdr")
    eng.answer("cmdr", "status", "false_alarm")
    assert e.status == "alarm"
    assert any(x["type"] == "patient_answer" and x["late"] for x in eng.events)


def test_invalid_answers_rejected(eng):
    eng.trigger(MANUAL)
    with pytest.raises(FlowError):
        eng.answer("cmdr", "status", "maybe")
    with pytest.raises(FlowError):
        eng.answer("eng", "status", "need_help")  # only the patient answers


def test_disclaimer_on_patient_screens(eng):
    eng.trigger(MANUAL)
    eng.answer("cmdr", "status", "need_help")
    for c in ("cmdr", "eng"):
        assert eng.view(c)["disclaimer"] == "Decision support, not diagnosis."
