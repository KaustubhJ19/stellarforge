"""The daily prevention loop in the habitat service (Spec 2): detect -> explain -> act -> check -> learn -> escalate.

DailyLoop wraps Spec 3's Detection with the same hook interface the service already calls
(on_message, on_label, briefing) plus annotate (a Trigger carries the HotSummary) and hot_summary(crew).

- detect:   Detection's drift / acute Alerts, plus the joint-pattern detector (backend/joint_anomaly.py).
- explain:  a non-green drift or acute Alert opens one plan per (crew, indicator, pattern), naming likely drivers
            from the HotSummary ("likely driver: suggestion, not diagnosis").
- act:      the plan is chosen by the person's bandit (backend/bandit.py) from the action-plan library
            (content/plans/, authored like protocols: evidence pack, draft, team approval).
- check:    at the follow-up time (team value per indicator) the drift is reversed if its Alert cleared or the
            latest value is back within reversal_sigma of the person's normal.
- learn:    the bandit is updated with reward 1 (reversed) or 0.
- escalate: not reversed -> the Alert again with urgency ESCALATE_TO_GROUND ("home-side actions failed"),
            carrying the plans tried and their results (optional field escalation, add-only, pending team agreement).
"""
import json
import zlib
from itertools import count
from pathlib import Path

from backend.bandit import LEARNING_LABEL, LinearThompson, prior_means
from backend.detection import SCHEMA_VERSION, Detection, load_content
from backend.features import HotSummary, context_vector
from backend.joint_anomaly import JointAnomaly

CONTENT = Path(__file__).resolve().parents[1] / "content"
PLANS = CONTENT / "plans"
VALUES = PLANS / "daily-loop.json"
WARM_START = PLANS / "warm-start.json"
ESCALATION_PLAN = "call-ground"
PLAN_LABEL = "suggestion, not diagnosis"
DRIVER_LABEL = "likely driver: suggestion, not diagnosis"
ESCALATE = "ESCALATE_TO_GROUND"


def load_values(path=VALUES):
    """{name: value} team values for Spec 2; every entry in the file carries a label and source."""
    return {v["name"]: v["value"] for v in json.loads(Path(path).read_text(encoding="utf-8"))["values"]}


def load_plans(folder=PLANS):
    """Action plans (Protocol-shaped). A plan with a step lacking a source is refused, never shown (safety rule 2)."""
    plans = {}
    for path in sorted(p for p in Path(folder).glob("*.json") if p.name.count(".") == 1):
        doc = json.loads(path.read_text(encoding="utf-8"))
        if doc.get("kind") != "action-plan":
            continue
        for step in doc["steps"]:
            src = step.get("source") or {}
            if not (str(src.get("guideline", "")).strip() and str(src.get("section", "")).strip()):
                raise ValueError(f"{path.name}: step {step.get('id')} has no source; plan refused")
        plans[doc["id"]] = doc
    return plans


def load_warm_start(path=WARM_START):
    return json.loads(Path(path).read_text(encoding="utf-8"))["prior_bias"] if Path(path).exists() else {}


def _msg(kind, payload):
    return {"t": payload["t"], "type": kind, "payload": {"schema_version": SCHEMA_VERSION, **payload}}


