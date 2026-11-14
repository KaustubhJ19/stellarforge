"""Ticket 09 (Spec 1 task 1.8): Service ("habitat network").

Spec: plays replays on the clock; accepts manual Readings, Triggers, Labels, ground replies;
pushes events to three windows; holds all Crew records.
Tests (d) time order to all three windows, (e) manual vs auto Trigger differ only in kind,
(f) restart resumes from stored state. Stories 17, 18 (emergency access logged), 21 (replies as Labels).
"""
import copy
import http.client
import json
import sys
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "contracts"))

from service import WINDOWS, HabitatService, make_server  # noqa: E402
from validate import ContractError  # noqa: E402

EX = ROOT / "contracts" / "examples"


def example(name, **changes):
    doc = json.loads((EX / f"{name}.example.json").read_text(encoding="utf-8"))
    doc.update(changes)
    return doc


class FakeMonotonic:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, s):
        self.value += s


def reading(crew, t, indicator="resting_heart_rate", value=60):
    r = example("Reading", crew=crew, t=t, indicator=indicator, value=value)
    del r["schema_version"]  # payloads inside a ReplayFile carry the file's version
    return r


def replay(crew, events):
    return {"schema_version": "1.0.0", "crew": crew, "profile": "mars_transit", "events": events}


def crew_records():
    return [example("CrewRecord", id=c) for c in ["A", "B", "C", "D"]]


@pytest.fixture
def real():
    return FakeMonotonic()


_open = []


@pytest.fixture(autouse=True)
def close_services():
    yield
    while _open:
        _open.pop().close()


def make(tmp_path, real, replays=(), **kw):
    svc = HabitatService(tmp_path / "habitat.sqlite", replays=list(replays), crew_records=crew_records(),
                         monotonic=real, **kw)
    _open.append(svc)
    return svc


def test_close_twice_is_safe(tmp_path, real):
    svc = make(tmp_path, real)
    svc.close()
    svc.close()


class Window:
    """Collects what one window receives."""

    def __init__(self, svc, name):
        self.got = []
        svc.subscribe(name, self.got.append)


# ---- loading and playing -------------------------------------------------------

def test_three_windows_patient_rescuer_ground():
    assert WINDOWS == ("patient", "rescuer", "ground")


def test_the_shared_replay_example_loads_and_plays(tmp_path, real):
    svc = make(tmp_path, real, [example("ReplayFile")])
    real.advance(3600)
    svc.tick()
    assert len(svc.store.query("reading")) == len(example("ReplayFile")["events"])


def test_invalid_replay_is_rejected_loudly(tmp_path, real):
    bad = replay("A", [{"t": 5, "type": "reading", "payload": {}}, {"t": 1, "type": "reading", "payload": {}}])
    with pytest.raises(ContractError):
        make(tmp_path, real, [bad])


def test_reading_event_with_invalid_payload_is_rejected_on_load(tmp_path, real):
    bad = replay("A", [{"t": 1, "type": "reading", "payload": {"crew": "A"}}])
    with pytest.raises(ContractError):
        make(tmp_path, real, [bad])


def test_events_are_delivered_only_when_the_clock_reaches_them(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": 0, "type": "reading", "payload": reading("A", 0)},
                                             {"t": 10, "type": "reading", "payload": reading("A", 10)}])])
    w = Window(svc, "patient")
    svc.tick()
    assert [e["t"] for e in w.got] == [0]
    real.advance(10)
    svc.tick()
    assert [e["t"] for e in w.got] == [0, 10]


def test_one_tick_commits_once_however_many_events_are_due(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": t, "type": "reading", "payload": reading("A", t)}
                                             for t in range(50)])])
    statements = []
    svc.store.conn.set_trace_callback(statements.append)
    real.advance(100)
    svc.tick()
    svc.store.conn.set_trace_callback(None)
    assert sum(s.strip().upper() == "COMMIT" for s in statements) == 1
    assert len(svc.store.query("reading")) == 50


