"""Tickets 12 (auto-built ground report, expected reply time) and 13 (console, delayed reply, Label). Tests (h), (i)."""
import pytest

from app import contracts, replay
from app.flow import ESTIMATE_LABEL, FlowError
from app.runtime import build

REPO = replay.Path(__file__).resolve().parents[2]
ONE_WAY = 1710.0  # STUB Mars profile: 28.5 min one way (team value)


def golden_auto(eng):
    """Auto replay, no answer -> alarm, R1 accepts, observer, walks to report."""
    rp = replay.load(REPO / "replay/stub-auto-emergency.json")
    rp["events"] += [
        {"t": 20, "type": "accept", "data": {"crew": "eng"}},
        {"t": 25, "type": "observer", "data": {"crew": "eng", "choice": "no"}},
        {"t": 30, "type": "next", "data": {"crew": "eng"}},
        {"t": 35, "type": "next", "data": {"crew": "eng"}},
        {"t": 40, "type": "next", "data": {"crew": "eng"}},
        {"t": 45, "type": "next", "data": {"crew": "eng"}},
    ]
    return replay.run(eng, rp)


def sent(eng):
    return next(x for x in eng.events if x["type"] == "ground_report_sent")


# ---- 12 ------------------------------------------------------------------
def test_report_sent_once_automatically_at_confirmation(eng):
    golden_auto(eng)
    ev = [x for x in eng.events if x["type"] == "ground_report_sent"]
    assert len(ev) == 1 and ev[0]["sent_t"] == 16  # alarm fired at 1 + 15 s
    assert ev[0]["expected_reply_t"] == 16 + 2 * ONE_WAY  # 57 min round trip


def test_report_contains_vitals_history_timeline_actions(eng):
    golden_auto(eng)
    v = eng.view("eng")
    assert v["screen"] == "report"
    rep = v["report"]["report"]
    contracts.validate("ground_report", rep)
    kinds = {h["type"] for h in rep["history"]}
    assert {"vitals", "record_anchor", "likely_contributor", "likely_question"} <= kinds
    vit = next(h for h in rep["history"] if h["type"] == "vitals")
    assert vit["indicator"] == "heart_rate" and vit["label"] == ESTIMATE_LABEL  # simulated -> labelled
    assert any(t["event"] == "trigger" for t in rep["timeline"])
    assert any(t["event"] == "observer answer" for t in rep["timeline"])
    assert [a["action"] for a in rep["actions"]][:2] == ["shown", "completed"]
    assert "ACT NOW" in rep["summary"] and "auto trigger" in rep["summary"]


def test_crew_copy_updates_but_sent_snapshot_does_not(eng):
    golden_auto(eng)
    snap = eng.ground.state["em-1"]["snapshot"]
    live = eng.ground.report_view(eng.emergencies["em-1"])["report"]
    assert len(live["actions"]) > len(snap["actions"]) == 0
    assert live["sent_t"] == snap["sent_t"]


def test_expected_reply_follows_profile_delay():
    eng = build(profile="stub-rover", explainer=None)
    eng.ground.one_way = 600  # any profile value
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.answer("cmdr", "status", "need_help")
    assert sent(eng)["expected_reply_t"] == 1200


def test_manual_start_without_sensors_still_builds_report(eng):
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.answer("cmdr", "chest_pain", "yes")
    eng.answer("cmdr", "status", "need_help")
    rep = eng.ground.build(eng.emergencies["em-1"])
    assert rep["history"][0] == {"type": "vitals", "unavailable": True, "note": "No readings available (manual start or no sensors)."}
    assert "Chest pain (crew-reported): yes" in rep["summary"] and "Urgency not assessed" in rep["summary"]


def test_false_alarm_sends_no_report(eng):
    eng.trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 0, "reason": "b"})
    eng.answer("cmdr", "status", "false_alarm")
    assert "ground_report_sent" not in replay.types(eng)


