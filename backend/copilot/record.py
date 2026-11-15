"""Hash-chained decision record (ticket 05). One log: copilot events live in the emergency timeline and store.

Later tickets append events with `FlowEngine.copilot_event(e, "<kind>", **data)` (stored as type `copilot_<kind>`).
Each event carries `prev`, the SHA-256 of the previous copilot event of the same emergency (GENESIS for the first).
Editing or removing any stored event breaks the next event's `prev`; the last event is covered by the in-memory
head (`digest(e.copilot_last)`), so pass `head=` to `verify` when it is known.
"""
from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass

GENESIS = "0" * 64
PREFIX = "copilot_"


def digest(obj) -> str:
    """SHA-256 over canonical JSON (sorted keys, no spaces), so a store round trip hashes the same."""
    return hashlib.sha256(json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode()).hexdigest()


def prev_hash(last: dict | None) -> str:
    return digest(last) if last else GENESIS


def chain_of(events: list[dict], emergency: str) -> list[dict]:
    return [ev for ev in events if ev.get("emergency") == emergency and str(ev.get("type", "")).startswith(PREFIX)]


@dataclass(frozen=True)
class ChainResult:
    ok: bool
    reason: str = ""


def verify(chain: list[dict], head: str | None = None) -> ChainResult:
    """Check every `prev` link; with `head` (digest of the newest event) also catches an edit to the last event."""
    prev = GENESIS
    for i, ev in enumerate(chain):
        if ev.get("prev") != prev:
            return ChainResult(False, f"event {i} ({ev.get('type')}) does not match the one before it")
        prev = digest(ev)
    if head is not None and prev != head:
        return ChainResult(False, "the newest event was changed or removed")
    return ChainResult(True)


def timings(chain: list[dict]) -> dict:
    """When the system first assessed, when the rescuer chose, and how long the investigator took (Mission clock s)."""
    first: dict[str, dict] = {}
    for ev in chain:
        first.setdefault(ev["type"][len(PREFIX):], ev)
    out: dict = {}
    if "assessment" in first:
        out["assessed_t"] = first["assessment"]["t"]
    if "choice" in first:
        out["chosen_t"] = first["choice"]["t"]
        if "assessment" in first:
            out["choice_after_s"] = round(first["choice"]["t"] - first["assessment"]["t"], 3)
    if first.get("investigator", {}).get("elapsed_s") is not None:
        out["investigator_elapsed_s"] = first["investigator"]["elapsed_s"]
    return out


def check_section(section: dict) -> ChainResult:
    """Re-verify the copy of the record carried in a ground report, against the head it was sent with."""
    return verify(section["events"], head=section["chain"]["head"])