def test_a_failed_tick_rolls_back_and_redelivers_nothing_twice(tmp_path, real, monkeypatch):
    svc = make(tmp_path, real, [replay("A", [{"t": t, "type": "reading", "payload": reading("A", t)}
                                             for t in (0, 1, 2)])])
    w = Window(svc, "patient")
    real.advance(5)
    original = svc.store.add
    calls = []

    def flaky(kind, doc, commit=True):
        calls.append(doc["t"])
        if doc["t"] == 2 and len(calls) == 3:
            raise RuntimeError("disk full")
        return original(kind, doc, commit=commit)
    monkeypatch.setattr(svc.store, "add", flaky)
    with pytest.raises(RuntimeError):
        svc.tick()
    assert svc.store.query("reading") == [] and w.got == []
    svc.tick()  # retry succeeds
    assert [r["t"] for r in svc.store.query("reading")] == [0, 1, 2]
    assert [e["t"] for e in w.got] == [0, 1, 2]


def test_replay_readings_are_stored(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": 0, "type": "reading", "payload": reading("A", 0)}])])
    svc.tick()
    assert svc.store.query("reading", crew="A")[0]["t"] == 0


# (d) -------------------------------------------------------------------------------

def test_d_events_from_several_replays_reach_all_three_windows_in_time_order(tmp_path, real):
    a = replay("A", [{"t": t, "type": "reading", "payload": reading("A", t)} for t in (0, 30, 60)])
    b = replay("B", [{"t": t, "type": "reading", "payload": reading("B", t)} for t in (10, 30, 50)])
    svc = make(tmp_path, real, [a, b])
    windows = [Window(svc, w) for w in WINDOWS]
    real.advance(100)
    svc.tick()
    times = [e["t"] for e in windows[0].got]
    assert times == sorted(times) and len(times) == 6
    assert windows[0].got == windows[1].got == windows[2].got


def test_skip_to_next_event_moves_the_clock_to_the_next_pending_event(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": 0, "type": "x", "payload": {}},
                                             {"t": 3600, "type": "x", "payload": {}}])])
    svc.tick()
    assert svc.skip() == 3600
    w = Window(svc, "ground")
    svc.tick()
    assert [e["t"] for e in w.got] == [3600]


# (e) -------------------------------------------------------------------------------

def test_e_manual_and_auto_trigger_differ_only_in_kind(tmp_path, real):
    auto = example("Trigger", kind="auto", crew="B", t=5, reason="collapse")
    del auto["schema_version"]
    svc = make(tmp_path, real, [replay("B", [{"t": 5, "type": "trigger", "payload": auto}])])
    w = Window(svc, "rescuer")
    real.advance(5)
    svc.tick()
    manual = dict(auto, kind="manual", schema_version="1.0.0")
    svc.post_trigger(manual)
    auto_msg, manual_msg = w.got
    assert auto_msg["type"] == manual_msg["type"] == "trigger"
    assert auto_msg["payload"]["kind"] == "auto" and manual_msg["payload"]["kind"] == "manual"
    strip = lambda m: {**m, "payload": {k: v for k, v in m["payload"].items() if k not in ("kind", "schema_version")}}
    assert strip(auto_msg) == strip(manual_msg)


def test_invalid_manual_trigger_is_rejected(tmp_path, real):
    svc = make(tmp_path, real)
    with pytest.raises(ContractError):
        svc.post_trigger({"kind": "panic"})


# manual inputs ------------------------------------------------------------------------

def test_manual_reading_is_stored_and_pushed(tmp_path, real):
    svc = make(tmp_path, real)
    w = Window(svc, "patient")
    doc = example("Reading", crew="C", t=0, source="manual")
    svc.post_reading(doc)
    assert svc.store.query("reading", crew="C") == [doc]
    assert w.got == [{"t": 0, "type": "reading", "payload": doc}]


def test_manual_label_is_stored(tmp_path, real):
    svc = make(tmp_path, real)
    svc.post_label({"crew": "A", "t": 3, "note": "false alarm"})
    assert svc.store.query("label", crew="A")[0]["note"] == "false alarm"


def test_ground_reply_is_stored_as_a_label_and_pushed(tmp_path, real):
    svc = make(tmp_path, real)
    w = Window(svc, "patient")
    report = example("GroundReport", crew="B", sent_t=1000, reply_t=4420, reply="Continue care")
    svc.post_ground_reply(report)
    labels = svc.store.query("label", crew="B")
    assert len(labels) == 1 and labels[0]["t"] == 4420 and labels[0]["report"] == report
    assert svc.store.query("ground_report", crew="B") == [report]
    assert w.got[-1]["type"] == "ground_reply"


