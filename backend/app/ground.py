"""Ground report (ticket 12) and ground console with delayed reply stored as a Label (ticket 13).

User decision: the report is built and sent automatically ONCE, when the emergency is
confirmed (patient "I need help" or the crew alarm). Ground receives that snapshot after
the one-way delay. The crew's copy keeps updating locally. Delays run on the Mission clock.
"""
from __future__ import annotations

import json

from copilot import record

from . import contracts
from .content import CONTENT, lint_content
from .flow import ESTIMATE_LABEL, NOT_ASSESSED, URGENCY_LABEL, Emergency, FlowError


MAX_OUTCOME_CHARS = 1000


def _content(name: str) -> dict:
    return json.loads((CONTENT / "ground" / name).read_text(encoding="utf-8"))


class Ground:
    def __init__(self, eng):
        self.eng = eng
        self.one_way = float(eng.profile["delay_one_way_s"])
        self.delay_label = eng.profile.get("delay_label", f"one-way delay {self.one_way / 60:.1f} min")
        self.likely_questions = list(_content("likely-questions.json")["questions"])
        self.scripted = _content("scripted-reply.json")["text"]
        self.state: dict[str, dict] = {}  # emergency id -> send / reply state

    # ------------------------------------------------------------- building
    def build(self, e: Emergency) -> dict:
        eng = self.eng
        rec = eng.records.get(e.patient, {})
        name = eng.name(e.patient)
        u = eng.urgency(e)
        chest = {"yes": "yes", "no": "no"}.get(e.answers.get("chest_pain"), "not answered")
        observer = {"yes": "responds", "no": "does not respond"}.get(e.observer or "", "not asked")
        summary = (
            f"{name}: {e.trigger['kind']} trigger at T+{e.started_t:.0f} s. "
            f"Urgency: {URGENCY_LABEL.get(u, NOT_ASSESSED)}. "
            f"Confirmed: {'yes' if e.trigger.get('confirmed') else 'no (crew alarm, no answer)' if e.path == 'no_answer' else 'pending'}. "
            f"Chest pain (crew-reported): {chest}. Observer: patient {observer}. "
            f"Rescuers: {', '.join(e.rescuers) or 'none yet'}."
        )
        if e.route:  # intent-first routing: say which protocol the rescuer was given, and why
            summary += f" Protocol: {e.route['protocol_id'] or 'none (not covered, ground to advise)'} (rule {e.route['rule_id']})."
        if e.intake:
            summary += " Intake: " + ", ".join(f"{k}={v}" for k, v in e.intake.items()) + "."
        history: list[dict] = []
        readings = eng.readings.get(e.patient, {})
        if readings:
            for r in readings.values():
                item = {"type": "vitals", "indicator": r["indicator"], "value": r["value"], "unit": r.get("unit"),
                        "t": r["t"], "source": r.get("source"), "state": r.get("state")}
                if r.get("source") == "sim":
                    item["label"] = ESTIMATE_LABEL
                history.append(item)
        else:
            history.append({"type": "vitals", "unavailable": True, "note": "No readings available (manual start or no sensors)."})
        history += [{"type": "record_anchor", "indicator": k, "mean": v.get("mean"), "sd": v.get("sd")}
                    for k, v in (rec.get("anchor") or {}).items()]
        history += [{"type": "likely_contributor", "text": c} for c in eng.contributors(e)["causes"]]
        history += [{"type": "likely_question", "text": q} for q in self.likely_questions]
        st = self.state.get(e.id, {})
        report = {
            "schema_version": contracts.SCHEMA_VERSION,
            "id": f"gr-{e.id}", "crew": e.patient, "summary": summary, "history": history,
            "timeline": list(e.timeline), "actions": list(e.actions),
            "sent_t": st.get("sent_t", eng.now()),
        }
        if section := self.copilot_section(e):  # add-only: what the copilot saw, suggested and the rescuer chose
            report["copilot"] = section
        if st.get("delivered"):  # Spec 1: reply_t is a number when present, so omit it until then
            report["reply_t"] = st["reply_t"]
            report["reply"] = st["reply"]
        return contracts.validate("ground_report", report)

    def copilot_section(self, e: Emergency) -> dict | None:
        """The hash-chained copilot record of this emergency with its verification status, or None without one."""
        with self.eng._lock:  # the async investigator appends events; read the store and the head together
            chain = record.chain_of(self.eng.store.events(), e.id)
            if not chain:
                return None
            head = record.digest(e.copilot_last)
        res = record.verify(chain, head=head)
        return {"chain": {"ok": res.ok, "reason": res.reason, "length": len(chain), "head": head}, "events": chain,
                "versions": dict(e.copilot.versions) if e.copilot else {}, "timings": record.timings(chain)}

    def _chain(self, e: Emergency, name: str, **data) -> None:
        if e.copilot:  # one log: ground steps join the copilot chain only when the copilot ran
            self.eng.copilot_event(e, name, **data)

    # --------------------------------------------------------------- sending
    def start(self, e: Emergency) -> None:
        if e.id in self.state:
            return
        now = self.eng.now()
        self.state[e.id] = {"sent_t": now}
        snap = self.build(e)
        self.state[e.id].update(snapshot=snap, arrives_t=now + self.one_way, expected_reply_t=now + 2 * self.one_way)
        self.eng.store.put_report(snap)
        self.eng._note(e, "ground report sent", report=snap["id"])
        self.eng.emit("ground_report_sent", emergency=e.id, report=snap["id"], sent_t=now,
                      arrives_t=now + self.one_way, expected_reply_t=now + 2 * self.one_way)

    def refresh(self, e: Emergency) -> None:
        """Re-take the snapshot while the report is still in transit (the route is decided after it was sent).
        Once it has reached ground it is fixed; the crew's own copy keeps updating."""
        st = self.state.get(e.id)
        if not st or self.eng.now() >= st["arrives_t"]:
            return
        st["snapshot"] = self.build(e)
        self.eng.store.put_report(st["snapshot"])

    def report_view(self, e: Emergency) -> dict | None:
        st = self.state.get(e.id)
        if not st:
            return None
        now = self.eng.now()
        return {
            "report": self.build(e),  # crew copy: live
            "expected_reply_t": st["expected_reply_t"],
            "delay_label": self.delay_label,
            "reply_visible": bool(st.get("delivered")),
            "reply_late": not st.get("delivered") and now > st["expected_reply_t"],
            "now": now,
        }

    # ------------------------------------------------------------- console
    def _by_report(self, report_id: str | None) -> tuple[str, dict]:
        if report_id is None:
            if len(self.state) != 1:
                raise FlowError("report id required")
            return next(iter(self.state.items()))
        for eid, st in self.state.items():
            if st["snapshot"]["id"] == report_id:
                return eid, st
        raise FlowError(f"unknown report {report_id}")

    @staticmethod
    def _carried_chain(snapshot: dict) -> dict | None:
        """Ground re-checks the copy of the record that came with the report (None when it carried none)."""
        section = snapshot.get("copilot")
        if not section:
            return None
        res = record.check_section(section)
        return {"ok": res.ok, "reason": res.reason, "length": len(section["events"])}

    def _outcomes(self, eid: str) -> list[dict]:
        return [{"id": lb["id"], "t": lb["t"], "text": lb["text"]}
                for lb in self.eng.store.labels() if lb.get("kind") == "outcome" and lb.get("emergency_id") == eid]

    def console_view(self) -> dict:
        now = self.eng.now()
        out = []
        for eid, st in self.state.items():
            arrived = now >= st["arrives_t"]
            out.append({"id": st["snapshot"]["id"], "crew": st["snapshot"]["crew"], "arrived": arrived,
                        "arrives_t": st["arrives_t"], "report": st["snapshot"] if arrived else None,
                        "replied": "reply" in st,
                        "copilot_chain": self._carried_chain(st["snapshot"]) if arrived else None,
                        "outcomes": self._outcomes(eid)})
        return {"now": now, "scripted_reply": self.scripted, "reports": out}

    def console_reply(self, report_id: str | None, text: str, scripted: bool = False) -> dict:
        with self.eng._lock:
            eid, st = self._by_report(report_id)
            now = self.eng.now()
            if now < st["arrives_t"]:
                raise FlowError("the report has not reached ground yet")
            if "reply" in st:
                raise FlowError("reply already sent")
            text = self.scripted if scripted else (text or "").strip()
            if not text:
                raise FlowError("reply text is empty")
            st.update(reply=text, scripted=scripted, typed_t=now, reply_t=now + self.one_way)
            self.eng.emit("ground_reply_sent", emergency=eid, report=st["snapshot"]["id"], scripted=scripted,
                          typed_t=now, reaches_crew_t=st["reply_t"])
            return {"report": st["snapshot"]["id"], "reaches_crew_t": st["reply_t"], "scripted": scripted}

    def add_outcome(self, report_id: str | None, text: str) -> dict:
        """The flight surgeon labels the outcome after the fact: a Label linked to crew and emergency that also joins
        the record chain. Several labels may follow one report; none changes the report that was sent."""
        text = (text or "").strip()
        if not text:
            raise FlowError("outcome text is empty")
        if len(text) > MAX_OUTCOME_CHARS:
            raise FlowError(f"outcome text is over {MAX_OUTCOME_CHARS} characters")
        if lint_content.find_drug_or_dose(text, lint_content.load_deny_list()):
            raise FlowError("outcome text must not name a medication or dose")
        with self.eng._lock:
            eid, st = self._by_report(report_id)
            now = self.eng.now()
            if now < st["arrives_t"]:
                raise FlowError("the report has not reached ground yet")
            e = self.eng.emergencies[eid]
            label_id = f"lb-outcome-{eid}-{len(self._outcomes(eid)) + 1}"
            self._chain(e, "outcome_label", label=label_id, text=text)
            label = contracts.validate("label", {
                "id": label_id, "crew": e.patient, "kind": "outcome", "t": now, "report": self.build(e),
                "text": text, "emergency_id": eid})
            self.eng.store.put_label(label)
            self.eng._note(e, "outcome labelled", label=label_id)
            self.eng.emit("label_stored", label=label_id, crew=e.patient)
            return {"label": label_id, "report": st["snapshot"]["id"]}

    def due_times(self) -> list[float]:
        out = []
        for st in self.state.values():
            out.append(st["arrives_t"])
            if "reply" in st and not st.get("delivered"):
                out.append(st["reply_t"])
            if not st.get("delivered") and not st.get("late"):
                out.append(st["expected_reply_t"] + 1e-3)
        return out

    def tick(self) -> None:
        now = self.eng.now()
        for eid, st in self.state.items():
            e = self.eng.emergencies[eid]
            if "reply" in st and not st.get("delivered") and now >= st["reply_t"]:
                st["delivered"] = True
                self._chain(e, "ground_reply", report=st["snapshot"]["id"], scripted=st["scripted"],
                            reply_t=st["reply_t"], text_sha256=record.digest(st["reply"]))
                report = self.build(e)
                label = contracts.validate("label", {
                    "id": f"lb-{eid}", "crew": e.patient, "kind": "ground_reply", "t": st["reply_t"], "report": report,
                    "text": st["reply"], "emergency_id": eid, "scripted": st["scripted"]})
                self.eng.store.put_label(label)
                self.eng.store.put_report(report)
                if self.eng.habitat:  # Spec 1 service stores the report and its Label together
                    try:
                        self.eng.habitat.post_ground_reply(report)
                    except Exception as err:  # noqa: BLE001
                        self.eng.emit("habitat_post_failed", what="ground_reply", error=str(err))
                self.eng._note(e, "ground reply received", scripted=st["scripted"])
                self.eng.emit("ground_reply_delivered", emergency=eid, report=st["snapshot"]["id"])
                self.eng.emit("label_stored", label=label["id"], crew=e.patient)
            if not st.get("delivered") and not st.get("late") and now > st["expected_reply_t"]:
                st["late"] = True
                self.eng.emit("ground_reply_late", emergency=eid, report=st["snapshot"]["id"])
