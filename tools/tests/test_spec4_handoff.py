"""Ticket 08 (Integration #1): files Spec 4's emergency engine needs from Spec 5.

Spec 4 (backend/app/content.py on integrate/spec2-into-emergency-services) loads, per protocol:
<id>.roles.json {roles: {step: R1|R2}}, <id>.excerpts.json {excerpts: [{step, section, text}]},
<id>.recorded.json {answers: {step: text}}; per profile: crew[], equipment[], delay_one_way_s, delay_label;
and tools/drug-denylist.txt (one drug name per line).
"""
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import content_lint as cl  # noqa: E402

PROTOCOLS = ["microgravity-cpr", "chest-pain"]
PROFILES = ["mars_transit", "station"]
P = ROOT / "content" / "protocols"


def load(path):
    return json.loads(path.read_text(encoding="utf-8"))


def step_ids(pid):
    return [s["id"] for s in load(P / f"{pid}.json")["steps"]]


@pytest.mark.parametrize("pid", PROTOCOLS)
def test_roles_name_real_steps_with_r1_or_r2(pid):
    roles = load(P / f"{pid}.roles.json")
    assert roles["protocol"] == pid and roles["roles"]
    assert set(roles["roles"]) <= set(step_ids(pid))
    assert set(roles["roles"].values()) <= {"R1", "R2"}


@pytest.mark.parametrize("pid", PROTOCOLS)
def test_every_step_has_a_sourced_excerpt(pid):
    doc = load(P / f"{pid}.excerpts.json")
    assert doc["protocol"] == pid
    by_step = {e["step"] for e in doc["excerpts"]}
    assert by_step == set(step_ids(pid))
    for e in doc["excerpts"]:
        assert e["section"].strip() and e["text"].strip()


@pytest.mark.parametrize("pid", PROTOCOLS)
def test_every_step_has_a_recorded_answer_without_drugs(pid):
    doc = load(P / f"{pid}.recorded.json")
    assert doc["protocol"] == pid and set(doc["answers"]) == set(step_ids(pid))
    for text in doc["answers"].values():
        assert text.strip()
        assert not cl.DRUG_RE.search(text) and not cl.DOSE_RE.search(text), text


@pytest.mark.parametrize("pid", PROTOCOLS)
def test_companion_files_hold_no_drug_or_dose(pid):
    for kind in ("excerpts", "recorded", "roles"):
        for text in cl._strings(load(P / f"{pid}.{kind}.json")):
            assert not cl.DRUG_RE.search(text) and not cl.DOSE_RE.search(text), (kind, text)


@pytest.mark.parametrize("prof", PROFILES)
def test_profile_has_the_fields_spec4_requires(prof):
    d = load(ROOT / "content" / "profiles" / f"{prof}.json")
    assert d["crew"] and all(isinstance(c, str) for c in d["crew"])
    assert isinstance(d["equipment"], list) and d["equipment"]
    assert d["delay_one_way_s"] == d["comm_delay"]["value"] * 60
    assert d["delay_label"].strip()


@pytest.mark.parametrize("prof", PROFILES)
def test_profile_carries_every_item_the_weightless_protocols_use(prof):
    # Spec 4 hides any step whose equipment is not on board; both profiles are weightless (covered).
    on_board = set(load(ROOT / "content" / "profiles" / f"{prof}.json")["equipment"])
    for pid in PROTOCOLS:
        for s in load(P / f"{pid}.json")["steps"]:
            assert set(s["equipment"]) <= on_board, (prof, s["id"], set(s["equipment"]) - on_board)


def test_drug_denylist_matches_the_sourced_blocklist():
    names = {n.lower() for g in load(ROOT / "tools" / "drug_blocklist.json")["groups"] for n in g["names"]}
    lines = (ROOT / "tools" / "drug-denylist.txt").read_text(encoding="utf-8").splitlines()
    listed = {l.strip().lower() for l in lines if l.strip() and not l.startswith("#")}
    assert listed == names


def test_lint_dir_skips_companion_files(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "x.roles.json").write_text(json.dumps({"protocol": "x", "roles": {}}))
    assert cl.lint_dir(tmp_path) == {}


@pytest.mark.parametrize("pid", PROTOCOLS)
def test_medical_review_sheet_lists_every_recorded_answer(pid):
    sheet = (ROOT / "docs" / "medical-review.md").read_text(encoding="utf-8")
    for sid in load(P / f"{pid}.recorded.json")["answers"]:
        assert f"| recorded `{sid}` |" in sheet, sid
