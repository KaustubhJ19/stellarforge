"""Collapse Copilot ticket 05: the rescuer's choice and the hash-chained decision record."""
import json
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app.flow import FlowError
from app.main import create_app
from app.runtime import REAL_RECORDS, build
from copilot import record
from sf_helpers import trig

CHEST = dict(responsive="yes", breathing="normal", main_problem="chest_pain")
INJURY = dict(responsive="yes", breathing="normal", main_problem="injury")


@pytest.fixture
def reng():
    return build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                 routing=True)


def routed(eng, answers=CHEST, patient="A", rescuer="B"):
    eng.trigger(trig(patient))
    eng.clock.advance(16)
    eng.tick()
    eng.accept(rescuer)
    if eng.view(rescuer)["screen"] == "observer":
        eng.observer_answer(rescuer, "no")
    eng.submit_intake(rescuer, answers)
    return eng.active_for(patient)


def chain(eng, e):
    return record.chain_of(eng.store.events(), e.id)


def last_choice(eng, e):
    """The async investigator note may land after the choice, so the newest event is not always the choice."""
    return [x for x in chain(eng, e) if x["type"] == "copilot_choice"][-1]


def to_contributors(eng, rescuer="B"):
    eng.next(rescuer)  # record -> contributors
    assert eng.view(rescuer)["screen"] == "contributors"


def test_router_default_is_logged_with_the_actor_and_the_protocol_is_unchanged(reng):
    e = routed(reng)
    before = e.protocol_id
    reng.copilot_choice("B", "router")
    last = last_choice(reng, e)
    assert (last["type"], last["kind"], last["by"], last["protocol_id"]) == ("copilot_choice", "router", "B", before)
    assert e.protocol_id == before and not [x for x in reng.events if x["type"] == "protocol_switched"]


def test_other_protocol_uses_the_override_and_logs_the_actor(reng):
    e = routed(reng)
    reng.copilot_choice("B", "other", "microgravity-cpr")
    assert e.protocol_id == "microgravity-cpr"
    sw = next(x for x in reng.events if x["type"] == "protocol_switched")
    assert sw["crew"] == "B" and sw["to"] == "microgravity-cpr"
    assert last_choice(reng, e)["kind"] == "other" and last_choice(reng, e)["by"] == "B"


def test_the_existing_override_control_counts_as_the_choice(reng):
    e = routed(reng)
    reng.switch_protocol("B", "microgravity-cpr")
    assert e.choice["kind"] == "other" and last_choice(reng, e)["kind"] == "other"


def test_suggestion_switches_through_the_override_and_is_refused_when_there_is_none(reng):
    e = routed(reng)
    with pytest.raises(FlowError, match="no suggestion"):
        reng.copilot_choice("B", "suggestion")
    e.copilot = replace(e.copilot, suggested_protocol="microgravity-cpr")
    reng.copilot_choice("B", "suggestion")
    assert e.protocol_id == "microgravity-cpr" and e.choice["kind"] == "suggestion"
    assert reng.view("B")["suggestion"]["protocol_id"] == "microgravity-cpr"


def test_none_is_accepted_and_leaves_the_router_pick(reng):
    e = routed(reng)
    before = e.protocol_id
    reng.copilot_choice("B", "none")
    assert e.choice["kind"] == "none" and e.protocol_id == before
    to_contributors(reng)
    reng.next("B")  # allowed now


def test_proceeding_to_the_steps_without_a_choice_is_refused(reng):
    routed(reng)
    to_contributors(reng)
    with pytest.raises(FlowError, match="choose"):
        reng.next("B")
    assert reng.view("B")["screen"] == "contributors" and reng.view("B")["choice"] is None


def test_a_choice_is_refused_before_the_intake_and_for_a_bad_kind_or_non_rescuer(reng):
    reng.trigger(trig("A"))
    reng.clock.advance(16)
    reng.tick()
    reng.accept("B")
    with pytest.raises(FlowError):
        reng.copilot_choice("B", "router")
    e = reng.active_for("A")
    reng.observer_answer("B", "no")
    reng.submit_intake("B", CHEST)
    with pytest.raises(FlowError, match="unknown choice"):
        reng.copilot_choice("B", "maybe")
    with pytest.raises(FlowError, match="only a rescuer"):
        reng.copilot_choice("C", "router")
    assert e.choice is None


