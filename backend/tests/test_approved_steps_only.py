"""Spec 1 (protocol library): the engine is the second guard. Drafts never reach crew, even if the
build linter was skipped. Seam: the flow engine + offline bundle, as the tablet API sees them.
Fixtures are visibly fake ("STUB step N")."""
import json
import shutil

import pytest

from app import offline
from app.content import CONTENT, load_protocol
from app.runtime import REAL_RECORDS, build
from sf_helpers import trig

import lint_content as lc

APPROVER = "Fixture Approver (not a real person)"
GUIDE = "STUB-GUIDELINE (not a real source)"


def step(n, **extra):
    return {"id": f"fx-{n}", "text": f"STUB step {n}", "source": {"guideline": GUIDE, "section": f"STUB-S{n}"},
            "equipment": [], "rescuers": 1, **extra}


def approved(s):
    s = dict(s, status="approved", approved_by=APPROVER, approved_on="2026-11-15")
    return dict(s, approved_hash=lc.step_hash(s))


def draft(s):
    return dict(s, status="draft", drafted_by="STUB tool / STUB model")


def protocol(pid, steps, **extra):
    return {"schema_version": "1.0.0", "id": pid, "title": f"STUB {pid} (not medical content)", "steps": steps, **extra}


@pytest.fixture
def content(tmp_path):
    root = tmp_path / "content"
    shutil.copytree(CONTENT, root)
    (root / "approvers.json").write_text(json.dumps({"approvers": [APPROVER]}), encoding="utf-8")
    edited = approved(step(4))
    edited["text"] = "STUB step 4, edited after approval"
    docs = {
        "fx-mixed": protocol("fx-mixed", [approved(step(1)), draft(step(2)), approved(step(3)), edited]),
        "fx-drafts": protocol("fx-drafts", [draft(step(1)), draft(step(2))]),
        "fx-stub": protocol("fx-stub", [step(1, text="Not stub text")], stub=True),
    }
    for pid, doc in docs.items():
        (root / "protocols" / f"{pid}.json").write_text(json.dumps(doc), encoding="utf-8")
    routes = json.loads((root / "triage" / "routes.json").read_text(encoding="utf-8"))
    routes["rows"] = [
        {"id": "fx-injury", "when": {"main_problem": "injury"}, "protocol": "fx-mixed", "reason": "STUB reason A."},
        {"id": "fx-other", "when": {"main_problem": "other"}, "protocol": "fx-drafts", "reason": "STUB reason B."},
        {"id": "fx-breathing", "when": {"main_problem": "breathing_trouble"}, "protocol": "fx-stub",
         "reason": "STUB reason C."},
    ] + routes["rows"]
    (root / "triage" / "routes.json").write_text(json.dumps(routes), encoding="utf-8")
    return root


@pytest.fixture
def eng(content):
    return build(protocol="stub-protocol", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                 routing=True, content_root=content)


def routed(eng, main_problem):
    eng.trigger(trig("A"))
    eng.clock.advance(16)
    eng.tick()
    eng.accept("B")
    if eng.view("B")["screen"] == "observer":
        eng.observer_answer("B", "no")
    eng.submit_intake("B", {"responsive": "yes", "breathing": "normal", "main_problem": main_problem})
    return eng.view("B")["route"]


def seen_steps(eng, crew="B"):
    while eng.view(crew)["screen"] in ("record", "contributors"):
        eng.next(crew)
    seen = []
    while (v := eng.view(crew))["screen"] == "step":
        seen.append(v["step"]["text"])
        eng.next(crew)
    return seen


def test_loader_keeps_only_approved_unchanged_steps(content):
    p = load_protocol("fx-mixed", content)
    assert [s.id for s in p.steps] == ["fx-1", "fx-3"]
    assert {sid for sid, _ in p.refused} == {"fx-2", "fx-4"}


def test_loader_refuses_drafts_without_an_approvers_list(content):
    (content / "approvers.json").unlink()
    assert load_protocol("fx-mixed", content).steps == ()


