"""L0 copilot session: the rule verdict and the instant template briefing (ticket 04).

Later tickets build on this:
- `build_session(...)` returns a frozen `CopilotSession`; the flow engine keeps the latest one on
  `Emergency.copilot` and rebuilds it (never mutates it) when the route is decided.
- `session.briefing` is a valid `briefing.schema.json` object; `session.l0` is the rule verdict
  {rule_id, protocol_id, protocol_available, reason, life_threat, fired}.
- L1/L2 add evidence lines and replace `template_text`/`text`; the LLM rewrite sets `source: "llm"`.
"""
from __future__ import annotations

from dataclasses import dataclass

from .hot_summary import HotSummary, NoHistory

SCHEMA_VERSION = "1.0.0"
CONTEXT_LABEL = "context; the protocol above comes first"
RULE_LABEL = "team value (router rule table, not clinically reviewed)"
NO_HISTORY_LABEL = "no history"


@dataclass(frozen=True)
class CopilotSession:
    assessment_id: str
    emergency: str
    crew: str
    t: float
    l0: dict
    history_digest: str | None  # HotSummary.digest(), None when there is no history
    briefing: dict


def l0_verdict(routes: dict, route: dict) -> dict:
    """What the L0 rule table decided. `protocol_id` is the rule's protocol even if its content is not authored yet."""
    row = next((r for r in routes["rows"] if r["id"] == route["rule_id"]), None)
    return {"rule_id": route["rule_id"], "protocol_id": row["protocol"] if row else None,
            "protocol_available": route["protocol_id"] is not None, "reason": route["reason"],
            "life_threat": bool(row and row.get("life_threat")), "fired": row is not None}


def _template(l0: dict, history: HotSummary | NoHistory) -> tuple[str, list[dict]]:
    if l0["fired"]:
        rule = f"Rule {l0['rule_id']}: {l0['reason']}"
        if l0["life_threat"]:
            rule += " Follow the protocol above first."
        evidence = [{"text": rule, "label": RULE_LABEL}]
    else:
        rule = "No rule has fired yet; waiting for the rescuer's answers."
        evidence = []
    if isinstance(history, NoHistory):
        hist = f"No history: {history.reason}."
        evidence.append({"text": hist, "label": NO_HISTORY_LABEL})
    else:
        hist = f"History snapshot received ({history.label}); not used at this level."
        evidence.append({"text": hist, "label": history.label})
    return f"{rule} {hist}", evidence


def build_session(*, emergency: str, crew: str, t: float, routes: dict, route: dict,
                  history: HotSummary | NoHistory) -> CopilotSession:
    l0 = l0_verdict(routes, route)
    text, evidence = _template(l0, history)
    assessment_id = f"assess-{emergency}"
    briefing = {"schema_version": SCHEMA_VERSION, "assessment_id": assessment_id, "crew": crew, "t": t,
                "text": text, "source": "template", "context_label": CONTEXT_LABEL, "evidence": evidence}
    digest = history.digest() if isinstance(history, HotSummary) else None
    return CopilotSession(assessment_id, emergency, crew, t, l0, digest, briefing)
