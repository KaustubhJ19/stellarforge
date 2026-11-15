"""Collapse Copilot ticket 02: HotSummary stub source and condition library."""
import json

import pytest

from app.habitat import Habitat
from app.content import REPO
from copilot.conditions import DEFAULT_PATH, load_conditions
from copilot.fixtures import FAKE_LABEL, fake_hot_summary
from copilot.hot_summary import HotSummary, NoHistory


def test_no_habitat_service_reports_no_history_not_an_error(eng):
    result = eng.hot_summaries.latest("cmdr")
    assert isinstance(result, NoHistory) and "no habitat service" in result.reason


def test_habitat_without_a_snapshot_reports_no_history(eng):
    from copilot.hot_summary import PushedHotSummaries
    result = PushedHotSummaries(habitat_configured=True).latest("cmdr")
    assert isinstance(result, NoHistory) and "no snapshot" in result.reason


def test_pushed_snapshot_is_readable_and_labelled_fake(eng):
    Habitat(eng, "http://unused").handle({"type": "hot_summary", "payload": fake_hot_summary("cmdr", t=50)})
    snap = eng.hot_summaries.latest("cmdr")
    assert isinstance(snap, HotSummary) and snap.label == FAKE_LABEL and snap.context["hours_since_eva"] == 2.0
    assert isinstance(eng.hot_summaries.latest("eng"), NoHistory)


def test_snapshot_riding_on_an_alert_is_stored_and_alert_still_ingested(eng):
    alert = {**json.loads((REPO / "contracts/examples/Alert.example.json").read_text()), "crew": "cmdr",
             "hot_summary": fake_hot_summary("cmdr", t=10)}
    habitat = Habitat(eng, "http://unused")
    habitat.handle({"type": "alert", "payload": alert})
    assert isinstance(eng.hot_summaries.latest("cmdr"), HotSummary)
    assert not habitat.errors, habitat.errors


def test_older_snapshot_does_not_replace_a_newer_one(eng):
    eng.hot_summaries.update(fake_hot_summary("cmdr", t=100))
    eng.hot_summaries.update(fake_hot_summary("cmdr", t=40))
    assert eng.hot_summaries.latest("cmdr").t == 100


def test_bad_push_is_rejected_and_logged_without_losing_the_old_snapshot(eng):
    eng.hot_summaries.update(fake_hot_summary("cmdr", t=1))
    habitat = Habitat(eng, "http://unused")
    habitat.handle({"type": "hot_summary", "payload": {"crew": "cmdr"}})
    assert habitat.errors and eng.hot_summaries.latest("cmdr").t == 1
    assert any(e["type"] == "habitat_message_rejected" for e in eng.events)


def test_digest_is_stable_and_changes_with_content():
    a = HotSummary.from_dict(fake_hot_summary("cmdr", t=1))
    assert a.digest() == HotSummary.from_dict(fake_hot_summary("cmdr", t=1)).digest()
    assert a.digest() != HotSummary.from_dict(fake_hot_summary("cmdr", t=2)).digest()


def test_library_loads_with_demo_and_extra_conditions_and_simulatable_flags():
    lib = load_conditions()
    ids = {c.id for c in lib.conditions}
    assert {"fainting", "decompression-sickness", "low-blood-sugar", "seizure", "head-injury"} <= ids
    assert {c.id for c in lib.simulatable()} == {"fainting", "low-blood-sugar", "cardiac-arrest"}
    assert not lib.get("decompression-sickness").simulatable
    assert all(c.signs and c.protocol_id and "team value" in c.prior_source for c in lib.conditions)


@pytest.mark.parametrize("mutate, message", [
    (lambda c: c.update(prior=1.5), "prior"),
    (lambda c: c["signs"][0].update(lr=0), "lr must be positive"),
    (lambda c: c["signs"][0].update(source=""), "source label"),
    (lambda c: c.pop("simulatable"), "simulatable"),
    (lambda c: c.update(protocol_id=""), "protocol_id"),
])
def test_invalid_library_is_rejected(tmp_path, mutate, message):
    raw = json.loads(DEFAULT_PATH.read_text(encoding="utf-8"))
    mutate(raw["conditions"][0])
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(raw))
    with pytest.raises(ValueError, match=message):
        load_conditions(bad)
