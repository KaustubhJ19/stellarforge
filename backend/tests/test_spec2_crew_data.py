"""Spec 2: new crew data paths and the HotSummary, through the habitat service fed by replays.

Seam: HabitatService(detection=build_loop(...)) plays replay files; we observe pushed messages,
service.hot_summary(crew) and the store. No internal running sums are inspected.
"""
import math

import pytest
from spec2_helpers import DAY, form, location, of_type, play, reading, record, replay

from validate import ContractError


def test_forms_and_glucose_round_trip_and_appear_in_the_snapshot(tmp_path):
    rp = replay("A", [
        reading("A", "glucose", 95, "mg/dL", 1 * DAY, source="manual"),
        form("A", "meal", 1 * DAY + 600, description="rehydrated pasta", kcal=650),
        form("A", "note", 1 * DAY + 700, text="slight headache after lunch"),
        form("A", "post_eva", 2 * DAY, eva_end_t=2 * DAY - 3600, fatigue=4, symptoms="cold hands"),
        reading("A", "glucose", 110, "mg/dL", 2 * DAY + 3600, source="manual"),
    ])
    svc, got = play(tmp_path, [rp])

    stored = svc.store.query("form", crew="A")
    assert [f["form"] for f in stored] == ["meal", "note", "post_eva"]
    assert stored[2]["answers"]["symptoms"] == "cold hands"
    assert [m["type"] for m in got].count("form") == 3

    snap = svc.hot_summary("A", requester="A")
    ctx = snap["context"]
    assert ctx["last_meal"]["t"] == 1 * DAY + 600 and ctx["last_meal"]["answers"]["kcal"] == 650
    assert ctx["last_note"]["answers"]["text"] == "slight headache after lunch"
    assert ctx["last_post_eva"]["answers"]["fatigue"] == 4
    assert ctx["hours_since_eva"] == pytest.approx(2.0)  # EVA ended 2 DAY - 1 h; latest event at 2 DAY + 1 h
    assert snap["indicators"]["glucose"]["value"] == 110
    assert snap["mission_day"] == 3


def test_a_posted_form_is_stored_pushed_and_counted(tmp_path):
    svc, got = play(tmp_path, [])
    svc.post_form({"schema_version": "1.0.0", "crew": "A", "form": "meal", "t": 50.0, "answers": {"description": "soup"}})
    assert svc.store.query("form", crew="A")[0]["answers"]["description"] == "soup"
    assert of_type(got, "form")[0]["payload"]["form"] == "meal"
    assert svc.hot_summary("A", requester="A")["context"]["last_meal"]["answers"]["description"] == "soup"


@pytest.mark.parametrize("bad", [
    {"crew": "A", "form": "diary", "t": 1, "answers": {}},  # unknown form
    {"crew": "A", "form": "meal", "answers": {}},  # no time
    {"crew": "A", "form": "meal", "t": 1},  # no answers
])
def test_an_invalid_form_is_refused(tmp_path, bad):
    svc, _ = play(tmp_path, [])
    with pytest.raises(ContractError):
        svc.post_form({"schema_version": "1.0.0", **bad})
    with pytest.raises(ContractError):
        play(tmp_path / "x", [replay("A", [{"t": 1, "type": "form", "payload": bad}])])


def test_cabin_dose_and_co2_become_per_person_team_values_by_location(tmp_path):
    """A and B share the habitat; B spends day 1-2 in the lab module, which has no readings (no exposure counted)."""
    cabin = "habitat"
    events = [
        location("A", "habitat", 0), location("B", "habitat", 0),
        reading(cabin, "radiation_dose_total", 0.5, "mGy/day", 0),
        reading(cabin, "cabin_pco2_1h", 2.0, "mmHg", 0),
        location("B", "lab", 1 * DAY),
        reading(cabin, "cabin_pco2_1h", 4.0, "mmHg", 1.5 * DAY),  # above the 3 mmHg limit from here
        location("B", "habitat", 2 * DAY),
        reading(cabin, "radiation_dose_total", 1.0, "mGy/day", 2 * DAY),
        reading(cabin, "cabin_pco2_1h", 2.0, "mmHg", 2.25 * DAY),  # back below
        reading(cabin, "radiation_dose_total", 1.0, "mGy/day", 3 * DAY),
    ]
    svc, _ = play(tmp_path, [replay("habitat", events)], records=[record("A"), record("B")])
    a, b = svc.hot_summary("A", requester="A")["context"], svc.hot_summary("B", requester="B")["context"]
    # A: 0.5 mGy/day for 2 days, then 1.0 for 1 day. B: away from the habitat on day 1-2 (no habitat dose).
    assert a["dose_mission_mGy"] == pytest.approx(2.0)
    assert b["dose_mission_mGy"] == pytest.approx(1.5)
    # CO2 above the limit from 1.5 to 2.25 days. A was there 18 h; B came back at 2.0 -> 6 h. Window: the last 24 h to 3 DAY.
    assert a["co2_above_limit_h_24h"] == pytest.approx(6.0)
    assert b["co2_above_limit_h_24h"] == pytest.approx(6.0)
    assert svc.hot_summary("A", requester="A")["exposure_label"] == "team value"


