"""Tickets 06 (crew alarm, Rescuer 1), 07 (record takeover + access log), 08 (likely contributors)."""
import threading

import pytest

from app import replay
from app.flow import AccessDenied, FlowError
from sf_helpers import alert

PRESS = {"t": 0, "type": "press_emergency", "data": {"crew": "cmdr"}}


def run(eng, *events, until=None):
    return replay.run(eng, {"id": "t", "events": list(events)}, until=until)


def alarm(eng):
    run(eng, PRESS, until=15)
    return eng.active_for("cmdr")


# ---- 06 ------------------------------------------------------------------
def test_alarm_rings_every_other_tablet_not_the_patient(eng):
    alarm(eng)
    ev = next(x for x in eng.events if x["type"] == "crew_alarm")
    assert sorted(ev["targets"]) == ["cmo", "eng", "sci"]
    for c in ev["targets"]:
        v = eng.view(c)
        assert v["screen"] == "alarm" and v["ring"] is True
    assert eng.view("cmdr")["screen"] == "patient_alarm"


def test_first_accept_is_rescuer_1_and_alarm_stops(eng):
    e = alarm(eng)
    assert eng.accept("eng") == "R1"
    assert e.rescuers == ["eng"]
    with pytest.raises(FlowError, match="already accepted by eng"):
        eng.accept("sci")
    assert "alarm_stopped" in replay.types(eng)
    assert all(eng.view(c)["screen"] != "alarm" for c in ("sci", "cmo"))
    assert eng.view("sci")["screen"] == "join_r2"


def test_simultaneous_accepts_produce_one_rescuer_1(eng):
    e = alarm(eng)
    results = []

    def go(c):
        try:
            results.append(eng.accept(c))
        except FlowError:
            results.append("lost")

    ts = [threading.Thread(target=go, args=(c,)) for c in ("eng", "sci", "cmo")]
    [t.start() for t in ts]
    [t.join() for t in ts]
    assert sorted(results) == ["R1", "lost", "lost"] and len(e.rescuers) == 1


def test_rescuer_1_answers_observer_question_and_flow_continues(eng):
    alarm(eng)
    eng.accept("eng")
    v = eng.view("eng")
    assert v["screen"] == "observer" and v["question"]["text"] == "Does the patient respond?"
    eng.observer_answer("eng", "yes")  # responds: recorded, emergency NOT dismissed
    e = eng.active_for("cmdr")
    assert e.observer == "yes" and e.status == "active"
    assert any(x["event"] == "observer answer" for x in e.timeline)
    assert eng.view("eng")["screen"] == "record"


def test_help_request_path_has_no_observer_question(eng):
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.answer("cmdr", "status", "need_help")
    eng.accept("sci")
    assert eng.view("sci")["screen"] == "record"
    assert "crew_alarm" not in replay.types(eng)


def test_patient_cannot_accept_own_alarm(eng):
    alarm(eng)
    with pytest.raises(FlowError):
        eng.accept("cmdr")


def test_alarm_with_only_one_other_crew_member():
    from app.runtime import build
    eng = build(profile="stub-rover")
    run(eng, PRESS, until=15)
    ev = next(x for x in eng.events if x["type"] == "crew_alarm")
    assert ev["targets"] == ["eng"]
    assert eng.accept("eng") == "R1"


