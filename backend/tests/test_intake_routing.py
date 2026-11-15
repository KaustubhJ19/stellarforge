"""Intent-first routing in the flow engine (docs/spec-intent-routing.md): intake, route, override, not-covered."""
import pytest

from app import triage
from app.flow import FlowError
from app.runtime import REAL_RECORDS, build
from sf_helpers import alert, trig

CHEST = dict(responsive="yes", breathing="normal", main_problem="chest_pain")
ARREST = dict(responsive="no", breathing="none", main_problem="collapse")
INJURY = dict(responsive="yes", breathing="normal", main_problem="injury")


@pytest.fixture
def reng():
    return build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS,
                 explainer=None, routing=True)


def alarmed(eng, patient="A", rescuer="B", kind="manual"):
    """Patient does not answer, the alarm rings, `rescuer` accepts and answers the observer question."""
    eng.trigger(trig(patient, kind=kind))
    eng.clock.advance(16)
    eng.tick()
    eng.accept(rescuer)
    if eng.view(rescuer)["screen"] == "observer":
        eng.observer_answer(rescuer, "no")
    return eng.active_for(patient)


def step_ids(eng, crew):
    seen = []
    while (v := eng.view(crew))["screen"] == "step":
        seen.append(v["step"]["id"])
        eng.next(crew)
    return seen, v


def to_steps(eng, crew):
    while (v := eng.view(crew))["screen"] in ("record", "contributors"):
        if v["screen"] == "contributors" and v["choice"] is None:  # ticket 05: a choice is required before the steps
            eng.copilot_choice(crew, "router")
        eng.next(crew)


def test_intake_screen_comes_before_the_record(reng):
    alarmed(reng)
    v = reng.view("B")
    assert v["screen"] == "intake"
    assert v["fields"]["main_problem"] == list(triage.INTAKE_VALUES["main_problem"])
    assert v["disclaimer"]


def test_arrest_answers_route_to_cpr_steps(reng):
    alarmed(reng)
    reng.submit_intake("B", ARREST)
    assert reng.view("B")["route"]["protocol_id"] == "microgravity-cpr"
    to_steps(reng, "B")
    assert reng.view("B")["step"]["id"] == "cpr-1-start"


def test_chest_pain_answers_route_to_the_chest_pain_protocol(reng):
    alarmed(reng)
    reng.submit_intake("B", CHEST)
    v = reng.view("B")
    assert v["route"] == {"protocol_id": "chest-pain", "rule_id": "chest-pain-responsive",
                          "reason": v["route"]["reason"]}
    to_steps(reng, "B")
    seen, last = step_ids(reng, "B")
    assert seen and all(s.startswith("cp-") for s in seen)
    assert last["screen"] == "report"


def test_not_covered_shows_no_steps_but_keeps_contributors_and_report(reng):
    reng.ingest_alert(alert("A", causes=("STUB cause 1", "STUB cause 2")))
    alarmed(reng)
    reng.submit_intake("B", INJURY)
    assert reng.view("B")["screen"] == "record"
    reng.next("B")
    v = reng.view("B")
    assert v["screen"] == "contributors" and v["route"]["protocol_id"] is None and v["causes"]
    reng.copilot_choice("B", "router")
    reng.next("B")
    v = reng.view("B")
    assert v["screen"] == "report"
    assert v["route"]["rule_id"] == "no-match"


def test_cabin_alert_routes_to_the_approved_cabin_air_protocol(reng):
    """Was "not covered until a cited protocol exists"; cabin-air was approved 2026-11-15 (Spec 1)."""
    alarmed(reng)
    reng.submit_intake("B", dict(responsive="yes", breathing="normal", main_problem="cabin_alert"))
    assert reng.view("B")["route"]["protocol_id"] == "cabin-air"
    to_steps(reng, "B")
    assert reng.view("B")["step"]["id"] == "air-1-check"


def test_auto_trigger_skips_the_questions_and_uses_cpr(reng):
    alarmed(reng, kind="auto")
    v = reng.view("B")
    assert v["screen"] == "record"  # no intake screen
    assert v["route"]["rule_id"] == "auto-trigger"
    to_steps(reng, "B")
    assert reng.view("B")["step"]["id"] == "cpr-1-start"


def test_intake_is_refused_out_of_turn_and_when_invalid(reng):
    alarmed(reng)
    with pytest.raises(triage.IntakeError):
        reng.submit_intake("B", dict(CHEST, breathing="loud"))
    with pytest.raises(FlowError):
        reng.submit_intake("C", CHEST)  # not a rescuer
    with pytest.raises(FlowError):
        reng.submit_intake("A", CHEST)  # the patient does not triage themselves
    reng.submit_intake("B", CHEST)
    with pytest.raises(FlowError):
        reng.submit_intake("B", ARREST)  # already submitted: use the override instead


