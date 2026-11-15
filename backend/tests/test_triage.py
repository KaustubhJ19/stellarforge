"""Intent-first routing (docs/spec-intent-routing.md): the router is a fixed table, first match wins."""
import json

import pytest

from app import triage
from app.content import CONTENT

AVAILABLE = {"microgravity-cpr", "chest-pain"}


def pick(intake=None, *, kind="manual", arrest=False, cabin=False, available=AVAILABLE):
    live = {"arrest": arrest, "cabin_alert": cabin}
    return triage.route(triage.load_routes(), intake, live, available, trigger_kind=kind)


def intake(**kw):
    return {"responsive": "yes", "breathing": "normal", "main_problem": "other"} | kw


@pytest.mark.parametrize("args, protocol, rule", [
    # row 1: unresponsive and not breathing normally
    (dict(intake=intake(responsive="no", breathing="none")), "microgravity-cpr", "unresponsive-not-breathing"),
    (dict(intake=intake(responsive="no", breathing="abnormal")), "microgravity-cpr", "unresponsive-not-breathing"),
    # row 2: live arrest rhythm wins even when the answers say otherwise
    (dict(intake=intake(main_problem="injury"), arrest=True), "microgravity-cpr", "arrest-rhythm"),
    # row 3: awake with chest pain
    (dict(intake=intake(main_problem="chest_pain")), "chest-pain", "chest-pain-responsive"),
    # an auto Trigger skips the questions
    (dict(intake=None, kind="auto"), "microgravity-cpr", "auto-trigger"),
])
def test_each_row_picks_its_protocol(args, protocol, rule):
    got = pick(**args)
    assert (got["protocol_id"], got["rule_id"]) == (protocol, rule)
    assert got["reason"]


def test_first_match_wins_over_later_rows():
    # unresponsive + chest pain: row 1 (CPR) comes before row 3 (chest pain)
    got = pick(intake(responsive="no", breathing="none", main_problem="chest_pain"))
    assert got["protocol_id"] == "microgravity-cpr"


@pytest.mark.parametrize("answers", [
    dict(main_problem="injury"),
    dict(main_problem="breathing_trouble"),
    dict(main_problem="other"),
    dict(responsive="no", breathing="normal"),  # unresponsive but breathing normally: not CPR
])
def test_everything_else_is_not_covered(answers):
    got = pick(intake(**answers))
    assert got["protocol_id"] is None and got["rule_id"] == "no-match"
    assert "ground" in got["reason"].lower()


def test_a_missing_protocol_is_not_covered_not_an_error():
    # cabin-air has no cited content yet: the route exists, the protocol does not
    got = pick(intake(main_problem="cabin_alert"))
    assert got["protocol_id"] is None
    assert got["rule_id"] == "cabin-alert-reported"
    assert "cabin-air" in got["reason"] and "not available" in got["reason"]


def test_live_cabin_alert_routes_to_cabin_air_when_it_exists():
    got = pick(intake(), cabin=True, available=AVAILABLE | {"cabin-air"})
    assert (got["protocol_id"], got["rule_id"]) == ("cabin-air", "cabin-alert-live")


@pytest.mark.parametrize("bad", [
    {"responsive": "maybe"}, {"breathing": "loud"}, {"main_problem": "headache"}, {"source": "magic"}, {"extra": "x"},
])
def test_invalid_intake_is_refused(bad):
    with pytest.raises(triage.IntakeError):
        triage.validate_intake(intake() | bad)


def test_incomplete_intake_is_refused():
    with pytest.raises(triage.IntakeError):
        triage.validate_intake({"responsive": "yes"})


def test_valid_intake_defaults_source_to_tap():
    assert triage.validate_intake(intake())["source"] == "tap"


def test_routes_only_name_real_or_pending_protocols():
    data = json.loads((CONTENT / "triage" / "routes.json").read_text(encoding="utf-8"))
    on_disk = {p.name.removesuffix(".json") for p in (CONTENT / "protocols").glob("*.json") if p.name.count(".") == 1}
    named = {r["protocol"] for r in data["rows"]}
    assert named <= on_disk | set(data["pending_protocols"])
    assert all(r["reason"] and r["id"] for r in data["rows"])
    assert len({r["id"] for r in data["rows"]}) == len(data["rows"])


def test_routes_contain_no_drug_or_dose():
    from app.content import lint_content
    text = (CONTENT / "triage" / "routes.json").read_text(encoding="utf-8")
    assert not lint_content.find_drug_or_dose(text, lint_content.load_deny_list())
