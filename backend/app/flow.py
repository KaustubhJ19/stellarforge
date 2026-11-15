"""Emergency flow engine (Spec 4): one server-side state machine shared by every tablet.

Both triggers (auto from Spec 3, manual from the Emergency button) enter `trigger()`
and nothing after entry branches on the trigger kind. Each tablet asks `view(crew)`
for the screen it should show. Every state change emits an event; golden replay tests
assert on those events and screens.
"""
from __future__ import annotations

import itertools
import threading
from dataclasses import dataclass, field

from copilot.hot_summary import PushedHotSummaries
from copilot import record
from copilot.session import CopilotSession, build_session

from . import contracts, triage
from .clock import MissionClock
from .content import Protocol, visible_steps
from .store import Store, StoreError

DISCLAIMER = "Decision support, not diagnosis."
CONFIRM_TIMEOUT_S = 15.0
URGENCY_LABEL = {
    "ACT_NOW": "ACT NOW",
    "ESCALATE_TO_GROUND": "ESCALATE TO GROUND",
    "MONITOR": "MONITOR",
    "ROUTINE": "ROUTINE",
}
NOT_ASSESSED = "Urgency not assessed (manual start)"
ESTIMATE_LABEL = "estimate, not validated"


class FlowError(ValueError):
    """Request is invalid for the current flow state (HTTP 409/422)."""


class AccessDenied(PermissionError):
    pass


@dataclass
class Emergency:
    id: str
    patient: str
    trigger: dict
    started_t: float
    confirm_deadline: float | None
    status: str = "confirming"  # confirming | help_requested | alarm | active | dismissed
    path: str | None = None  # help_requested | no_answer
    answers: dict = field(default_factory=dict)
    observer: str | None = None
    rescuers: list[str] = field(default_factory=list)  # [R1, R2]
    done: dict[str, list[str]] = field(default_factory=dict)  # crew -> completed item keys, in order
    record_view: dict[str, dict] = field(default_factory=dict)  # crew -> record or error
    timeline: list[dict] = field(default_factory=list)
    actions: list[dict] = field(default_factory=list)
    protocol_id: str | None = None  # which protocol the steps come from; None = not covered
    route: dict | None = None  # {protocol_id, rule_id, reason} once the router (or an override) has run
    intake: dict | None = None  # the confirmed Intake form
    needs_intake: bool = False  # routing is on and the Trigger was not the automatic arrest rule
    copilot: CopilotSession | None = None  # Spec 3 L0 session; None when routing is off
    choice: dict | None = None  # the rescuer's copilot choice {kind, protocol_id, by}; required before the steps
    copilot_last: dict | None = None  # newest event of this emergency's hash chain (decision record)

    @property
    def open(self) -> bool:
        return self.status != "dismissed"

    def role(self, crew: str) -> str | None:
        if crew in self.rescuers:
            return f"R{self.rescuers.index(crew) + 1}"
        return None


