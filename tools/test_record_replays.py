"""Recorded replays (Spec 2 / Spec 5 request): a ReplayFile played through detection and Forecast B, with
the output written back into the file so the home screen can run with the service stopped.

Out events: "alert" (Alert), "trigger" (Trigger), "reading_state" (Reading) and "forecast" (provisional
Forecast schema, contracts/provisional/forecast.schema.json). Each output event sits right after the
event that caused it, and its event t is that cause's time, so the file stays in time order; a released
Reading keeps its own time in the payload.
"""
import json
import sys
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from backend.detection import load_content
from tools.record_replays import CrewForecaster, record, train_models

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "contracts"))
from validate import validate  # noqa: E402

DAY, AM7 = 86_400, 7 * 3_600
CONTRACT = {"alert": "Alert", "trigger": "Trigger", "reading_state": "Reading"}
FORECAST = Draft202012Validator(json.loads((ROOT / "contracts/provisional/forecast.schema.json").read_text()))
NOISE = [0.0, 1.5, -1.5, 0.75, -0.75, 1.0, -1.0]
WELLNESS = {"fatigue": 3, "mood": 3, "readiness": 7, "sleep_quality": 3, "soreness": 2, "stress": 3}


def reading(crew, indicator, value, unit, day):
    t = day * DAY + AM7
    return {"t": t, "type": "reading", "payload": {"crew": crew, "indicator": indicator, "value": value, "unit": unit,
                                                   "t": t, "source": "sensor", "confidence": 0.9, "state": "released"}}


def jump_replay():
    events = [reading("J", "resting_heart_rate", 60 + NOISE[d % 7], "bpm", d) for d in range(30)]
    events += [reading("J", "resting_heart_rate", 85, "bpm", 30)] + [reading("J", "resting_heart_rate", 60, "bpm", 31)]
    return {"schema_version": "1.0.0", "crew": "J", "profile": "mars_transit", "events": events}


def record_j(replays=None, forecaster=None):
    cutoffs, bounds = load_content()
    rec = {"schema_version": "1.0.0", "id": "J", "sex": "female", "missionProfile": "mars_transit",
           "anchor": {"resting_heart_rate": {"mean": 60.0, "sd": 1.0}}}
    return record(replays or [jump_replay()], [rec], cutoffs, bounds, forecaster)


def added(rp, kind=None):
    return [e for e in rp["events"] if e["type"] not in ("reading", "crew_report") and kind in (None, e["type"])]


def assert_valid(rp):
    times = [e["t"] for e in rp["events"]]
    assert times == sorted(times), "events must stay in time order"
    for e in rp["events"]:
        if e["type"] in CONTRACT:
            validate(CONTRACT[e["type"]], e["payload"])
        elif e["type"] == "forecast":
            FORECAST.validate(e["payload"])
    validate("ReplayFile", rp)
    return True


# --- Detection output ---------------------------------------------------------------------------

def test_input_events_are_kept_unchanged_and_in_order():
    rp = jump_replay()
    out = record_j([rp])[0]
    assert [e for e in out["events"] if e["type"] == "reading"] == rp["events"]
    assert {k: out[k] for k in ("schema_version", "crew", "profile")} == {k: rp[k] for k in ("schema_version", "crew", "profile")}


def test_alert_and_quarantine_follow_the_reading_that_caused_them():
    out = record_j()[0]
    assert_valid(out)
    i = next(i for i, e in enumerate(out["events"]) if e["type"] == "alert" and e["payload"]["kind"] == "acute")
    cause = next(e for e in reversed(out["events"][:i]) if e["type"] == "reading")  # a drift alert may come first
    assert cause["payload"]["value"] == 85 and out["events"][i]["t"] == cause["t"]
    states = [(e["payload"]["value"], e["payload"]["state"]) for e in added(out, "reading_state")]
    assert (85, "quarantined") in states


def test_a_later_release_keeps_the_file_in_time_order_and_the_reading_its_own_time():
    out = record_j()[0]
    assert_valid(out)
    released = [e for e in added(out, "reading_state") if e["payload"]["state"] == "released"]
    assert released and released[0]["payload"]["t"] == 30 * DAY + AM7 and released[0]["t"] == 31 * DAY + AM7


