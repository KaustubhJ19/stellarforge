"""Read-only tools for the L3 investigator (ticket 13). No write path, no network: they only read
one HotSummary snapshot and the condition library, and every result is a flat {field: scalar} map
so the verifier can compare a cited (tool, field, value) with exactly what the tool returned."""
from __future__ import annotations

from typing import Any

from app.explainer import words

from .conditions import ConditionLibrary
from .hot_summary import HotSummary

MAX_MATCHES = 3

TOOL_DOCS = {
    "history": "Per-indicator baseline statistics (z scores, CUSUM, slopes). Args: none.",
    "alerts": "Open alerts for this crew member. Args: none.",
    "forms": "Form answers and crew notes, e.g. the post-EVA form. Args: none.",
    "summary": "Context numbers: sleep debt, dose, hours since EVA, trends. Args: none.",
    "library_search": 'Search the condition library by keyword. Args: {"query": "text"}.',
}


def flatten(obj: Any, prefix: str = "") -> dict[str, Any]:
    if isinstance(obj, dict):
        items = obj.items()
    elif isinstance(obj, list):
        items = enumerate(obj)
    else:
        return {prefix: obj}
    out: dict[str, Any] = {}
    for k, v in items:
        out |= flatten(v, f"{prefix}.{k}" if prefix else str(k))
    return out


def _library_search(library: ConditionLibrary, query: str) -> dict[str, Any]:
    q = words(query)
    scored = sorted(((len(q & words(c.name + " " + " ".join(s.text for s in c.signs))), c)
                     for c in library.conditions), key=lambda x: -x[0])
    out: dict[str, Any] = {}
    for score, c in scored[:MAX_MATCHES]:
        if score == 0:
            break
        out |= {f"{c.id}.name": c.name, f"{c.id}.protocol_id": c.protocol_id} | {
            f"{c.id}.sign.{s.id}": s.text for s in c.signs}
    return out


def run_tool(name: str, args: dict, snap: HotSummary, library: ConditionLibrary) -> dict[str, Any]:
    """Raises KeyError for a tool that does not exist and ValueError for bad arguments."""
    if name == "history":
        return flatten(snap.indicators)
    if name == "alerts":
        return flatten(snap.open_alerts) | {"count": len(snap.open_alerts)}
    if name == "forms":
        return flatten(snap.form_answers)
    if name == "summary":
        return flatten(snap.context)
    if name == "library_search":
        query = args.get("query") if isinstance(args, dict) else None
        if not isinstance(query, str) or not query.strip():
            raise ValueError("library_search needs a query")
        return _library_search(library, query)
    raise KeyError(name)