def test_hot_summary_is_pushed_with_alerts_and_triggers(tmp_path):
    events = [reading("A", "resting_heart_rate", 60 + (12 if d >= 20 else 0), "bpm", d * DAY) for d in range(30)]
    svc, got = play(tmp_path, [replay("A", events)])
    alerts = of_type(got, "alert")
    assert alerts, "a +4 sd rise must alert"
    assert all(m["hot_summary"]["crew"] == "A" for m in alerts)
    svc.post_trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "A", "t": 31 * DAY, "reason": "button"})
    trig = of_type(got, "trigger")[-1]
    assert trig["hot_summary"]["indicators"]["resting_heart_rate"]["value"] == 72
    assert not math.isnan(trig["hot_summary"]["indicators"]["resting_heart_rate"]["z_anchor"])


def test_the_emergency_service_keeps_the_latest_pushed_hot_summary(eng):
    """Spec 2 story 17: the HotSummary rides on the Alert / Trigger push; the emergency service just keeps it."""
    from app.habitat import Habitat
    from sf_helpers import alert

    hab = Habitat(eng, "http://127.0.0.1:1")  # never started: messages are handed in directly
    hab.handle({"t": 5, "type": "alert", "payload": alert(crew="cmdr"), "hot_summary": {"crew": "cmdr", "t": 5, "mission_day": 1}})
    hab.handle({"t": 6, "type": "alert", "payload": alert(crew="cmdr"), "hot_summary": {"crew": "someone-else", "t": 6}})
    assert eng.hot_summaries["cmdr"]["t"] == 5  # a summary for another crew member is not filed under this one


# ---- privacy: free text never goes out to every window (team decision, option A) --------------

PRIVATE = ("slight headache", "rehydrated pasta", "cold hands")


def text_replay():
    return replay("A", [
        form("A", "meal", 1 * DAY, description="rehydrated pasta"),
        form("A", "note", 1 * DAY + 60, text="slight headache"),
        form("A", "post_eva", 2 * DAY, eva_end_t=2 * DAY - 3600, symptoms="cold hands"),
        *[reading("A", "resting_heart_rate", 60 + (12 if d >= 20 else 0), "bpm", d * DAY) for d in range(3, 30)],
    ])


def test_pushed_messages_carry_no_crew_note_meal_or_post_eva_text(tmp_path):
    svc, got = play(tmp_path, [text_replay()])
    svc.post_trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "A", "t": 31 * DAY, "reason": "button"})
    import json
    pushed = json.dumps(got)
    assert not [p for p in PRIVATE if p in pushed]
    assert of_type(got, "form") and of_type(got, "alert") and of_type(got, "trigger")
    ctx = of_type(got, "trigger")[-1]["hot_summary"]["context"]
    assert ctx["last_note_t"] == 1 * DAY + 60 and ctx["last_meal_t"] == 1 * DAY and ctx["last_post_eva_t"] == 2 * DAY
    assert ctx["hours_since_eva"] is not None  # the numbers still go out


def test_own_summary_has_the_text_another_persons_needs_an_emergency_and_is_logged(tmp_path):
    svc, _ = play(tmp_path, [text_replay()], records=[record("A"), record("B")])
    assert svc.hot_summary("A", requester="A")["context"]["last_note"]["answers"]["text"] == "slight headache"
    with pytest.raises(PermissionError):
        svc.hot_summary("A", requester="B")
    assert svc.store.query("access_log", crew="A") == []
    assert svc.hot_summary("A", requester="B", emergency=True)["context"]["last_note"]["answers"]["text"] == "slight headache"
    log = svc.store.query("access_log", crew="A")
    assert [(e["opened_by"], e["emergency"], e["what"]) for e in log] == [("B", True, "hot_summary")]
