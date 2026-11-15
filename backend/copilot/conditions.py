"""Condition library: priors, cited signs with likelihood ratios, mapped protocol, simulatable flag."""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

DEFAULT_PATH = Path(__file__).resolve().parents[2] / "content" / "copilot" / "conditions.json"


@dataclass(frozen=True)
class Sign:
    id: str
    text: str
    lr: float  # likelihood ratio: P(sign | condition) / P(sign | not condition)
    source: str  # label, e.g. "team value" or a citation


@dataclass(frozen=True)
class Condition:
    id: str
    name: str
    prior: float  # P(condition | collapse), 0 < p < 1
    prior_source: str
    protocol_id: str  # may name a protocol that is not authored yet
    simulatable: bool  # Pulse can simulate it, so L1 can train on it
    signs: tuple[Sign, ...]


@dataclass(frozen=True)
class ConditionLibrary:
    note: str
    conditions: tuple[Condition, ...]

    def get(self, condition_id: str) -> Condition:
        for c in self.conditions:
            if c.id == condition_id:
                return c
        raise KeyError(condition_id)

    def simulatable(self) -> tuple[Condition, ...]:
        return tuple(c for c in self.conditions if c.simulatable)


def _problems(raw: dict) -> list[str]:
    errs, seen = [], set()
    if not raw.get("conditions"):
        errs.append("no conditions")
    for c in raw.get("conditions", []):
        cid = c.get("id", "?")
        if cid in seen:
            errs.append(f"{cid}: duplicate id")
        seen.add(cid)
        if not isinstance(c.get("simulatable"), bool):
            errs.append(f"{cid}: simulatable must be true or false")
        if not (isinstance(c.get("prior"), (int, float)) and 0 < c["prior"] < 1):
            errs.append(f"{cid}: prior must be between 0 and 1")
        for key in ("name", "prior_source", "protocol_id"):
            if not str(c.get(key, "")).strip():
                errs.append(f"{cid}: missing {key}")
        for s in c.get("signs", []):
            if not (isinstance(s.get("lr"), (int, float)) and s["lr"] > 0):
                errs.append(f"{cid}/{s.get('id', '?')}: lr must be positive")
            if not str(s.get("source", "")).strip():
                errs.append(f"{cid}/{s.get('id', '?')}: lr needs a source label")
    return errs


def load_conditions(path: Path = DEFAULT_PATH) -> ConditionLibrary:
    raw = json.loads(Path(path).read_text(encoding="utf-8"))
    errs = _problems(raw)
    if errs:
        raise ValueError("invalid condition library: " + "; ".join(errs))
    return ConditionLibrary(
        note=raw.get("note", ""),
        conditions=tuple(
            Condition(c["id"], c["name"], float(c["prior"]), c["prior_source"], c["protocol_id"], c["simulatable"],
                      tuple(Sign(s["id"], s["text"], float(s["lr"]), s["source"]) for s in c.get("signs", [])))
            for c in raw["conditions"]))
