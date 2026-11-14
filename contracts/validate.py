"""Shared validator for the seven Spec 1 contracts.

Python use:
    from validate import validate, ContractError
    validate("Reading", document)   # raises ContractError if invalid

Command line:
    python contracts/validate.py <Contract> <file.json>   # exit 0 valid, 1 invalid
"""
import json
import sys
from functools import lru_cache
from pathlib import Path

from jsonschema import Draft202012Validator

HERE = Path(__file__).resolve().parent

CONTRACTS = {
    "Reading": "reading.schema.json",
    "Alert": "alert.schema.json",
    "CrewRecord": "crew-record.schema.json",
    "ReplayFile": "replay-file.schema.json",
    "Protocol": "protocol.schema.json",
    "GroundReport": "ground-report.schema.json",
    "Trigger": "trigger.schema.json",
}


class ContractError(ValueError):
    """Raised when a document does not match its contract."""


@lru_cache(maxsize=None)
def _validator(name):
    schema = json.loads((HERE / CONTRACTS[name]).read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def validate(name, document):
    """Validate a document against a contract. Raises ContractError listing every problem."""
    if name not in CONTRACTS:
        raise ContractError(f"Unknown contract {name!r}; expected one of {sorted(CONTRACTS)}")
    problems = [
        f"{'/'.join(str(p) for p in err.absolute_path) or '(root)'}: {err.message}"
        for err in sorted(_validator(name).iter_errors(document), key=lambda e: list(map(str, e.absolute_path)))
    ]
    if name == "ReplayFile" and not problems:
        times = [event["t"] for event in document["events"]]
        for i in range(1, len(times)):
            if times[i] < times[i - 1]:
                problems.append(f"events/{i}/t: events must be ordered by t ({times[i]} after {times[i - 1]})")
    if problems:
        raise ContractError(f"{name} invalid:\n  " + "\n  ".join(problems))


def main(argv):
    if len(argv) != 3:
        print(__doc__, file=sys.stderr)
        return 2
    name, path = argv[1], Path(argv[2])
    try:
        validate(name, json.loads(path.read_text(encoding="utf-8")))
    except ContractError as exc:
        print(exc, file=sys.stderr)
        return 1
    print(f"{path}: valid {name}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