def test_approved_protocol_routes_and_renders_only_approved_steps(eng):
    assert routed(eng, "injury")["protocol_id"] == "fx-mixed"
    assert seen_steps(eng) == ["STUB step 1", "STUB step 3"]


def test_draft_only_protocol_routes_to_not_covered(eng):
    route = routed(eng, "other")
    assert route["protocol_id"] is None and route["rule_id"] == "fx-other"
    assert "Contact ground" in route["reason"]


def test_stub_protocol_is_never_routed(eng):
    route = routed(eng, "breathing_trouble")
    assert route["protocol_id"] is None


def test_stub_protocol_with_non_stub_text_shows_no_steps(content):
    assert load_protocol("fx-stub", content).steps == ()


def test_offline_bundle_holds_approved_protocols_and_steps_only(eng):
    b = offline.bundle(eng)
    assert "fx-drafts" not in b["protocols"] and "fx-stub" not in b["protocols"]
    assert [s["text"] for s in b["protocols"]["fx-mixed"]["steps"]] == ["STUB step 1", "STUB step 3"]
    shown = json.dumps(b["protocols"])
    assert "fx-2" not in shown and "edited after approval" not in shown


def test_rendered_step_carries_no_approval_bookkeeping(eng):
    routed(eng, "injury")
    while eng.view("B")["screen"] in ("record", "contributors"):
        eng.next("B")
    assert set(eng.view("B")["step"]) == {"id", "text", "source", "equipment", "rescuers"}


# ---- the real route table and condition records (Spec 1 stories 21, 22, 2) -----------------------

from app import triage  # noqa: E402

REAL_ROUTES = json.loads((CONTENT / "triage" / "routes.json").read_text(encoding="utf-8"))
CONDITIONS = [json.loads(p.read_text(encoding="utf-8")) for p in sorted((CONTENT / "conditions").glob("*.json"))]


def test_every_condition_has_a_router_row_or_waits_for_a_team_agreed_intake_value():
    routed_ids = {r["protocol"] for r in REAL_ROUTES["rows"]}
    waiting = set(REAL_ROUTES["unrouted_conditions"]) - {"note"}
    for c in CONDITIONS:
        assert c["protocol"] in routed_ids or c["id"] in waiting, c["id"]


def test_route_rows_only_use_values_the_intake_offers():
    for row in REAL_ROUTES["rows"]:
        for key, want in row["when"].items():
            if key in triage.INTAKE_VALUES:
                for v in want if isinstance(want, list) else [want]:
                    assert v in triage.INTAKE_VALUES[key], (row["id"], key, v)


def test_pending_condition_rows_resolve_to_not_covered():
    pending = {c["protocol"] for c in CONDITIONS if c["state"] == "pending"}
    assert pending <= set(REAL_ROUTES["pending_protocols"])
    collapse = {"responsive": "yes", "breathing": "normal", "main_problem": "collapse", "source": "tap"}
    r = triage.route(REAL_ROUTES, collapse, {}, available={"microgravity-cpr", "chest-pain"})
    assert r["protocol_id"] is None and r["rule_id"] == "collapse-responsive" and "Contact ground" in r["reason"]


def test_no_pending_protocol_file_ships_without_approved_steps():
    """A pending condition either has no protocol file yet, or the engine finds no approved step in it."""
    for pid in REAL_ROUTES["pending_protocols"]:
        if (CONTENT / "protocols" / f"{pid}.json").exists():
            assert load_protocol(pid).steps == (), f"{pid} has approved steps: move it out of pending_protocols"


@pytest.mark.parametrize("breathing", ["abnormal", "none"])
def test_collapse_row_never_catches_a_patient_not_breathing_normally(breathing):
    intake = {"responsive": "yes", "breathing": breathing, "main_problem": "collapse", "source": "tap"}
    r = triage.route(REAL_ROUTES, intake, {}, available={"microgravity-cpr", "chest-pain", "fainting"})
    assert r["rule_id"] != "collapse-responsive" and r["protocol_id"] != "fainting"
