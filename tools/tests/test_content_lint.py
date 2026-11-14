"""Ticket 02 (Spec 5 task 5.3): content linter.

Test (a): fails on a protocol step with no source.
Test (b): fails on any drug name or dose in protocol content.
The real protocol files in content/protocols/ must lint clean.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import content_lint as cl  # noqa: E402

GOOD = {
    "schema_version": "1.0.0",
    "id": "test-protocol",
    "title": "Test protocol (fixture, not medical content)",
    "steps": [{
        "id": "s1",
        "text": "Fixture step text",
        "source": {"guideline": "Fixture guideline 2020", "section": "Results"},
        "equipment": [],
        "rescuers": 1,
    }],
}


def with_step(**changes):
    doc = copy.deepcopy(GOOD)
    doc["steps"][0].update(changes)
    return doc


def test_good_protocol_has_no_problems():
    assert cl.lint_protocol(GOOD) == []


def test_contract_violation_is_reported():
    doc = copy.deepcopy(GOOD)
    del doc["steps"][0]["rescuers"]
    assert any("contract" in p.lower() for p in cl.lint_protocol(doc))


@pytest.mark.parametrize("source", [
    {"guideline": "", "section": "Results"},
    {"guideline": "Fixture guideline", "section": "  "},
    {"guideline": None, "section": "Results"},
], ids=["empty-guideline", "blank-section", "null-guideline"])
def test_step_without_real_source_fails(source):
    problems = cl.lint_protocol(with_step(source=source))
    assert any("source" in p for p in problems)


def test_step_missing_source_fails():
    doc = copy.deepcopy(GOOD)
    del doc["steps"][0]["source"]
    assert cl.lint_protocol(doc)


@pytest.mark.parametrize("text", [
    "Give epinephrine now",
    "Consider Adrenaline",
    "amiodarone if shockable",
    "Give aspirin",
    "Inject 1 mg IV",
    "300mg loading",
    "0.5 mcg/kg",
    "10 mL of solution",
], ids=["epinephrine", "adrenaline-caps", "amiodarone", "aspirin",
        "dose-mg", "dose-mg-nospace", "dose-mcg", "dose-ml"])
def test_drug_name_or_dose_in_step_text_fails(text):
    problems = cl.lint_protocol(with_step(text=text))
    assert any("drug" in p or "dose" in p for p in problems)


def test_drug_in_equipment_fails():
    assert cl.lint_protocol(with_step(equipment=["AED", "epinephrine auto-injector"]))


def test_drug_in_title_fails():
    doc = copy.deepcopy(GOOD)
    doc["title"] = "Atropine protocol"
    assert cl.lint_protocol(doc)


def test_flight_surgeon_handoff_is_allowed():
    text = "Medication: per flight surgeon / onboard medical checklist"
    assert cl.lint_protocol(with_step(text=text)) == []


def test_numbers_without_dose_units_are_allowed():
    assert cl.lint_protocol(with_step(text="Give 30 compressions, then 2 breaths")) == []


def run_cli(content_dir):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "content_lint.py"), str(content_dir)],
                          capture_output=True, text=True)


def test_cli_exits_zero_on_clean_content(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "p.json").write_text(json.dumps(GOOD))
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr


def test_cli_exits_nonzero_and_names_file_on_problem(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "bad.json").write_text(json.dumps(with_step(text="Give 1 mg epinephrine")))
    result = run_cli(tmp_path)
    assert result.returncode == 1
    assert "bad.json" in result.stderr


def test_cli_fails_on_invalid_json(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "broken.json").write_text("{not json")
    assert run_cli(tmp_path).returncode == 1


def test_repo_content_lints_clean():
    protocols = list((ROOT / "content" / "protocols").glob("*.json"))
    assert protocols, "expected at least one protocol in content/protocols"
    result = run_cli(ROOT / "content")
    assert result.returncode == 0, result.stderr
