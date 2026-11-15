"""Ticket 02 / spec test (f): the content linter."""
import json
import subprocess
import sys
from pathlib import Path

import jsonschema
import pytest

import lint_content as L

REPO = Path(__file__).resolve().parents[2]
SRC = {"guideline": "FAKE-G", "section": "F-1"}
# Test-only fake names (the real deny-list is supplied by Spec 5).
FAKE_DENY = ["testdrugium", "fakeocillin"]


def proto(*steps):
    return {"id": "t", "title": "t", "steps": list(steps)}


def step(text="FAKE step text", source=SRC, sid="s1"):
    s = {"id": sid, "text": text, "equipment": [], "rescuers": 1}
    if source is not None:
        s["source"] = source
    return s


def reasons(data, deny=FAKE_DENY):
    return [i.reason for i in L.lint_data(data, "x.json", deny)]


def test_stub_protocol_matches_contract_and_passes():
    schema = json.loads((REPO / "contracts/protocol.schema.json").read_text(encoding="utf-8"))
    stub = json.loads((REPO / "content/protocols/stub-protocol.json").read_text(encoding="utf-8"))
    jsonschema.validate(stub, schema)
    assert stub["stub"] is True and len(stub["steps"]) == 3
    assert L.lint_tree(REPO / "content", L.load_deny_list()) == []


def test_step_without_source_fails_and_names_step():
    issues = L.lint_data(proto(step(source=None, sid="no-src")), "x.json", FAKE_DENY)
    assert len(issues) == 1 and issues[0].where == "step no-src" and "no source" in issues[0].reason


@pytest.mark.parametrize("src", [{"guideline": "G"}, {"section": "S"}, {"guideline": "", "section": "S"}, {"guideline": "G", "section": " "}])
def test_partial_source_fails(src):
    assert any("no source" in r for r in reasons(proto(step(source=src))))


@pytest.mark.parametrize("text", ["Give testdrugium now", "TESTDRUGIUM", "use FakeOcillin."])
def test_drug_name_fails(text):
    assert any(r.startswith("drug name") for r in reasons(proto(step(text))))


def test_drug_name_inside_other_word_does_not_match():
    assert reasons(proto(step("notestdrugiumx"))) == []


@pytest.mark.parametrize("text", ["300 mg", "300mg", "0.5 mg", "1 mg/kg", "10 mL", "2 units", "5 mcg", "1,5 g"])
def test_dose_fails(text):
    assert any(r.startswith("dose") for r in reasons(proto(step(f"FAKE step {text} here"))))


@pytest.mark.parametrize("text", ["30 compressions", "2 rescuers", "step 3 of 5", "wait 15 s", "per flight surgeon / onboard medical checklist"])
def test_non_dose_text_passes(text):
    assert reasons(proto(step(text))) == []


def test_threshold_without_source_fails_and_with_source_passes():
    assert reasons({"cards": [{"name": "x", "threshold": 1}]}) == ["threshold has no source"]
    assert reasons({"cards": [{"name": "x", "threshold": 1, "source": SRC}]}) == []


def test_drug_or_dose_in_any_content_file_fails():
    assert reasons({"answers": {"s1": "take 5 mg"}})


def test_cli_exits_nonzero_on_bad_content(tmp_path):
    (tmp_path / "bad.json").write_text(json.dumps(proto(step(source=None))), encoding="utf-8")
    r = subprocess.run([sys.executable, str(REPO / "tools/lint_content.py"), str(tmp_path)], capture_output=True, text=True)
    assert r.returncode == 1 and "LINT FAIL" in r.stdout
    r = subprocess.run([sys.executable, str(REPO / "tools/lint_content.py")], capture_output=True, text=True)
    assert r.returncode == 0, r.stdout


def test_glucose_lab_unit_is_not_a_dose():
    assert L.find_drug_or_dose("glucose above 250 mg/dL", []) is None


def test_real_dose_still_fails():
    assert L.find_drug_or_dose("give 250 mg now", []) is not None
