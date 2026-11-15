"""Spec 2 data paths: provisional shapes that are not among Spec 1's seven frozen contracts.

  form      -> contracts/provisional/crew-form.schema.json     (post-EVA form, meal, crew note)
  location  -> contracts/provisional/crew-location.schema.json (crew-location timeline for exposure)
Glucose is an ordinary Reading (indicator "glucose"). Failing documents raise ContractError like the frozen ones.
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

CONTRACTS = Path(__file__).resolve().parents[1] / "contracts"
sys.path.insert(0, str(CONTRACTS))
from validate import ContractError  # noqa: E402

PROVISIONAL = {"form": "crew-form.schema.json", "location": "crew-location.schema.json"}


@lru_cache(maxsize=None)
def _validator(kind):
    return Draft202012Validator(json.loads((CONTRACTS / "provisional" / PROVISIONAL[kind]).read_text(encoding="utf-8")))


def validate_provisional(kind, doc):
    if kind not in PROVISIONAL:
        raise ContractError(f"Unknown provisional shape {kind!r}; expected one of {sorted(PROVISIONAL)}")
    problems = [f"{'/'.join(map(str, e.absolute_path)) or '(root)'}: {e.message}" for e in _validator(kind).iter_errors(doc)]
    if problems:
        raise ContractError(f"{kind} invalid:\n  " + "\n  ".join(problems))
    return doc
