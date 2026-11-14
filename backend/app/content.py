"""Load protocol content and Mission profiles (read-only) and apply the step filters.

Content comes from content/ (Spec 5 owns the real files; stub-* files are
non-clinical test doubles). Steps that fail the safety checks are refused at
runtime even if the build-time linter was skipped.
"""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from pathlib import Path
from types import MappingProxyType

from . import contracts

REPO = Path(__file__).resolve().parents[2]
CONTENT = REPO / "content"
sys.path.insert(0, str(REPO / "tools"))
import lint_content  # noqa: E402

MEDICATION_PLACEHOLDER = lint_content.MEDICATION_PLACEHOLDER


def _read(path: Path):
    return json.loads(path.read_text(encoding="utf-8"))


@dataclass(frozen=True)
class Step:
    id: str
    text: str
    guideline: str
    section: str
    equipment: tuple[str, ...]
    rescuers: int

    def public(self) -> dict:
        return {"id": self.id, "text": self.text, "source": {"guideline": self.guideline, "section": self.section},
                "equipment": list(self.equipment), "rescuers": self.rescuers}


@dataclass(frozen=True)
class Protocol:
    id: str
    title: str
    stub: bool
    steps: tuple[Step, ...]
    refused: tuple[tuple[str, str], ...] = ()  # (step id, reason)
    excerpts: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))  # step id -> tuple[str]
    recorded: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))  # step id -> str
    roles: MappingProxyType = field(default_factory=lambda: MappingProxyType({}))  # step id -> "R1" | "R2"

    def step(self, sid: str) -> Step | None:
        return next((s for s in self.steps if s.id == sid), None)


def load_protocol(pid: str, root: Path = CONTENT, deny: list[str] | None = None) -> Protocol:
    deny = lint_content.load_deny_list() if deny is None else deny
    raw = _read(root / "protocols" / f"{pid}.json")
    steps, refused = [], []
    for s in raw.get("steps", []):
        issues = lint_content.lint_data({"steps": [s]}, pid, deny)
        if issues:
            refused.append((s.get("id", "?"), "; ".join(i.reason for i in issues)))
            continue
        steps.append(Step(s["id"], s["text"], s["source"]["guideline"], s["source"]["section"],
                          tuple(s.get("equipment", [])), int(s.get("rescuers", 1))))
    excerpts: dict[str, tuple[str, ...]] = {}
    ex_path = root / "protocols" / f"{pid}.excerpts.json"
    if ex_path.exists():
        for e in _read(ex_path).get("excerpts", []):
            if not lint_content.find_drug_or_dose(e["text"], deny):
                excerpts[e["step"]] = excerpts.get(e["step"], ()) + (e["text"],)
    recorded: dict[str, str] = {}
    rec_path = root / "protocols" / f"{pid}.recorded.json"
    if rec_path.exists():
        for sid, text in _read(rec_path).get("answers", {}).items():
            if not lint_content.find_drug_or_dose(text, deny):
                recorded[sid] = text
    roles: dict[str, str] = {}
    roles_path = root / "protocols" / f"{pid}.roles.json"
    if roles_path.exists():
        for sid, role in _read(roles_path).get("roles", {}).items():
            if role not in ("R1", "R2"):
                raise ValueError(f"{roles_path.name}: step {sid}: role must be R1 or R2")
            roles[sid] = role
    return Protocol(raw["id"], raw["title"], bool(raw.get("stub")), tuple(steps), tuple(refused),
                    MappingProxyType(excerpts), MappingProxyType(recorded), MappingProxyType(roles))


def load_profile(pid: str, root: Path = CONTENT) -> dict:
    return contracts.validate("mission_profile", _read(root / "profiles" / f"{pid}.json"))


def visible_steps(protocol: Protocol, equipment_on_board, rescuer_count: int, role: str | None = None) -> list[Step]:
    """Equipment filter (story 14), rescuer-count filter (story 15) and role split (story 16).

    Role map (content/protocols/<id>.roles.json, supplied by Spec 5): with two or more
    rescuers each sees steps for their role plus unmapped steps; with one rescuer the
    role split does not apply (but steps needing 2 rescuers stay hidden)."""
    on_board = set(equipment_on_board)
    steps = [s for s in protocol.steps if set(s.equipment) <= on_board and s.rescuers <= rescuer_count]
    if rescuer_count >= 2 and role:
        steps = [s for s in steps if protocol.roles.get(s.id) in (None, role)]
    return steps
