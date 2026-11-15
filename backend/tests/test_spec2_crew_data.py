"""Spec 2: new crew data paths and the HotSummary, through the habitat service fed by replays.

Seam: HabitatService(detection=build_loop(...)) plays replay files; we observe pushed messages,
service.hot_summary(crew) and the store. No internal running sums are inspected.
"""
import json
import math
from pathlib import Path

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

    from copilot.fixtures import fake_hot_summary

    hab = Habitat(eng, "http://127.0.0.1:1")  # never started: messages are handed in directly
    hab.handle({"t": 5, "type": "alert", "payload": alert(crew="cmdr"), "hot_summary": fake_hot_summary("cmdr", t=5)})
    hab.handle({"t": 6, "type": "alert", "payload": alert(crew="cmdr"), "hot_summary": fake_hot_summary("someone-else", t=6)})
    assert eng.hot_summaries.latest("cmdr").t == 5  # a summary for another crew member is not filed under this one
    assert not hasattr(eng.hot_summaries.latest("someone-else"), "t")


def test_an_unreadable_pushed_hot_summary_never_blocks_its_alert(eng):
    from app.habitat import Habitat
    from sf_helpers import alert

    hab = Habitat(eng, "http://127.0.0.1:1")
    a = alert(crew="cmdr")
    hab.handle({"t": 5, "type": "alert", "payload": a, "hot_summary": {"crew": "cmdr", "t": 5}})
    hab.handle({"t": 6, "type": "alert", "payload": a, "hot_summary": {"crew": "cmdr", "t": 6, "mission_day": 1}})
    assert eng.alerts["cmdr"]["id"] == a["id"] and sum(e.startswith("hot_summary") for e in hab.errors) == 2


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


def test_a_form_pushed_after_a_failed_annotate_still_carries_no_answers(tmp_path, monkeypatch):
    svc, got = play(tmp_path, [])
    monkeypatch.setattr(svc.detection, "annotate", lambda m: 1 / 0)  # privacy must fail closed
    svc.post_form({"schema_version": "1.0.0", "crew": "A", "form": "note", "t": 50.0, "answers": {"text": "private"}})
    assert "answers" not in of_type(got, "form")[0]["payload"] and "private" not in json.dumps(got)


# ---- Spec 2 -> Spec 3: the copilot reads the HotSummary the habitat service really pushes ------------

def test_the_copilot_reads_the_real_pushed_hot_summary(tmp_path, eng):
    from app.habitat import Habitat
    from copilot.hot_summary import HotSummary

    svc, got = play(tmp_path, [text_replay()])
    svc.post_trigger({"schema_version": "1.0.0", "kind": "manual", "crew": "A", "t": 31 * DAY, "reason": "button"})
    trig = of_type(got, "trigger")[-1]
    pushed = trig["hot_summary"]
    hab = Habitat(eng, "http://127.0.0.1:1")
    hab.handle({**trig, "payload": {**trig["payload"], "crew": "A"}})
    snap = eng.hot_summaries.latest("A")
    assert isinstance(snap, HotSummary), hab.errors
    hr = snap.indicators["resting_heart_rate"]
    assert hr["z_anchor"] == pushed["indicators"]["resting_heart_rate"]["z_anchor"]
    assert hr["slope_72h"] == pushed["indicators"]["resting_heart_rate"]["slope_per_day"]["72h"]
    ctx, src = snap.context, pushed["context"]
    assert ctx["sleep_debt_3d_h"] == src["sleep_debt_3d_min"] / 60 and ctx["mission_day"] == pushed["mission_day"]
    q = json.loads((Path(__file__).resolve().parents[2] / "content/copilot/dose-conversion.json").read_text())
    assert q["source"] and ctx["dose_7d_mGy"] == src["dose_7d_mGy"]
    assert ctx["dose_7d_msv"] == pytest.approx(src["dose_7d_mGy"] * q["value"]) and "Berger" in ctx["dose_msv_label"]
    assert snap.form_answers == {}  # the public push carries no free text
    assert ctx["hours_since_eva"] == src["hours_since_eva"] is not None
    assert not any(p in json.dumps(snap.to_dict()) for p in PRIVATE)  # still no free text


@pytest.fixture
def reng():  # routing on, crew A-D, as the copilot runs
    from app.runtime import REAL_RECORDS, build
    return build(copilot=True, protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                 routing=True)


def test_an_emergency_record_opening_gives_the_copilot_the_form_answers(tmp_path, reng):
    eng = reng
    """The rescuer's logged emergency opening also fetches the full summary (GET /hot_summary ... emergency=1)."""
    from test_copilot_record import routed

    svc, _ = play(tmp_path, [text_replay()])
    calls = []

    class FakeHabitat:  # stands in for app.habitat.Habitat: answers from the real habitat service
        def record(self, crew, requester, emergency):
            return eng.records.get(crew)

        def hot_summary(self, crew, requester, emergency):
            calls.append((crew, requester, emergency))
            return svc.hot_summary("A", requester="A")  # the service's full summary for crew A (owner view)

    eng.habitat = FakeHabitat()
    routed(eng)  # patient A, rescuer B: the intake leads to the record screen, which opens the record
    assert calls == [("A", "B", True)]
    forms = eng.hot_summaries.latest("A").form_answers
    assert forms["post_eva"]["symptoms"] == "cold hands" and forms["note"]["text"] == "slight headache"
    assert "last_note" not in eng.hot_summaries.latest("A").context  # free text only under form_answers


def test_a_failed_summary_fetch_never_blocks_the_record(reng):
    eng = reng
    from test_copilot_record import routed

    class DownHabitat:
        def record(self, crew, requester, emergency):
            return eng.records.get(crew)

        def hot_summary(self, crew, requester, emergency):
            raise ConnectionError("hot summary not available: down")

    eng.habitat = DownHabitat()
    e = routed(eng)
    assert eng.view("B")["screen"] == "record" and eng.view("B")["ok"] is True
    assert any(ev["type"] == "hot_summary_unavailable" for ev in eng.store.events()) and e is not None
