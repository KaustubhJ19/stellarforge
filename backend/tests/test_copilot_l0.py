"""Collapse Copilot ticket 04: L0 airway rule and the briefing, through the emergency HTTP API."""
import re

import pytest
from fastapi.testclient import TestClient

from app.contracts import validate
from app.main import create_app
from app.runtime import REAL_RECORDS, build
from copilot.fixtures import fake_hot_summary
from sf_helpers import SV, trig

LABEL = "context; the protocol above comes first"
DOSE = re.compile(r"\b\d+\s?(mg|mcg|ml|g|units?)\b|aspirin|epinephrine|adrenaline|nitro|oxygen at", re.I)
BREATHING = {"responsive": "yes", "breathing": "none", "main_problem": "breathing_trouble"}
CHEST = {"responsive": "yes", "breathing": "normal", "main_problem": "chest_pain"}


@pytest.fixture
def api():
    eng = build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                routing=True)
    with TestClient(create_app(eng, ticker=False)) as c:
        c.eng = eng
        yield c


def reading(crew, indicator, value, t=0):
    return {"schema_version": SV, "crew": crew, "indicator": indicator, "value": value, "unit": "fraction", "t": t,
            "source": "sensor", "confidence": 1.0, "state": "released"}


def to_intake(api, patient="A", rescuer="B"):
    assert api.post("/api/trigger", json=trig(patient)).status_code == 201
    api.eng.clock.advance(16)
    api.eng.tick()
    api.post("/api/accept", json={"crew": rescuer})
    api.post("/api/observer", json={"crew": rescuer, "choice": "no"})
    return api.get("/api/view", params={"crew": rescuer}).json()


def intake(api, answers, rescuer="B"):
    return api.post("/api/intake", json={"crew": rescuer, "intake": answers}).json()


def test_briefing_shows_on_the_intake_screen_with_no_history_and_the_context_label(api):
    v = to_intake(api)
    assert v["screen"] == "intake"
    assert v["briefing"]["context_label"] == LABEL
    assert "No history" in v["briefing"]["text"]
    assert v["l0"]["fired"] is False
    validate_briefing(v["briefing"])


def validate_briefing(b):
    import jsonschema, json
    from app.contracts import CONTRACTS
    jsonschema.validate(b, json.loads((CONTRACTS / "provisional" / "briefing.schema.json").read_text()))


def test_no_breathing_fires_the_airway_rule_and_its_protocol_comes_first(api):
    to_intake(api)
    v = intake(api, BREATHING)
    assert v["route"]["rule_id"] == "airway-low-spo2-or-no-breathing"
    assert (v["l0"]["protocol_id"], v["l0"]["life_threat"], v["l0"]["fired"]) == ("cabin-air", True, True)
    assert v["briefing"]["context_label"] == LABEL
    assert "Follow the protocol above first" in v["briefing"]["text"]
    assert v["briefing"]["evidence"][0]["label"]
    assert not DOSE.search(v["briefing"]["text"])
    validate_briefing(v["briefing"])


def test_low_spo2_on_the_live_feed_fires_the_airway_rule_without_intake_help(api):
    api.post("/api/stream/reading", json=reading("A", "spo2", 0.82))
    v = to_intake(api)
    assert v["l0"]["rule_id"] == "airway-low-spo2-or-no-breathing" and v["l0"]["fired"]  # already before the answers
    v = intake(api, CHEST)  # chest pain would route elsewhere; the airway threat comes first
    assert v["route"]["rule_id"] == "airway-low-spo2-or-no-breathing"


def test_normal_spo2_does_not_fire_the_airway_rule(api):
    api.post("/api/stream/reading", json=reading("A", "spo2", 0.975))
    to_intake(api)
    v = intake(api, CHEST)
    assert v["route"]["rule_id"] == "chest-pain-responsive" and v["l0"]["life_threat"] is False


def test_auto_trigger_still_skips_the_questions_and_routes_to_cpr(api):
    assert api.post("/api/stream/trigger", json=trig("A", kind="auto", reason="arrest")).status_code == 201
    api.eng.clock.advance(16)
    api.eng.tick()
    api.post("/api/accept", json={"crew": "B"})
    v = api.get("/api/view", params={"crew": "B"}).json()
    assert v["route"]["protocol_id"] == "microgravity-cpr"
    assert v["l0"]["life_threat"] and v["briefing"]["context_label"] == LABEL


def test_a_pushed_hot_summary_is_reported_without_changing_the_rule_verdict(api):
    api.eng.hot_summaries.update(fake_hot_summary("A"))
    v = to_intake(api)
    assert "History snapshot received" in v["briefing"]["text"]
    assert v["briefing"]["evidence"][-1]["label"].startswith("team value (fake fixture")


def test_the_patient_tablet_gets_no_briefing(api):
    to_intake(api)
    assert "briefing" not in api.get("/api/view", params={"crew": "A"}).json()


def test_routing_off_has_no_briefing():
    eng = build(explainer=None)
    with TestClient(create_app(eng, ticker=False)) as c:
        c.post("/api/trigger", json=trig("A"))
        eng.clock.advance(16)
        eng.tick()
        c.post("/api/accept", json={"crew": "B"})
        assert "briefing" not in c.get("/api/view", params={"crew": "B"}).json()
