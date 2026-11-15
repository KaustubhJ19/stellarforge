"""Intent-first router (docs/spec-intent-routing.md).

A fixed table in content/triage/routes.json maps a confirmed Intake plus live state to ONE
protocol id. No model decides anything here: a language model may only help fill the Intake,
and a person confirms it before it reaches `route()`. A route whose protocol has no cited
content yet resolves to "not covered", never to an invented one.
"""
from __future__ import annotations

import json
from pathlib import Path

from .content import CONTENT

INTAKE_VALUES = {
    "responsive": ("yes", "no"),
    "breathing": ("normal", "abnormal", "none"),
    "main_problem": ("chest_pain", "breathing_trouble", "cabin_alert", "collapse", "injury", "other"),
    "source": ("tap", "text_confirmed"),
}
REQUIRED = ("responsive", "breathing", "main_problem")
ROUTES_PATH = CONTENT / "triage" / "routes.json"


ARREST_RHYTHMS = ("VT", "VF", "PEA", "asystole")  # same rule names as backend/emergency.py
PULSE_ARREST_NAMES = ("VentricularFibrillation", "VentricularTachycardia", "PulselessElectricalActivity", "Asystole")


class IntakeError(ValueError):
    """The intake form has a missing, unknown or out-of-range field."""


def intake_fields() -> dict[str, list[str]]:
    """What the tablet may offer. `source` is set by the system, never typed."""
    return {k: list(v) for k, v in INTAKE_VALUES.items() if k != "source"}


def is_arrest_rhythm(value) -> bool:
    """Rule name (VT, VF, PEA, asystole) or a Pulse rhythm name containing one."""
    return isinstance(value, str) and (value in ARREST_RHYTHMS or any(n in value for n in PULSE_ARREST_NAMES))


def load_routes(path: Path = ROUTES_PATH) -> dict:
    return json.loads(path.read_text(encoding="utf-8"))


def validate_intake(raw: dict) -> dict:
    """Return a clean copy of the form, or raise. The only way an Intake reaches the router."""
    if not isinstance(raw, dict):
        raise IntakeError("intake: must be an object")
    extra = set(raw) - set(INTAKE_VALUES)
    if extra:
        raise IntakeError(f"intake: unknown field {sorted(extra)[0]}")
    missing = [f for f in REQUIRED if f not in raw]
    if missing:
        raise IntakeError(f"intake: missing {missing[0]}")
    clean = {"source": "tap"} | raw
    for field, value in clean.items():
        if value not in INTAKE_VALUES[field]:
            raise IntakeError(f"intake: {field}: '{value}' is not one of {', '.join(INTAKE_VALUES[field])}")
    return clean


def _matches(when: dict, facts: dict) -> bool:
    for key, want in when.items():
        have = facts.get(key)
        if isinstance(want, list):
            if have not in want:
                return False
        elif have != want:
            return False
    return True


def route(routes: dict, intake: dict | None, live: dict, available: set[str], trigger_kind: str | None = None) -> dict:
    """First matching row wins. Returns {protocol_id | None, rule_id, reason}."""
    facts = (intake or {}) | {"trigger_kind": trigger_kind, "live_arrest": bool(live.get("arrest")),
                               "live_cabin_alert": bool(live.get("cabin_alert")),
                               # L0 airway rule: low SpO2 on the live feed, or the rescuer reports no breathing
                               "airway_threat": bool(live.get("low_spo2")) or (intake or {}).get("breathing") == "none"}
    for row in routes["rows"]:
        if not _matches(row["when"], facts):
            continue
        if row["protocol"] in available:
            return {"protocol_id": row["protocol"], "rule_id": row["id"], "reason": row["reason"]}
        return {"protocol_id": None, "rule_id": row["id"],
                "reason": f"{row['reason']} Protocol '{row['protocol']}' is not available yet. Contact ground."}
    fb = routes["fallback"]
    return {"protocol_id": None, "rule_id": fb["id"], "reason": fb["reason"]}
