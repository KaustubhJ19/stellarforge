"""Wire the engine from content + test doubles (Spec 1/5 stand-ins until integration)."""
from __future__ import annotations

import json
import os
from pathlib import Path

from .clock import MissionClock
from .content import CONTENT, REPO, load_profile, load_protocol
from .flow import FlowEngine
from .store import Store

DEFAULT_PROTOCOL = "stub-protocol"
DEFAULT_PROFILE = "stub-mars"
DEFAULT_RECORDS = REPO / "replay" / "stub-crew-records.json"


def load_records(path=DEFAULT_RECORDS) -> dict[str, dict]:
    """Crew records from one file or several (comma-separated). A file holds a list of
    CrewRecords (Spec 1 / Spec 2 fixtures) or {"records": [...]}."""
    from . import contracts
    paths = [p for p in str(path).split(",") if p.strip()] if isinstance(path, str) else [path]
    out: dict[str, dict] = {}
    for p in paths:
        data = json.loads(Path(p).read_text(encoding="utf-8"))
        for r in data if isinstance(data, list) else data["records"]:
            out[r["id"]] = contracts.validate("crew_record", r)
    return out


def build(protocol: str = DEFAULT_PROTOCOL, profile: str = DEFAULT_PROFILE, db: str = ":memory:",
          clock: MissionClock | None = None, records_path=None, content_root=CONTENT,
          explainer="ollama", habitat_url: str | None = None) -> FlowEngine:
    habitat_url = habitat_url or os.environ.get("SF_HABITAT_URL")
    if habitat_url:
        from .habitat import HabitatClock
        clock = HabitatClock(habitat_url)
    questions = json.loads((CONTENT / "flow" / "confirm-questions.json").read_text(encoding="utf-8"))
    eng = FlowEngine(Store(db), clock or MissionClock(), load_protocol(protocol, content_root),
                     load_profile(profile, content_root),
                     load_records(records_path or os.environ.get("SF_RECORDS") or DEFAULT_RECORDS), questions)
    from .explainer import Explainer, ollama_transport
    if explainer == "ollama":
        explainer = ollama_transport(os.environ.get("SF_OLLAMA_MODEL", "llama3.2:3b"),
                                     os.environ.get("SF_OLLAMA_URL", "http://127.0.0.1:11434"))
    eng.explainer = Explainer(eng, explainer)
    if habitat_url:
        from .habitat import Habitat
        eng.habitat = Habitat(eng, habitat_url)
    try:
        from .ground import Ground  # ticket 12
        eng.ground = Ground(eng)
    except ImportError:
        pass
    return eng
