"""Backend-down support (ticket 14).

* `bundle()` — what a tablet caches so it can run an offline emergency mode: cited steps
  (Mission-profile equipment, solo-rescuer filter), profile, Crew records, questions.
* `sync()` — idempotent upload of what tablets queued while the backend was down:
  manual Triggers, step actions and record accesses logged on the tablet. Synced items are
  recorded with their original mission times; they do NOT start a live flow or an alarm
  after the fact.
"""
from __future__ import annotations

from . import triage
from .contracts import ContractError, validate
from .content import visible_steps
from .flow import DISCLAIMER

KINDS = {"trigger", "step_shown", "step_completed", "record_access"}


def _protocol(eng, p) -> dict:
    steps = visible_steps(p, eng.profile["equipment"], 1)
    return {"id": p.id, "title": p.title, "stub": p.stub, "steps": [s.public() for s in steps]}


def bundle(eng) -> dict:
    return {
        "protocol": _protocol(eng, eng.protocol),  # kept for tablets that do not route
        "protocols": {pid: _protocol(eng, p) for pid, p in eng.protocols.items()},
        "routes": eng.routes,  # the same rule table, so a tablet routes the same way offline
        "intake_fields": triage.intake_fields(),
        "profile": {"id": eng.profile["id"], "crew": eng.crew, "delay_label": eng.profile.get("delay_label")},
        "records": {c: eng.records.get(c) for c in eng.crew if eng.records.get(c)},
        "names": {c: eng.name(c) for c in eng.crew},
        "questions": eng.questions["patient"],
        "disclaimer": DISCLAIMER,
    }


def sync(eng, tablet: str, items: list[dict]) -> dict:
    eng._check_crew(tablet)
    accepted, duplicates = 0, 0
    with eng._lock:
        for it in items:
            iid, kind, t, data = it.get("id"), it.get("type"), it.get("t"), it.get("data") or {}
            if not isinstance(iid, str) or kind not in KINDS or not isinstance(t, (int, float)) or t < 0:
                raise ContractError(f"sync: invalid item {it!r}")
            # validate fully before marking the id as synced, so a bad item can be fixed and re-sent
            if kind == "trigger":
                validate("trigger", data)
            elif kind == "record_access":
                actor, subject = data.get("actor"), data.get("subject")
                eng._check_crew(actor)
                eng._check_crew(subject)
            if not eng.store.mark_synced(iid):
                duplicates += 1
                continue
            if kind == "trigger":
                eng.emit("offline_trigger", tablet=tablet, original_t=t, crew=data["crew"], kind=data["kind"])
            elif kind in ("step_shown", "step_completed"):
                eng.emit(f"offline_{kind}", tablet=tablet, original_t=t, step=data.get("step"), patient=data.get("patient"))
            elif kind == "record_access":
                eng.store.log_access(t, actor, subject, None, True, "offline emergency access (logged on tablet, synced)")
                eng.emit("offline_record_access", tablet=tablet, original_t=t, actor=actor, subject=subject)
            accepted += 1
    return {"accepted": accepted, "duplicates": duplicates}
