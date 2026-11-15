"""Validate payloads against the shared contracts.

Spec 1's frozen schemas in contracts/ are authoritative. Label and MissionProfile are not
among Spec 1's seven contracts; their provisional shapes live in contracts/provisional/
until the team agrees them.
"""
from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

import jsonschema

CONTRACTS = Path(__file__).resolve().parents[2] / "contracts"
SCHEMA_VERSION = "1.0.0"

FILES = {
    "trigger": CONTRACTS / "trigger.schema.json",
    "alert": CONTRACTS / "alert.schema.json",
    "protocol": CONTRACTS / "protocol.schema.json",
    "ground_report": CONTRACTS / "ground-report.schema.json",
    "reading": CONTRACTS / "reading.schema.json",
    "crew_record": CONTRACTS / "crew-record.schema.json",
    "replay_file": CONTRACTS / "replay-file.schema.json",
    "label": CONTRACTS / "provisional" / "label.schema.json",
    "mission_profile": CONTRACTS / "provisional" / "mission_profile.schema.json",
}


class ContractError(ValueError):
    pass


@lru_cache(maxsize=None)
def schema(name: str) -> dict:
    return json.loads(FILES[name].read_text(encoding="utf-8"))


@lru_cache(maxsize=None)
def _validator(name: str):
    """Built once per contract: jsonschema.validate re-checks the schema on every call (about 1.6 ms per Reading)."""
    s = schema(name)
    cls = jsonschema.validators.validator_for(s)
    cls.check_schema(s)
    return cls(s)


def validate(name: str, obj) -> dict:
    e = jsonschema.exceptions.best_match(_validator(name).iter_errors(obj))  # the error jsonschema.validate would raise
    if e is not None:
        path = "/".join(str(p) for p in e.absolute_path) or "$"
        raise ContractError(f"{name}: {path}: {e.message}") from None
    return obj
