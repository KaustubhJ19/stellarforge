"""HotSummary: everything a later model needs about one crew member, kept up to date per message (Spec 2).

One module for runtime (backend/daily_loop.py in the habitat service) and training (Spec 3), so features
cannot drift apart. Constant time per message: running sums over sliding windows, evicted amortised O(1),
in the same style as Baseline A (backend/baseline_a.py), whose Anchor z, Adaptive baseline and CuSum it reads.

Per indicator: latest value, z vs Anchor, z vs Adaptive baseline, CuSum state, least-squares slopes (per day)
over the last 1 h, 24 h, 72 h and 7 d. Context: 3-day sleep debt, mission and 7-day dose, hours with CO2 above
the limit in the last 24 h, hours since last EVA, glucose and temperature trend, last meal / note / post-EVA
form, mission day. Open alerts. Exposure is derived from cabin readings plus the location timeline: "team value".
"""
import math
from collections import deque

DAY, HOUR = 86_400.0, 3_600.0
SLOPE_WINDOWS = {"1h": HOUR, "24h": DAY, "72h": 3 * DAY, "7d": 7 * DAY}
TREND = "72h"  # glucose and temperature trends: daily readings need more than one point in the window
DOSE_RATE = "radiation_dose_total"  # cabin Reading, mGy/day (tools/cabin_dose_replay.py)
CO2_1H = "cabin_pco2_1h"  # cabin Reading, mmHg one-hour average (tools/cabin_dose_replay.py)
DEFAULT_CABIN = "habitat"
EXPOSURE_LABEL = "team value"
LABEL = "estimate from your own data; team values"


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class _Slope:
    """Least-squares slope of value over time in a sliding window, from running sums (times relative to an origin).

    shortcut: every reading in the window is kept (the 7 d window too). Fine for daily wearable values and the
    40-minute 1 Hz emergency stream; a 1 Hz sensor running for days would need downsampling first.
    """

    def __init__(self, span):
        self.span, self.items = span, deque()
        self.n = self.st = self.sv = self.stt = self.stv = 0.0
        self.origin = None

    def add(self, t, v):
        if self.origin is None:
            self.origin = t
        x = (t - self.origin) / DAY
        self.items.append((t, x, v))
        self.n += 1
        self.st += x
        self.sv += v
        self.stt += x * x
        self.stv += x * v
        self.evict(t)

    def evict(self, now):
        while self.items and self.items[0][0] <= now - self.span:
            _, x, v = self.items.popleft()
            self.n -= 1
            self.st -= x
            self.sv -= v
            self.stt -= x * x
            self.stv -= x * v
        if not self.items:  # re-anchor so the sums stay small and exact
            self.n = self.st = self.sv = self.stt = self.stv = 0.0
            self.origin = None

    def slope(self):
        if self.n < 2:
            return None
        den = self.n * self.stt - self.st * self.st
        if den <= 1e-12:
            return None
        return (self.n * self.stv - self.st * self.sv) / den


class _WindowSum:
    """Sum of (t, amount) items in the last span seconds."""

    def __init__(self, span):
        self.span, self.items, self.total = span, deque(), 0.0

    def add(self, t, amount):
        if amount:
            self.items.append((t, amount))
            self.total += amount
        self.value(t)  # evict as we go, so the window never holds more than span seconds of items

    def value(self, now):
        while self.items and self.items[0][0] <= now - self.span:
            self.total -= self.items.popleft()[1]
        return max(self.total, 0.0) if self.items else 0.0


class _Person:
    def __init__(self, crew):
        self.crew = crew
        self.latest = {}  # indicator -> (value, unit, t)
        self.slopes = {}  # indicator -> {window: _Slope}
        self.sleep_debt = _WindowSum(3 * DAY)
        self.cabin, self.accrued_to = DEFAULT_CABIN, None
        self.dose_total, self.dose_7d = 0.0, _WindowSum(7 * DAY)
        self.co2_above = _WindowSum(DAY)
        self.forms = {}  # form kind -> latest form
        self.eva_end_t = None
        self.open_alerts = {}  # (indicator, kind, pattern) -> {id, kind, indicator, status, urgency, t, pattern}


