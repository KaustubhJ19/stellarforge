"""Collapse Copilot ticket 13: L3 investigator tools, verifier and notes panel (fake transport, no Ollama)."""
import json
import threading

import pytest

from app.runtime import REAL_RECORDS, build
from copilot.fixtures import fake_hot_summary
from copilot.hot_summary import HotSummary, NoHistory
from copilot.investigator import UNAVAILABLE, run_investigator, verify_note
from copilot.investigator_tools import run_tool
from copilot.conditions import load_conditions
from sf_helpers import trig

SNAP = HotSummary.from_dict(fake_hot_summary("A", t=5))
GOOD = {"claim": "Elbow joint pain is on the post-EVA form, consistent with decompression sickness, ask ground.",
        "evidence": [{"tool": "forms", "field": "post_eva.elbow_joint_pain", "value": True}]}


def fake(calls=({"tool": "forms"},), notes=(GOOD,)):
    """Scripted model: first prompt asks for tools, second for notes."""
    def transport(prompt: str) -> str:
        if prompt.startswith("Tool results"):
            return json.dumps({"notes": list(notes)})
        return json.dumps({"calls": list(calls)})
    return transport


def note(claim, **ref):
    return {"claim": claim, "evidence": [{"tool": "forms", "field": "post_eva.elbow_joint_pain", "value": True} | ref]}


# ----------------------------------------------------------------------- tools
def test_tools_return_flat_read_only_results():
    lib = load_conditions()
    assert run_tool("forms", {}, SNAP, lib) == {"post_eva.elbow_joint_pain": True}
    assert run_tool("summary", {}, SNAP, lib)["hours_since_eva"] == 2.0
    assert run_tool("history", {}, SNAP, lib)["heart_rate.z_anchor"] == 2.1
    assert run_tool("alerts", {}, SNAP, lib)["count"] == 1
    hits = run_tool("library_search", {"query": "joint pain after EVA"}, SNAP, lib)
    assert hits["decompression-sickness.protocol_id"] == "decompression-sickness"
    with pytest.raises(KeyError):
        run_tool("write_record", {}, SNAP, lib)
    with pytest.raises(ValueError):
        run_tool("library_search", {}, SNAP, lib)


# -------------------------------------------------------------------- verifier
def test_verified_claim_is_shown_with_source_pointer():
    r = run_investigator(SNAP, fake())
    assert r.status == "ok" and r.dropped == 0 and len(r.notes) == 1
    src = r.notes[0]["sources"][0]
    assert (src["tool"], src["field"], src["value"]) == ("forms", "post_eva.elbow_joint_pain", True)
    assert src["crew"] == "A" and src["snapshot_label"] == SNAP.label and src["snapshot_t"] == 5.0
    assert r.snapshot_digest == SNAP.digest()


@pytest.mark.parametrize("bad, why", [
    (note("Elbow pain, wrong value.", value=False), "evidence does not match the tool result"),
    (note("Elbow pain, field invented.", field="post_eva.knee_pain"), "evidence does not match the tool result"),
    (note("Elbow pain, tool never called.", tool="history"), "tool not called"),
    ({"claim": "Elbow pain with no evidence.", "evidence": []}, "no evidence"),
    ({"claim": "", "evidence": GOOD["evidence"]}, "malformed"),
    (note("Elbow pain started 3 hours ago."), "number not in the cited values"),
    (note("Give 500 mg of aspirin for the pain."), "drug or dose"),
    (note("x" * 300), "too long"),
])
def test_fabricated_or_unsafe_claim_is_dropped_and_counted(bad, why):
    r = run_investigator(SNAP, fake(notes=[bad, GOOD]))
    assert r.status == "ok" and len(r.notes) == 1 and r.dropped == 1 and r.dropped_reasons == (why,)
    assert not bad["claim"] or bad["claim"] not in json.dumps(r.to_dict())  # dropped text never reaches the panel or the record


