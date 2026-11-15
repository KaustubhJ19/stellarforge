"""Spec 2 action plans fall under the protocol safety rules (story 15; emergency-protocol-safety rules 2, 4, 9).

Linter rule (f): a non-stub plan with a step lacking a source, a drug name or dose, or no team approval fails.
Runtime: the daily loop refuses to load a plan whose step has no source. The shipped plans lint clean
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
from backend.daily_loop import load_plans  # noqa: E402

GOOD = {"schema_version": "1.0.0", "id": "fixture-plan", "title": "Fixture plan (not medical content)", "kind": "action-plan",
        "addresses": ["sleep_debt"], "approval": {"status": "approved", "approved_by": "fixture team", "approved_on": "2026-11-15"},
        "steps": [{"id": "f1", "text": "Fixture step text", "source": {"guideline": "Fixture guideline 2020", "section": "Results"},
                   "equipment": [], "rescuers": 1}]}


def write(folder, doc, name="fixture-plan.json"):
    (folder / "plans").mkdir(parents=True, exist_ok=True)
    (folder / "plans" / name).write_text(json.dumps(doc), encoding="utf-8")


def bad(change):
    doc = copy.deepcopy(GOOD)
    change(doc)
    return doc


@pytest.mark.parametrize("doc, problem", [
    (bad(lambda d: d["steps"][0]["source"].update(section="")), "source"),
    (bad(lambda d: d["steps"][0].update(text="Give 5 mg of fixture")), "dose"),
    (bad(lambda d: d["approval"].update(approved_by=None)), "approval"),
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
