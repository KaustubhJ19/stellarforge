"""Emergency Trigger: auto-detect from the live stream, or the manual button (Spec 3 ticket 05).

Auto rule (Spec 3 "Auto-detect rule"): raise a Trigger when either
- the rhythm state is VT, VF, PEA or asystole, or
- heart rate is extreme (at or above hr_high, or below hr_low) for sustain_s seconds AND systolic BP is below sbp_low.
Works on rhythm state, HR and BP from the Pulse replay, not on an ECG waveform. Chest pain is crew-reported.
The cut-offs are "Earth reference / team value" items kept in content/, so they are passed in.
Indicator names ("rhythm", "heart_rate", "systolic_bp") are placeholders until the Spec 1 contracts exist.
"""
from dataclasses import dataclass

from backend.baseline_a import BaselineA, likely_causes, urgency

ARREST_RHYTHMS = {"VT", "VF", "PEA", "asystole"}  # Spec 3 auto-detect rule


@dataclass(frozen=True)
class EmergencyThresholds:
    hr_high: float  # bpm
    hr_low: float  # bpm
    sbp_low: float  # mmHg, systolic
    sustain_s: float  # seconds the heart rate must stay extreme


def _trigger(kind: str, crew: str, t: float, reason: str) -> dict:
    return {"kind": kind, "crew": crew, "t": t, "reason": reason, "confirmed": None}


def manual_trigger(crew: str, t: float, reason: str) -> dict:
    """The Emergency / Help a crewmate button: same shape as an auto Trigger, so the flow after is identical."""
    return _trigger("manual", crew, t, reason)


class AutoDetect:
    """Watches one crew member's stream; raises at most one auto Trigger until reset()."""

    def __init__(self, crew: str, thresholds: EmergencyThresholds):
        self.crew, self.th = crew, thresholds
        self.extreme_since: float | None = None
        self.sbp: float | None = None
        self.fired = False

    def reset(self):
        self.fired, self.extreme_since = False, None

    def process(self, indicator: str, value, t: float) -> dict | None:
        if self.fired:
            return None
        reason = None
        if indicator == "rhythm" and value in ARREST_RHYTHMS:
            reason = f"rhythm {value}"
        elif indicator == "systolic_bp":
            self.sbp = value
        elif indicator == "heart_rate":
            extreme = value >= self.th.hr_high or value < self.th.hr_low  # AHA 2025: >=150/min, <50/min
            self.extreme_since = (t if self.extreme_since is None else self.extreme_since) if extreme else None
        if (reason is None and self.extreme_since is not None and t - self.extreme_since >= self.th.sustain_s
                and self.sbp is not None and self.sbp < self.th.sbp_low):
            reason = f"heart rate extreme for {t - self.extreme_since:.0f} s with systolic BP {self.sbp:.0f} mmHg"
        if reason is None:
            return None
        self.fired = True
        return _trigger("auto", self.crew, t, reason)


def emergency_alert(trigger: dict, baseline: BaselineA, min_sigma: float) -> dict:
    """The emergency Alert for either Trigger kind: red, ACT_NOW, with 2-3 likely causes from Baseline A."""
    return {"id": f"{trigger['crew']}-emergency-{trigger['t']:.0f}", "kind": "emergency", "crew": trigger["crew"],
            "indicator": None, "deviation": None, "status": "red", "urgency": urgency("emergency", "red"),
            "likely_causes": likely_causes(baseline, min_sigma), "t": trigger["t"]}
