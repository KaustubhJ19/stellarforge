"""Spec 1 (protocol library): the build linter enforces "AI drafts, humans approve, AI never overrides".

Seam: tools/content_lint.lint_dir on a throwaway content folder. Fixtures are visibly fake.
"""
import copy
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import content_lint as cl  # noqa: E402
import lint_content as lc  # noqa: E402

APPROVER = "Fixture Approver (not a real person)"
GUIDE = "STUB-GUIDELINE (not a real source)"
ENVS = {e: {"covered": False, "label": cl.NOT_COVERED} for e in cl.ENVIRONMENTS}


def approved(step, by=APPROVER, on="2026-11-15"):
    s = dict(step, status="approved", approved_by=by, approved_on=on)
    s["approved_hash"] = lc.step_hash(s)
    return s


STEP = {"id": "fx-1", "text": "STUB step 1", "source": {"guideline": GUIDE, "section": "STUB-S1"},
        "equipment": [], "rescuers": 1}
PROTOCOL = {"schema_version": "1.0.0", "id": "fx", "title": "Fixture protocol (not medical content)",
            "condition_ids": ["fx-condition"], "steps": [approved(STEP)]}
PACK = {"protocol": "fx", "conditions": ["fx-condition"], "why": "STUB why",
        "sources": [{"guideline": GUIDE, "licence": "STUB licence", "licence_checked": False}],
        "recommendations": [{"guideline": GUIDE, "section": "STUB-S1", "quotes": ["STUB quote 1"]}],
        "microgravity": "STUB applicability", "pulse": {"model": "no", "scenario": None}}
CONDITION = {"id": "fx-condition", "name": "Fixture condition", "protocol": "fx", "state": "existing",
             "prior_incidence": {"status": "pending", "value": None, "source": None},
             "signs": [], "pulse": {"model": "no", "scenario": None}, "labels": ["STUB label"]}


def write(root, rel, doc):
    p = root / rel
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(doc), encoding="utf-8")


@pytest.fixture
def tree(tmp_path):
    """Build a content folder; returns a function that lints it with overrides."""
    root = tmp_path / "content"

    def make(protocol=PROTOCOL, pack=PACK, approvers=(APPROVER,), condition=CONDITION):
        write(root, "approvers.json", {"approvers": list(approvers)})
        write(root, "protocols/fx.json", protocol)
        if pack is not None:
            write(root, "protocols/fx.evidence.json", pack)
        if not protocol.get("stub"):  # stubs are test doubles: no coverage entry, like stub-protocol
            write(root, "protocols/coverage.json", {"fx": {"source": GUIDE, "environments": ENVS}})
        if condition is not None:
            write(root, "conditions/fx-condition.json", condition)
        return {p.name: v for p, v in cl.lint_dir(root).items()}
    return make


def with_step(**changes):
    doc = copy.deepcopy(PROTOCOL)
    doc["steps"][0].update(changes)
    return doc


def test_approved_cited_protocol_lints_clean(tree):
    assert tree() == {}


def test_draft_step_fails_the_build(tree):
    draft = dict(STEP, status="draft", drafted_by="STUB tool / STUB model")
    failures = tree(protocol=dict(PROTOCOL, steps=[draft]))
    assert any("not approved" in p for p in failures["fx.json"])


def test_step_without_status_fails_the_build(tree):
    failures = tree(protocol=dict(PROTOCOL, steps=[STEP]))
    assert any("not approved" in p for p in failures["fx.json"])


def test_draft_without_drafted_by_fails(tree):
    failures = tree(protocol=dict(PROTOCOL, steps=[dict(STEP, status="draft")]))
    assert any("drafted_by" in p for p in failures["fx.json"])


@pytest.mark.parametrize("name", ["Fixture Aprover (typo)", "Claude", ""])
def test_approver_not_on_the_list_fails(tree, name):
    failures = tree(protocol=dict(PROTOCOL, steps=[approved(STEP, by=name)]))
    assert any("approvers list" in p for p in failures["fx.json"])


def test_empty_approvers_list_means_nothing_is_approved(tree):
    failures = tree(approvers=())
    assert any("approvers list" in p for p in failures["fx.json"])


@pytest.mark.parametrize("on", [None, "15/11/2026", "2026-13-40"])
def test_approved_step_needs_a_real_date(tree, on):
    failures = tree(protocol=dict(PROTOCOL, steps=[approved(STEP, on=on)]))
    assert any("approved_on" in p for p in failures["fx.json"])


@pytest.mark.parametrize("change", [
    {"text": "STUB step 1, edited after approval"},
    {"source": {"guideline": GUIDE, "section": "STUB-S2"}},
    {"rescuers": 2},
    {"equipment": ["stub-kit"]},
], ids=["text", "section", "rescuers", "equipment"])
def test_any_edit_to_an_approved_step_returns_it_to_draft(tree, change):
    failures = tree(protocol=with_step(**change))
    assert any("changed after approval" in p for p in failures["fx.json"])