def test_api_alarm_flow(client, eng):
    client.post("/api/trigger", json={"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.clock.advance(15)
    eng.tick()
    assert client.post("/api/accept", json={"crew": "eng"}).json() == {"role": "R1"}
    r = client.post("/api/accept", json={"crew": "sci"})
    assert r.status_code == 409 and "already accepted" in r.json()["error"]


# ---- 07 ------------------------------------------------------------------
def rescuer_on_record(eng):
    alarm(eng)
    eng.accept("eng")
    eng.observer_answer("eng", "no")
    return eng.active_for("cmdr")


def test_rescuer_opens_patient_record_and_it_is_logged(eng):
    e = rescuer_on_record(eng)
    v = eng.view("eng")
    assert v["screen"] == "record" and v["ok"] and v["record"]["id"] == "cmdr"
    log = eng.store.access_log("cmdr")
    assert len(log) == 1
    entry = log[0]
    assert (entry["actor"], entry["subject"], entry["emergency_id"], entry["allowed"]) == ("eng", "cmdr", e.id, True)
    assert entry["t"] == eng.now()
    assert "record_opened" in replay.types(eng)


def test_polling_the_view_does_not_reopen_or_relog(eng):
    rescuer_on_record(eng)
    for _ in range(5):
        eng.view("eng")
    assert len(eng.store.access_log("cmdr")) == 1


def test_open_record_outside_emergency_refused_and_logged(eng, client):
    with pytest.raises(AccessDenied):
        eng.open_record("eng", "cmdr")
    log = eng.store.access_log("cmdr")
    assert log[-1]["allowed"] is False and "refused" in log[-1]["reason"]
    assert client.get("/api/record", params={"actor": "sci", "subject": "cmdr"}).status_code == 403


def test_record_refused_after_emergency_ends(eng):
    e = eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.answer("cmdr", "status", "false_alarm")
    with pytest.raises(AccessDenied):
        eng.open_record("eng", "cmdr", e.id)


def test_log_write_failure_blocks_the_record(eng, client):
    alarm(eng)
    eng.accept("eng")
    eng.store.fail_access_log = True
    eng.observer_answer("eng", "no")
    v = eng.view("eng")
    assert v["screen"] == "record" and v["ok"] is False and "record" not in v
    r = client.get("/api/record", params={"actor": "eng", "subject": "cmdr"})
    assert r.status_code == 503 and "crew" not in r.json()


def test_rescuer_2_record_opening_is_logged_too(eng):
    rescuer_on_record(eng)
    eng.join_r2("sci")
    assert [x["actor"] for x in eng.store.access_log("cmdr")] == ["eng", "sci"]


def test_own_record_needs_no_emergency(eng):
    assert eng.open_record("cmdr", "cmdr")["id"] == "cmdr"


def test_patient_can_view_own_access_log_only(client, eng):
    rescuer_on_record(eng)
    r = client.get("/api/access-log", params={"crew": "cmdr", "viewer": "cmdr"})
    assert r.status_code == 200 and r.json()[0]["actor"] == "eng"
    assert client.get("/api/access-log", params={"crew": "cmdr", "viewer": "eng"}).status_code == 403


def test_patient_is_cmo_still_works(eng):
    run(eng, {"t": 0, "type": "press_emergency", "data": {"crew": "cmo"}}, until=15)
    eng.accept("eng")
    eng.observer_answer("eng", "no")
    rec = eng.view("eng")["record"]
    assert rec["id"] == "cmo" and rec["missionProfile"] == "stub-mars"  # Spec 1 CrewRecord shape


# ---- 08 ------------------------------------------------------------------
@pytest.mark.parametrize("n,shown,msg", [(0, 0, True), (1, 1, True), (2, 2, False), (3, 3, False), (5, 3, False)])
def test_contributors_count(eng, n, shown, msg):
    eng.ingest_alert(alert(causes=[f"STUB cause {i}" for i in range(n)]))
    rescuer_on_record(eng)
    eng.next("eng")
    v = eng.view("eng")
    assert v["screen"] == "contributors" and len(v["causes"]) == shown
    assert v["causes"] == [f"STUB cause {i}" for i in range(shown)]  # order kept, nothing invented
    assert (v["message"] is not None) == msg


def test_manual_trigger_without_alert_shows_empty_message(eng):
    rescuer_on_record(eng)
    eng.next("eng")
    v = eng.view("eng")
    assert v["causes"] == [] and v["message"] == "No history-based contributors available."
    eng.next("eng")
    assert eng.view("eng")["screen"] == "step"
