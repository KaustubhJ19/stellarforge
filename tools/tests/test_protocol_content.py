"""Ticket 03 (Spec 5 task 5.3): rules the real protocol content must keep.

Observable rules only (not wording taste): rescuer minimums the guideline states,
equipment Spec 4 can render, honest Earth-reference labels, and the hand-offs.
"""
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
PROTOCOLS = ROOT / "content" / "protocols"
EARTH = "Earth reference, no space data"


def load(pid):
    return json.loads((PROTOCOLS / f"{pid}.json").read_text(encoding="utf-8"))


def steps(pid):
    return load(pid)["steps"]


@pytest.mark.parametrize("pid", ["microgravity-cpr", "chest-pain"])
def test_protocol_has_coverage_entry(pid):
    coverage = json.loads((PROTOCOLS / "coverage.json").read_text(encoding="utf-8"))
    assert pid in coverage


def test_airway_steps_need_at_least_two_rescuers():
    # Hinkelbein 2020, Abstract (Results): airway only with at least two rescuers.
    airway = [s for s in steps("microgravity-cpr") if "airway" in s["text"].lower() or "intubation" in s["text"].lower()]
    assert airway
    assert all(s["rescuers"] >= 2 for s in airway)


def test_venous_access_needs_more_than_two_rescuers():
    # Hinkelbein 2020, Recommendation 16.
    venous = [s for s in steps("microgravity-cpr") if "venous access" in s["text"].lower()]
    assert venous
    assert all(s["rescuers"] > 2 for s in venous)


def test_defibrillation_steps_use_the_restraint_system():
    # Hinkelbein 2020, Recommendation 10: defibrillate only on a restrained, isolated patient.
    defib = [s for s in steps("microgravity-cpr") if s["text"].lower().startswith(("use the aed", "defibrillation"))]
    assert defib
    assert all("Crew Medical Restraint System" in s["equipment"] for s in defib)


@pytest.mark.parametrize("pid", ["microgravity-cpr", "chest-pain"])
def test_equipment_is_named_for_spec4(pid):
    for s in steps(pid):
        assert isinstance(s["equipment"], list)
        assert all(isinstance(e, str) and e.strip() for e in s["equipment"])


@pytest.mark.parametrize("pid", ["microgravity-cpr", "chest-pain"])
def test_earth_sources_are_labelled(pid):
    for s in steps(pid):
        g = s["source"]["guideline"]
        if "ESC" in g or "European Society of Cardiology" in g:
            assert EARTH in g


def test_chest_pain_phase_hands_medication_to_the_flight_surgeon():
    texts = [s["text"].lower() for s in steps("chest-pain")]
    assert any("per flight surgeon / onboard medical checklist" in t for t in texts)


def test_chest_pain_phase_informs_mission_control():
    assert any("mission control" in s["text"].lower() for s in steps("chest-pain"))


def test_chest_pain_phase_records_an_ecg_and_readies_the_aed():
    texts = " ".join(s["text"].lower() for s in steps("chest-pain"))
    assert "ecg" in texts and "defibrillat" in texts


def detection_content():
    return json.loads((ROOT / "content" / "profiles" / "detection-cut-offs.json").read_text(encoding="utf-8"))


def bound(indicator):
    return next(b for b in detection_content()["safety_bounds"] if b["indicator"] == indicator)


def test_body_temperature_low_is_nasa_hypothermia():
    b = bound("body_temperature")
    assert (b["low"], b["high"]) == (35.0, 38.0)
    assert "NASA-STD-3001" in b["source"] and "standards.nasa.gov" in b["source"]


def test_glucose_bound_is_ada_level_2():
    # Decision 2026-11-15: personal baseline plus a level 2 Safety bound. Level 1 (70) fired on
    # 7 of 28 Inspiration4 values (OSD-575); level 2 fires on 3 (all at R+45).
    b = bound("glucose")
    assert (b["low"], b["high"]) == (54, 250)
    assert "PMC11635034" in b["source"] and "Table 6.2" in b["source"]


def test_in_flight_temperature_shift_is_sourced():
    shift = next(c for c in detection_content()["cutoffs"] if c["name"] == "expected_shift")
    assert shift["value"].get("body_temperature") == 1.0
    assert "PMC5701078" in shift["source"]


def test_medical_review_sheet_matches_bound_values():
    sheet = (ROOT / "docs" / "medical-review.md").read_text(encoding="utf-8")
    for b in detection_content()["safety_bounds"]:
        assert f"| `{b['indicator']}` | {b['low']} | {b['high']} |" in sheet, b["indicator"]


def test_medical_review_sheet_lists_every_step_and_bound():
    # Ticket 14 gate: a clinician signs every item; the sheet must not fall behind the content.
    sheet = (ROOT / "docs" / "medical-review.md").read_text(encoding="utf-8")
    for pid in ("microgravity-cpr", "chest-pain"):
        for s in steps(pid):
            assert f"`{s['id']}`" in sheet, s["id"]
    bounds = json.loads((ROOT / "content" / "profiles" / "detection-cut-offs.json").read_text(encoding="utf-8"))
    for b in bounds["safety_bounds"]:
        assert f"`{b['indicator']}`" in sheet, b["indicator"]


@pytest.mark.parametrize("pid", ["microgravity-cpr", "chest-pain"])
def test_step_ids_are_unique(pid):
    ids = [s["id"] for s in steps(pid)]
    assert len(ids) == len(set(ids))
