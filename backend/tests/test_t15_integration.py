"""Ticket 15: integration with Spec 1's real habitat service (in-process) and Spec 3 Alert shapes."""
import json
import socket
import sys
import time
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(REPO / "backend"))
from service import HabitatService, make_server  # noqa: E402  (Spec 1)

from app.runtime import build  # noqa: E402
from sf_helpers import SV, alert  # noqa: E402

RECORDS = json.loads((REPO / "replay/stub-crew-records.json").read_text(encoding="utf-8"))["records"]


def wait(cond, timeout=5.0):
    end = time.time() + timeout
    while time.time() < end:
        if cond():
            return True
        time.sleep(0.05)
    return False


@pytest.fixture
def habitat(tmp_path):
    with socket.socket() as s:
        s.bind(("127.0.0.1", 0))
        port = s.getsockname()[1]
    replay = {"schema_version": SV, "crew": "cmdr", "profile": "stub-mars", "events": [
        {"t": 120, "type": "reading", "payload": {"crew": "cmdr", "indicator": "heart_rate", "value": 140, "unit": "bpm", "t": 120,
                                               "source": "sim", "confidence": 0.5, "state": "event"}},
        {"t": 180, "type": "trigger", "payload": {"kind": "auto", "crew": "cmdr", "t": 180, "reason": "STUB collapse (test double)"}},
    ]}
    svc = HabitatService(str(tmp_path / "h.sqlite"), [replay], RECORDS)
    svc.set_speed(60)
    httpd = make_server(svc, port=port, tick_interval=0.05)
    import threading
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    yield svc, f"http://127.0.0.1:{port}"
    httpd.shutdown()
    svc.close()


def test_spec1_replay_reaches_the_flow_through_the_service(habitat):
    svc, url = habitat
    eng = build(explainer=None, habitat_url=url)
    eng.habitat.start()
    try:
        assert eng.habitat.connected.wait(5)
        assert wait(lambda: eng.view("cmdr")["screen"] == "verdict", 8), eng.habitat.errors
        trig = next(e for e in eng.events if e["type"] == "trigger")
        assert trig["kind"] == "auto"
        assert eng.readings["cmdr"]["heart_rate"]["source"] == "sim"
        # Spec 3 Alert shape (as pushed by their hook): objects in likely_causes
        eng.habitat.handle({"t": 3, "type": "alert", "payload": alert(causes=["Low sleep (suggestion, not diagnosis)", "B"])})
        assert eng.view("cmdr")["urgency_label"] == "ACT NOW"
        # no answer for 15 mission seconds at 60x -> crew alarm
        eng.tick()
        assert wait(lambda: (eng.tick() or True) and eng.view("eng")["screen"] == "alarm", 3)
        eng.accept("eng")
        eng.observer_answer("eng", "no")
        v = eng.view("eng")
        assert v["screen"] == "record" and v["ok"] and v["record"]["id"] == "cmdr"
        spec1_log = svc.store.query("access_log", crew="cmdr")
        assert len(spec1_log) == 1 and spec1_log[0]["opened_by"] == "eng"  # logged by Spec 1 too
        assert eng.store.access_log("cmdr")[0]["actor"] == "eng"  # and locally (owner view)
        eng.next("eng")
        assert eng.view("eng")["causes"][0] == "Low sleep (suggestion, not diagnosis)"
    finally:
        eng.habitat.stop()


def test_ground_reply_is_stored_as_label_by_spec1(habitat):
    svc, url = habitat
    eng = build(explainer=None, habitat_url=url)
    eng.trigger({"schema_version": SV, "kind": "manual", "crew": "cmdr", "t": eng.now(), "reason": "button"})
    eng.answer("cmdr", "status", "need_help")
    e = eng.active_for("cmdr")
    st = eng.ground.state[e.id]
    st.update(reply="Flight surgeon reply.", scripted=False, reply_t=st["sent_t"] + 3420, typed_t=st["sent_t"] + 1710)
    eng.clock._t = st["reply_t"]  # move our view of the clock past delivery
    eng.ground.tick()
    labels = svc.store.query("label", crew="cmdr")
    assert len(labels) == 1 and labels[0]["kind"] == "ground_reply" and labels[0]["report"]["reply"] == "Flight surgeon reply."
    assert svc.store.query("ground_report", crew="cmdr")[0]["reply_t"] == st["reply_t"]
    assert eng.store.labels("cmdr")[0]["text"] == "Flight surgeon reply."


def test_spec1_refusal_blocks_record_and_service_down_keeps_local_flow(habitat):
    svc, url = habitat
    eng = build(explainer=None, habitat_url=url)
    eng.trigger({"schema_version": SV, "kind": "manual", "crew": "cmdr", "t": eng.now(), "reason": "button"})
    eng.answer("cmdr", "status", "need_help")
    eng.habitat.url = "http://127.0.0.1:9"  # service gone
    eng.accept("eng")
    v = eng.view("eng")
    assert v["screen"] == "record" and v["ok"] is False  # can't confirm with Spec 1 -> no record shown
    eng.next("eng")
    assert eng.view("eng")["screen"] == "contributors"  # the flow itself continues


def test_bad_stream_message_does_not_stop_the_flow(habitat):
    svc, url = habitat
    eng = build(explainer=None, habitat_url=url)
    eng.habitat.handle({"t": 1, "type": "alert", "payload": {"bad": True}})
    assert any(e["type"] == "habitat_message_rejected" for e in eng.events)
    eng.trigger({"schema_version": SV, "kind": "manual", "crew": "cmdr", "t": eng.now(), "reason": "button"})
    assert eng.view("cmdr")["screen"] == "verdict"
