"""Wire the engine from content + test doubles (Spec 1/5 stand-ins until integration)."""
from __future__ import annotations

import json
import os

from . import triage
from .clock import MissionClock
from .content import CONTENT, REPO, load_profile, load_protocol
from .flow import FlowEngine
from .store import Store

DEFAULT_PROTOCOL = "stub-protocol"
DEFAULT_PROFILE = "stub-mars"
DEFAULT_RECORDS = REPO / "replay" / "stub-crew-records.json"  # the test double; the service defaults to REAL_RECORDS
REAL_RECORDS = REPO / "replay" / "crew-records.json"


def load_records(path=DEFAULT_RECORDS) -> dict[str, dict]:
    from . import contracts
    data = json.loads(path.read_text(encoding="utf-8"))
    records = data["records"] if isinstance(data, dict) else data  # Spec 1 writes a bare list, the stub wraps it
    return {r["id"]: contracts.validate("crew_record", r) for r in records}


def build(protocol: str = DEFAULT_PROTOCOL, profile: str = DEFAULT_PROFILE, db: str = ":memory:",
          clock: MissionClock | None = None, records_path=DEFAULT_RECORDS, content_root=CONTENT,
          explainer="ollama", habitat_url: str | None = None, routing: bool = False,
          investigator=None) -> FlowEngine:
    habitat_url = habitat_url or os.environ.get("SF_HABITAT_URL")
    if habitat_url:
        from .habitat import HabitatClock
        clock = HabitatClock(habitat_url)
    questions = json.loads((CONTENT / "flow" / "confirm-questions.json").read_text(encoding="utf-8"))
    main = load_protocol(protocol, content_root)
    protocols, routes = {main.id: main}, None
    if routing:  # intent-first: load every protocol the route table can pick that has cited content
        routes = triage.load_routes(content_root / "triage" / "routes.json")
        for pid in sorted({r["protocol"] for r in routes["rows"]} - {main.id}):
            if (content_root / "protocols" / f"{pid}.json").exists():
                protocols[pid] = load_protocol(pid, content_root)
    eng = FlowEngine(Store(db), clock or MissionClock(), main, load_profile(profile, content_root),
                     load_records(records_path), questions, protocols=protocols, routes=routes)
    from .explainer import Explainer, ollama_transport
    url = os.environ.get("SF_OLLAMA_URL", "http://127.0.0.1:11434")
    if explainer == "ollama":
        explainer = ollama_transport(os.environ.get("SF_OLLAMA_MODEL", "llama3.2:3b"), url)
        from copilot.investigator_eval import load_config
        cfg = load_config()
        if investigator is None and cfg["enabled"]:  # ship gate (ticket 14): off by default unless the eval passed
            from copilot.investigator import SYSTEM, TIME_BOX_S  # same local server, JSON replies, longer answers
            investigator = ollama_transport(os.environ.get("SF_INVESTIGATOR_MODEL", cfg["model"]), url,
                                            timeout=TIME_BOX_S, system=SYSTEM, num_predict=400, json_mode=True)
    eng.explainer = Explainer(eng, explainer)
    from copilot.investigator import InvestigatorRunner
    eng.investigator = InvestigatorRunner(eng, investigator)
    from copilot.hot_summary import PushedHotSummaries  # Spec 3: latest Spec 2 snapshot per crew
    eng.hot_summaries = PushedHotSummaries(habitat_configured=bool(habitat_url))
    if habitat_url:
        from .habitat import Habitat
        eng.habitat = Habitat(eng, habitat_url)
    try:
        from .ground import Ground  # ticket 12
        eng.ground = Ground(eng)
    except ImportError:
        pass
    return eng
