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


def _cusum(c):
    """Spec 2 keeps both one-sided CuSum sums; the copilot reads one signed number (the larger side)."""
    if not isinstance(c, dict):
        return c
    up, down = c.get("up") or 0.0, c.get("down") or 0.0
    return up if up >= down else -down


def from_spec2(d: dict) -> dict:
    """Map the snapshot the habitat service pushes (backend/features.py, Spec 2) to the copilot's shape.
    Spec 2's own keys stay in `context` beside the mapped ones, so nothing is lost. Units: slopes stay per day;
    radiation stays mGy under its own key and the copilot's mSv fields are None (no mGy -> mSv factor agreed);
    the push carries no free text (privacy option A), so `form_answers` is empty."""
    indicators = {}
    for name, ind in d["indicators"].items():
        slopes = ind.get("slope_per_day") or {}
        indicators[name] = {"z_anchor": ind.get("z_anchor"), "z_adaptive": ind.get("z_adaptive"),
                            "cusum": _cusum(ind.get("cusum")), "value": ind.get("value"), "unit": ind.get("unit"),
                            **{f"slope_{w}": slopes.get(w) for w in ("1h", "24h", "72h", "7d")}}
    c = d["context"]
    sleep = c.get("sleep_debt_3d_min")
    context = {**c, "sleep_debt_3d_h": sleep / 60 if sleep is not None else None,
               "dose_mission_msv": None, "dose_7d_msv": None,
               "glucose_trend": c.get("glucose_trend_per_day"), "temperature_trend": c.get("temperature_trend_per_day"),
               "last_meal_logged_t": c.get("last_meal_t"), "mission_day": d.get("mission_day")}
    return {"crew": d["crew"], "t": d["t"], "label": d["label"], "indicators": indicators, "context": context,
            "form_answers": {}, "open_alerts": d.get("open_alerts", [])}


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
        if isinstance(payload, dict) and "form_answers" not in payload and "mission_day" in payload:
            try:
                payload = from_spec2(payload)  # the real Spec 2 push
            except (KeyError, TypeError, AttributeError) as e:
                raise ValueError(f"hot summary (Spec 2 shape) unreadable: {e!r}") from None
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
