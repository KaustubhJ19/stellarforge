"""Tickets 09 (one cited step per screen, equipment filter) and 10 (roles, rescuer-count filter)."""
import json
import shutil

import pytest

from app import replay
from app.content import MEDICATION_PLACEHOLDER, CONTENT
from app.flow import FlowError
from app.runtime import build

PRESS = {"t": 0, "type": "press_emergency", "data": {"crew": "cmdr"}}


def to_steps(eng, rescuer="eng"):
    replay.run(eng, {"id": "t", "events": [PRESS]}, until=15)
    eng.accept(rescuer)
    eng.observer_answer(rescuer, "no")
    eng.next(rescuer)  # record -> contributors
    eng.next(rescuer)  # contributors -> first step
    return eng.active_for("cmdr")


def walk(eng, crew):
    """Collect the step ids a rescuer sees, one screen at a time."""
    seen = []
    while (v := eng.view(crew))["screen"] == "step":
        seen.append(v["step"]["id"])
        eng.next(crew)
    return seen, v["screen"]


@pytest.fixture
def content(tmp_path):
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    return root


def edit(root, rel, fn):
    p = root / rel
    data = json.loads(p.read_text(encoding="utf-8"))
    fn(data)
    p.write_text(json.dumps(data), encoding="utf-8")


# ---- 09 ------------------------------------------------------------------
def test_one_step_per_screen_with_source(eng):
    to_steps(eng)
    v = eng.view("eng")
    assert v["screen"] == "step" and set(v["step"]) == {"id", "text", "source", "equipment", "rescuers"}
    assert v["step"]["source"] == {"guideline": "STUB-GUIDELINE (not a real source)", "section": "STUB-S1"}
    assert v["stub"] is True and v["index"] == 1 and v["disclaimer"] == "Decision support, not diagnosis."


def test_solo_rescuer_walks_filtered_steps_then_report(eng):
    to_steps(eng)
    seen, end = walk(eng, "eng")
    assert seen == ["stub-1", "stub-2"]  # stub-3 needs 2 rescuers
    assert end == "report"


def test_equipment_not_on_board_is_hidden(content):
    edit(content, "profiles/stub-mars.json", lambda d: d.update(equipment=[]))
    eng = build(content_root=content)
    to_steps(eng)
    seen, _ = walk(eng, "eng")
    assert "stub-2" not in seen and seen == ["stub-1"]


def test_unsourced_step_is_refused_at_runtime(content):
    edit(content, "protocols/stub-protocol.json", lambda d: d["steps"][0].pop("source"))
    eng = build(content_root=content)
    assert [e["step"] for e in eng.events if e["type"] == "step_refused"] == ["stub-1"]
    to_steps(eng)
    seen, _ = walk(eng, "eng")
    assert "stub-1" not in seen


def test_step_with_dose_is_refused_at_runtime(content):
    edit(content, "protocols/stub-protocol.json", lambda d: d["steps"][1].update(text="STUB give 5 mg"))
    eng = build(content_root=content)
    assert any(e["type"] == "step_refused" and e["step"] == "stub-2" for e in eng.events)


def test_medication_step_shows_only_placeholder(content):
    edit(content, "protocols/stub-protocol.json", lambda d: d["steps"][0].update(text=MEDICATION_PLACEHOLDER))
    eng = build(content_root=content)
    to_steps(eng)
    assert eng.view("eng")["step"]["text"] == MEDICATION_PLACEHOLDER


def test_step_shown_and_completed_are_recorded_with_times(eng):
    e = to_steps(eng)
    eng.clock.advance(5)
    eng.next("eng")
    acts = [(a["action"], a["step"]) for a in e.actions]
    assert acts[:3] == [("shown", "stub-1"), ("completed", "stub-1"), ("shown", "stub-2")]
    assert e.actions[1]["t"] == eng.now()


def test_back_returns_to_previous_step(eng):
    to_steps(eng)
    eng.next("eng")
    assert eng.view("eng")["step"]["id"] == "stub-2"
    eng.back("eng")
    assert eng.view("eng")["step"]["id"] == "stub-1"


def test_step_text_is_read_only(eng):
    to_steps(eng)
    with pytest.raises(Exception):
        eng.protocol.steps[0].text = "changed"  # frozen dataclass


# ---- 10 ------------------------------------------------------------------
def test_two_rescuers_split_by_role(eng):
    to_steps(eng, "eng")
    eng.join_r2("sci")
    eng.next("sci")  # record -> contributors
    eng.next("sci")
    r2, _ = walk(eng, "sci")
    r1, _ = walk(eng, "eng")
    assert r1 == ["stub-1"]  # R1 track
    assert r2 == ["stub-2", "stub-3"]  # R2 track, two-rescuer step now visible
    assert any(e["type"] == "rescuer_assigned" and e["role"] == "R2" for e in eng.events)


def test_rescuer_2_joining_mid_flow_updates_without_restart(eng):
    to_steps(eng, "eng")
    eng.next("eng")  # now on stub-2 (solo sees all)
    eng.join_r2("sci")
    # stub-2 is R2's now; R1 moves on without restarting
    assert eng.view("eng")["screen"] == "report"
    assert eng.view("sci")["screen"] == "record"


def test_rover_profile_has_no_rescuer_2():
    eng = build(profile="stub-rover")
    replay.run(eng, {"id": "t", "events": [PRESS]}, until=15)
    eng.accept("eng")
    assert all(eng.view(c)["screen"] != "join_r2" for c in eng.crew)
    with pytest.raises(FlowError):
        eng.join_r2("cmdr")


def test_role_assignments_in_timeline(eng):
    e = to_steps(eng)
    eng.join_r2("sci")
    events = [x["event"] for x in e.timeline]
    assert "rescuer 1 assigned" in events and "rescuer 2 assigned" in events


def test_invalid_role_in_map_fails_loading(content):
    edit(content, "protocols/stub-protocol.roles.json", lambda d: d["roles"].update({"stub-1": "R3"}))
    with pytest.raises(ValueError):
        build(content_root=content)
