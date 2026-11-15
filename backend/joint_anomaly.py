"""Joint-pattern anomaly (Spec 2): several small shifts at once, scored together per person.

Residual forecaster per indicator: the forecast is the person's own normal learned over the first train_days
(mean of the daily values: the last Reading of each day); the residual is the smoothed daily value (EWMA across
days) minus it. Once a day the residual vector gets a Mahalanobis score (Mahalanobis 1936) against the covariance
of the training days, shrunk toward its diagonal (Ledoit & Wolf 2004) and scaled by smoothing / (2 - smoothing),
the variance of an EWMA of independent days. The limit is Hotelling's T-squared upper control limit for individual
observations with the mean and covariance estimated from n training days (NIST/SEMATECH 6.5.4.3):
k (n + 1)(n - 1) / (n (n - k)) * F(1 - false_alarm_p; k, n - k). Correlated indicators that move together as usual
(sleep and sleep score) add little; independent ones moving together add a lot.

Raises kind "drift" with pattern "joint" and the indicators involved (each indicator's share of the score at or
above min_contribution) after persist_days days in a row above the threshold, with at least min_indicators
involved; a green Alert after persist_days below. Constant time per Reading: the daily score costs O(k^2) for
a fixed number k of indicators. Team values: content/plans/daily-loop.json "joint".
"""
import math

import numpy as np
from scipy.stats import f as f_dist

from backend.baseline_a import urgency
from backend.detection import SCHEMA_VERSION

DAY = 86_400
CAUSE_LABEL = "suggestion, not diagnosis"


def _num(v):
    return isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)


class _Person:
    def __init__(self):
        self.today, self.carry, self.smoothed, self.day, self.first_day = {}, {}, None, None, None
        self.train_rows = []  # dicts of daily values (last Reading of the day, carried forward), one per training day
        self.indicators, self.mean, self.sd, self.precision, self.threshold = None, None, None, None, None
        self.above = self.below = 0
        self.raised, self.last_score = False, None


class JointAnomaly:
    def __init__(self, crew_ids, train_days=21, smoothing=0.3, false_alarm_p=0.001, persist_days=2,
                 min_indicators=2, shrinkage=0.2, min_contribution=0.15, min_coverage=0.7):
        self.people = {c: _Person() for c in crew_ids}
        self.train_days, self.alpha, self.p = train_days, smoothing, false_alarm_p
        self.persist, self.min_ind, self.shrink, self.min_share = persist_days, min_indicators, shrinkage, min_contribution
        self.min_coverage = min_coverage

    def on_message(self, message):
        p = message.get("payload") or {}
        person = self.people.get(p.get("crew"))
        if message.get("type") != "reading" or person is None or not _num(p.get("value")):
            return []
        day = int(p["t"] // DAY)
        out = []
        if person.day is not None and day > person.day:
            out = self._close_day(p["crew"], person, p["t"])
        if person.first_day is None:
            person.first_day = day
        person.day = day
        person.today[p["indicator"]] = p["value"]
        return out

    def below_threshold(self, crew):
        person = self.people[crew]
        return person.last_score is not None and person.last_score <= person.threshold

    # ---- daily score ---------------------------------------------------------------------
    def _close_day(self, crew, person, t):
        person.carry.update(person.today)
        person.today = {}
        if person.precision is None:
            if person.day - person.first_day < self.train_days:
                person.train_rows.append(dict(person.carry))
                return []
            self._fit(person)
            if person.precision is None:
                return []
        if any(i not in person.carry for i in person.indicators):
            return []
        x = np.array([person.carry[i] for i in person.indicators], float)
        person.smoothed = x if person.smoothed is None else self.alpha * x + (1 - self.alpha) * person.smoothed
        z = person.smoothed - person.mean
        pz = person.precision @ z
        score = float(z @ pz)
        person.last_score = score
        share = z * pz / score if score > 0 else np.zeros_like(z)
        involved = [person.indicators[i] for i in np.argsort(-share) if share[i] >= self.min_share]
        if score > person.threshold:
            person.above, person.below = person.above + 1, 0
        else:
            person.above, person.below = 0, person.below + 1
        if not person.raised and person.above >= self.persist and len(involved) >= self.min_ind:
            person.raised = True
            tier = "red" if score >= 2 * person.threshold else "amber"
            return [self._alert(crew, person, t, tier, score, z, involved)]
        if person.raised and person.below >= self.persist:
            person.raised = False
            return [self._alert(crew, person, t, "green", score, z, involved)]
        return []

    def _fit(self, person):
        rows = person.train_rows
        if len(rows) < 3:
            return
        seen = {}
        for r in rows:
            for k in r:
                seen[k] = seen.get(k, 0) + 1
        inds = sorted(k for k, n in seen.items() if n >= self.min_coverage * len(rows))
        X = np.array([[r[k] for k in inds] for r in rows if all(k in r for k in inds)], float)
        if len(X) < 3:
            return
        sd = X.std(axis=0, ddof=1)
        keep = sd > 1e-9
        inds, X, sd = [k for k, ok in zip(inds, keep) if ok], X[:, keep], sd[keep]
        if len(inds) < self.min_ind:
            return
        n, k = len(X), len(inds)
        if n <= k + 1:
            return
        cov = np.cov(X, rowvar=False)
        cov = (1 - self.shrink) * cov + self.shrink * np.diag(np.diag(cov))
        smooth = self.alpha / (2 - self.alpha)  # variance of an EWMA of independent days
        person.indicators, person.mean, person.sd = inds, X.mean(axis=0), sd * math.sqrt(smooth)
        person.precision = np.linalg.inv(smooth * cov)
        person.threshold = float(k * (n + 1) * (n - 1) / (n * (n - k)) * f_dist.ppf(1 - self.p, k, n - k))

    def _alert(self, crew, person, t, tier, score, z, involved):
        zs = {k: float(z[i] / person.sd[i]) for i, k in enumerate(person.indicators)}
        causes = []
        for k in involved[:3]:
            others = [o.replace("_", " ") for o in involved if o != k]
            causes.append({"indicator": k, "direction": "up" if zs[k] > 0 else "down",
                           "note": f"{k.replace('_', ' ')} {zs[k]:+.1f} sd, together with {', '.join(others)} "
                                   f"(joint pattern; {CAUSE_LABEL})"})
        return {"t": t, "type": "alert", "payload": {
            "schema_version": SCHEMA_VERSION, "id": f"{crew}-drift-joint-{t:.0f}", "kind": "drift", "crew": crew,
            "indicator": involved[0] if involved else person.indicators[0],
            "deviation": {"mahalanobis_sq": score, "threshold": person.threshold, "sigma_by_indicator": zs},
            "status": tier, "urgency": urgency("drift", tier), "likely_causes": causes if tier != "green" else [],
            "t": t, "pattern": "joint", "indicators": involved}}