class HotSummary:
    """Per-crew running features. Feed every incoming message and every Alert it produced; read snapshot(crew)."""

    def __init__(self, crew_ids, baselines=None, sleep_need_min=420.0, co2_limit_mmhg=3.0, min_window=7):
        self.people = {c: _Person(c) for c in crew_ids}
        self.baselines = baselines or {}  # crew -> BaselineA (Anchor z, Adaptive baseline, CuSum)
        self.sleep_need, self.co2_limit, self.min_window = sleep_need_min, co2_limit_mmhg, min_window
        self.cabins = {}  # cabin id -> {"rate": mGy/day, "co2_above": bool}
        self.now = 0.0

    # ---- input --------------------------------------------------------------------------
    def update(self, message):
        p, kind = message.get("payload") or {}, message.get("type")
        t = p.get("t", message.get("t"))
        if _num(t):
            self.now = max(self.now, t)
        crew = p.get("crew")
        if kind == "reading":
            if crew in self.people:
                self._reading(self.people[crew], p)
            else:
                self._cabin(crew, p)
        elif kind == "form" and crew in self.people:
            person = self.people[crew]
            person.forms[p["form"]] = p
            if p["form"] == "post_eva":
                end = p["answers"].get("eva_end_t", p["t"])
                person.eva_end_t = end if _num(end) else p["t"]
        elif kind == "location" and crew in self.people:
            person = self.people[crew]
            self._accrue(person, p["t"])
            person.cabin = p["cabin"]

    def alert(self, alert):
        """Track open alerts: a non-green Alert opens (or raises) one, a green one clears it."""
        person = self.people.get(alert.get("crew"))
        if person is None:
            return
        key = (alert["indicator"], alert["kind"], alert.get("pattern"))
        if alert["status"] == "green":
            person.open_alerts.pop(key, None)
        else:
            person.open_alerts[key] = {k: alert.get(k) for k in ("id", "kind", "indicator", "status", "urgency", "t", "pattern")}

    def _reading(self, person, p):
        ind, v, t = p["indicator"], p["value"], p["t"]
        person.latest[ind] = (v, p.get("unit"), t)
        if not _num(v):
            return
        windows = person.slopes.setdefault(ind, {w: _Slope(s) for w, s in SLOPE_WINDOWS.items()})
        for s in windows.values():
            s.add(t, v)
        if ind == "sleep_duration":
            person.sleep_debt.add(t, max(0.0, self.sleep_need - v))

    def _cabin(self, cabin, p):
        ind, v, t = p["indicator"], p["value"], p["t"]
        if ind not in (DOSE_RATE, CO2_1H) or not _num(v):
            return
        for person in self.people.values():  # O(crew): a fixed, small number
            if person.cabin == cabin:
                self._accrue(person, t)
        state = self.cabins.setdefault(cabin, {"rate": 0.0, "co2_above": False})
        if ind == DOSE_RATE:
            state["rate"] = v
        else:
            state["co2_above"] = v > self.co2_limit

    def _accrue(self, person, t):
        """Add exposure from the person's cabin since the last accrual (piecewise-constant cabin values)."""
        if person.accrued_to is not None and t > person.accrued_to:
            dt = t - person.accrued_to
            state = self.cabins.get(person.cabin)
            if state:
                dose = state["rate"] * dt / DAY
                person.dose_total += dose
                person.dose_7d.add(t, dose)
                if state["co2_above"]:
                    person.co2_above.add(t, dt / HOUR)
        if person.accrued_to is None or t > person.accrued_to:
            person.accrued_to = t

    # ---- output -------------------------------------------------------------------------
    def snapshot(self, crew):
        person = self.people[crew]
        now = self.now
        self._accrue(person, now)
        baseline = self.baselines.get(crew)
        indicators = {}
        for ind, (v, unit, t) in person.latest.items():
            slopes = {}
            for w, s in person.slopes.get(ind, {}).items():
                s.evict(now)
                slopes[w] = s.slope()
            indicators[ind] = {"value": v, "unit": unit, "t": t, **self._baseline(baseline, ind, v),
                               "slope_per_day": slopes or {w: None for w in SLOPE_WINDOWS}}
        trend = lambda ind: indicators.get(ind, {}).get("slope_per_day", {}).get(TREND)
        meal, note, eva = (person.forms.get(k) for k in ("meal", "note", "post_eva"))
        context = {
            "sleep_debt_3d_min": person.sleep_debt.value(now),
            "dose_mission_mGy": person.dose_total,
            "dose_7d_mGy": person.dose_7d.value(now),
            "co2_above_limit_h_24h": person.co2_above.value(now),
            "cabin": person.cabin,
            "hours_since_eva": (now - person.eva_end_t) / HOUR if person.eva_end_t is not None else None,
            "glucose_trend_per_day": trend("glucose"),
            "temperature_trend_per_day": trend("body_temperature"),
            "last_meal": meal, "last_note": note, "last_post_eva": eva,
            "last_meal_t": meal["t"] if meal else None,
        }
        return {"crew": crew, "t": now, "mission_day": int(now // DAY) + 1, "indicators": indicators,
                "context": context, "open_alerts": list(person.open_alerts.values()),
                "exposure_label": EXPOSURE_LABEL, "label": LABEL}

    def _baseline(self, baseline, ind, v):
        out = {"z_anchor": None, "z_adaptive": None, "cusum": None}
        if baseline is None or not _num(v):
            return out
        if ind in baseline.latest_z:
            out["z_anchor"] = baseline.latest_z[ind]
        if ind in baseline.cusum:
            up, down = baseline.cusum[ind]
            out["cusum"] = {"up": up, "down": down}
        w = baseline.windows.get(ind)
        if w is not None:
            n, mean, sd = w.stats()
            if n >= self.min_window and sd > 0:
                out["z_adaptive"] = (v - mean) / sd
        return out


def context_vector(snapshot, indicator, rules):
    """Fixed-length numeric context for learning (bandit, Spec 3 training): same function at runtime and offline.
    rules: driver_rules from content/plans/daily-loop.json."""
    ctx = snapshot["context"]
    z = (snapshot["indicators"].get(indicator) or {}).get("z_anchor")
    eva = ctx["hours_since_eva"]
    return [
        1.0,
        min(ctx["sleep_debt_3d_min"] / rules["sleep_debt_min"], 3.0) / 3.0,
        min(ctx["co2_above_limit_h_24h"] / max(rules["co2_above_h"], 1e-9), 3.0) / 3.0,
        1.0 if eva is not None and eva <= rules["eva_within_h"] else 0.0,
        min(ctx["dose_7d_mGy"] / rules["dose_7d_mGy"], 3.0) / 3.0,
        min(abs(z), 6.0) / 6.0 if _num(z) else 0.0,
    ]


CONTEXT_FEATURES = ["bias", "sleep_debt", "co2_above", "recent_eva", "dose_7d", "drift_size"]
