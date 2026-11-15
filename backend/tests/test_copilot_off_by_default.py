"""Spec 3 is future scope (team decision 2026-11-15): the architecture stays, but the shipped build runs with the
copilot off (content/copilot/copilot.json). Off means the emergency flow behaves as it did without Spec 3."""
import json

from app.content import CONTENT
from app.runtime import REAL_RECORDS, build
from test_copilot_record import CHEST, routed


def default_engine():
    return build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer=None,
                 routing=True)


def test_shipped_config_has_the_copilot_and_investigator_off():
    assert json.loads((CONTENT / "copilot" / "copilot.json").read_text(encoding="utf-8"))["enabled"] is False
    assert json.loads((CONTENT / "copilot" / "investigator.json").read_text(encoding="utf-8"))["enabled"] is False


def test_off_no_briefing_no_choice_gate_no_copilot_record():
    eng = default_engine()
    e = routed(eng, CHEST)
    assert e.copilot is None and e.copilot_last is None
    v = eng.view("B")
    assert not {"briefing", "l0", "choice", "suggestion", "investigator"} & set(v)
    while eng.view("B")["screen"] in ("record", "contributors"):
        eng.next("B")  # no copilot choice is asked for before the steps
    assert eng.view("B")["screen"] == "step"
    assert "copilot" not in eng.ground.build(e)


def test_off_the_airway_row_is_left_out_and_on_it_is_back():
    off = {r["id"] for r in default_engine().routes["rows"]}
    on = {r["id"] for r in build(copilot=True, explainer=None, routing=True).routes["rows"]}
    assert "airway-low-spo2-or-no-breathing" not in off and "airway-low-spo2-or-no-breathing" in on
    assert on - off == {"airway-low-spo2-or-no-breathing"}


def test_off_no_investigator_model_and_no_form_answer_fetch():
    eng = build(protocol="microgravity-cpr", profile="mars_transit", records_path=REAL_RECORDS, explainer="ollama",
                routing=True)
    assert eng.investigator.transport is None
    calls = []

    class FakeHabitat:
        def record(self, crew, requester, emergency):
            return eng.records.get(crew)

        def hot_summary(self, crew, requester, emergency):
            calls.append(crew)
            return {}

    eng.habitat = FakeHabitat()
    routed(eng, CHEST)
    assert calls == []  # the crew's private form answers are not fetched for a copilot that is off
