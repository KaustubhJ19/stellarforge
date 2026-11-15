"""Provisional schemas: shapes in use that are not among Spec 1's seven frozen contracts.

Forecast (Spec 3, Forecast B, P1): fields as Spec 3 produces them
(crew, t, value, low, high, label, drivers, population, personal_correction, base).
"""
import json
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

PROVISIONAL = Path(__file__).resolve().parents[1] / "provisional"


def forecast_validator():
    schema = json.loads((PROVISIONAL / "forecast.schema.json").read_text(encoding="utf-8"))
    Draft202012Validator.check_schema(schema)
    return Draft202012Validator(schema)


FORECAST = {"schema_version": "1.0.0", "crew": "A", "t": 86400, "value": 6.4, "low": 5.1, "high": 7.6,
            "label": "estimate, not validated", "drivers": {"sleep_duration": -0.4, "fatigue": 0.2},
            "population": 6.1, "personal_correction": 0.3, "base": 6.0}


def test_forecast_schema_is_marked_provisional_and_valid_json_schema():
    schema = json.loads((PROVISIONAL / "forecast.schema.json").read_text(encoding="utf-8"))
    assert schema["x-status"].startswith("PROVISIONAL")
    forecast_validator()


def test_spec3_forecast_payload_is_valid():
    assert not list(forecast_validator().iter_errors(FORECAST))


@pytest.mark.parametrize("field", ["crew", "t", "value", "low", "high", "label", "drivers",
                                   "population", "personal_correction", "base"])
def test_every_spec3_field_is_required(field):
    doc = dict(FORECAST)
    del doc[field]
    assert list(forecast_validator().iter_errors(doc))


def test_drivers_must_map_names_to_numbers():
    assert list(forecast_validator().iter_errors(dict(FORECAST, drivers={"sleep": "high"})))


def test_schema_version_is_optional_like_other_replay_payloads():
    doc = dict(FORECAST)
    del doc["schema_version"]
    assert not list(forecast_validator().iter_errors(doc))


@pytest.mark.parametrize("name, good, bad", [
    ("crew-form", {"schema_version": "1.0.0", "crew": "A", "form": "post_eva", "t": 10, "answers": {"eva_end_t": 5}},
     {"crew": "A", "form": "diary", "t": 10, "answers": {}}),
    ("crew-location", {"schema_version": "1.0.0", "crew": "A", "cabin": "habitat", "t": 10}, {"crew": "A", "t": 10}),
])
def test_spec2_shapes_are_provisional_valid_and_strict_enough(name, good, bad):
    schema = json.loads((PROVISIONAL / f"{name}.schema.json").read_text(encoding="utf-8"))
    assert schema["x-status"].startswith("PROVISIONAL")
    Draft202012Validator.check_schema(schema)
    v = Draft202012Validator(schema)
    assert not list(v.iter_errors(good))
    assert list(v.iter_errors(bad))
