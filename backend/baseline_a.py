"""Baseline A: judge each crew member's Readings against their own normal (Spec 3, tickets 03, 04, 06, 07, 09).

- Anchor: fixed pre-flight mean and spread per Indicator (from CrewRecord.anchor). Slow shifts are tracked
  with a two-sided CuSum against Anchor + expected space shift ("team value") -> Drift alerts.
- Adaptive baseline: 28-day sliding window of released Readings only -> Acute alerts (z-score).
- Quarantine: while an Alert is open, Readings are held; released on a "false alarm"/"normal" Label or
  after 24 h, moved to the Event store on a confirmed Event. Held or event data never updates A.
- Constant time per Reading (running sums; window eviction is amortised O(1)).
References: Mishra 2020 https://www.nature.com/articles/s41551-020-00640-6 ;
Alavi 2022 https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/ ; CuSum: Page 1954, https://doi.org/10.2307/2333009
All cut-offs are passed in (Thresholds): they are team values kept in content/, not in code.
Works on plain values until the Spec 1 contracts exist; an adapter will map Reading/Alert JSON.
"""
import math
from collections import deque
from dataclasses import dataclass

TIERS = ("green", "amber", "red")
WINDOW_S = 28 * 86_400  # Spec 3 Baseline A: 28-day Adaptive baseline
HOLD_S = 24 * 3_600  # Spec 3 Baseline A: release held Readings after 24 h with no confirmed Event
RELEASE_TAGS = {"false alarm", "normal"}
EVENT_TAG = "confirmed event"


@dataclass(frozen=True)
class Thresholds:
    cusum_k: float  # slack per Reading, in Anchor sd
    drift_amber: float  # CuSum level for amber / red
    drift_red: float
    acute_amber: float  # |z| against the Adaptive baseline for amber / red
    acute_red: float
    min_window: int  # Readings needed before the Adaptive baseline is trusted


def worse(a: str, b: str) -> str:
    return max(a, b, key=TIERS.index)


def _tier(score: float, amber: float, red: float) -> str:
    return "red" if score >= red else "amber" if score >= amber else "green"


def urgency(kind: str | None, level: str) -> str:
    """Spec 3 'Status and urgency'. A red Drift alert stays MONITOR: the rule escalates only red Acute alerts."""
    if kind == "emergency":
        return "ACT_NOW"
    if kind == "acute" and level == "red":
        return "ESCALATE_TO_GROUND"
    return "MONITOR" if level in ("amber", "red") else "ROUTINE"


def status(level: str, value: float, bound: dict | None) -> dict:
    """The one Status rule: the worse of A's level and the Safety bound. Always carries text, not colour alone."""
    low, high = (bound.get("low"), bound.get("high")) if bound else (None, None)
    outside = (low is not None and value < low) or (high is not None and value > high)  # None: no limit that side
    result = worse(level, "red" if outside else "green")
    text = {"green": "Normal", "amber": "Watch", "red": "Alert"}[result]
    if outside:
        text += f": outside safety limit ({bound['label']})"
    return {"status": result, "text": text}


class _Window:
    """Released Readings of one Indicator in the last 28 days, with running sums."""

    def __init__(self):
        self.items, self.total, self.squares = deque(), 0.0, 0.0

    def add(self, t: float, v: float):
        self.items.append((t, v))
        self.total += v
        self.squares += v * v

    def evict(self, now: float):
        while self.items and self.items[0][0] <= now - WINDOW_S:
            _, v = self.items.popleft()
            self.total -= v
            self.squares -= v * v

    def stats(self) -> tuple[int, float, float]:
        n = len(self.items)
        if n < 2:
            return n, (self.total / n if n else math.nan), math.nan
        mean = self.total / n
        return n, mean, math.sqrt(max(self.squares - n * mean * mean, 0.0) / (n - 1))


