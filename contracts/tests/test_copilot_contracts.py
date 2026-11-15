"""Spec 3 provisional copilot contracts: decision-record, condition-assessment, briefing, Alert.assessment_id."""
import copy
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).resolve().parents[1]
PROVISIONAL = CONTRACTS / "provisional"
sys.path.insert(0, str(CONTRACTS))

from validate import ContractError, validate  # noqa: E402

SHAPES = {
    "condition-assessment": "ConditionAssessment",
    "briefing": "Briefing",
    "decision-record": "DecisionRecord",
}


def schema_validator(name):
    schema = json.loads((PROVISIONAL / f"{name}.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


def example(name):
    return json.loads((PROVISIONAL / "examples" / f"{SHAPES[name]}.example.json").read_text(encoding="utf-8"))


def errors(name, doc):
    return list(schema_validator(name).iter_errors(doc))


def mutated(name, mutate):
    doc = copy.deepcopy(example(name))
    mutate(doc)
    return doc


@pytest.mark.parametrize("name", SHAPES)
def test_schema_is_marked_provisional_and_example_is_valid(name):
    schema = json.loads((PROVISIONAL / f"{name}.schema.json").read_text(encoding="utf-8"))
    assert schema["x-status"].startswith("PROVISIONAL")
    assert not errors(name, example(name))


INVALID = {
    "condition-assessment": {
        "no conditions": lambda d: d.update(conditions=[]),
        "missing id": lambda d: d.pop("id"),
        "posterior above 1": lambda d: d["conditions"][0].update(posterior=1.2),
        "condition without label": lambda d: d["conditions"][0].pop("label"),
        "empty label": lambda d: d["conditions"][0].update(label=""),
        "condition without posterior": lambda d: d["conditions"][0].pop("posterior"),
        "condition without protocol_id key": lambda d: d["conditions"][0].pop("protocol_id"),
        "evidence line without label": lambda d: d["conditions"][0]["evidence"][0].pop("label"),
        "rank zero": lambda d: d["conditions"][0].update(rank=0),
    },
    "briefing": {
        "missing assessment_id": lambda d: d.pop("assessment_id"),
        "unknown source": lambda d: d.update(source="guess"),
        "missing context label": lambda d: d.pop("context_label"),
        "evidence line without label": lambda d: d["evidence"][0].pop("label"),
        "probability above 1": lambda d: d["evidence"][0].update(probability=2),
    },
    "decision-record": {
        "no events key": lambda d: d.pop("events"),
        "unknown event type": lambda d: d["events"][0].update(type="other"),
        "event without hash": lambda d: d["events"][1].pop("hash"),
        "short hash": lambda d: d["events"][1].update(hash="abc"),
        "prev_hash missing": lambda d: d["events"][0].pop("prev_hash"),
    },
}


@pytest.mark.parametrize(
    "name,case",
    [(name, case) for name, cases in INVALID.items() for case in cases],
)
def test_invalid_examples_are_rejected(name, case):
    assert errors(name, mutated(name, INVALID[name][case]))


def test_alert_assessment_id_is_optional_and_must_be_a_string():
    alert = json.loads((CONTRACTS / "examples" / "Alert.example.json").read_text(encoding="utf-8"))
    validate("Alert", alert)
    validate("Alert", dict(alert, assessment_id="assess-1"))
    with pytest.raises(ContractError):
        validate("Alert", dict(alert, assessment_id=7))