class FlowEngine:
    def __init__(self, store: Store, clock: MissionClock, protocol: Protocol, profile: dict,
                 crew_records: dict[str, dict], questions: dict,
                 protocols: dict[str, Protocol] | None = None, routes: dict | None = None):
        self.store, self.clock, self.protocol, self.profile = store, clock, protocol, profile
        self.protocols = protocols or {protocol.id: protocol}  # every protocol the router may pick
        self.routes = routes  # None = routing off: every Trigger uses `protocol`
        self.crew = list(profile["crew"])
        self.records = crew_records
        self.questions = questions
        self.events: list[dict] = []
        self.emergencies: dict[str, Emergency] = {}
        self.alerts: dict[str, dict] = {}  # crew -> latest emergency Alert (Spec 3)
        self.readings: dict[str, dict[str, dict]] = {}  # crew -> indicator -> latest Reading
        self.ground = None  # set by ground module (ticket 12)
        self.habitat = None  # Spec 1 service adapter (ticket 15), optional
        self.hot_summaries = PushedHotSummaries()  # Spec 3: latest Spec 2 snapshot per crew (runtime replaces it)
        self.investigator = None  # Spec 3 L3 InvestigatorRunner (runtime sets it)
        self._ids = itertools.count(1)
        self._screens: dict[str, str] = {c: "idle" for c in self.crew}
        self._lock = threading.RLock()
        for p in self.protocols.values():
            for sid, reason in p.refused:  # unsafe content never reaches a screen
                self.emit("step_refused", step=sid, reason=reason)

    @property
    def routing(self) -> bool:
        return self.routes is not None

    def proto(self, e: "Emergency") -> Protocol | None:
        """The protocol this emergency uses, or None when the router found nothing that covers it."""
        return self.protocols.get(e.protocol_id) if e.protocol_id else None

    # ------------------------------------------------------------------ util
    def now(self) -> float:
        return self.clock.now()

    def emit(self, type_: str, **data) -> dict:
        ev = {"t": round(self.now(), 3), "type": type_, **data}
        self.events.append(ev)
        self.store.add_event(ev)
        return ev

    def _note(self, e: Emergency, what: str, **data) -> None:
        e.timeline.append({"t": round(self.now(), 3), "event": what, **data})

    def active_for(self, patient: str) -> Emergency | None:
        return next((e for e in self.emergencies.values() if e.patient == patient and e.open), None)

    def _get(self, eid: str | None, *, for_crew: str | None = None) -> Emergency:
        if eid:
            e = self.emergencies.get(eid)
            if not e or not e.open:
                raise FlowError(f"no open emergency {eid}")
            return e
        opened = [e for e in self.emergencies.values() if e.open and e.patient != for_crew]
        if len(opened) != 1:
            raise FlowError("emergency id required" if opened else "no open emergency")
        return opened[0]

    def _check_crew(self, crew: str) -> None:
        if crew not in self.crew:
            raise contracts.ContractError(f"unknown crew '{crew}'")

    # ------------------------------------------------------------- stream in
    def ingest_alert(self, alert: dict) -> None:
        with self._lock:
            contracts.validate("alert", alert)
            if alert["kind"] == "emergency":
                self.alerts[alert["crew"]] = alert
            self.emit("alert", id=alert["id"], crew=alert["crew"], kind=alert["kind"], urgency=alert["urgency"])

    def ingest_reading(self, reading: dict) -> None:
        with self._lock:
            contracts.validate("reading", reading)
            self.readings.setdefault(reading["crew"], {})[reading["indicator"]] = reading

    # -------------------------------------------------------------- triggers
    def trigger(self, trig: dict) -> Emergency:
        """Single entry point for auto and manual Triggers (story 3)."""
        with self._lock:
            contracts.validate("trigger", trig)
            self._check_crew(trig["crew"])
            existing = self.active_for(trig["crew"])
            if existing:
                self.emit("trigger_duplicate", emergency=existing.id, kind=trig["kind"], crew=trig["crew"])
                self._note(existing, "duplicate trigger ignored", kind=trig["kind"])
                return existing
            e = Emergency(id=f"em-{next(self._ids)}", patient=trig["crew"], trigger=dict(trig),
                          started_t=self.now(), confirm_deadline=self.now() + CONFIRM_TIMEOUT_S,
                          protocol_id=self.protocol.id)
            self.emergencies[e.id] = e
            self._note(e, "trigger", kind=trig["kind"], reason=trig["reason"])
            self.emit("trigger", emergency=e.id, kind=trig["kind"], crew=e.patient, reason=trig["reason"])
            if self.routing:
                e.needs_intake = trig["kind"] != "auto"
                e.protocol_id = None  # no protocol until the router (or the arrest rule) has picked one
                if not e.needs_intake:  # the arrest rule fired: skip the questions
                    self._set_route(e, triage.route(self.routes, None, self._live(e.patient), set(self.protocols),
                                                    trigger_kind="auto"))
                if e.copilot is None:  # manual Trigger: L0 on the live facts alone, the answers come later
                    self._copilot(e)
            self._refresh()
            return e

    def urgency(self, e: Emergency) -> str | None:
        alert = self.alerts.get(e.patient)
        return alert["urgency"] if alert else None

    # --------------------------------------------------------- confirmation
    def answer(self, crew: str, question: str, choice: str, eid: str | None = None) -> Emergency:
        with self._lock:
            e = self.active_for(crew) if eid is None else self._get(eid)
            if not e or e.patient != crew:
                raise FlowError("only the patient answers the confirm questions")
            q = next((q for q in self.questions["patient"] if q["id"] == question), None)
            if not q or choice not in {c["id"] for c in q["choices"]}:
                raise FlowError(f"invalid answer {question}={choice}")
            late = e.status != "confirming"
            e.answers[question] = choice
            self._note(e, "patient answer", question=question, choice=choice, late=late,
                       **({"crew_reported": True} if question == "chest_pain" else {}))
            self.emit("patient_answer", emergency=e.id, question=question, choice=choice, late=late)
            if late:  # after the alarm the answer is recorded only; the flow is not changed
                self._refresh()
                return e
            e.confirm_deadline = None  # any answer means the patient responded
            if question == "status" and choice == "false_alarm":
                e.status = "dismissed"
                e.trigger["confirmed"] = False
                reason = "patient answered: " + next(c["label"] for c in q["choices"] if c["id"] == choice)
                self._note(e, "dismissed as false alarm", reason=reason)
                self.emit("false_alarm_dismissed", emergency=e.id, reason=reason)
            elif question == "status" and choice == "need_help":
                e.status, e.path = "help_requested", "help_requested"
                e.trigger["confirmed"] = True
                self._note(e, "confirmed by patient")
                self.emit("confirmed", emergency=e.id, by="patient")
                self._started(e)
            self._refresh()
            return e

    def tick(self) -> None:
        """Fire due timers: no answer within 15 s rings the crew alarm (story 6)."""
        with self._lock:
            for e in list(self.emergencies.values()):
                if e.status == "confirming" and e.confirm_deadline is not None and self.now() >= e.confirm_deadline:
                    e.status, e.path, e.confirm_deadline = "alarm", "no_answer", None
                    targets = [c for c in self.crew if c != e.patient]
                    self._note(e, "no answer in 15 s; crew alarm")
                    self.emit("no_answer", emergency=e.id)
                    self.emit("crew_alarm", emergency=e.id, targets=targets)
                    self._started(e)
            if self.ground:
                self.ground.tick()
            self._refresh()

    def due_times(self) -> list[float]:
        """Mission times at which a timer will fire (used by the replay runner)."""
        out = [e.confirm_deadline for e in self.emergencies.values()
               if e.status == "confirming" and e.confirm_deadline is not None]
        if self.ground:
            out += self.ground.due_times()
        return out

    def _started(self, e: Emergency) -> None:
        if self.ground:
            self.ground.start(e)

    # --------------------------------------------------------------- rescuers
    def accept(self, crew: str, eid: str | None = None) -> str:
        """Accept the crew alarm or join a help request. First wins = Rescuer 1."""
        with self._lock:
            self._check_crew(crew)
            e = self._get(eid, for_crew=crew)
            if crew == e.patient:
                raise FlowError("the patient cannot be the rescuer")
            if e.status not in ("alarm", "help_requested"):
                if e.rescuers:
                    raise FlowError(f"already accepted by {e.rescuers[0]}")
                raise FlowError("nothing to accept")
            e.rescuers.append(crew)
            e.status = "active"
            self._note(e, "rescuer 1 assigned", crew=crew)
            self.emit("rescuer_assigned", emergency=e.id, crew=crew, role="R1")
            if e.path == "no_answer":
                self.emit("alarm_stopped", emergency=e.id)
            self._enter(e, crew)
            self._refresh()
            return "R1"

    def can_join_r2(self, e: Emergency, crew: str) -> bool:
        return (e.status == "active" and len(e.rescuers) == 1 and crew not in (e.patient, *e.rescuers)
                and (e.route is not None or not e.needs_intake)  # Rescuer 2 joins after the route is known
                and len(self.crew) > 2)  # two-person rover profile: no Rescuer 2

    def join_r2(self, crew: str, eid: str | None = None) -> str:
        with self._lock:
            self._check_crew(crew)
            e = self._get(eid, for_crew=crew)
            if not self.can_join_r2(e, crew):
                raise FlowError("Rescuer 2 is not available")
            e.rescuers.append(crew)
            self._note(e, "rescuer 2 assigned", crew=crew)
            self.emit("rescuer_assigned", emergency=e.id, crew=crew, role="R2")
            self._enter(e, crew)
            self._refresh()
            return "R2"

    def observer_answer(self, crew: str, choice: str, eid: str | None = None) -> None:
        with self._lock:
            e = self._get(eid, for_crew=crew)
            if e.role(crew) != "R1" or self._current(e, crew) != "observer":
                raise FlowError("observer question is for Rescuer 1 after a crew alarm")
            q = self.questions["observer"]
            if choice not in {c["id"] for c in q["choices"]}:
                raise FlowError(f"invalid observer answer {choice}")
            e.observer = choice
            self._note(e, "observer answer", question=q["text"], choice=choice, by=crew)
            self.emit("observer_answer", emergency=e.id, crew=crew, choice=choice)
            self._advance(e, crew)
            self._refresh()

    # --------------------------------------------------------------- routing
    def _live(self, patient: str) -> dict:
        """Live facts the router may use. No cabin alert stream exists in the flow yet, so it is always False."""
        rhythm = self.readings.get(patient, {}).get("cardiac_rhythm")
        return {"arrest": bool(rhythm) and triage.is_arrest_rhythm(rhythm["value"]), "cabin_alert": False,
                "low_spo2": self._spo2_low(patient)}

    def _spo2_low(self, patient: str) -> bool:
        bound = ((self.routes or {}).get("thresholds") or {}).get("spo2_low")
        value = self.readings.get(patient, {}).get("spo2", {}).get("value")
        if not bound or isinstance(value, bool) or not isinstance(value, (int, float)):
            return False
        return (value / 100 if value > 1 else value) < bound["value"]  # Pulse sends a 0-1 fraction; accept percent too

    def _copilot(self, e: Emergency, route: dict | None = None) -> None:
        """Rebuild the L0 copilot session (briefing + rule verdict) from the facts known now."""
        route = route or triage.route(self.routes, e.intake, self._live(e.patient), set(self.protocols),
                                      trigger_kind=e.trigger["kind"])
        e.copilot = c = build_session(emergency=e.id, crew=e.patient, t=round(self.now(), 3), routes=self.routes,
                                      route=route, history=self.hot_summaries.latest(e.patient))
        self.copilot_event(e, "assessment", trigger=e.trigger, l0=c.l0, history_sha256=c.history_digest,
                           versions=c.versions, briefing=c.briefing)

    def copilot_event(self, e: Emergency, name: str, /, **data) -> dict:
        """Append `copilot_<name>` to the emergency timeline and store, chained to the previous copilot event."""
        with self._lock:
            ev = self.emit(f"{record.PREFIX}{name}", emergency=e.id, prev=record.prev_hash(e.copilot_last), **data)
            e.copilot_last = ev
            return ev

    def verify_copilot(self, eid: str) -> record.ChainResult:
        """Re-read the stored events of one emergency and check the chain, including its newest event."""
        e = self.emergencies[eid]
        return record.verify(record.chain_of(self.store.events(), eid),
                             head=record.digest(e.copilot_last) if e.copilot_last else None)

    CHOICES = ("router", "suggestion", "other", "none")

    def copilot_choice(self, crew: str, kind: str, protocol: str | None = None, eid: str | None = None) -> dict:
        """The rescuer's required decision: keep the router default, take the copilot suggestion, pick another
        protocol, or act alone. Suggestion and other go through the existing override."""
        with self._lock:
            self._check_crew(crew)
            e = self._get(eid, for_crew=crew)
            if e.role(crew) is None:
                raise FlowError("only a rescuer can choose")
            if e.copilot is None:
                raise FlowError("no copilot session for this emergency")
            if kind not in self.CHOICES:
                raise FlowError(f"unknown choice '{kind}'")
            if kind == "suggestion":
                protocol = e.copilot.suggested_protocol
                if not protocol:
                    raise FlowError("the copilot has no suggestion")
            if kind in ("suggestion", "other"):
                if not protocol:
                    raise FlowError("name the protocol to switch to")
                self.switch_protocol(crew, protocol, e.id)  # logs the switch and the choice
            else:
                self._guard_intake(e)
                self._record_choice(e, crew, kind)
            self._refresh()
            return e.choice

    def _guard_intake(self, e: Emergency) -> None:
        if e.needs_intake and e.intake is None:
            raise FlowError("answer the intake first; the choice is about the protocol it chose")

    def _record_choice(self, e: Emergency, crew: str, kind: str) -> None:
        e.choice = {"kind": kind, "protocol_id": e.protocol_id, "by": crew}
        self._note(e, "copilot choice", **e.choice)
        self.copilot_event(e, "choice", assessment_id=e.copilot.assessment_id, **e.choice)

    def _set_route(self, e: Emergency, route: dict) -> None:
        e.route, e.protocol_id = route, route["protocol_id"]
        self._note(e, "routed", protocol=route["protocol_id"], rule=route["rule_id"], reason=route["reason"])
        self.emit("routed", emergency=e.id, protocol=route["protocol_id"], rule=route["rule_id"])
        self._copilot(e, route)
        if self.ground:
            self.ground.refresh(e)

    def submit_intake(self, crew: str, intake: dict, eid: str | None = None) -> dict:
        """Rescuer 1 confirms what is happening; the rule table picks the protocol (never a model)."""
        with self._lock:
            self._check_crew(crew)
            e = self._get(eid, for_crew=crew)
            if e.role(crew) != "R1" or self._current(e, crew) != "intake":
                raise FlowError("intake is for Rescuer 1, once, before the record; use the override to change protocol")
            clean = triage.validate_intake(intake)
            e.intake = clean
            self._note(e, "intake", by=crew, **clean)
            self.emit("intake", emergency=e.id, crew=crew, **clean)
            self._set_route(e, triage.route(self.routes, clean, self._live(e.patient), set(self.protocols),
                                            trigger_kind=e.trigger["kind"]))
            self._advance(e, crew)
            self._refresh()
            return e.route

    def switch_protocol(self, crew: str, protocol_id: str, eid: str | None = None) -> dict:
        """A rescuer overrides the router. Logged with who and from/to; the router can be wrong."""
        with self._lock:
            self._check_crew(crew)
            e = self._get(eid, for_crew=crew)
            if e.role(crew) is None:
                raise FlowError("only a rescuer can switch protocol")
            if protocol_id not in self.protocols:
                raise FlowError(f"unknown protocol '{protocol_id}'")
            self._guard_intake(e)
            before = e.protocol_id
            e.route = {"protocol_id": protocol_id, "rule_id": "override", "reason": f"Switched by {crew}."}
            e.protocol_id = protocol_id
            for c, done in e.done.items():  # steps of the old protocol must not count as done in the new one
                e.done[c] = [k for k in done if not k.startswith("step:")]
            self._note(e, "protocol switched", by=crew, **{"from": before, "to": protocol_id})
            self.emit("protocol_switched", emergency=e.id, crew=crew, to=protocol_id, **{"from": before})
            if self.ground:  # after the note, so the report in flight lists the switch
                self.ground.refresh(e)
            if e.copilot:  # the override is also the rescuer's copilot choice
                self._record_choice(e, crew, "suggestion" if protocol_id == e.copilot.suggested_protocol else "other")
            self._refresh()
            return e.route

    # ------------------------------------------------------------ sequence
    def steps_for(self, e: Emergency, crew: str):
        p = self.proto(e)
        if p is None:  # not covered: no steps, ground takes over
            return []
        return visible_steps(p, self.profile["equipment"], len(e.rescuers), e.role(crew))

    def sequence(self, e: Emergency, crew: str) -> list[str]:
        items = ["observer"] if (e.role(crew) == "R1" and e.path == "no_answer") else []
        if e.needs_intake and e.role(crew) == "R1":
            items.append("intake")
        items += ["record", "contributors"] + [f"step:{s.id}" for s in self.steps_for(e, crew)] + ["report"]
        return items

    def _current(self, e: Emergency, crew: str) -> str | None:
        done = e.done.get(crew, [])
        return next((k for k in self.sequence(e, crew) if k not in done), None)

    def _enter(self, e: Emergency, crew: str) -> None:
        """Side effects when a rescuer lands on an item (record opening, step shown)."""
        cur = self._current(e, crew)
        if cur == "record" and crew not in e.record_view:
            try:
                e.record_view[crew] = {"ok": True, "record": self.open_record(crew, e.patient, e.id)}
            except (StoreError, AccessDenied, PermissionError, OSError) as err:
                e.record_view[crew] = {"ok": False, "error": str(err)}
        elif cur and cur.startswith("step:"):
            sid = cur[5:]
            if not any(a["step"] == sid and a["by"] == crew and a["action"] == "shown" for a in e.actions):
                e.actions.append({"t": round(self.now(), 3), "action": "shown", "step": sid, "by": crew})
                self.emit("step_shown", emergency=e.id, crew=crew, step=sid)

    def _advance(self, e: Emergency, crew: str) -> None:
        cur = self._current(e, crew)
        if cur is None:
            return
        e.done.setdefault(crew, []).append(cur)
        if cur.startswith("step:"):
            e.actions.append({"t": round(self.now(), 3), "action": "completed", "step": cur[5:], "by": crew})
            self._note(e, "step completed", step=cur[5:], by=crew)
            self.emit("step_completed", emergency=e.id, crew=crew, step=cur[5:])
        self._enter(e, crew)

    def next(self, crew: str, eid: str | None = None) -> None:
        with self._lock:
            e = self._get(eid, for_crew=crew)
            cur = self._current(e, crew)
            if e.role(crew) is None or cur in (None, "observer", "intake", "report"):
                raise FlowError("nothing to continue")
            if cur == "contributors" and e.copilot and e.choice is None:
                raise FlowError("choose a protocol option (or act on your own) before the steps")
            self._advance(e, crew)
            self._refresh()

    def back(self, crew: str, eid: str | None = None) -> None:
        with self._lock:
            e = self._get(eid, for_crew=crew)
            done = e.done.get(crew, [])
            if e.role(crew) is None or not done or done[-1] in ("observer", "intake"):
                raise FlowError("nothing to go back to")
            undone = done.pop()
            self._note(e, "went back", item=undone, by=crew)
            self._refresh()

    # --------------------------------------------------------- record access
    def open_record(self, actor: str, subject: str, eid: str | None = None) -> dict:
        """Emergency-mode access to another person's Crew record. Logged before it is returned."""
        with self._lock:
            self._check_crew(actor)
            self._check_crew(subject)
            record = self.records.get(subject)
            if actor == subject:
                return record
            e = next((x for x in self.emergencies.values()
                      if x.open and x.patient == subject and actor in x.rescuers and (eid is None or x.id == eid)), None)
            if e is None:
                self.store.log_access(self.now(), actor, subject, eid, False, "refused: not in emergency mode")
                self.emit("record_access_refused", actor=actor, subject=subject)
                raise AccessDenied("another person's record opens only in emergency mode")
            self.store.log_access(self.now(), actor, subject, e.id, True, f"emergency access as {e.role(actor)}")
            if self.habitat:  # Spec 1 service is the record source and logs the opening as well
                record = self.habitat.record(subject, actor, emergency=True)
            self.emit("record_opened", emergency=e.id, actor=actor, subject=subject)
            self._note(e, "record opened", by=actor)
            return record

    # ------------------------------------------------------------------ views
    def view(self, crew: str) -> dict:
        with self._lock:
            self._check_crew(crew)
            v = self._view(crew) | {"t": round(self.now(), 3)}
            if v["screen"] != "idle":
                v["disclaimer"] = DISCLAIMER
            return v

    def _base(self, e: Emergency) -> dict:
        return {"emergency": e.id, "patient": e.patient, "patient_name": self.name(e.patient)}

    def _view(self, crew: str) -> dict:
        e = self.active_for(crew)
        if e:  # this tablet belongs to the patient
            b = self._base(e)
            if e.status == "confirming":
                u = self.urgency(e)
                left = None if e.confirm_deadline is None else max(0.0, e.confirm_deadline - self.now())
                return b | {"screen": "verdict", "urgency": u, "urgency_label": URGENCY_LABEL.get(u, NOT_ASSESSED),
                            "questions": self.questions["patient"], "answers": dict(e.answers),
                            "seconds_left": None if left is None else round(left, 1)}
            screen = {"help_requested": "help_requested", "alarm": "patient_alarm", "active": "patient_waiting"}[e.status]
            return b | {"screen": screen, "rescuers": list(e.rescuers)}
        for e in self.emergencies.values():
            if e.open and crew in e.rescuers:
                return self._base(e) | self._rescuer_view(e, crew)
        for e in self.emergencies.values():
            if not e.open or crew == e.patient:
                continue
            if e.status == "alarm":
                return self._base(e) | {"screen": "alarm", "ring": True}
            if e.status == "help_requested":
                return self._base(e) | {"screen": "join", "ring": False}
            if self.can_join_r2(e, crew):
                return self._base(e) | {"screen": "join_r2", "ring": False, "rescuer1": e.rescuers[0]}
        return {"screen": "idle"}

    def _rescuer_view(self, e: Emergency, crew: str) -> dict:
        cur = self._current(e, crew)
        role = e.role(crew)
        v = {"role": role, "can_back": bool(e.done.get(crew)) and e.done[crew][-1] not in ("observer", "intake")}
        if self.routing:  # the tablet shows "Using X, because Y" and the override choices
            v |= {"route": e.route, "protocols": [{"id": p.id, "title": p.title} for p in self.protocols.values()]}
            if e.copilot:  # Spec 3 briefing beside the intake screen and the banner; context, not instruction
                v |= {"briefing": e.copilot.briefing, "l0": e.copilot.l0, "choice": e.choice,
                      "suggestion": self._suggestion(e)}
                if self.investigator:  # L3 notes: separate panel, read-only, cannot touch route or steps
                    v |= self.investigator.view(e)
        if cur == "observer":
            return v | {"screen": "observer", "question": self.questions["observer"]}
        if cur == "intake":
            return v | {"screen": "intake", "fields": triage.intake_fields()}
        if cur == "record":
            return v | {"screen": "record"} | e.record_view.get(crew, {"ok": False, "error": "not opened"})
        if cur == "contributors":
            return v | {"screen": "contributors"} | self.contributors(e)
        if cur and cur.startswith("step:"):
            steps = self.steps_for(e, crew)
            ids = [s.id for s in steps]
            sid = cur[5:]
            p = self.proto(e)
            return v | {"screen": "step", "step": p.step(sid).public(),
                        "index": ids.index(sid) + 1, "total": len(ids), "stub": p.stub}
        return v | {"screen": "report", "report": self.ground.report_view(e) if self.ground else None}

    def _suggestion(self, e: Emergency) -> dict | None:
        pid = e.copilot.suggested_protocol if e.copilot else None
        return {"protocol_id": pid, "title": self.protocols[pid].title} if pid in self.protocols else None

    def name(self, crew: str) -> str:
        """Spec 1 CrewRecord has no display name: show the crew id."""
        return f"Crew {crew}"

    @staticmethod
    def cause_text(c) -> str:
        """Spec 1 Alert.likely_causes item: {indicator, direction, note}; Spec 3 writes the note."""
        if isinstance(c, str):
            return c
        return c.get("note") or f"{c.get('indicator')} {c.get('direction')}"

    def contributors(self, e: Emergency) -> dict:
        alert = self.alerts.get(e.patient)
        causes = [self.cause_text(c) for c in alert["likely_causes"]][:3] if alert else []
        return {"causes": causes,
                "message": None if len(causes) >= 2 else
                ("No history-based contributors available." if not causes else "Only one history-based contributor available.")}

    def _refresh(self) -> None:
        for c in self.crew:
            s = self._view(c)["screen"]
            if self._screens.get(c) != s:
                self._screens[c] = s
                self.emit("screen", crew=c, screen=s)
