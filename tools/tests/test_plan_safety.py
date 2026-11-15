"""Spec 2 action plans fall under the protocol safety rules (story 15; emergency-protocol-safety rules 2, 4, 9).

Linter rule (f): a non-stub plan with a step lacking a source, a drug name or dose, or Spec 1 approval fails.
Runtime: the daily loop refuses a plan whose step has no source or a stub with non-STUB text, and serves only
steps approved by a listed name, unchanged since approval (Spec 1 rule 1). The shipped plans lint clean
(they are STUB placeholders until the team authors them through the Spec 1 workflow).
Fixtures are visibly fake.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT))

import content_lint as cl  # noqa: E402
import lint_content as lc  # noqa: E402
from backend.daily_loop import load_plans  # noqa: E402

APPROVER = "Fixture Approver (not a real person)"
GUIDE = "Fixture guideline 2020"


def approved(step):
    step = dict(step, status="approved", approved_by=APPROVER, approved_on="2026-11-15")
    return dict(step, approved_hash=lc.step_hash(step))


GOOD = {"schema_version": "1.0.0", "id": "fixture-plan", "title": "Fixture plan (not medical content)", "kind": "action-plan",
        "addresses": ["sleep_debt"],
        "steps": [approved({"id": "f1", "text": "Fixture step text", "source": {"guideline": GUIDE, "section": "Results"},
                            "equipment": [], "rescuers": 1})]}
PACK = {"protocol": "fixture-plan", "recommendations": [{"guideline": GUIDE, "section": "Results", "quotes": ["Fixture quote"]}]}


def write(folder, doc, name="fixture-plan.json"):
    (folder / "plans").mkdir(parents=True, exist_ok=True)
    (folder / "plans" / name).write_text(json.dumps(doc), encoding="utf-8")
    (folder / "plans" / "fixture-plan.evidence.json").write_text(json.dumps(PACK), encoding="utf-8")
    (folder / "approvers.json").write_text(json.dumps({"approvers": [APPROVER]}), encoding="utf-8")


def edited(d):
    d["steps"][0]["text"] = "Fixture step text, edited after approval"


def bad(change):
    doc = copy.deepcopy(GOOD)
    change(doc)
    return doc


@pytest.mark.parametrize("doc, problem", [
    (bad(lambda d: d["steps"][0]["source"].update(section="")), "source"),
    (bad(lambda d: d["steps"][0].update(text="Give 5 mg of fixture")), "dose"),
    (bad(lambda d: d["steps"][0].update(status="draft", drafted_by="STUB tool / STUB model")), "not approved"),
    (bad(lambda d: d["steps"][0].update(approved_by="Someone else")), "not on the approvers list"),
    (bad(edited), "changed after approval"),
    (bad(lambda d: d["steps"].__setitem__(0, approved(dict(d["steps"][0], source={"guideline": GUIDE, "section": "Not in pack"})))),
     "not in its evidence pack"),
])
def test_linter_fails_an_unsafe_or_unapproved_plan(tmp_path, doc, problem):
    write(tmp_path, doc)
    failures = cl.lint_dir(tmp_path)
    assert any(problem in p for ps in failures.values() for p in ps), failures


def test_linter_passes_an_approved_sourced_plan(tmp_path):
    write(tmp_path, GOOD)
    assert not cl.lint_dir(tmp_path)


def test_shipped_plans_lint_clean():
    assert not {p: v for p, v in cl.lint_dir(ROOT / "content").items() if "plans" in str(p)}


def test_runtime_refuses_a_plan_with_an_unsourced_step(tmp_path):
    write(tmp_path, bad(lambda d: d["steps"][0]["source"].update(guideline=" ")))
    with pytest.raises(ValueError, match="no source"):
        load_plans(tmp_path / "plans")


def test_shipped_plans_are_marked_draft_stubs_until_the_team_approves_them():
    plans = load_plans()
    assert set(plans) == {"hydration", "sleep-timing", "exercise-countermeasure", "co2-check", "crew-check-in", "call-ground"}
    for p in plans.values():
        assert p["stub"] is True and p["title"].startswith("STUB") and p["approval"]["approved_by"] is None
        assert all(s["text"].startswith("STUB") for s in p["steps"])


def test_runtime_serves_only_approved_unchanged_plan_steps(tmp_path):
    doc = copy.deepcopy(GOOD)
    doc["steps"].append(dict(GOOD["steps"][0], id="f2", status="draft", drafted_by="STUB tool / STUB model"))
    write(tmp_path, doc)
    assert [s["id"] for s in load_plans(tmp_path / "plans")["fixture-plan"]["steps"]] == ["f1"]


@pytest.mark.parametrize("change", [lambda d: d["steps"][0].update(status="draft", drafted_by="STUB tool"), edited])
def test_runtime_never_loads_a_plan_with_no_approved_step(tmp_path, change):
    write(tmp_path, bad(change))
    assert load_plans(tmp_path / "plans") == {}


def test_runtime_refuses_a_stub_plan_with_real_looking_text(tmp_path):
    write(tmp_path, bad(lambda d: d.update(stub=True)))
    with pytest.raises(ValueError, match="non-STUB"):
        load_plans(tmp_path / "plans")
