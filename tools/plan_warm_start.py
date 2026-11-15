"""Warm start for the action-plan bandit from the existing what-if forecast (Spec 2; backend/forecast_b.py).

For each action, the what-if forecast is asked: "if today's answers changed like this, how much would tomorrow's
readiness change?" The mean change over PMData people-days (0-10 scale), divided by 10, becomes the action's
prior bias in content/plans/warm-start.json. The mapping from action to answer changes is a team value, and the
forecast is "estimate, not validated", so the prior is only a starting point the bandit then learns away from.

  PMDATA_DIR=data/pmdata python tools/plan_warm_start.py
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
OUT = ROOT / "content" / "plans" / "warm-start.json"

# team value: which daily answers each action is expected to move, in the forecast's own units
WHAT_IF = {
    "hydration": {"fatigue": -1},
    "sleep-timing": {"sleep_duration_h": +1, "sleep_quality": +1},
    "exercise-countermeasure": {"stress": -1, "mood": +1},
    "co2-check": {"fatigue": -1},
    "crew-check-in": {"mood": +1, "stress": -1},
}


def compute(pmdata, min_days=7, sample_every=5):
    import numpy as np
    from backend.forecast_b import FEATURES, daily_pairs, load_pmdata, train, what_if

    pairs = daily_pairs(load_pmdata(pmdata))
    people = sorted(pairs.person.unique())
    calib = people[::4]
    model = train(pairs[~pairs.person.isin(calib)], pairs[pairs.person.isin(calib)])
    gains = {a: [] for a in WHAT_IF}
    for person in people:
        own = pairs[pairs.person == person].reset_index(drop=True)
        for i in range(min_days, len(own), sample_every):
            history, today = own.iloc[:i], own.iloc[i]
            base = what_if(model, history, today, {}, min_days)["value"]
            for action, change in WHAT_IF.items():
                changed = {k: float(np.clip(today[k] + v, 1, 5)) if k != "sleep_duration_h" else float(today[k] + v)
                           for k, v in change.items() if k in FEATURES}
                gains[action].append(what_if(model, history, today, changed, min_days)["value"] - base)
    return {a: round(float(np.mean(g)) / 10.0, 4) for a, g in gains.items()}, len(people)


def main():
    pmdata = Path(os.environ.get("PMDATA_DIR", ROOT / "data" / "pmdata"))
    if not (pmdata / "p01" / "pmsys" / "wellness.csv").exists():
        sys.exit(f"PMData not found at {pmdata} (set PMDATA_DIR)")
    bias, n = compute(pmdata)
    doc = {"about": "Prior bias per action for the plan bandit (backend/bandit.py): mean change in tomorrow's readiness "
                    "(0-10, divided by 10) from the what-if forecast when today's answers move as in tools/plan_warm_start.py WHAT_IF.",
           "label": "estimate, not validated (what-if forecast); action-to-answer mapping is a team value",
           "source": f"backend/forecast_b.py what_if on PMData wellness answers ({n} people, CC BY 4.0); rerun: python tools/plan_warm_start.py",
           "what_if": WHAT_IF, "prior_bias": bias}
    OUT.write_text(json.dumps(doc, indent=1) + "\n", encoding="utf-8")
    print(json.dumps(bias))


if __name__ == "__main__":
    main()