class BaselineA:
    def __init__(self, crew: str, anchor: dict, thresholds: Thresholds, expected_shift: dict, shift_ramp_s: float = 0.0):
        """shift_ramp_s: expected_shift grows in a straight line from 0 at launch (t = 0) to full size at this time; 0 = full at once."""
        bad = [k for k, a in anchor.items() if not a["sd"] > 0]
        if bad:
            raise ValueError(f"Anchor spread must be > 0 for {bad}")
        self.crew, self.anchor, self.th, self.shift = crew, anchor, thresholds, expected_shift
        self.shift_ramp_s = shift_ramp_s
        self.windows: dict[str, _Window] = {}
        self.cusum: dict[str, tuple[float, float]] = {}  # (upward, downward)
        self.raised: dict[tuple[str, str], str] = {}  # highest tier already alerted per (indicator, kind)
        self.drift: dict[str, dict] = {}  # per Indicator: tier, run start, run sum/count, unit, last t
        self.latest_z: dict[str, float] = {}
        self.held: list[dict] = []
        self.hold_since: float | None = None
        self.event_store: list[dict] = []

    def shift_at(self, indicator: str, t: float) -> float:
        """Expected space shift at Mission time t (seconds from launch)."""
        full = self.shift.get(indicator, 0.0)
        return full * min(max(t / self.shift_ramp_s, 0.0), 1.0) if self.shift_ramp_s > 0 else full

    def adaptive_mean(self, indicator: str) -> float | None:
        w = self.windows.get(indicator)
        return w.stats()[1] if w and w.items else None

    def process(self, indicator: str, value: float, unit: str, t: float, **fields) -> dict:
        """fields: other Reading fields (source, confidence, ...) carried unchanged on held/released Readings."""
        released = self._release() if self.hold_since is not None and t - self.hold_since >= HOLD_S else []
        alerts, level = [], "green"

        cusum_next = None
        if indicator in self.anchor:  # Drift: CuSum against Anchor + expected space shift
            a = self.anchor[indicator]
            z = (value - a["mean"] - self.shift_at(indicator, t)) / a["sd"]
            up, down = self.cusum.get(indicator, (0.0, 0.0))
            cusum_next = (max(0.0, up + z - self.th.cusum_k), max(0.0, down - z - self.th.cusum_k))
            c = max(cusum_next)
            self.latest_z[indicator] = z
            tier = _tier(c, self.th.drift_amber, self.th.drift_red)
            self._track_run(indicator, c, tier, value, unit, t)
            level = worse(level, tier)
            alerts += self._maybe_alert("drift", indicator, tier, {"sigma": z, "cusum": c}, t)

        window = self.windows.setdefault(indicator, _Window())
        window.evict(t)
        n, mean, sd = window.stats()
        if n >= self.th.min_window and sd > 0:  # Acute: z against the 28-day Adaptive baseline
            za = (value - mean) / sd
            tier = _tier(abs(za), self.th.acute_amber, self.th.acute_red)
            level = worse(level, tier)
            alerts += self._maybe_alert("acute", indicator, tier, {"sigma": za, "cusum": None}, t)

        reading = fields | {"crew": self.crew, "indicator": indicator, "value": value, "unit": unit, "t": t}
        if any(al["status"] != "green" for al in alerts) and self.hold_since is None:  # a cleared Alert holds nothing
            self.hold_since = t
        if self.hold_since is not None:  # Quarantine: held data never updates A
            reading["state"] = "quarantined"
            self.held.append(reading)
        else:
            reading["state"] = "released"
            window.add(t, value)
            if cusum_next is not None:
                self.cusum[indicator] = cusum_next
        return {"state": reading["state"], "level": level, "alerts": alerts, "released": released}

    def label(self, tag: str, t: float) -> list[dict]:
        """Hook for Spec 4: a Label releases held Readings or moves them to the Event store."""
        if tag in RELEASE_TAGS:
            return self._release()
        if tag == EVENT_TAG:
            moved = [r | {"state": "event"} for r in self.held]
            self.event_store += moved
            self.held, self.hold_since = [], None
            return moved
        raise ValueError(f"unknown label {tag!r}")

    def _release(self) -> list[dict]:
        out = []
        for r in self.held:
            self.windows.setdefault(r["indicator"], _Window()).add(r["t"], r["value"])
            out.append(r | {"state": "released"})
        self.held, self.hold_since = [], None
        return out

    def _maybe_alert(self, kind: str, indicator: str, tier: str, deviation: dict, t: float) -> list[dict]:
        key = (indicator, kind)
        if tier == "green":
            if self.raised.pop(key, None) is None:
                return []  # nothing to clear
        elif TIERS.index(tier) <= TIERS.index(self.raised.get(key, "green")):
            return []  # already alerted at this tier
        else:
            self.raised[key] = tier
        zs = list(self.latest_z.values())
        deviation |= {"combined": math.sqrt(sum(z * z for z in zs) / len(zs)) if zs else None}
        return [{"id": f"{self.crew}-{kind}-{indicator}-{t:.0f}", "kind": kind, "crew": self.crew,
                 "indicator": indicator, "deviation": deviation, "status": tier, "urgency": urgency(kind, tier),
                 "likely_causes": [], "t": t}]

    def _track_run(self, indicator: str, c: float, tier: str, value: float, unit: str, t: float):
        run = self.drift.setdefault(indicator, {"start": None, "sum": 0.0, "n": 0})
        if c == 0:
            run.update(start=None, sum=0.0, n=0)
        else:
            if run["start"] is None:
                run["start"] = t
            run["sum"] += value
            run["n"] += 1
        run.update(tier=tier, unit=unit, last=t)


def _drift_note(a: BaselineA, indicator: str) -> str | None:
    """'resting hr +6 bpm over 9 days' from the current CuSum run, or None if there is no run."""
    run = a.drift.get(indicator)
    if not run or not run["n"]:
        return None
    normal = a.anchor[indicator]["mean"] + a.shift_at(indicator, run["last"])
    days = round((run["last"] - run["start"]) / 86_400) + 1
    return f"{indicator.replace('_', ' ')} {run['sum'] / run['n'] - normal:+.0f} {run['unit']} over {days} days"


def briefing(a: BaselineA) -> list[str]:
    """Morning briefing in words from A's numbers, e.g. 'resting hr +6 bpm over 9 days'."""
    lines = [_drift_note(a, ind) for ind, run in a.drift.items() if run["tier"] != "green"]
    return [line for line in lines if line] or ["All indicators within your normal."]


LIKELY_CAUSE_LABEL = "suggestion, not diagnosis"  # Spec 3 "Likely-cause ranking"


def likely_causes(a: BaselineA, min_sigma: float, top: int = 3) -> list[dict]:
    """Up to 3 Indicators furthest from the person's normal (Anchor), as Alert.likely_causes.

    Rule-based from A's numbers; it never chooses protocol steps (the confirmed Trigger does).
    The contract has no label field, so the label is part of each note.
    """
    ranked = sorted((i for i, z in a.latest_z.items() if abs(z) >= min_sigma), key=lambda i: -abs(a.latest_z[i]))
    causes = []
    for ind in ranked[:top]:
        z = a.latest_z[ind]
        note = _drift_note(a, ind) or \
            f"{ind.replace('_', ' ')} {z * a.anchor[ind]['sd']:+.0f} {a.drift[ind]['unit']} from your normal"
        causes.append({"indicator": ind, "direction": "up" if z > 0 else "down", "note": f"{note} ({LIKELY_CAUSE_LABEL})"})
    return causes
