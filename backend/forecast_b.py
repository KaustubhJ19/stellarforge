"""Forecast B (P1): tomorrow's self-reported Readiness (0-10) with a range and its drivers.

- Gradient-boosted trees (scikit-learn) trained on PMData daily wellness answers (CC BY 4.0).
- Range: split conformal interval, MAPIE (https://github.com/scikit-learn-contrib/MAPIE),
  see Angelopoulos & Bates, https://arxiv.org/abs/2107.07511.
- Drivers: SHAP (Lundberg & Lee 2017, https://arxiv.org/abs/1705.07874).
- Personalised by residual correction: the population forecast is shifted by the person's mean past error.
The in-app attention test is meant to be an input too, but PMData has no such column, so it is not used yet.
Status: "estimate, not validated".
"""
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import shap
from mapie.regression import SplitConformalRegressor
from sklearn.ensemble import HistGradientBoostingRegressor

FEATURES = ["fatigue", "mood", "readiness", "sleep_duration_h", "sleep_quality", "soreness", "stress"]
ONE_TO_FIVE = ["fatigue", "mood", "sleep_quality", "soreness", "stress"]
SCALE = (0.0, 10.0)  # PMData readiness scale, verified in ticket 01 (docs/datasets.md)
CONFIDENCE = 0.9  # Spec 3 Testing Decisions: interval coverage target about 90%


def load_pmdata(root: Path) -> pd.DataFrame:
    """One row per person per day from every pXX/pmsys/wellness.csv."""
    frames = []
    for f in sorted(Path(root).glob("p*/pmsys/wellness.csv")):
        df = pd.read_csv(f)
        df["person"] = f.parent.parent.name
        df["date"] = pd.to_datetime(df["effective_time_frame"], utc=True).dt.tz_localize(None).dt.normalize()
        frames.append(df)
    df = pd.concat(frames, ignore_index=True)
    df = df[(df[ONE_TO_FIVE] > 0).all(axis=1)]  # 0 is outside the 1-5 scale: a blank submission
    return df.sort_values(["person", "date"]).drop_duplicates(["person", "date"], keep="last")


def daily_pairs(df: pd.DataFrame) -> pd.DataFrame:
    """Today's answers (FEATURES) with tomorrow's readiness (target); only calendar-consecutive days."""
    df = df.sort_values(["person", "date"]).reset_index(drop=True)
    nxt = df.groupby("person")[["date", "readiness"]].shift(-1)
    keep = (nxt["date"] - df["date"]) == pd.Timedelta(days=1)
    return df.loc[keep, ["person", "date", *FEATURES]].assign(target=nxt.loc[keep, "readiness"]).reset_index(drop=True)


def train(train_pairs: pd.DataFrame, calib_pairs: pd.DataFrame, confidence: float = CONFIDENCE) -> dict:
    """Population model on one set of people, conformal range calibrated on other people."""
    # Small trees: about 1,300 day pairs; the library defaults did worse than "tomorrow = today".
    trees = HistGradientBoostingRegressor(max_depth=3, max_iter=100, learning_rate=0.05, min_samples_leaf=40,
                                          random_state=0).fit(train_pairs[FEATURES], train_pairs["target"])
    mapie = SplitConformalRegressor(trees, confidence_level=confidence, prefit=True)
    with warnings.catch_warnings():  # MAPIE strips the DataFrame's column names internally; ours are correct
        warnings.filterwarnings("ignore", message="X does not have valid feature names", category=UserWarning)
        mapie.conformalize(calib_pairs[FEATURES], calib_pairs["target"])
    return {"trees": trees, "mapie": mapie, "explainer": shap.TreeExplainer(trees)}


def forecast(model: dict, history: pd.DataFrame, today: pd.Series, min_days: int, remeasure_width: float) -> dict:
    """Tomorrow's readiness for one person from today's answers and their own past pairs (history)."""
    row = today[FEATURES].to_frame().T.astype(float)
    population = float(model["trees"].predict(row)[0])
    clip = lambda v: float(np.clip(v, *SCALE))
    if len(history) < min_days:
        correction, (low, high), label = 0.0, SCALE, "learning your pattern"
    else:
        correction = float((history["target"] - model["trees"].predict(history[FEATURES])).mean())
        _, bounds = model["mapie"].predict_interval(row)
        low, high = clip(bounds[0, 0, 0] + correction), clip(bounds[0, 1, 0] + correction)
        label = "re-measure" if high - low > remeasure_width else None
    explanation = model["explainer"](row)
    return {
        "value": clip(population + correction), "low": low, "high": high, "label": label,
        "population": population, "personal_correction": correction,
        "base": float(explanation.base_values[0]),
        "drivers": dict(zip(FEATURES, map(float, explanation.values[0]))),
    }


def what_if(model: dict, history: pd.DataFrame, today: pd.Series, changes: dict, min_days: int) -> dict:
    """Forecast with some of today's answers changed. A what-if, so never validated."""
    unknown = set(changes) - set(FEATURES)
    if unknown:
        raise ValueError(f"unknown answers in what-if: {sorted(unknown)}")
    changed = today[FEATURES].copy()
    changed.update(pd.Series(changes, dtype=float))
    out = forecast(model, history, changed, min_days, remeasure_width=SCALE[1])
    return {"value": out["value"], "label": "estimate, not validated"}


def evaluate_held_out(df: pd.DataFrame, min_days: int, folds: int = 4) -> dict:
    """Walk forward through people never used to train: each day uses only that person's earlier days."""
    pairs = daily_pairs(df)
    people = sorted(pairs["person"].unique())
    errors, covered, widths, persistence = [], [], [], []
    for k in range(folds):
        test = people[k::folds]
        rest = [p for p in people if p not in test]
        calib = rest[::4]
        model = train(pairs[pairs.person.isin(set(rest) - set(calib))], pairs[pairs.person.isin(calib)])
        for person in test:
            own = pairs[pairs.person == person].reset_index(drop=True)
            for i in range(min_days, len(own)):
                out = forecast(model, own.iloc[:i], own.iloc[i], min_days, remeasure_width=SCALE[1])
                truth = own.at[i, "target"]
                errors.append(abs(out["value"] - truth))
                covered.append(out["low"] <= truth <= out["high"])
                widths.append(out["high"] - out["low"])
                persistence.append(abs(own.at[i, "readiness"] - truth))  # "tomorrow = today" for comparison
    return {"people": len(people), "forecasts": len(errors), "mean_error": float(np.mean(errors)),
            "persistence_mean_error": float(np.mean(persistence)), "coverage": float(np.mean(covered)),
            "mean_width": float(np.mean(widths))}
