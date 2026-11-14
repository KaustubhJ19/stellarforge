"""Ticket 15: the real chain — Spec 1 habitat service + Spec 3 detection -> Spec 4 flow.

Only the sensor input is simulated (one Reading posted to the service, labelled as a test
double); the service, detection, adapter and flow are the teams' real code.
"""
import json
import socket
import sys
import threading
import time
from pathlib import Path

import httpx
import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO))
sys.path.insert(0, str(REPO / "backend"))
from backend.detection import Detection, load_content  # noqa: E402  (Spec 3)
from service import HabitatService, make_server  # noqa: E402  (Spec 1, with the Spec 3 hook applied)

from app.runtime import build  # noqa: E402

RECORDS_FILES = [REPO / "frontend/src/fixtures/crew-records.json", REPO / "replay/stub-crew-records-CD.json"]
SV = "1.0.0"


def records():
    out = []
    for p in RECORDS_FILES:
        d = json.loads(p.read_text(encoding="utf-8"))
        out += d if isinstance(d, list) else d["records"]
    return out


def wait(cond, timeout=8.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def chain(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    crew = records()
    cutoffs, bounds = load_content()
    svc = HabitatService(str(tmp_path / "h.sqlite"), [], crew, detection=Detection(crew, cutoffs, bounds))
    httpd = make_server(svc, port=port, tick_interval=0.05)
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    url = f"http://127.0.0.1:{port}"
    eng = build(explainer=None, profile="stub-mars_transit", habitat_url=url,
                records_path=",".join(str(p) for p in RECORDS_FILES))
    eng.habitat.start()
    assert eng.habitat.connected.wait(5)
    yield svc, url, eng
    eng.habitat.stop()
    httpd.shutdown()
    svc.close()


def test_spec3_detects_arrest_rhythm_and_the_flow_starts_with_its_urgency(chain):
    svc, url, eng = chain
    t = eng.now() + 1
    # Simulated sensor input (test double): one cardiac-rhythm Reading for crew B.
    r = httpx.post(f"{url}/reading", json={"schema_version": SV, "crew": "B", "indicator": "cardiac_rhythm", "value": "VF",
                                           "unit": "rhythm", "t": t, "source": "sim", "confidence": 1.0, "state": "released"})
    assert r.status_code == 200
    assert wait(lambda: eng.active_for("B") is not None), eng.habitat.errors
    trig = next(e for e in eng.events if e["type"] == "trigger")
    assert trig["kind"] == "auto" and trig["crew"] == "B"  # made by Spec 3 detection, not by us
    assert wait(lambda: eng.view("B").get("urgency") == "ACT_NOW"), eng.alerts
    v = eng.view("B")
    assert v["screen"] == "verdict" and v["urgency_label"] == "ACT NOW"
    alert = eng.alerts["B"]
    assert alert["kind"] == "emergency"
    # Spec 3 derives likely causes from the crew's history; this run has none, so it returns
    # none rather than inventing any, and the flow shows its empty message.
    assert all("not diagnosis" in c["note"] for c in alert["likely_causes"])  # Spec 3 wording
    assert len(eng.contributors(eng.active_for("B"))["causes"]) == len(alert["likely_causes"][:3])


def test_manual_trigger_goes_to_the_service_and_spec3_answers_with_an_alert(chain):
    svc, url, eng = chain
    from fastapi.testclient import TestClient
    from app.main import create_app
    with TestClient(create_app(eng, ticker=False)) as client:
        r = client.post("/api/trigger", json={"schema_version": SV, "kind": "manual", "crew": "A", "t": eng.now(), "reason": "Emergency button"})
        assert r.status_code == 201
    # The service echoes the Trigger (de-duplicated by the flow) and detection adds an emergency Alert.
    assert wait(lambda: "A" in eng.alerts), eng.habitat.errors
    assert eng.view("A")["urgency_label"] == "ACT NOW"
    assert len(eng.emergencies) == 1
    assert any(e["type"] == "trigger_duplicate" for e in eng.events)


def test_record_access_is_logged_by_spec1_for_real_crew(chain):
    svc, url, eng = chain
    eng.trigger({"schema_version": SV, "kind": "manual", "crew": "B", "t": eng.now(), "reason": "Help a crewmate (requested by A)"})
    eng.answer("B", "status", "need_help")
    eng.accept("A")
    v = eng.view("A")
    assert v["screen"] == "record" and v["ok"] and v["record"]["id"] == "B" and v["record"]["sex"] == "female"
    assert svc.store.query("access_log", crew="B")[0]["opened_by"] == "A"
