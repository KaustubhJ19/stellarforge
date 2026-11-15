"""Visibly fake HotSummary values for tests and the demo until Spec 2 delivers the real feed."""
from __future__ import annotations

FAKE_LABEL = "team value (fake fixture, not real crew data)"


def fake_hot_summary(crew: str = "cmdr", t: float = 0.0, **context_overrides) -> dict:
    """Day-120 crew member, two hours after an EVA, resting HR drifted up, sleep debt grown."""
    context = {"sleep_debt_3d_h": 4.5, "dose_mission_msv": 95.0, "dose_7d_msv": 4.2,
               "co2_above_limit_h_24h": 0.0, "hours_since_eva": 2.0, "glucose_trend": "falling",
               "temperature_trend": "flat", "last_meal_logged_t": None, "mission_day": 120}
    context.update(context_overrides)
    flat = {"z_anchor": 0.0, "z_adaptive": 0.0, "cusum": 0.0, "slope_1h": 0.0, "slope_24h": 0.0,
            "slope_72h": 0.0, "slope_7d": 0.0}
    return {"crew": crew, "t": t, "label": FAKE_LABEL,
            "indicators": {"heart_rate": {**flat, "z_anchor": 2.1, "z_adaptive": 1.4, "cusum": 3.0, "slope_72h": 1.5},
                           "sleep_duration": {**flat, "z_anchor": -1.8, "slope_72h": -0.4}},
            "context": context,
            "form_answers": {"post_eva": {"elbow_joint_pain": True}},
            "open_alerts": [{"id": "fake-alert-1", "kind": "drift"}]}
