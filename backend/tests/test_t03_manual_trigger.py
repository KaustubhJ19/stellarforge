"""Ticket 03: manual Emergency trigger -> urgency verdict; golden harness; disclaimer."""
import pytest

from app import replay
from app.flow import DISCLAIMER, NOT_ASSESSED
from sf_helpers import alert

REPO = replay.Path(__file__).resolve().parents[2]


def test_golden_manual_button_opens_verdict(eng):
    replay.run(eng, replay.load(REPO / "replay/stub-manual-emergency.json"))
    assert replay.types(eng)[:1] == ["trigger"]
    trig = next(e for e in eng.events if e["type"] == "trigger")
    assert trig["kind"] == "manual" and trig["crew"] == "cmdr"
    assert replay.screens(eng, "cmdr") == ["verdict"]
    v = eng.view("cmdr")
    assert v["urgency"] is None and v["urgency_label"] == NOT_ASSESSED
    assert v["disclaimer"] == DISCLAIMER


@pytest.mark.parametrize("code,label", [("ACT_NOW", "ACT NOW"), ("ESCALATE_TO_GROUND", "ESCALATE TO GROUND"),
                                        ("MONITOR", "MONITOR"), ("ROUTINE", "ROUTINE")])
def test_verdict_plain_words_from_alert(eng, code, label):
    eng.ingest_alert(alert(urgency=code))
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "button"})
    assert eng.view("cmdr")["urgency_label"] == label


def test_button_works_with_no_sensors_or_readings(eng):
    assert eng.readings == {} and eng.alerts == {}
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "eng", "t": 0, "reason": "button"})
    assert eng.view("eng")["screen"] == "verdict"


def test_duplicate_trigger_does_not_open_second_session(eng):
    a = eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "button"})
    b = eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 1, "reason": "button again"})
    assert a is b and len(eng.emergencies) == 1
    assert "trigger_duplicate" in replay.types(eng)


def test_api_manual_trigger_and_view(client):
    r = client.post("/api/trigger", json={"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 3, "reason": "button"})
    assert r.status_code == 201
    v = client.get("/api/view", params={"crew": "cmdr"}).json()
    assert v["screen"] == "verdict" and v["disclaimer"] == DISCLAIMER


@pytest.mark.parametrize("body", [
    {"schema_version": "1.0.0", "kind": "panic", "crew": "cmdr", "t": 0, "reason": "x"},
    {"schema_version": "1.0.0", "kind": "manual", "t": 0, "reason": "x"},
    {"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "reason": "x"},
    {"schema_version": "1.0.0", "kind": "manual", "crew": "nobody", "t": 0, "reason": "x"},
    {"schema_version": "1.0.0", "kind": "auto", "crew": "cmdr", "t": 0, "reason": "x"},
])
def test_api_rejects_invalid_trigger(client, body):
    r = client.post("/api/trigger", json=body)
    assert r.status_code == 422 and "error" in r.json()
    # still usable afterwards
    assert client.post("/api/trigger", json={"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "x"}).status_code == 201


def test_idle_tablet_has_no_emergency_screen(eng):
    v = eng.view("sci")
    assert v["screen"] == "idle" and "disclaimer" not in v
