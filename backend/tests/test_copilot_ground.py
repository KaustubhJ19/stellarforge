"""Collapse Copilot ticket 06: the ground report carries the copilot record; outcome labels join it."""
import json

import pytest
from fastapi.testclient import TestClient

from app import contracts
from app.flow import FlowError
from app.main import create_app
from app.runtime import REAL_RECORDS, build
from copilot import record
from sf_helpers import trig
from test_copilot_record import CHEST, routed


@pytest.fixture
def reng():
    return build(copilot=True, protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                 routing=True)


def arrive(eng):
    eng.clock.advance(eng.ground.one_way + 1)
    eng.tick()


def started(eng):
    e = routed(eng, CHEST)
    eng.copilot_choice("B", "router")
    return e


def test_report_carries_the_chain_with_status_versions_and_timings(reng):
    e = started(reng)
    section = reng.ground.build(e)["copilot"]
    kinds = [ev["type"] for ev in section["events"]]
    assert "copilot_assessment" in kinds and "copilot_choice" in kinds
    assert section["chain"]["ok"] and section["chain"]["length"] == len(kinds)
    assert section["chain"]["head"] == record.digest(e.copilot_last)
    assert section["versions"]["model"] and "choice_after_s" in section["timings"]
    contracts.validate("ground_report", reng.ground.build(e))


def test_existing_report_fields_are_untouched_and_no_copilot_without_a_session(eng):  # routing off: no session
    crew = eng.crew[0]
    eng.trigger(trig(crew))
    eng.clock.advance(16)
    eng.tick()
    rep = eng.ground.build(eng.active_for(crew))
    assert "copilot" not in rep and {"id", "crew", "summary", "history", "timeline", "actions", "sent_t"} <= set(rep)


def test_ground_re_verifies_the_carried_copy_and_catches_an_edit(reng):
    e = started(reng)
    arrive(reng)
    entry = reng.ground.console_view()["reports"][0]
    assert entry["copilot_chain"]["ok"] is True
    forged = json.loads(json.dumps(entry["report"]))
    next(ev for ev in forged["copilot"]["events"] if ev["type"] == "copilot_choice")["kind"] = "none"
    assert not record.check_section(forged["copilot"]).ok
    forged["copilot"]["events"].pop()  # dropping the newest event is caught by the head
    assert not record.check_section(forged["copilot"]).ok
    assert reng.verify_copilot(e.id).ok


def test_investigator_event_is_folded_into_the_chain_and_into_the_report(reng):
    e = started(reng)  # the rescuer view already started the real investigator run (no model: it ends at once)
    reng.investigator.join(e.id)  # wait for its event; adding a second one would race the thread
    section = reng.ground.build(e)["copilot"]
    ran = [ev for ev in section["events"] if ev["type"] == "copilot_investigator"]
    assert len(ran) == 1 and section["timings"]["investigator_elapsed_s"] == ran[0]["elapsed_s"]
    assert section["chain"]["ok"]
    assert reng.verify_copilot(e.id).ok


def test_reply_delivery_joins_the_chain_and_the_label_report_carries_it(reng):
    e = started(reng)
    arrive(reng)
    reng.ground.console_reply(None, "STUB reply")
    reng.clock.advance(reng.ground.one_way + 1)
    reng.tick()
    lb = next(x for x in reng.store.labels() if x["kind"] == "ground_reply")
    kinds = [ev["type"] for ev in lb["report"]["copilot"]["events"]]
    assert "copilot_ground_reply" in kinds and lb["report"]["copilot"]["chain"]["ok"]
    assert "STUB reply" not in json.dumps(lb["report"]["copilot"])  # only its hash is chained
    assert reng.verify_copilot(e.id).ok


def test_outcome_label_is_stored_linked_and_chained(reng):
    e = started(reng)
    arrive(reng)
    out = reng.ground.add_outcome(None, "Recovered, back on duty after rest.")
    lb = next(x for x in reng.store.labels("A") if x["kind"] == "outcome")
    assert (lb["id"], lb["emergency_id"], lb["crew"], lb["text"]) == (out["label"], e.id, "A", "Recovered, back on duty after rest.")
    assert any(ev["type"] == "copilot_outcome_label" and ev["label"] == lb["id"] for ev in lb["report"]["copilot"]["events"])
    assert reng.verify_copilot(e.id).ok
    assert reng.ground.console_view()["reports"][0]["outcomes"][0]["text"] == lb["text"]
    reng.ground.add_outcome(None, "Second note.")
    assert len(reng.ground.console_view()["reports"][0]["outcomes"]) == 2


def test_outcome_label_is_refused_before_arrival_when_empty_or_naming_a_drug(reng):
    started(reng)
    with pytest.raises(FlowError, match="not reached ground"):
        reng.ground.add_outcome(None, "too early")
    arrive(reng)
    with pytest.raises(FlowError, match="empty"):
        reng.ground.add_outcome(None, "   ")
    with pytest.raises(FlowError, match="medication or dose"):
        reng.ground.add_outcome(None, "Gave 500 mg of aspirin.")
    assert not [x for x in reng.store.labels() if x["kind"] == "outcome"]


def test_outcome_endpoint(reng):
    started(reng)
    arrive(reng)
    with TestClient(create_app(reng, ticker=False)) as c:
        assert c.post("/api/console/outcome", json={"text": "Stable."}).status_code == 200
        assert c.post("/api/console/outcome", json={"text": ""}).status_code == 409
        assert [x for x in c.get("/api/labels", params={"crew": "A"}).json() if x["kind"] == "outcome"]
