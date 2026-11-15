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


# --- Safety bounds and detection cut-offs (content/profiles/detection-cut-offs.json) ---

def bounds(**bound_changes):
    b = {"indicator": "heart_rate", "low": 50, "high": 150, "label": "Earth reference, no space data",
         "source": "AHA 2025 algorithms https://cpr.heart.org/"}
    b.update(bound_changes)
    return {"cutoffs": [{"name": "drift_red", "value": 8, "label": "team value", "source": "twice drift_amber"}],
            "safety_bounds": [b]}


def test_good_bounds_have_no_problems():
    assert cl.lint_bounds(bounds()) == []


@pytest.mark.parametrize("source", ["", "  ", None])
def test_bound_with_no_source_fails(source):
    assert any("source" in p for p in cl.lint_bounds(bounds(source=source)))


def test_bound_needs_a_label():
    assert cl.lint_bounds(bounds(label=""))


def test_bound_with_neither_limit_fails():
    assert cl.lint_bounds(bounds(low=None, high=None))


def test_one_sided_bound_is_allowed():
    assert cl.lint_bounds(bounds(high=None)) == []


def test_low_above_high_fails():
    assert cl.lint_bounds(bounds(low=160, high=150))


def test_nonstandard_label_needs_a_linked_source():
    assert cl.lint_bounds(bounds(label="crew personal value", source="crew record"))
    assert cl.lint_bounds(bounds(label="crew personal value", source="NASA https://nlsp.nasa.gov/x")) == []


def test_cutoff_with_no_source_fails():
    doc = bounds()
    doc["cutoffs"][0]["source"] = ""
    assert cl.lint_bounds(doc)


def test_bounds_file_is_not_linted_as_a_profile(tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / cl.BOUNDS_FILE).write_text(json.dumps(bounds()))
    assert cl.lint_dir(tmp_path) == {}


def test_bad_bounds_file_fails_lint_dir(tmp_path):
    (tmp_path / "profiles").mkdir()
    (tmp_path / "profiles" / cl.BOUNDS_FILE).write_text(json.dumps(bounds(source="")))
    assert tmp_path / "profiles" / cl.BOUNDS_FILE in cl.lint_dir(tmp_path)


@pytest.mark.parametrize("indicator", ["heart_rate", "systolic_bp", "glucose", "body_temperature"])
def test_repo_has_a_safety_bound_for(indicator):
    doc = json.loads((ROOT / "content" / "profiles" / cl.BOUNDS_FILE).read_text())
    assert indicator in {b["indicator"] for b in doc["safety_bounds"]}


# --- Measurement cards (content/cards/), test (c) ---

def card(**changes):
    doc = {"indicator": "heart_rate", "unit": "bpm",
           "how": ["Read it from the wearable."],
           "why": {"text": "Fixture why.", "hrp_risk": "Risk of Cardiovascular Adaptations",
                   "source": "https://www.nasa.gov/hrp/risks/"},
           "if_abnormal": {"now": "a", "remeasure": "b", "tell_crew": "c", "tell_ground": "d"},
           "space_note": "Fixture note.", "labels": ["team value"], "sources": ["https://www.nasa.gov/hrp/risks/"]}
    doc.update(changes)
    return doc


def test_good_card_has_no_problems():
    assert cl.lint_card(card()) == []


def test_why_must_name_a_real_hrp_risk():
    problems = cl.lint_card(card(why={"text": "x", "hrp_risk": "Risk of Being Unwell", "source": "s"}))
    assert any("HRP risk" in p for p in problems)


def test_uncovered_risk_is_allowed_with_a_reason():
    why = {"text": "x", "hrp_risk": "uncovered", "uncovered_reason": "No HRP risk names it.", "source": "s"}
    assert cl.lint_card(card(why=why)) == []


def test_uncovered_risk_needs_a_reason():
    assert cl.lint_card(card(why={"text": "x", "hrp_risk": "uncovered", "source": "s"}))


def test_why_needs_a_source():
    assert cl.lint_card(card(why={"text": "x", "hrp_risk": "Risk of Cardiovascular Adaptations", "source": ""}))


@pytest.mark.parametrize("key", ["now", "remeasure", "tell_crew", "tell_ground"])
def test_every_if_abnormal_step_is_filled(key):
    steps = {"now": "a", "remeasure": "b", "tell_crew": "c", "tell_ground": "d", key: ""}
    assert cl.lint_card(card(if_abnormal=steps))


@pytest.mark.parametrize("field", ["how", "unit", "space_note", "indicator"])
def test_card_fields_are_required(field):
    doc = card()
    del doc[field]
    assert cl.lint_card(doc)


@pytest.mark.parametrize("text", ["Below 54 mg/dL", "3.0 mmol/L", "about 1.8 mSv/day"])
def test_concentrations_are_not_doses(text):
    assert cl.lint_card(card(space_note=text)) == []


def test_drug_or_dose_on_a_card_fails():
    assert cl.lint_card(card(how=["Take 5 mg melatonin"]))


def test_bad_card_file_fails_lint_dir(tmp_path):
    (tmp_path / "cards").mkdir()
    (tmp_path / "cards" / "hr.json").write_text(json.dumps(card(unit="")))
    assert tmp_path / "cards" / "hr.json" in cl.lint_dir(tmp_path)


@pytest.mark.parametrize("indicator", ["heart_rate", "systolic_bp", "sleep_duration", "glucose",
                                       "body_temperature", "mood"])
def test_repo_has_a_card_for(indicator):
    assert (ROOT / "content" / "cards" / f"{indicator}.json").exists()


def write_clean(tmp_path):
    """Clean = cited, no drugs or doses, and (Spec 1) approved by a listed person with an evidence pack."""
    import lint_content as lc

    (tmp_path / "protocols").mkdir()
    name = "Fixture Approver (not a real person)"
    doc = copy.deepcopy(GOOD)
    s = doc["steps"][0]
    s.update(status="approved", approved_by=name, approved_on="2026-11-15")
    s["approved_hash"] = lc.step_hash(s)
    (tmp_path / "approvers.json").write_text(json.dumps({"approvers": [name]}))
    (tmp_path / "protocols" / "p.json").write_text(json.dumps(doc))
    src = s["source"]
    (tmp_path / "protocols" / "test-protocol.evidence.json").write_text(json.dumps({
        "protocol": "test-protocol", "why": "Fixture", "microgravity": "Fixture", "pulse": {"model": "no"},
        "sources": [{"guideline": src["guideline"], "licence": "Fixture licence"}],
        "recommendations": [{"guideline": src["guideline"], "section": src["section"], "quotes": ["Fixture quote"]}]}))
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


def test_stub_test_doubles_are_not_linted_as_content(tmp_path):
    # Spec 4's non-clinical test doubles declare "stub": true; they are not Spec 5 content.
    (tmp_path / "protocols").mkdir()
    (tmp_path / "profiles").mkdir()
    (tmp_path / "protocols" / "stub-protocol.json").write_text(json.dumps({"id": "stub-protocol", "stub": True, "steps": []}))
    (tmp_path / "profiles" / "stub-mars.json").write_text(json.dumps({"id": "stub-mars", "stub": True}))
    assert cl.lint_dir(tmp_path) == {}


def test_a_real_protocol_without_stub_flag_is_still_linted(tmp_path):
    (tmp_path / "protocols").mkdir()
    (tmp_path / "protocols" / "p.json").write_text(json.dumps({"id": "p", "steps": []}))
    assert cl.lint_dir(tmp_path)
