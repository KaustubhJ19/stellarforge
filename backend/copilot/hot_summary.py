"""HotSummary snapshot as the emergency service receives it, and the latest-per-crew source."""
from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Any

INDICATOR_FIELDS = ("z_anchor", "z_adaptive", "cusum", "slope_1h", "slope_24h", "slope_72h", "slope_7d")
CONTEXT_FIELDS = ("sleep_debt_3d_h", "dose_mission_msv", "dose_7d_msv", "co2_above_limit_h_24h",
                  "hours_since_eva", "glucose_trend", "temperature_trend", "last_meal_logged_t", "mission_day")
REQUIRED = ("crew", "t", "label", "indicators", "context", "form_answers", "open_alerts")


@dataclass(frozen=True)
class HotSummary:
    crew: str
    t: float  # Mission clock seconds the snapshot was taken
    label: str  # honest source label, e.g. "team value (fake fixture)"
    indicators: dict[str, dict[str, float]]  # indicator -> INDICATOR_FIELDS
    context: dict[str, Any]  # CONTEXT_FIELDS; value None when unknown
    form_answers: dict[str, Any]  # post-EVA form, crew notes
    open_alerts: list[dict[str, Any]] = field(default_factory=list)  # {"kind": ..., "id": ...}

    @classmethod
    def from_dict(cls, d: dict) -> "HotSummary":
        if not isinstance(d, dict):
            raise ValueError("hot summary must be an object")
        missing = [k for k in REQUIRED if k not in d]
        if missing:
            raise ValueError(f"hot summary missing {missing}")
        for name, ind in d["indicators"].items():
            bad = [k for k in INDICATOR_FIELDS if k not in ind]
            if bad:
                raise ValueError(f"hot summary indicator {name} missing {bad}")
        bad = [k for k in CONTEXT_FIELDS if k not in d["context"]]
        if bad:
            raise ValueError(f"hot summary context missing {bad}")
        if not str(d["label"]).strip():
            raise ValueError("hot summary needs a source label")
        return cls(crew=str(d["crew"]), t=float(d["t"]), label=d["label"], indicators=d["indicators"],
                   context=d["context"], form_answers=d["form_answers"], open_alerts=list(d["open_alerts"]))

    def to_dict(self) -> dict:
        return {"crew": self.crew, "t": self.t, "label": self.label, "indicators": self.indicators,
                "context": self.context, "form_answers": self.form_answers, "open_alerts": self.open_alerts}

    def digest(self) -> str:
        """SHA-256 of the canonical JSON, for the decision record."""
        return hashlib.sha256(json.dumps(self.to_dict(), sort_keys=True).encode()).hexdigest()


@dataclass(frozen=True)
class NoHistory:
    """Explicit 'no history' answer: L1-L3 skip, only L0 runs."""
    crew: str
    reason: str


class PushedHotSummaries:
    """Latest snapshot per crew, fed by the habitat service push. Empty store = no history."""

    def __init__(self, habitat_configured: bool = False):
        self._habitat_configured = habitat_configured
        self._latest: dict[str, HotSummary] = {}
        self._lock = threading.Lock()

    def update(self, payload: dict) -> HotSummary:
        snap = HotSummary.from_dict(payload)  # raises ValueError on a bad push; the caller logs it
        with self._lock:
            old = self._latest.get(snap.crew)
            if old is None or snap.t >= old.t:  # a late, older snapshot never replaces a newer one
                self._latest[snap.crew] = snap
        return snap

    def latest(self, crew: str) -> HotSummary | NoHistory:
        with self._lock:
            snap = self._latest.get(crew)
        if snap:
            return snap
        reason = ("no snapshot received from the habitat service for this crew member"
                  if self._habitat_configured else "no habitat service connected")
        return NoHistory(crew, reason)
