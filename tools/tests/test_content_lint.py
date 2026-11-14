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


@pytest.mark.parametrize("name", ["zolpidem", "Modafinil", "melatonin", "loratadine", "promethazine",
                                  "ciprofloxacin", "silver sulfadiazine", "loperamide"])
def test_iss_kit_drug_is_blocked(name):
    assert cl.lint_protocol(with_step(text=f"Take {name} now"))


def test_every_blocklist_group_has_source_basis_and_names():
    data = json.loads((ROOT / "tools" / "drug_blocklist.json").read_text())
    assert data["groups"]
    for g in data["groups"]:
        assert g["source"].strip() and g["basis"].strip() and g["names"]


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


def test_medication_mention_without_flight_surgeon_handoff_fails():
    problems = cl.lint_protocol(with_step(text="Give the cardiac medication from the kit"))
    assert any("flight surgeon" in p for p in problems)


def test_medicine_in_a_citation_is_allowed():
    src = {"guideline": "Society of Aerospace Medicine guideline 2020", "section": "Results"}
    assert cl.lint_protocol(with_step(source=src)) == []


# --- environment coverage (content/protocols/coverage.json) ---

def coverage(**env_changes):
    envs = {
        "spacecraft-transit": {"covered": True, "basis": "Aims and scope"},
        "station": {"covered": True, "basis": "Aims and scope"},
        "moon-base": {"covered": False, "label": "not covered by published guidance"},
        "mars-base": {"covered": False, "label": "not covered by published guidance"},
        "rover": {"covered": False, "label": "not covered by published guidance"},
    }
    envs.update(env_changes)
    return {"test-protocol": {"source": "Fixture guideline 2020", "environments": envs}}


def test_good_coverage_has_no_problems():
    assert cl.lint_coverage(coverage(), {"test-protocol"}) == []


def test_protocol_without_coverage_entry_fails():
    assert any("other-protocol" in p for p in cl.lint_coverage(coverage(), {"test-protocol", "other-protocol"}))


def test_coverage_for_unknown_protocol_fails():
    assert cl.lint_coverage(coverage(), set())


def test_every_environment_must_be_listed():
    doc = coverage()
    del doc["test-protocol"]["environments"]["rover"]
    assert any("rover" in p for p in cl.lint_coverage(doc, {"test-protocol"}))


def test_unknown_environment_fails():
    assert cl.lint_coverage(coverage(**{"asteroid": {"covered": False, "label": "x"}}), {"test-protocol"})


def test_covered_environment_needs_a_basis():
    assert cl.lint_coverage(coverage(station={"covered": True, "basis": " "}), {"test-protocol"})


def test_uncovered_environment_needs_the_honest_label():
    doc = coverage(**{"moon-base": {"covered": False, "label": "probably fine"}})
    assert cl.lint_coverage(doc, {"test-protocol"})


def test_coverage_needs_a_source():
    doc = coverage()
    doc["test-protocol"]["source"] = ""
    assert cl.lint_coverage(doc, {"test-protocol"})


def test_coverage_notes_need_a_section():
    doc = coverage()
    doc["test-protocol"]["environments"]["spacecraft-transit"]["notes"] = [{"text": "A note", "section": ""}]
    assert cl.lint_coverage(doc, {"test-protocol"})


def test_cli_fails_when_coverage_file_missing(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "p.json").write_text(json.dumps(GOOD))
    assert cl.lint_dir(tmp_path)


# --- Mission profiles (content/profiles/), test (d) ---

def profile(**changes):
    sourced = {"value": "x", "status": "sourced", "source": "https://www.nasa.gov/hrp/hazards/"}
    team = {"value": "y", "status": "not confirmed: team value"}
    doc = {"id": "test_profile", "name": "Test profile",
           **{f: dict(sourced) for f in cl.PROFILE_FIELDS}}
    doc["medical_kit"] = dict(team, value=[])
    doc.update(changes)
    return doc


def test_good_profile_has_no_problems():
    assert cl.lint_profile(profile()) == []


@pytest.mark.parametrize("field", ["gravity", "comm_delay", "medical_kit", "closed_habitat"])
def test_missing_profile_field_fails(field):
    doc = profile()
    del doc[field]
    assert any(field in p for p in cl.lint_profile(doc))


def test_value_with_no_status_fails():
    assert cl.lint_profile(profile(gravity={"value": "weightless"}))


def test_unknown_status_fails():
    assert cl.lint_profile(profile(gravity={"value": "weightless", "status": "probably"}))


@pytest.mark.parametrize("source", [None, "", "NASA website", "ftp://example.org"])
def test_sourced_value_needs_a_link(source):
    value = {"value": "weightless", "status": "sourced"}
    if source is not None:
        value["source"] = source
    assert any("link" in p for p in cl.lint_profile(profile(gravity=value)))


def test_team_value_needs_no_link():
    assert cl.lint_profile(profile(dust={"value": "none", "status": "not confirmed: team value"})) == []


def test_profile_needs_id_and_name():
    doc = profile()
    doc["name"] = ""
    assert cl.lint_profile(doc)


def test_bad_profile_file_fails_lint_dir(tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / "p.json").write_text(json.dumps(profile(gravity={"value": "x"})))
    assert tmp_path / "profiles" / "p.json" in cl.lint_dir(tmp_path)


def test_repo_has_a_mars_transit_profile():
    assert (ROOT / "content" / "profiles" / "mars_transit.json").exists()


def write_clean(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "p.json").write_text(json.dumps(GOOD))
    (tmp_path / "protocols" / "coverage.json").write_text(json.dumps(coverage()))


def test_main_returns_zero_on_clean_content(tmp_path, capsys):
    write_clean(tmp_path)
    assert cl.main(["content_lint.py", str(tmp_path)]) == 0
    assert "clean" in capsys.readouterr().out


def test_main_returns_one_and_reports_problem(tmp_path, capsys):
    write_clean(tmp_path)
    (tmp_path / "protocols" / "bad.json").write_text(json.dumps(with_step(text="Give 1 mg epinephrine")))
    assert cl.main(["content_lint.py", str(tmp_path)]) == 1
    assert "bad.json" in capsys.readouterr().err


def run_cli(content_dir):
    return subprocess.run([sys.executable, str(ROOT / "tools" / "content_lint.py"), str(content_dir)],
                          capture_output=True, text=True)


def test_cli_exits_zero_on_clean_content(tmp_path):
    write_clean(tmp_path)
    result = run_cli(tmp_path)
    assert result.returncode == 0, result.stderr


def test_cli_exits_nonzero_and_names_file_on_problem(tmp_path):
    write_clean(tmp_path)
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