class DailyLoop:
    def __init__(self, detection, crew_records, values=None, plans=None, warm_start=None, seed=0):
        self.detection = detection
        self.values = values or load_values()
        self.crew = [r["id"] for r in crew_records]
        min_window = detection.baselines[self.crew[0]].th.min_window if self.crew else 7
        self.summary = HotSummary(self.crew, detection.baselines, sleep_need_min=self.values["sleep_need_min"],
                                  co2_limit_mmhg=self.values["co2_limit_mmhg"], min_window=min_window)
        self.joint = JointAnomaly(self.crew, **self.values["joint"])
        self.plans = plans if plans is not None else load_plans()
        self.arms = [p for p in self.plans if p != ESCALATION_PLAN]
        b = self.values["bandit"]
        means = prior_means(self.arms, warm_start if warm_start is not None else load_warm_start(),
                            {a: self.plans[a].get("addresses", []) for a in self.arms}, b["driver_weight"], b["warm_start_scale"])
        self.bandits = {c: LinearThompson(self.arms, means, b["prior_precision"], b["noise"], seed=zlib.crc32(f"{seed}-{c}".encode()))
                        for c in self.crew}
        self.open = {}  # (crew, indicator, pattern) -> open plan
        self.active = {}  # (crew, indicator, pattern) -> {alert kind: latest non-green Alert}
        self.escalated = set()  # keys escalated and not yet cleared: no new plan until the Alert clears
        self.tried = {}  # (crew, indicator, pattern) -> plans tried for the current Alert
        self._ids = count(1)

    # ---- service hook -----------------------------------------------------------------
    def on_message(self, message):
        out = list(self.detection.on_message(message))
        self.summary.update(message)
        out += self.joint.on_message(message)
        new = []
        for m in out:
            if m["type"] == "alert":
                self.summary.alert(m["payload"])
                new += self._on_alert(m["payload"])
        t = message.get("t", 0)
        new += self._follow_ups(t)
        return [self._with_summary(m) for m in out + new]

    def on_label(self, label):
        return self.detection.on_label(label)

    def briefing(self, crew):
        return self.detection.briefing(crew)

    def annotate(self, message):
        return self._with_summary(message)

    def hot_summary(self, crew):
        return self.summary.snapshot(crew)

    def bandit_state(self, crew):
        b = self.bandits[crew]
        return {"updates": b.updates, "last_reward": b.last_reward, "label": LEARNING_LABEL}

    # ---- explain + act ------------------------------------------------------------------
    def _on_alert(self, alert):
        if alert["kind"] not in ("drift", "acute") or alert["crew"] not in self.bandits:
            return []
        key = (alert["crew"], alert["indicator"], alert.get("pattern"))
        kinds = self.active.setdefault(key, {})
        if alert["status"] == "green":
            kinds.pop(alert["kind"], None)
            if kinds:
                return []  # another alert kind on this indicator is still open
            self.active.pop(key, None)
            self.escalated.discard(key)
            self.tried.pop(key, None)
            if key in self.open:
                self.open[key]["cleared"] = True
            return []
        kinds[alert["kind"]] = alert
        if key in self.open or key in self.escalated or alert["urgency"] == ESCALATE:
            return []
        snap = self.summary.snapshot(alert["crew"])
        x = context_vector(snap, alert["indicator"], self.values["driver_rules"])
        action = self.bandits[alert["crew"]].choose(x)
        plan = self.plans[action]
        follow = self.values["follow_up_h"]
        hours = follow.get("joint" if alert.get("pattern") == "joint" else alert["indicator"], follow["default"])
        payload = {"id": f"plan-{alert['crew']}-{next(self._ids)}", "crew": alert["crew"], "t": alert["t"],
                   "alert_id": alert["id"], "alert_kind": alert["kind"], "indicator": alert["indicator"],
                   "pattern": alert.get("pattern"), "action": action, "title": plan["title"], "steps": plan["steps"],
                   "stub": bool(plan.get("stub")), "approval": plan.get("approval", {}),
                   "drivers": self._drivers(snap), "follow_up_due_t": alert["t"] + hours * 3600,
                   "label": PLAN_LABEL, "learning_label": LEARNING_LABEL}
        self.open[key] = {"plan": payload, "x": x, "cleared": False}
        return [_msg("plan", payload)]

    def _drivers(self, snap):
        r, c = self.values["driver_rules"], snap["context"]
        out = []
        if c["sleep_debt_3d_min"] >= r["sleep_debt_min"]:
            out.append(("sleep_debt", f"sleep debt {c['sleep_debt_3d_min']:.0f} min over 3 days"))
        if c["co2_above_limit_h_24h"] >= r["co2_above_h"]:
            out.append(("co2", f"CO2 above the limit for {c['co2_above_limit_h_24h']:.1f} h in the last 24 h (team value)"))
        if c["hours_since_eva"] is not None and c["hours_since_eva"] <= r["eva_within_h"]:
            out.append(("recent_eva", f"EVA ended {c['hours_since_eva']:.0f} h ago"))
        if c["dose_7d_mGy"] >= r["dose_7d_mGy"]:
            out.append(("dose", f"radiation dose {c['dose_7d_mGy']:.1f} mGy in 7 days (team value)"))
        return [{"name": n, "note": note, "label": DRIVER_LABEL} for n, note in out]

    # ---- check + learn + escalate ---------------------------------------------------------
    def _follow_ups(self, t):
        out = []
        for key in [k for k, o in self.open.items() if t >= o["plan"]["follow_up_due_t"]]:
            o = self.open.pop(key)
            plan, crew = o["plan"], key[0]
            reversed_ = o["cleared"] or self._back_to_normal(key, plan["alert_kind"])
            self.bandits[crew].update(plan["action"], o["x"], 1.0 if reversed_ else 0.0)
            result = "reversed" if reversed_ else "not reversed"
            tried = self.tried.setdefault(key, [])
            tried.append({"plan_id": plan["id"], "action": plan["action"], "opened_t": plan["t"],
                          "follow_up_due_t": plan["follow_up_due_t"], "result": result})
            out.append(_msg("plan_result", {"id": f"{plan['id']}-result", "plan_id": plan["id"], "crew": crew, "t": t,
                                            "indicator": plan["indicator"], "pattern": plan["pattern"],
                                            "action": plan["action"], "result": result, "learning_label": LEARNING_LABEL}))
            if reversed_:
                self.tried.pop(key, None)
                continue
            kinds = self.active.get(key) or {}
            alert = kinds.get(plan["alert_kind"]) or next(iter(kinds.values()), None)
            if alert is None:
                continue
            self.escalated.add(key)
            esc = {k: v for k, v in alert.items() if k != "schema_version"}
            esc.update(id=f"{alert['id']}-escalated", urgency=ESCALATE, t=t,
                       escalation={"reason": "home-side actions failed", "plans_tried": list(tried),
                                   "next_plan": ESCALATION_PLAN})
            out.append(_msg("alert", esc))
            self.summary.alert(esc)
        return out

    def _back_to_normal(self, key, alert_kind):
        crew, indicator, pattern = key
        if pattern == "joint":
            return self.joint.below_threshold(crew)
        ind = self.summary.snapshot(crew)["indicators"].get(indicator) or {}
        z = ind.get("z_adaptive") if alert_kind == "acute" else ind.get("z_anchor")
        return z is not None and abs(z) <= self.values["reversal_sigma"]

    def _with_summary(self, message):
        crew = (message.get("payload") or {}).get("crew")
        if message["type"] in ("alert", "trigger") and crew in self.summary.people:
            return {**message, "hot_summary": self.summary.snapshot(crew)}
        return message


def build_loop(crew_records, values=None, **kw):
    cutoffs, bounds = load_content()
    return DailyLoop(Detection(crew_records, cutoffs, bounds), crew_records, values=values, **kw)
