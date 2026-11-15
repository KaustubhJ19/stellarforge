"""Golden replay runner (the Spec 4 test seam): feed a replay file through the engine
and return the events and per-tablet screens that result."""
from __future__ import annotations

import json
from pathlib import Path

from . import contracts
from .contracts import SCHEMA_VERSION
from .flow import FlowEngine


def load(path) -> dict:
    return contracts.validate("replay_file", json.loads(Path(path).read_text(encoding="utf-8")))


def dispatch(eng: FlowEngine, ev: dict) -> None:
    d = ev.get("payload", ev.get("data")) or {}
    kind = ev["type"]
    if kind == "reading":
        eng.ingest_reading(d)
    elif kind == "alert":
        eng.ingest_alert(d)
    elif kind == "trigger":  # auto Trigger from the stream (Spec 3)
        eng.trigger(d)
    elif kind == "press_emergency":  # the manual button: posts a manual Trigger
        eng.trigger({"schema_version": SCHEMA_VERSION, "kind": "manual", "crew": d["crew"], "t": eng.now(),
                     "reason": d.get("reason", "Emergency button")})
    elif kind == "answer":
        eng.answer(d["crew"], d["question"], d["choice"])
    elif kind == "accept":
        eng.accept(d["crew"])
    elif kind == "join_r2":
        eng.join_r2(d["crew"])
    elif kind == "observer":
        eng.observer_answer(d["crew"], d["choice"])
    elif kind == "next":
        eng.next(d["crew"])
    elif kind == "back":
        eng.back(d["crew"])
    elif kind == "explain":
        eng.explainer.explain(d["crew"], d.get("question"))
    elif kind == "console_reply":
        eng.ground.console_reply(d["report"] if "report" in d else None, d["text"], scripted=d.get("scripted", False))
    elif kind in ("tick", "crew_report"):  # crew_report: Spec 1 marker (chest pain is crew-reported in the UI)
        pass
    else:
        raise ValueError(f"unknown replay event type '{kind}'")


def run(eng: FlowEngine, replay: dict, until: float | None = None) -> FlowEngine:
    """Run events in time order; timers between events fire at their exact due time."""
    for ev in sorted(replay["events"], key=lambda e: e["t"]):
        _advance_to(eng, ev["t"])
        dispatch(eng, ev)
        eng.tick()
    if until is not None:
        _advance_to(eng, until)
    return eng


def _advance_to(eng: FlowEngine, t: float) -> None:
    """Jump the clock from timer to timer so every timer fires at its exact time."""
    while True:
        due = [d for d in eng.due_times() if eng.now() < d <= t]
        if not due:
            break
        eng.clock.set(min(due))
        eng.tick()
    if eng.now() < t:
        eng.clock.set(t)
        eng.tick()


def screens(eng: FlowEngine, crew: str) -> list[str]:
    return [e["screen"] for e in eng.events if e["type"] == "screen" and e["crew"] == crew]


def types(eng: FlowEngine) -> list[str]:
    return [e["type"] for e in eng.events if e["type"] != "screen"]
