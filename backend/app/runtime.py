"""Wire the engine from content + test doubles (Spec 1/5 stand-ins until integration)."""
from __future__ import annotations

import json
import os

from .clock import MissionClock
from .content import CONTENT, REPO, load_profile, load_protocol
from .flow import FlowEngine
from .store import Store

DEFAULT_PROTOCOL = "stub-protocol"
DEFAULT_PROFILE = "stub-mars"
DEFAULT_RECORDS = REPO / "replay" / "stub-crew-records.json"


def load_records(path=DEFAULT_RECORDS) -> dict[str, dict]:
    from . import contracts
    data = json.loads(path.read_text(encoding="utf-8"))
    return {r["id"]: contracts.validate("crew_record", r) for r in data["records"]}


def build(protocol: str = DEFAULT_PROTOCOL, profile: str = DEFAULT_PROFILE, db: str = ":memory:",
          clock: MissionClock | None = None, records_path=DEFAULT_RECORDS, content_root=CONTENT,
          explainer="ollama", habitat_url: str | None = None) -> FlowEngine:
    habitat_url = habitat_url or os.environ.get("SF_HABITAT_URL")
    if habitat_url:
        from .habitat import HabitatClock
        clock = HabitatClock(habitat_url)
    questions = json.loads((CONTENT / "flow" / "confirm-questions.json").read_text(encoding="utf-8"))
    eng = FlowEngine(Store(db), clock or MissionClock(), load_protocol(protocol, content_root),
                     load_profile(profile, content_root),
                     load_records(records_path), questions)
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