def test_approved_step_citing_a_section_missing_from_the_pack_fails(tree):
    pack = dict(PACK, recommendations=[{"guideline": GUIDE, "section": "STUB-S9", "quotes": ["STUB quote"]}])
    failures = tree(pack=pack)
    assert any("evidence pack" in p and "STUB-S1" in p for p in failures["fx.json"])


def test_approved_protocol_without_an_evidence_pack_fails(tree):
    failures = tree(pack=None)
    assert any("evidence pack" in p for p in failures["fx.json"])


def test_dose_text_still_fails_even_when_approved(tree):
    failures = tree(protocol=dict(PROTOCOL, steps=[approved(dict(STEP, text="STUB give 5 mg"))]))
    assert any("dose" in p for p in failures["fx.json"])


@pytest.mark.parametrize("missing", ["why", "sources", "recommendations", "microgravity", "pulse"])
def test_evidence_pack_needs_every_part(tree, missing):
    pack = {k: v for k, v in PACK.items() if k != missing}
    failures = tree(pack=pack)
    assert any(missing in p for p in failures["fx.evidence.json"])


def test_evidence_pack_source_needs_a_licence(tree):
    failures = tree(pack=dict(PACK, sources=[{"guideline": GUIDE, "licence": ""}]))
    assert any("licence" in p for p in failures["fx.evidence.json"])


def test_evidence_pack_recommendation_needs_a_quote(tree):
    pack = dict(PACK, recommendations=[{"guideline": GUIDE, "section": "STUB-S1", "quotes": []}])
    failures = tree(pack=pack)
    assert any("quote" in p for p in failures["fx.evidence.json"])


# ---- stubs cannot be used to slip content past the gate -------------------------------------

def test_stub_protocol_with_non_stub_text_fails(tree):
    stub = dict(PROTOCOL, stub=True, steps=[dict(STEP, text="Press firmly on the chest")])
    failures = tree(protocol=stub, pack=None, condition=None)
    assert any("STUB" in p for p in failures["fx.json"])


def test_stub_may_carry_the_fixed_medication_handoff(tree):
    stub = dict(PROTOCOL, stub=True, steps=[dict(STEP, text=lc.MEDICATION_PLACEHOLDER)])
    assert tree(protocol=stub, pack=None, condition=None) == {}


def test_stub_protocol_with_stub_text_needs_no_approval(tree):
    stub = dict(PROTOCOL, stub=True, steps=[STEP])
    assert tree(protocol=stub, pack=None, condition=None) == {}


# ---- condition records ----------------------------------------------------------------------

@pytest.mark.parametrize("missing", ["name", "protocol", "state", "prior_incidence", "pulse", "labels", "signs"])
def test_condition_record_needs_every_field(tree, missing):
    failures = tree(condition={k: v for k, v in CONDITION.items() if k != missing})
    assert any(missing in p for p in failures["fx-condition.json"])


def test_sourced_prior_needs_a_value_and_a_source(tree):
    cond = dict(CONDITION, prior_incidence={"status": "sourced", "value": 0.01, "source": ""})
    assert any("source" in p for p in tree(condition=cond)["fx-condition.json"])


def test_team_value_prior_is_allowed_with_a_value(tree):
    cond = dict(CONDITION, prior_incidence={"status": "team value", "value": 0.01, "source": None})
    assert tree(condition=cond) == {}


def test_pending_prior_has_no_value(tree):
    cond = dict(CONDITION, prior_incidence={"status": "pending", "value": 0.5, "source": None})
    assert any("pending" in p for p in tree(condition=cond)["fx-condition.json"])


def test_sign_with_likelihood_ratio_needs_a_source(tree):
    cond = dict(CONDITION, signs=[{"sign": "STUB sign", "lr_positive": 3.0, "source": ""}])
    assert any("sign" in p for p in tree(condition=cond)["fx-condition.json"])


def test_existing_condition_must_name_a_protocol_on_disk(tree):
    cond = dict(CONDITION, protocol="no-such-protocol")
    assert any("no-such-protocol" in p for p in tree(condition=cond)["fx-condition.json"])


def test_pending_condition_may_name_a_protocol_not_written_yet(tree):
    cond = dict(CONDITION, protocol="not-written-yet", state="pending")
    assert tree(condition=cond) == {}


# ---- the real library --------------------------------------------------------------------------

def test_every_real_condition_record_lints_clean():
    failures = {p.name: v for p, v in cl.lint_dir(ROOT / "content").items() if p.parent.name == "conditions"}
    assert failures == {}


