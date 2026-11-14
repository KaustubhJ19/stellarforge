"""Detection for the habitat service: Spec 1 messages in, contract-valid messages out (Spec 3).

Feed it every replay or manual message the service delivers ({"t", "type", "payload"}) and every Label;
push what it returns to the windows. It never sees its own output, so feed it only incoming events.
  "alert"         payload: Alert   (drift, acute, or emergency with likely causes)
  "trigger"       payload: Trigger (kind auto; the manual button's Trigger comes in and gets the same Alert)
  "reading_state" payload: Reading with its new state (quarantined, released or event)
Service hook (data lead's file), e.g. in HabitatService.tick / post_reading / post_trigger:
  for out in self.detection.on_message(message): self._push(out)
and in post_label:  for out in self.detection.on_label(doc): self._push(out)
Cut-offs come from content/ as a {name: value} dict (names in docs/cut-offs-needed.md).
"""
from backend.baseline_a import EVENT_TAG, RELEASE_TAGS, BaselineA, Thresholds
from backend.emergency import AutoDetect, EmergencyThresholds, emergency_alert

SCHEMA_VERSION = "1.0.0"  # contracts/*.schema.json


def _message(kind: str, payload: dict) -> dict:
    return {"t": payload["t"], "type": kind, "payload": {"schema_version": SCHEMA_VERSION, **payload}}


class Detection:
    def __init__(self, crew_records: list[dict], cutoffs: dict):
        th = Thresholds(**{k: cutoffs[k] for k in Thresholds.__dataclass_fields__})
        eth = EmergencyThresholds(**{k: cutoffs[k] for k in EmergencyThresholds.__dataclass_fields__})
        self.min_sigma = cutoffs["min_sigma"]
        shift = cutoffs.get("expected_shift", {})  # "team value"; none known yet
        self.baselines, self.auto = {}, {}
        for rec in crew_records:
            anchor = {k: a for k, a in rec["anchor"].items() if a["sd"] > 0}  # a zero spread cannot score
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

    def on_label(self, label: dict) -> list[dict]:
        """A crew tag in label["note"]: "false alarm" / "normal" release held Readings, "confirmed event" stores them."""
        tag, crew = label.get("note"), label.get("crew")
        if crew not in self.baselines or tag not in RELEASE_TAGS | {EVENT_TAG}:
            return []
        return [_message("reading_state", r) for r in self.baselines[crew].label(tag, label["t"])]