def test_record_holds_trigger_verdict_hash_versions_briefing_choice_and_time(reng):
    e = routed(reng)
    reng.clock.advance(3)
    reng.copilot_choice("B", "router")
    first, *_, last = chain(reng, e)
    assert first["type"] == "copilot_assessment" and first["prev"] == record.GENESIS
    assert first["trigger"]["kind"] == "manual" and first["l0"]["rule_id"] and "history_sha256" in first
    assert first["versions"]["routes_sha256"] and first["versions"]["model"] and first["briefing"]["text"]
    assert last["type"] == "copilot_choice" and last["t"] == reng.now()
    assert all(x["type"].startswith("copilot_") for x in chain(reng, e))


def test_copilot_events_share_the_one_store_and_timeline(reng):
    e = routed(reng)
    reng.copilot_choice("B", "router")
    stored = reng.store.events()
    assert [x for x in stored if x["type"] == "copilot_choice"] and [x for x in stored if x["type"] == "routed"]
    assert any(n["event"] == "copilot choice" for n in e.timeline)


def test_chain_verifies_and_chains_are_per_emergency(reng):
    e = routed(reng)
    reng.copilot_choice("B", "none")
    assert reng.verify_copilot(e.id).ok
    assert all(b["prev"] == record.digest(a) for a, b in zip(chain(reng, e), chain(reng, e)[1:]))


@pytest.mark.parametrize("which", [0, 1, -1])
def test_editing_any_stored_event_makes_verification_fail(reng, which):
    e = routed(reng)
    reng.copilot_choice("B", "router")
    stored = reng.store.events()
    idx = [i for i, x in enumerate(stored) if x.get("type", "").startswith("copilot_")][which]
    row = stored[idx]
    row = {**row, "t": row["t"] + 1} if which == 0 else {**row, "protocol_id": "forged", "kind": "forged"}
    reng.store._db.execute("UPDATE events SET data=? WHERE id=?", (json.dumps(row), idx + 1))
    result = reng.verify_copilot(e.id)
    assert not result.ok and result.reason


def test_removing_a_stored_event_makes_verification_fail(reng):
    e = routed(reng)
    reng.copilot_choice("B", "router")
    stored = reng.store.events()
    first = next(i for i, x in enumerate(stored) if x.get("type") == "copilot_assessment")
    reng.store._db.execute("DELETE FROM events WHERE id=?", (first + 1,))
    assert not reng.verify_copilot(e.id).ok


def test_verify_without_a_head_cannot_see_an_edit_to_the_last_event_but_with_the_head_it_does():
    a = {"type": "copilot_x", "emergency": "e", "prev": record.GENESIS}
    b = {"type": "copilot_x", "emergency": "e", "prev": record.digest(a), "v": 1}
    assert record.verify([a, b]).ok and record.verify([a, b], head=record.digest(b)).ok
    assert not record.verify([a, {**b, "v": 2}], head=record.digest(b)).ok


def test_api_choice_and_gate():
    eng = build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                routing=True)
    with TestClient(create_app(eng, ticker=False)) as c:
        routed(eng)
        eng.next("B")
        assert c.post("/api/next", json={"crew": "B"}).status_code == 409
        bad = c.post("/api/copilot-choice", json={"crew": "B", "choice": "other"})
        assert bad.status_code == 409
        ok = c.post("/api/copilot-choice", json={"crew": "B", "choice": "none"})
        assert ok.status_code == 200 and ok.json()["choice"]["kind"] == "none"
        assert c.post("/api/next", json={"crew": "B"}).status_code == 200


def test_a_life_threat_rule_never_waits_for_a_choice(reng):
    reng.trigger(trig("A", kind="auto", reason="arrest"))
    reng.clock.advance(16)
    reng.tick()
    reng.accept("B")
    if reng.view("B")["screen"] == "observer":
        reng.observer_answer("B", "no")
    assert reng.view("B")["l0"]["life_threat"] is True
    for _ in range(4):  # walk to the first step; the choice is never demanded
        if reng.view("B")["screen"] not in ("record", "contributors"):
            break
        reng.next("B")
    assert reng.view("B")["choice"] is None
    assert reng.view("B")["screen"] not in ("record", "contributors")