def test_two_replays_of_one_crew_share_one_baseline_and_keep_their_own_files():
    first, second = jump_replay(), jump_replay()
    first["events"], second["events"] = first["events"][:30], second["events"][30:]
    a, b = record_j([first, second])
    assert not added(a, "alert") and added(b, "alert")  # the jump is judged against the first file's days
    assert assert_valid(a) and assert_valid(b)


# --- Forecast -------------------------------------------------------------------------------------

def wellness_replay(days):
    events = []
    for d in range(days):
        events += [reading("J", k, v, "score", d) for k, v in WELLNESS.items()]
        events.append(reading("J", "sleep_duration", 450, "min", d))
    return {"schema_version": "1.0.0", "crew": "J", "profile": "mars_transit", "events": events}


def fake_forecast(calls):
    def fn(model, history, today, min_days, remeasure_width):
        calls.append((model, len(history), dict(today), min_days, remeasure_width))
        return {"value": 6.5, "low": 5.0, "high": 8.0, "label": None, "population": 6.4,
                "personal_correction": 0.1, "base": 6.0, "drivers": {k: 0.0 for k in today.index}}
    return fn


def test_one_forecast_per_complete_day_with_sleep_in_hours_and_past_pairs_as_history():
    calls = []
    fc = CrewForecaster({"J": "model-J"}, min_days=7, remeasure_width=6.0, forecast_fn=fake_forecast(calls))
    out = record_j([wellness_replay(4)], fc)[0]
    assert_valid(out)
    forecasts = added(out, "forecast")
    assert [e["t"] for e in forecasts] == [d * DAY + AM7 for d in range(4)]
    assert [n for _, n, *_ in calls] == [0, 1, 2, 3]  # day d has d earlier (today, tomorrow's readiness) pairs
    assert calls[0][0] == "model-J" and calls[0][2]["sleep_duration_h"] == 7.5 and calls[0][3:] == (7, 6.0)


def test_forecast_payload_has_the_provisional_fields_and_an_honest_label():
    fc = CrewForecaster({"J": "m"}, 7, 6.0, forecast_fn=fake_forecast([]))
    p = added(record_j([wellness_replay(1)], fc)[0], "forecast")[0]["payload"]
    FORECAST.validate(p)
    assert (p["crew"], p["label"]) == ("J", "estimate, not validated")  # no label from the model -> honest default


def test_a_day_missing_an_answer_gets_no_forecast():
    rp = wellness_replay(2)
    rp["events"] = [e for e in rp["events"] if not (e["payload"]["indicator"] == "soreness" and e["t"] < DAY)]
    fc = CrewForecaster({"J": "m"}, 7, 6.0, forecast_fn=fake_forecast([]))
    assert [e["t"] for e in added(record_j([rp], fc)[0], "forecast")] == [DAY + AM7]


def test_crew_without_a_model_gets_no_forecast():
    fc = CrewForecaster({}, 7, 6.0, forecast_fn=fake_forecast([]))
    assert not added(record_j([wellness_replay(2)], fc)[0], "forecast")


# --- Real data (needs PMData, git-ignored) --------------------------------------------------------

PMDATA = Path.home() / "Vedant/Claude/Nasa/datasets/pmdata/extracted"


@pytest.mark.skipif(not (PMDATA / "p01/pmsys/wellness.csv").exists(), reason="PMData not downloaded")
def test_real_crew_b_forecasts_validate_and_never_train_on_crew_b():
    mapping = json.loads((ROOT / "replay/crew-replays.source.json").read_text())["mapping"]
    models = train_models(PMDATA, {"B": mapping["B"]})
    assert mapping["B"] not in models["B"]["people"]
    cutoffs, bounds = load_content()
    rp = json.loads((ROOT / "replay/crew-B.json").read_text())
    rp["events"] = [e for e in rp["events"] if e["t"] < 40 * DAY]
    records = json.loads((ROOT / "replay/crew-records.json").read_text())
    fc = CrewForecaster(models, cutoffs["forecast_min_days"], cutoffs["forecast_remeasure_width"])
    out = record([rp], records, cutoffs, bounds, fc)[0]
    assert_valid(out)
    assert len(added(out, "forecast")) > 20
