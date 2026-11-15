"""Spec 2 joint-pattern anomaly through the habitat service: several small shifts together raise one drift alert
marked pattern "joint" that names the indicators involved; plain noise raises none.
"""
import random

from spec2_helpers import DAY, of_type, play, reading, record, replay

from validate import validate

NORMAL = {"resting_heart_rate": (60, 2, "bpm"), "sleep_duration": (450, 40, "min"), "mood": (3.5, 0.5, "score 1-5"),
          "stress": (2.5, 0.5, "score 1-5")}
SHIFT = {"resting_heart_rate": +1.5, "sleep_duration": -1.5, "mood": -1.5}  # in sd: each small on its own
# Behaviour check on one fixed seed; detection power and false alerts are measured on PMData in tools/test_joint_pattern.py.


def noisy(days, shift_from=None, seed=1):
    rng, ev = random.Random(seed), []
    for d in range(days):
        for k, (ind, (mean, sd, unit)) in enumerate(NORMAL.items()):
            s = SHIFT.get(ind, 0) * sd if shift_from is not None and d >= shift_from else 0
            ev.append(reading("A", ind, round(rng.gauss(mean + s, sd), 2), unit, d * DAY + (6 + k) * 3600))
    return replay("A", ev)


def rec():
    return [record("A", anchor={"resting_heart_rate": {"mean": 60, "sd": 2}, "sleep_duration": {"mean": 450, "sd": 40}})]


def joint_alerts(got):
    return [m["payload"] for m in of_type(got, "alert") if m["payload"].get("pattern") == "joint"]


def test_combined_small_shifts_raise_one_joint_drift_alert_naming_them(tmp_path):
    _, got = play(tmp_path, [noisy(50, shift_from=35, seed=4)], records=rec())
    raised = [a for a in joint_alerts(got) if a["status"] != "green" and "escalation" not in a]
    assert len(raised) == 1
    alert = raised[0]
    validate("Alert", alert)
    assert alert["kind"] == "drift" and alert["urgency"] == "MONITOR"
    assert 35 * DAY <= alert["t"] <= 50 * DAY
    assert len(set(alert["indicators"]) & set(SHIFT)) >= 2, "names the shifted indicators"
    assert alert["indicator"] in SHIFT and alert["indicator"] == alert["indicators"][0]
    assert all("joint pattern" in c["note"] for c in alert["likely_causes"])
    plan = [m["payload"] for m in of_type(got, "plan") if m["payload"]["pattern"] == "joint"]
    assert plan and plan[0]["alert_id"] == alert["id"]


def test_noise_alone_raises_no_joint_alert(tmp_path):
    for seed in range(3):
        (tmp_path / str(seed)).mkdir()
        _, got = play(tmp_path / str(seed), [noisy(60, seed=seed)], records=rec())
        assert not [a for a in joint_alerts(got) if a["status"] != "green"], f"seed {seed}"
