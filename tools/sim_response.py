"""Simulated response model for the plan bandit (Spec 2): action -> drift change with noise. Not real crew.

Each simulated person has a hidden effect per action: a shared base effect, a bonus when the action addresses
the episode's driver (sleep debt -> sleep timing, CO2 -> CO2 check, recent EVA -> hydration), and a personal
offset (some actions simply work better for some people). Drift change = effect + Gaussian noise, in sd of the
drift; the drift is reversed when the change reaches 1 sd. All numbers are made up for the demonstration:
label "simulated response, not proven".
"""
import random

ACTIONS = ["hydration", "sleep-timing", "exercise-countermeasure", "co2-check", "crew-check-in"]
DRIVER_OF = {"sleep-timing": "sleep_debt", "co2-check": "co2", "hydration": "recent_eva"}
BASE = {"hydration": 0.6, "sleep-timing": 0.7, "exercise-countermeasure": 0.6, "co2-check": 0.4, "crew-check-in": 0.5}
MATCH_BONUS, PERSONAL_SD, NOISE_SD, REVERSAL = 0.9, 0.5, 0.5, 1.0
LABEL = "simulated response, not proven"


class Person:
    def __init__(self, seed):
        self.rng = random.Random(seed)
        self.offset = {a: self.rng.gauss(0, PERSONAL_SD) for a in ACTIONS}

    def episode(self):
        """A drift episode: which drivers are present and how big the drift is; returned as a HotSummary-like snapshot."""
        drivers = {d for d in ("sleep_debt", "co2", "recent_eva") if self.rng.random() < 0.3}
        z = self.rng.uniform(1.5, 4.0)
        snap = {"context": {"sleep_debt_3d_min": 300.0 if "sleep_debt" in drivers else 30.0,
                            "co2_above_limit_h_24h": 4.0 if "co2" in drivers else 0.0,
                            "hours_since_eva": 10.0 if "recent_eva" in drivers else None,
                            "dose_7d_mGy": 3.5},
                "indicators": {"resting_heart_rate": {"z_anchor": z}}}
        return snap, drivers

    def respond(self, action, drivers):
        effect = BASE[action] + self.offset[action] + (MATCH_BONUS if DRIVER_OF.get(action) in drivers else 0.0)
        return effect + self.rng.gauss(0, NOISE_SD) >= REVERSAL
