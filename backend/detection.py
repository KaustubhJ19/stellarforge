"""Detection for the habitat service: Spec 1 messages in, contract-valid messages out (Spec 3).

Feed it every replay or manual message the service delivers ({"t", "type", "payload"}) and every Label;
push what it returns to the windows. It never sees its own output, so feed it only incoming events.
  "alert"         payload: Alert   (drift, acute, or emergency with likely causes)
  "trigger"       payload: Trigger (kind auto; the manual button's Trigger comes in and gets the same Alert)
  "reading_state" payload: Reading with its new state (quarantined, released or event)
Service hook (data lead's file), e.g. in HabitatService.tick / post_reading / post_trigger:
  for out in self.detection.on_message(message): self._push(out)
and in post_label:  for out in self.detection.on_label(doc): self._push(out)
Cut-offs and Safety bounds come from content/profiles/detection-cut-offs.json (load_content).
"""
import json
from pathlib import Path

from backend.baseline_a import EVENT_TAG, RELEASE_TAGS, BaselineA, Thresholds, briefing, status, urgency
from backend.emergency import AutoDetect, EmergencyThresholds, emergency_alert

CONTENT = Path(__file__).resolve().parents[1] / "content" / "profiles" / "detection-cut-offs.json"

SCHEMA_VERSION = "1.0.0"  # contracts/*.schema.json


def _message(kind: str, payload: dict) -> dict:
    return {"t": payload["t"], "type": kind, "payload": {"schema_version": SCHEMA_VERSION, **payload}}


def load_content(path: Path = CONTENT) -> tuple[dict, list[dict]]:
    """({name: value} cut-offs, Safety bounds) from the content file; every entry there carries a label and source."""
    doc = json.loads(Path(path).read_text(encoding="utf-8"))
    return {c["name"]: c["value"] for c in doc["cutoffs"]}, doc["safety_bounds"]


class Detection:
    def __init__(self, crew_records: list[dict], cutoffs: dict, safety_bounds: list[dict] = ()):
        th = Thresholds(**{k: cutoffs[k] for k in Thresholds.__dataclass_fields__})
        eth = EmergencyThresholds(**{k: cutoffs[k] for k in EmergencyThresholds.__dataclass_fields__})
        self.min_sigma = cutoffs["min_sigma"]
        shift = cutoffs.get("expected_shift", {})  # "team value"; none known yet
        floor = cutoffs.get("min_anchor_sd", {})  # a 14-day Anchor spread is too tight for months of real life
        self.bounds = {b["indicator"]: b for b in safety_bounds}
        self.breached: set[tuple[str, str]] = set()
        self.baselines, self.auto = {}, {}
        for rec in crew_records:
            anchor = {k: {**a, "sd": max(a["sd"], floor.get(k, 0))} for k, a in rec["anchor"].items()}
            anchor = {k: a for k, a in anchor.items() if a["sd"] > 0}  # a zero spread cannot score
            self.baselines[rec["id"]] = BaselineA(rec["id"], anchor, th, shift)
            self.auto[rec["id"]] = AutoDetect(rec["id"], eth)

    def on_message(self, message: dict) -> list[dict]:
        p = message["payload"]
        crew = p.get("crew")
        if crew not in self.baselines:
            return []
        if message["type"] == "trigger":
            return [_message("alert", emergency_alert(p, self.baselines[crew], self.min_sigma))]
        if message["type"] != "reading":
            return []
        out = []
        trigger = self.auto[crew].process(p["indicator"], p["value"], p["t"])
        if trigger:
            out += [_message("trigger", trigger),
                    _message("alert", emergency_alert(trigger, self.baselines[crew], self.min_sigma))]
        out += self._safety(p)
        baseline = self.baselines[crew]
        if p["indicator"] in baseline.anchor:
            extra = {k: v for k, v in p.items() if k not in ("schema_version", "crew", "indicator", "value", "unit", "t", "state")}
            res = baseline.process(p["indicator"], p["value"], p["unit"], p["t"], **extra)
            out += [_message("reading_state", r) for r in res["released"]]
            out += [_message("alert", a) for a in res["alerts"]]
            if res["state"] != "released":
                out.append(_message("reading_state", {**extra, **{k: p[k] for k in ("crew", "indicator", "value", "unit", "t")},
                                                      "state": res["state"]}))
        return out

    def _safety(self, p: dict) -> list[dict]:
        """Safety bound: an absolute limit that never learns. Outside it -> one red alert; back inside -> one green alert."""
        bound, key = self.bounds.get(p["indicator"]), (p["crew"], p["indicator"])
        if bound is None or not isinstance(p["value"], (int, float)):
            return []
        inside = status("green", p["value"], bound)["status"] != "red"
        if inside != (key in self.breached):
            return []  # still inside, or still outside and already alerted
        self.breached ^= {key}
        tier = "green" if inside else "red"  # green: back inside, clears the earlier red Alert
        return [_message("alert", {"id": f"{p['crew']}-safety-{p['indicator']}-{p['t']:.0f}", "kind": "acute",
                                   "crew": p["crew"], "indicator": p["indicator"],
                                   "deviation": {"value": p["value"], "bound": {k: bound.get(k) for k in ("low", "high", "label", "source")}},
                                   "status": tier, "urgency": urgency("acute", tier), "likely_causes": [], "t": p["t"]})]

    def briefing(self, crew: str) -> list[str]:
        return briefing(self.baselines[crew])

    def on_label(self, label: dict) -> list[dict]:
        """A crew tag in label["note"]: "false alarm" / "normal" release held Readings, "confirmed event" stores them."""
        tag, crew = label.get("note"), label.get("crew")
        if crew not in self.baselines or tag not in RELEASE_TAGS | {EVENT_TAG}:
            return []
        return [_message("reading_state", r) for r in self.baselines[crew].label(tag, label["t"])]