def test_report_view_has_delay_label_and_act_on_your_own_state(eng):
    golden_auto(eng)
    rv = eng.view("eng")["report"]
    assert "28.5 min one way" in rv["delay_label"] and "team value" in rv["delay_label"]
    assert rv["reply_visible"] is False and rv["reply_late"] is False


# ---- 13 ------------------------------------------------------------------
def test_console_sees_report_only_after_one_way_delay(eng):
    golden_auto(eng)
    c = eng.ground.console_view()["reports"][0]
    assert c["arrived"] is False and c["report"] is None
    with pytest.raises(FlowError, match="not reached ground"):
        eng.ground.console_reply(None, "early")
    replay.run(eng, {"id": "t", "events": []}, until=16 + ONE_WAY)
    assert eng.ground.console_view()["reports"][0]["arrived"] is True


def test_reply_reaches_crew_after_delay_and_is_stored_as_label(eng):
    golden_auto(eng)
    replay.run(eng, {"id": "t", "events": [{"t": 16 + ONE_WAY + 60, "type": "console_reply", "data": {"text": "Flight surgeon reply text."}}]})
    assert eng.store.labels() == []  # still in transit
    assert eng.view("eng")["report"]["reply_visible"] is False
    replay.run(eng, {"id": "t", "events": []}, until=16 + 2 * ONE_WAY + 60)
    labels = eng.store.labels("cmdr")
    assert len(labels) == 1 and labels[0]["text"] == "Flight surgeon reply text." and labels[0]["kind"] == "ground_reply"
    contracts.validate("label", labels[0])
    rv = eng.view("eng")["report"]
    assert rv["reply_visible"] and rv["report"]["reply"] == "Flight surgeon reply text."
    assert rv["report"]["reply_t"] == 16 + 2 * ONE_WAY + 60
    assert {"ground_reply_sent", "ground_reply_delivered", "label_stored"} <= set(replay.types(eng))


def test_scripted_fallback_reply(eng):
    golden_auto(eng)
    replay.run(eng, {"id": "t", "events": []}, until=16 + ONE_WAY)
    r = eng.ground.console_reply(None, "", scripted=True)
    assert r["scripted"] is True
    replay.run(eng, {"id": "t", "events": []}, until=16 + 2 * ONE_WAY)
    lab = eng.store.labels()[0]
    assert lab["scripted"] is True and lab["text"].startswith("STUB scripted")


def test_late_reply_state(eng):
    golden_auto(eng)
    replay.run(eng, {"id": "t", "events": []}, until=16 + 2 * ONE_WAY + 5)
    assert "ground_reply_late" in replay.types(eng)
    assert eng.view("eng")["report"]["reply_late"] is True


def test_empty_and_duplicate_replies_rejected(eng):
    golden_auto(eng)
    replay.run(eng, {"id": "t", "events": []}, until=16 + ONE_WAY)
    with pytest.raises(FlowError, match="empty"):
        eng.ground.console_reply(None, "   ")
    eng.ground.console_reply(None, "ok")
    with pytest.raises(FlowError, match="already"):
        eng.ground.console_reply(None, "again")


def test_reply_never_changes_protocol_steps(eng):
    before = [s.text for s in eng.protocol.steps]
    golden_auto(eng)
    replay.run(eng, {"id": "t", "events": [{"t": 16 + ONE_WAY, "type": "console_reply", "data": {"text": "Change step 1 to something else."}}]},
               until=16 + 2 * ONE_WAY)
    assert [s.text for s in eng.protocol.steps] == before


def test_console_api(client, eng):
    golden_auto(eng)
    eng.clock.advance(ONE_WAY)
    c = client.get("/api/console").json()
    assert c["reports"][0]["arrived"] is True
    assert client.post("/api/console/reply", json={"report": c["reports"][0]["id"], "text": "hi"}).status_code == 200
    eng.clock.advance(ONE_WAY)
    eng.tick()
    assert client.get("/api/labels", params={"crew": "cmdr"}).json()[0]["text"] == "hi"