def test_ground_reply_is_all_or_nothing(tmp_path, real, monkeypatch):
    svc = make(tmp_path, real)
    original = svc.store.add

    def fail_on_label(kind, doc, commit=True):
        if kind == "label":
            raise RuntimeError("disk full")
        return original(kind, doc, commit=commit)
    monkeypatch.setattr(svc.store, "add", fail_on_label)
    with pytest.raises(RuntimeError):
        svc.post_ground_reply(example("GroundReport", crew="B", sent_t=1000, reply_t=4420, reply="x"))
    monkeypatch.undo()
    assert svc.store.query("ground_report") == [] and svc.store.query("label") == []


def test_a_failing_window_does_not_stop_the_others(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": 0, "type": "reading", "payload": reading("A", 0)}])])

    def broken(message):
        raise RuntimeError("window crashed")
    svc.subscribe("patient", broken)
    healthy = Window(svc, "ground")
    svc.tick()
    assert [e["t"] for e in healthy.got] == [0]


def test_duplicate_crew_ids_are_rejected(tmp_path, real):
    with pytest.raises(ValueError):
        HabitatService(tmp_path / "h.sqlite", replays=[], crew_records=[example("CrewRecord", id="A")] * 2,
                       monotonic=real)


def test_an_opened_record_cannot_change_the_stored_one(tmp_path, real):
    svc = make(tmp_path, real)
    svc.open_crew_record("A", requester="A")["sex"] = "changed"
    assert svc.open_crew_record("A", requester="A")["sex"] == "male"


def test_ground_reply_without_a_reply_is_rejected(tmp_path, real):
    svc = make(tmp_path, real)
    report = example("GroundReport")
    report.pop("reply")
    with pytest.raises(ValueError):
        svc.post_ground_reply(report)


# crew records (stories 17, 18) ------------------------------------------------------------

def test_holds_all_crew_records(tmp_path, real):
    svc = make(tmp_path, real)
    assert sorted(svc.crew_ids()) == ["A", "B", "C", "D"]


def test_own_record_opens_without_a_log_entry(tmp_path, real):
    svc = make(tmp_path, real)
    assert svc.open_crew_record("A", requester="A")["id"] == "A"
    assert svc.store.query("access_log") == []


def test_another_persons_record_needs_emergency_mode(tmp_path, real):
    svc = make(tmp_path, real)
    with pytest.raises(PermissionError):
        svc.open_crew_record("B", requester="A")


def test_emergency_opening_of_another_record_is_logged(tmp_path, real):
    svc = make(tmp_path, real)
    real.advance(42)
    assert svc.open_crew_record("B", requester="A", emergency=True)["id"] == "B"
    log = svc.store.query("access_log", crew="B")
    assert log == [{"crew": "B", "t": 42, "opened_by": "A", "emergency": True}]


def test_unknown_crew_record_is_an_error(tmp_path, real):
    svc = make(tmp_path, real)
    with pytest.raises(KeyError):
        svc.open_crew_record("Z", requester="A", emergency=True)


def test_invalid_crew_record_is_rejected(tmp_path, real):
    with pytest.raises(ContractError):
        HabitatService(tmp_path / "h.sqlite", replays=[], crew_records=[{"id": "A"}], monotonic=real)


# (f) restart ------------------------------------------------------------------------------

def test_f_restart_mid_replay_resumes_without_lost_or_duplicated_events(tmp_path, real):
    events = [{"t": t, "type": "reading", "payload": reading("A", t)} for t in (0, 10, 20, 30)]
    rp = replay("A", events)
    svc = make(tmp_path, real, [rp])
    first = Window(svc, "patient")
    real.advance(15)
    svc.tick()
    assert [e["t"] for e in first.got] == [0, 10]
    svc.close()  # crash / restart

    real2 = FakeMonotonic()
    svc2 = make(tmp_path, real2, [copy.deepcopy(rp)])
    assert svc2.clock.now() == 15
    second = Window(svc2, "patient")
    real2.advance(20)
    svc2.tick()
    assert [e["t"] for e in second.got] == [20, 30]
    assert [r["t"] for r in svc2.store.query("reading", crew="A")] == [0, 10, 20, 30]


def test_restart_with_different_replays_does_not_resume_silently(tmp_path, real):
    svc = make(tmp_path, real, [replay("A", [{"t": 0, "type": "x", "payload": {}}])])
    svc.tick()
    svc.close()
    with pytest.raises(ValueError):
        make(tmp_path, FakeMonotonic(), [replay("A", [{"t": 0, "type": "y", "payload": {}}])])


def test_restart_keeps_the_clock_speed(tmp_path, real):
    svc = make(tmp_path, real)
    svc.set_speed(60)
    svc.close()
    assert make(tmp_path, FakeMonotonic()).clock.speed == 60


# HTTP + SSE ----------------------------------------------------------------------------

@pytest.fixture
def server(tmp_path, real):
    a = replay("A", [{"t": t, "type": "reading", "payload": reading("A", t)} for t in (0, 20)])
    b = replay("B", [{"t": 10, "type": "reading", "payload": reading("B", 10)}])
    svc = make(tmp_path, real, [a, b])
    httpd = make_server(svc, port=0, tick_interval=None)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield svc, httpd.server_address[1]
    httpd.shutdown()
    httpd.server_close()
    svc.close()


def sse_open(port, window):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request("GET", f"/events?window={window}")
    resp = conn.getresponse()
    assert resp.status == 200
    assert resp.getheader("Content-Type").startswith("text/event-stream")
    return conn, resp


def sse_read(resp, n):
    out = []
    while len(out) < n:
        line = resp.readline().decode("utf-8").strip()
        if line.startswith("data: "):
            out.append(json.loads(line[6:]))
    return out


def request(port, method, path, body=None):
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.request(method, path, body=json.dumps(body) if body is not None else None,
                 headers={"Content-Type": "application/json"})
    resp = conn.getresponse()
    data = resp.read()
    conn.close()
    return resp.status, (json.loads(data) if data else None)


def test_http_three_windows_receive_events_in_time_order(server, real):
    svc, port = server
    streams = [sse_open(port, w) for w in WINDOWS]
    svc.wait_for_subscribers(3)
    real.advance(30)
    svc.tick()
    got = [sse_read(resp, 3) for _, resp in streams]
    assert [e["t"] for e in got[0]] == [0, 10, 20]
    assert got[0] == got[1] == got[2]
    for conn, _ in streams:
        conn.close()


def test_http_unknown_window_is_rejected(server):
    _, port = server
    status, _ = request(port, "GET", "/events?window=kitchen")
    assert status == 400


def test_http_manual_trigger_is_pushed(server):
    svc, port = server
    conn, resp = sse_open(port, "rescuer")
    svc.wait_for_subscribers(1)
    trig = example("Trigger", crew="B", t=0)
    status, _ = request(port, "POST", "/trigger", trig)
    assert status == 200
    assert sse_read(resp, 1)[0]["payload"] == trig
    conn.close()


def test_http_invalid_body_is_400_with_reason(server):
    _, port = server
    status, body = request(port, "POST", "/reading", {"crew": "A"})
    assert status == 400 and "Reading invalid" in body["error"]


def test_http_crew_record_access_and_logging(server, real):
    svc, port = server
    assert request(port, "GET", "/crew/B?requester=A")[0] == 403
    status, rec = request(port, "GET", "/crew/B?requester=A&emergency=1")
    assert status == 200 and rec["id"] == "B"
    assert len(svc.store.query("access_log", crew="B")) == 1


def test_http_clock_speed_and_skip(server):
    svc, port = server
    assert request(port, "POST", "/clock/speed", {"speed": 60})[0] == 200
    assert svc.clock.speed == 60
    assert request(port, "POST", "/clock/speed", {"speed": 7})[0] == 400
    status, body = request(port, "POST", "/clock/skip")
    assert status == 200 and body["t"] == 10  # pending events at 0, 10, 20; clock at 0
    status, body = request(port, "GET", "/clock")
    assert status == 200 and body["label"] == "demo time" and body["speed"] == 60


def test_http_malformed_content_length_is_400(server):
    _, port = server
    conn = http.client.HTTPConnection("127.0.0.1", port, timeout=5)
    conn.putrequest("POST", "/label")
    conn.putheader("Content-Length", "abc")
    conn.endheaders()
    assert conn.getresponse().status == 400
    conn.close()


def test_http_unknown_path_is_404(server):
    _, port = server
    assert request(port, "GET", "/nope")[0] == 404


def test_server_listens_on_localhost_only(tmp_path, real):
    svc = make(tmp_path, real)
    httpd = make_server(svc, port=0, tick_interval=None)
    try:
        assert httpd.server_address[0] == "127.0.0.1"
    finally:
        httpd.server_close()
        svc.close()