def test_override_switches_protocol_and_is_logged_with_the_actor(reng):
    e = alarmed(reng)
    reng.submit_intake("B", CHEST)
    reng.switch_protocol("B", "microgravity-cpr")
    assert reng.view("B")["route"]["protocol_id"] == "microgravity-cpr"
    assert reng.view("B")["route"]["rule_id"] == "override"
    to_steps(reng, "B")
    assert reng.view("B")["step"]["id"] == "cpr-1-start"
    entry = next(t for t in e.timeline if t["event"] == "protocol switched")
    assert entry["by"] == "B" and entry["from"] == "chest-pain" and entry["to"] == "microgravity-cpr"
    assert any(ev["type"] == "protocol_switched" for ev in reng.events)


def test_override_can_rescue_a_not_covered_result(reng):
    alarmed(reng)
    reng.submit_intake("B", INJURY)
    reng.switch_protocol("B", "chest-pain")
    to_steps(reng, "B")
    assert reng.view("B")["step"]["id"].startswith("cp-")


def test_override_refuses_unknown_protocols_and_non_rescuers(reng):
    alarmed(reng)
    reng.submit_intake("B", CHEST)
    with pytest.raises(FlowError):
        reng.switch_protocol("B", "made-up")
    with pytest.raises(FlowError):
        reng.switch_protocol("C", "microgravity-cpr")


def test_ground_report_names_the_protocol_the_rule_and_the_answers(reng):
    alarmed(reng)
    reng.submit_intake("B", CHEST)
    summary = reng.ground.build(reng.active_for("A"))["summary"]
    assert "chest-pain" in summary and "chest-pain-responsive" in summary and "chest_pain" in summary


def test_report_in_flight_to_ground_carries_the_route_but_not_after_it_arrives(reng):
    e = alarmed(reng)  # the report is sent at the alarm, before anyone answers the intake
    reng.submit_intake("B", CHEST)
    sent = reng.ground.state[e.id]["snapshot"]
    assert "chest-pain-responsive" in sent["summary"] and "chest_pain" in sent["summary"]
    reng.clock.advance(reng.ground.one_way + 1)  # now it has reached ground: frozen
    reng.switch_protocol("B", "microgravity-cpr")
    assert "chest-pain-responsive" in reng.ground.state[e.id]["snapshot"]["summary"]
    assert "override" in reng.ground.build(e)["summary"]  # the crew copy stays live


def test_report_in_flight_lists_the_override_in_its_timeline(reng):
    e = alarmed(reng)
    reng.submit_intake("B", CHEST)
    reng.switch_protocol("B", "microgravity-cpr")
    events = [t["event"] for t in reng.ground.state[e.id]["snapshot"]["timeline"]]
    assert "protocol switched" in events


def test_override_before_the_intake_is_refused(reng):
    alarmed(reng)
    with pytest.raises(FlowError):
        reng.switch_protocol("B", "chest-pain")


def test_switching_back_replays_the_steps_of_that_protocol(reng):
    alarmed(reng)
    reng.submit_intake("B", CHEST)
    to_steps(reng, "B")
    first = reng.view("B")["step"]["id"]
    reng.next("B")
    assert reng.view("B")["step"]["id"] != first
    reng.switch_protocol("B", "microgravity-cpr")
    reng.switch_protocol("B", "chest-pain")
    assert reng.view("B")["step"]["id"] == first


def test_explainer_uses_the_protocol_of_the_emergency(reng):
    alarmed(reng)
    reng.submit_intake("B", CHEST)
    to_steps(reng, "B")
    out = reng.explainer.explain("B")
    assert out["step"].startswith("cp-")


def test_offline_bundle_carries_every_protocol_and_the_route_table(reng):
    from app import offline
    b = offline.bundle(reng)
    assert {"microgravity-cpr", "chest-pain"} <= set(b["protocols"])
    assert b["routes"]["rows"] and b["intake_fields"]["responsive"] == ["yes", "no"]
    assert b["protocol"]["id"] == "microgravity-cpr"  # existing key kept for current tablets


def test_default_build_has_no_routing(eng):
    eng.trigger(trig("cmdr"))
    eng.clock.advance(16)
    eng.tick()
    eng.accept("eng")
    eng.observer_answer("eng", "no")
    assert eng.view("eng")["screen"] == "record"  # unchanged behaviour without routing


def test_api_intake_and_switch(reng):
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(reng, ticker=False)) as c:
        alarmed(reng)
        assert c.get("/api/view", params={"crew": "B"}).json()["screen"] == "intake"
        bad = c.post("/api/intake", json={"crew": "B", "intake": dict(CHEST, breathing="loud")})
        assert bad.status_code == 422
        ok = c.post("/api/intake", json={"crew": "B", "intake": CHEST})
        assert ok.status_code == 200 and ok.json()["route"]["protocol_id"] == "chest-pain"
        sw = c.post("/api/switch-protocol", json={"crew": "B", "protocol": "microgravity-cpr"})
        assert sw.status_code == 200 and sw.json()["route"]["rule_id"] == "override"
        assert c.post("/api/switch-protocol", json={"crew": "B", "protocol": "nope"}).status_code == 409