def test_every_new_condition_from_spec_1_has_a_record():
    ids = {p.stem for p in (ROOT / "content" / "conditions").glob("*.json")}
    assert ids >= {"cardiac-arrest", "chest-pain", "fainting", "low-blood-sugar", "cabin-air", "severe-bleeding",
                   "sepsis", "overheating", "decompression-sickness", "seizure", "head-injury"}


def test_real_evidence_packs_lint_clean():
    failures = {p.name: v for p, v in cl.lint_dir(ROOT / "content").items() if p.name.endswith(".evidence.json")}
    assert failures == {}


# ---- the approval tool (run by a person, never by an AI) -------------------------------------

import subprocess  # noqa: E402

import approve_steps  # noqa: E402


def test_approve_tool_refuses_without_a_terminal():
    r = subprocess.run([sys.executable, str(ROOT / "tools" / "approve_steps.py"), "microgravity-cpr"],
                       input="anyone\ny\n", capture_output=True, text=True)
    assert r.returncode == 2 and "human act" in r.stderr


def test_approve_records_name_date_and_hash_that_lints_clean(tree):
    doc = dict(PROTOCOL, steps=[dict(STEP, status="draft", drafted_by="STUB tool / STUB model")])
    approve_steps.approve(doc, ["fx-1"], APPROVER, {APPROVER}, "2026-11-15")
    s = doc["steps"][0]
    assert (s["status"], s["approved_by"], s["approved_on"]) == ("approved", APPROVER, "2026-11-15")
    assert tree(protocol=doc) == {}


def test_approve_rejects_a_name_not_on_the_list():
    with pytest.raises(approve_steps.ApprovalError):
        approve_steps.approve(copy.deepcopy(PROTOCOL), ["fx-1"], "Claude", {APPROVER}, "2026-11-15")


# ---- the review sheet -----------------------------------------------------------------------------

import review_sheet  # noqa: E402


def test_review_sheet_puts_each_draft_next_to_its_quote():
    doc = dict(PROTOCOL, steps=[dict(STEP, status="draft", drafted_by="STUB tool / STUB model"),
                                dict(STEP, id="fx-2", source={"guideline": GUIDE, "section": "STUB-S9"}, status="draft",
                                     drafted_by="STUB tool")])
    sheet = review_sheet.render(doc, PACK, {APPROVER})
    row1 = next(line for line in sheet.splitlines() if line.startswith("| `fx-1`"))
    assert "STUB step 1" in row1 and "STUB quote 1" in row1 and "draft (STUB tool / STUB model)" in row1
    assert "not in evidence pack" in next(line for line in sheet.splitlines() if line.startswith("| `fx-2`"))


def test_review_sheet_shows_who_approved():
    sheet = review_sheet.render(PROTOCOL, PACK, {APPROVER})
    assert f"approved by {APPROVER} on 2026-11-15" in sheet


# ---- the second linter (tools/lint_content.py) runs the same gate -----------------------------------

def test_second_linter_also_fails_a_draft_and_passes_an_approved_step(tmp_path):
    write(tmp_path, "approvers.json", {"approvers": [APPROVER]})
    write(tmp_path, "protocols/fx.json", dict(PROTOCOL, steps=[approved(STEP), dict(STEP, id="fx-2", status="draft",
                                                                                     drafted_by="STUB tool")]))
    issues = lc.lint_tree(tmp_path, lc.load_deny_list())
    assert [(i.where, "not approved" in i.reason) for i in issues] == [("step fx-2", True)]


def test_second_linter_fails_a_stub_with_real_looking_text(tmp_path):
    write(tmp_path, "protocols/fx.json", dict(PROTOCOL, stub=True, steps=[dict(STEP, text="Press on the chest")]))
    assert any("STUB" in i.reason for i in lc.lint_tree(tmp_path, lc.load_deny_list()))


# ---- Ponytail review follow-ups ------------------------------------------------------------------------

def test_approved_step_without_a_source_is_reported_not_a_crash(tree):
    s = {k: v for k, v in STEP.items() if k != "source"}
    failures = tree(protocol=dict(PROTOCOL, steps=[approved(s)]))
    assert any("evidence pack" in p or "contract" in p for p in failures["fx.json"])


def test_approve_tool_rejects_an_unknown_step_id_before_asking_anything(monkeypatch, capsys, tmp_path):
    write(tmp_path, "approvers.json", {"approvers": [APPROVER]})
    write(tmp_path, "protocols/fx.json", PROTOCOL)
    monkeypatch.setattr(sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr(sys.stdout, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda *_: pytest.fail("must not prompt"))
    assert approve_steps.main(["fx", "--step", "fx-typo", "--content", str(tmp_path)]) == 1
    assert "fx-typo" in capsys.readouterr().err
