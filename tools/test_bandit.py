"""Plan bandit vs a fixed plan against the simulated response model (Spec 2 Testing Decisions).

Same pieces the daily loop uses at runtime: backend/bandit.py LinearThompson with prior_means warm-started from
content/plans/warm-start.json, context from backend/features.py context_vector. Fixed plan: the single action
with the best average effect in the simulation (the strongest one-size-fits-all choice, chosen with hindsight).
Label: "learns per person; demonstrated on simulated response, not proven".
Report: PYTHONPATH=. python tools/test_bandit.py
"""
import json
import statistics

import pytest

from backend.bandit import LinearThompson, prior_means
from backend.daily_loop import load_plans, load_values, load_warm_start
from backend.features import context_vector
from sim_response import ACTIONS, BASE, Person

PEOPLE, EPISODES = 12, 60  # about one drift alert every 2-3 days over a 5-month transit


def simulate(policy, people=PEOPLE, episodes=EPISODES, seed=0):
    values, plans = load_values(), load_plans()
    b = values["bandit"]
    means = prior_means(ACTIONS, load_warm_start(), {a: plans[a]["addresses"] for a in ACTIONS},
                        b["driver_weight"], b["warm_start_scale"])
    curves = []
    for p in range(people):
        person = Person(f"{seed}-{p}")
        bandit = LinearThompson(ACTIONS, means, b["prior_precision"], b["noise"], seed=p)
        fixed = max(BASE, key=BASE.get)
        rewards = []
        for _ in range(episodes):
            snap, drivers = person.episode()
            x = context_vector(snap, "resting_heart_rate", values["driver_rules"])
            action = bandit.choose(x) if policy == "bandit" else fixed
            r = person.respond(action, drivers)
            if policy == "bandit":
                bandit.update(action, x, float(r))
            rewards.append(r)
        curves.append(rewards)
    return curves


def report(seeds=range(5)):
    out = {}
    for policy in ("bandit", "fixed"):
        rates, late = [], []
        for s in seeds:
            curves = simulate(policy, seed=s)
            rates.append(statistics.mean(r for c in curves for r in c))
            late.append(statistics.mean(r for c in curves for r in c[EPISODES // 2:]))
        out[policy] = {"reversal_rate": statistics.mean(rates), "second_half_rate": statistics.mean(late)}
    out["setup"] = f"{PEOPLE} simulated people x {EPISODES} drift episodes, {len(list(seeds))} seeds; simulated response, not proven"
    return out


@pytest.fixture(scope="module")
def result():
    return report()


def test_bandit_reverses_more_drifts_than_a_fixed_plan(result):
    assert result["bandit"]["reversal_rate"] > result["fixed"]["reversal_rate"] + 0.05, result


def test_bandit_improves_as_it_learns(result):
    assert result["bandit"]["second_half_rate"] >= result["bandit"]["reversal_rate"], result


if __name__ == "__main__":
    print(json.dumps(report(), indent=1))
