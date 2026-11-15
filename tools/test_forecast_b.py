"""Ticket 11 (P1): Forecast B, tomorrow's Readiness with a range and an explanation.

What goes in: a person's daily wellness answers. What comes out: tomorrow's Readiness (0-10),
a conformal range, a label, and the drivers (SHAP). Held-out people are never used to train.
Run the held-out report from the repo root: PYTHONPATH=. python tools/test_forecast_b.py
"""
import os
from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from backend.forecast_b import FEATURES, daily_pairs, evaluate_held_out, forecast, load_pmdata, train, what_if

PMDATA = Path(os.environ.get("PMDATA_DIR", Path.home() / "Vedant/Claude/Nasa/datasets/pmdata/extracted"))
# Test values only; the real cut-offs are team values kept in content/.
MIN_DAYS, REMEASURE_WIDTH = 7, 6.0


def fake_wellness(people: int = 8, days: int = 60, seed: int = 0) -> pd.DataFrame:
    """Daily answers where tomorrow's readiness follows today's sleep quality and fatigue."""
    rng = np.random.default_rng(seed)
    n = people * days
    df = pd.DataFrame({
        "person": np.repeat([f"p{p:02d}" for p in range(people)], days),
        "date": np.tile(pd.date_range("2020-01-01", periods=days), people),
        "fatigue": rng.integers(1, 6, n), "mood": rng.integers(2, 5, n),
        "sleep_duration_h": rng.normal(7, 1, n), "sleep_quality": rng.integers(1, 6, n),
        "soreness": rng.integers(1, 6, n), "stress": rng.integers(1, 6, n),
    })
    prev = df.groupby("person")[["sleep_quality", "fatigue"]].shift(1)
    own_normal = np.repeat(rng.normal(0, 1, people), days)  # each person has their own normal
    df["readiness"] = (5 + (prev["sleep_quality"] - 3) - 0.8 * (prev["fatigue"] - 3) + own_normal
                       + rng.normal(0, 0.5, n)).fillna(5).clip(0, 10).round()
    return df


@pytest.fixture(scope="module")
def model():
    pairs = daily_pairs(fake_wellness())
    return train(pairs[pairs.person < "p05"], pairs[pairs.person >= "p05"])


@pytest.fixture(scope="module")
def newcomer():
    return daily_pairs(fake_wellness(people=1, seed=9).assign(person="p99"))


def run(model, newcomer, days, **kw):
    kw = {"min_days": MIN_DAYS, "remeasure_width": REMEASURE_WIDTH} | kw
    return forecast(model, newcomer.iloc[:days], newcomer.iloc[days][FEATURES], **kw)


def test_forecast_gives_tomorrow_readiness_inside_a_range(model, newcomer):
    out = run(model, newcomer, 30)
    assert 0 <= out["low"] <= out["value"] <= out["high"] <= 10
    assert out["label"] is None


def test_new_person_gets_a_wide_range_learning_your_pattern(model, newcomer):
    out = run(model, newcomer, 3)
    assert out["label"] == "learning your pattern"
    assert (out["low"], out["high"]) == (0.0, 10.0)


def test_wide_range_says_re_measure(model, newcomer):
    assert run(model, newcomer, 30, remeasure_width=0.1)["label"] == "re-measure"


def test_drivers_explain_the_population_forecast(model, newcomer):
    out = run(model, newcomer, 30)
    assert set(out["drivers"]) == set(FEATURES)
    # SHAP values add up to the population forecast; the personal correction is reported apart.
    assert out["base"] + sum(out["drivers"].values()) == pytest.approx(out["population"], abs=1e-6)
    assert max(out["drivers"], key=lambda k: abs(out["drivers"][k])) in ("sleep_quality", "fatigue")


def test_personal_correction_learns_a_persons_own_normal(model, newcomer):
    shifted = newcomer.assign(target=newcomer.target + 2)  # this person always feels 2 points readier
    assert run(model, shifted, 30)["personal_correction"] > 1.0


def test_what_if_is_labelled_estimate_not_validated(model, newcomer):
    out = what_if(model, newcomer.iloc[:30], newcomer.iloc[30][FEATURES], {"sleep_quality": 5}, MIN_DAYS)
    assert out["label"] == "estimate, not validated"
    assert 0 <= out["value"] <= 10
    with pytest.raises(ValueError):
        what_if(model, newcomer.iloc[:30], newcomer.iloc[30][FEATURES], {"sleep_qualty": 5}, MIN_DAYS)


def test_pairs_only_join_consecutive_days():
    pairs = daily_pairs(fake_wellness(people=1, days=5).drop(index=2))  # a missed day
    assert len(pairs) == 2  # day 0->1 and 3->4; 1->3 is not "tomorrow"


@pytest.mark.skipif(not (PMDATA / "p01/pmsys/wellness.csv").exists(), reason="PMData not downloaded (set PMDATA_DIR)")
def test_held_out_people_interval_coverage_near_90_percent():
    report = evaluate_held_out(load_pmdata(PMDATA), MIN_DAYS)
    assert report["people"] == 16
    assert 0.85 <= report["coverage"] <= 0.95


if __name__ == "__main__":
    for k, v in evaluate_held_out(load_pmdata(PMDATA), MIN_DAYS).items():
        print(f"{k}: {v:.3f}" if isinstance(v, float) else f"{k}: {v}")
