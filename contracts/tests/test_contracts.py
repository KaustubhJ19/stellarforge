"""Tests for the seven Spec 1 contracts and the shared validator.

Each test asserts behaviour stated in the Contracts table of Spec 1:
required fields, allowed values, confidence 0-1, schema_version, events ordered by t.
"""
import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

CONTRACTS_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(CONTRACTS_DIR))

from validate import CONTRACTS, ContractError, validate  # noqa: E402

EXAMPLES = CONTRACTS_DIR / "examples"


def example(name):
    return json.loads((EXAMPLES / f"{name}.example.json").read_text(encoding="utf-8"))


def rejected(name, doc):
    with pytest.raises(ContractError):
        validate(name, doc)


# ---- every contract -------------------------------------------------------

def test_there_are_exactly_the_seven_spec_contracts():
    assert sorted(CONTRACTS) == sorted(
        ["Reading", "Alert", "CrewRecord", "ReplayFile", "Protocol", "GroundReport", "Trigger"]
    )


@pytest.mark.parametrize("name", CONTRACTS)
def test_schema_is_valid_json_schema_2020_12(name):
    schema = json.loads((CONTRACTS_DIR / CONTRACTS[name]).read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    assert schema["$schema"] == "https://json-schema.org/draft/2020-12/schema"


@pytest.mark.parametrize("name", CONTRACTS)
def test_example_document_is_valid(name):
    validate(name, example(name))


@pytest.mark.parametrize("name", CONTRACTS)
def test_schema_version_is_required(name):
    doc = example(name)
    del doc["schema_version"]
    rejected(name, doc)


REQUIRED = {
    "Reading": ["crew", "indicator", "value", "unit", "t", "source", "confidence", "state"],
    "Alert": ["id", "kind", "crew", "indicator", "deviation", "status", "urgency", "likely_causes", "t"],
    "CrewRecord": ["id", "sex", "anchor", "missionProfile"],
    "ReplayFile": ["crew", "profile", "events"],
    "Protocol": ["id", "title", "steps"],
    "GroundReport": ["id", "crew", "summary", "history", "timeline", "actions", "sent_t"],
    "Trigger": ["kind", "crew", "t", "reason"],
}


@pytest.mark.parametrize("name,field", [(n, f) for n, fs in REQUIRED.items() for f in fs])
def test_every_listed_field_is_required(name, field):
    doc = example(name)
    del doc[field]
    rejected(name, doc)


OPTIONAL = {"GroundReport": ["reply_t", "reply"], "Trigger": ["confirmed"]}


@pytest.mark.parametrize("name,field", [(n, f) for n, fs in OPTIONAL.items() for f in fs])
def test_question_mark_fields_are_optional(name, field):
    doc = example(name)
    doc.pop(field, None)
    validate(name, doc)


ENUMS = [
    ("Reading", "source", ["sensor", "camera", "mic", "manual", "lab", "sim"]),
    ("Reading", "state", ["released", "quarantined", "event"]),
    ("Alert", "kind", ["acute", "drift", "emergency"]),
    ("Alert", "status", ["green", "amber", "red"]),
    ("Alert", "urgency", ["ACT_NOW", "ESCALATE_TO_GROUND", "MONITOR", "ROUTINE"]),
    ("Trigger", "kind", ["auto", "manual"]),
]


@pytest.mark.parametrize("name,field,allowed", ENUMS)
def test_enum_accepts_every_spec_value(name, field, allowed):
    for value in allowed:
        doc = example(name)
        doc[field] = value
        validate(name, doc)


@pytest.mark.parametrize("name,field,allowed", ENUMS)
def test_enum_rejects_other_values(name, field, allowed):
    doc = example(name)
    doc[field] = "not_a_spec_value"
    rejected(name, doc)


# ---- Reading ---------------------------------------------------------------

@pytest.mark.parametrize("confidence", [0, 0.5, 1])
def test_reading_confidence_inside_0_to_1_is_accepted(confidence):
    doc = example("Reading")
    doc["confidence"] = confidence
    validate("Reading", doc)


@pytest.mark.parametrize("confidence", [-0.01, 1.01, "high"])
def test_reading_confidence_outside_0_to_1_is_rejected(confidence):
    doc = example("Reading")
    doc["confidence"] = confidence
    rejected("Reading", doc)


def test_reading_t_must_be_seconds_number():
    doc = example("Reading")
    doc["t"] = "noon"
    rejected("Reading", doc)


# ---- nested shapes ---------------------------------------------------------

def test_alert_likely_cause_needs_indicator_direction_note():
    for field in ["indicator", "direction", "note"]:
        doc = example("Alert")
        doc["likely_causes"] = [{"indicator": "x", "direction": "up", "note": "n"}]
        del doc["likely_causes"][0][field]
        rejected("Alert", doc)


def test_alert_likely_causes_may_be_empty():
    doc = example("Alert")
    doc["likely_causes"] = []
    validate("Alert", doc)


def test_crew_record_anchor_entries_need_mean_and_sd():
    for field in ["mean", "sd"]:
        doc = example("CrewRecord")
        doc["anchor"] = {"heart_rate": {"mean": 60, "sd": 4}}
        del doc["anchor"]["heart_rate"][field]
        rejected("CrewRecord", doc)


def test_protocol_step_needs_every_listed_field():
    for field in ["id", "text", "source", "equipment", "rescuers"]:
        doc = example("Protocol")
        del doc["steps"][0][field]
        rejected("Protocol", doc)


def test_protocol_step_source_needs_guideline_and_section():
    for field in ["guideline", "section"]:
        doc = example("Protocol")
        del doc["steps"][0]["source"][field]
        rejected("Protocol", doc)


def test_replay_event_needs_t_type_payload():
    for field in ["t", "type", "payload"]:
        doc = example("ReplayFile")
        del doc["events"][0][field]
        rejected("ReplayFile", doc)


# ---- ReplayFile ordered by t -------------------------------------------------

def test_replay_events_in_time_order_are_accepted_including_ties():
    doc = example("ReplayFile")
    doc["events"] = [
        {"t": 0, "type": "a", "payload": {}},
        {"t": 5, "type": "b", "payload": {}},
        {"t": 5, "type": "c", "payload": {}},
    ]
    validate("ReplayFile", doc)


def test_replay_events_out_of_time_order_are_rejected():
    doc = example("ReplayFile")
    doc["events"] = [
        {"t": 10, "type": "a", "payload": {}},
        {"t": 5, "type": "b", "payload": {}},
    ]
    with pytest.raises(ContractError, match="ordered by t"):
        validate("ReplayFile", doc)


# ---- validator behaviour -----------------------------------------------------

def test_unknown_contract_name_is_an_error():
    with pytest.raises(ContractError):
        validate("NotAContract", {})


def test_error_names_the_failing_field():
    doc = example("Reading")
    doc["confidence"] = 2
    with pytest.raises(ContractError, match="confidence"):
        validate("Reading", doc)


def test_validate_does_not_modify_the_document():
    doc = example("ReplayFile")
    before = copy.deepcopy(doc)
    validate("ReplayFile", doc)
    assert doc == before


def test_command_line_exit_codes(tmp_path):
    good = EXAMPLES / "Reading.example.json"
    bad = tmp_path / "bad.json"
    broken = example("Reading")
    broken["source"] = "telepathy"
    bad.write_text(json.dumps(broken), encoding="utf-8")
    script = CONTRACTS_DIR / "validate.py"
    ok = subprocess.run([sys.executable, str(script), "Reading", str(good)], capture_output=True, text=True)
    fail = subprocess.run([sys.executable, str(script), "Reading", str(bad)], capture_output=True, text=True)
    assert ok.returncode == 0, ok.stderr
    assert fail.returncode == 1
    assert "source" in fail.stderr