def test_number_in_claim_must_come_from_cited_values():
    calls = [{"tool": "summary"}]
    ok = {"claim": "It was 2 hours since the EVA.", "evidence": [{"tool": "summary", "field": "hours_since_eva", "value": 2.0}]}
    bad = {"claim": "It was 9 hours since the EVA.", "evidence": ok["evidence"]}
    r = run_investigator(SNAP, fake(calls, [ok, bad]))
    assert [n["claim"] for n in r.notes] == [ok["claim"]] and r.dropped == 1


def test_bool_is_not_a_number_match():
    assert verify_note(note("Pain noted.", value=1), [("forms", {"post_eva.elbow_joint_pain": True})], [])[0] is None


def test_unknown_tool_requests_are_skipped_not_run():
    r = run_investigator(SNAP, fake(calls=[{"tool": "delete_record"}, {"tool": "forms"}]))
    assert r.status == "ok" and len(r.notes) == 1


def test_at_most_five_notes_are_kept():
    r = run_investigator(SNAP, fake(notes=[GOOD] * 8))
    assert len(r.notes) == 5 and r.dropped == 3


# ---------------------------------------------------------------- unavailable
def test_no_history_no_model_and_bad_replies_are_unavailable_never_raised():
    assert run_investigator(NoHistory("A", "no habitat service connected"), fake()).status == "unavailable"
    assert run_investigator(SNAP, None).reason == "no local model"
    r = run_investigator(SNAP, lambda p: "not json at all")
    assert r.status == "unavailable" and UNAVAILABLE in r.to_dict()["message"]

    def down(_):
        raise ConnectionError("refused")
    assert run_investigator(SNAP, down).status == "unavailable"


def test_time_box_is_enforced():
    release = threading.Event()
    try:
        r = run_investigator(SNAP, lambda p: release.wait(5) and "{}", time_box=0.2)
        assert r.status == "unavailable" and "time box" in r.reason and r.elapsed_s < 2
    finally:
        release.set()


# ------------------------------------------------------- through the emergency
def start(investigator, snapshot=True):
    eng = build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS,
                explainer=None, routing=True, investigator=investigator)
    if snapshot:
        eng.hot_summaries.update(fake_hot_summary("A", t=1))
    eng.trigger(trig("A", kind="manual"))
    eng.clock.advance(16)
    eng.tick()
    eng.accept("B")
    if eng.view("B")["screen"] == "observer":
        eng.observer_answer("B", "no")
    return eng


def panel(eng):
    eng.investigator.join(eng.active_for("A").id)
    return eng.view("B")["investigator"]


def test_notes_panel_is_separate_and_notes_leave_briefing_and_rule_untouched():
    eng = start(fake())
    before = {k: eng.view("B")[k] for k in ("briefing", "l0", "route")}
    p = panel(eng)
    after = eng.view("B")
    assert p["status"] == "ok" and p["notes"][0]["sources"] and "do not change the ranking" in p["label"]
    assert {k: after[k] for k in ("briefing", "l0", "route")} == before
    assert "investigator" not in after["briefing"]


def test_record_gets_notes_and_dropped_counts_without_dropped_text():
    eng = start(fake(notes=[GOOD, note("Give 500 mg of aspirin.")]))
    panel(eng)
    e = eng.active_for("A")
    ev = next(x for x in e.timeline if x["event"] == "investigator")
    assert len(ev["notes"]) == 1 and ev["dropped"] == 1 and ev["dropped_reasons"] == ["drug or dose"]
    assert "aspirin" not in json.dumps(e.timeline) and any(x["type"] == "copilot_investigator" for x in eng.events)


def test_panel_says_unavailable_on_failure_and_emergency_still_works():
    eng = start(lambda p: (_ for _ in ()).throw(ConnectionError("down")))
    p = panel(eng)
    assert p["status"] == "unavailable" and p["message"].startswith(UNAVAILABLE)
    assert eng.view("B")["screen"] in ("intake", "record", "step")


def test_no_history_shows_unavailable_with_the_reason():
    p = panel(start(fake(), snapshot=False))
    assert p["status"] == "unavailable" and "no history" in p["message"]


def test_running_state_while_the_model_is_busy():
    release = threading.Event()
    eng = start(lambda p: release.wait(5) and "{}")
    try:
        assert eng.view("B")["investigator"]["status"] == "running"
    finally:
        release.set()
