"""Ticket 07: HRP risk map.

A judge sees which of NASA's 17 HRP risks the tool covers, through which Indicators and cards,
and which it does not cover. The map is generated from content/cards/*.json, so it can only
claim a risk that a card names.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import content_lint as cl  # noqa: E402
import hrp_map as hm  # noqa: E402

CARDS = ROOT / "content" / "cards"
SOURCE = "https://www.nasa.gov/hrp/risks/"


def real():
    return hm.build(CARDS)


def test_all_17_risks_are_listed_with_the_source_link():
    text = hm.render(real())
    assert len(cl.HRP_RISKS) == 17
    for risk in cl.HRP_RISKS:
        assert risk in text, risk
    assert SOURCE in text


def test_every_risk_is_either_covered_or_uncovered_never_both():
    m = real()
    assert set(m["covered"]) | set(m["uncovered"]) == cl.HRP_RISKS
    assert not set(m["covered"]) & set(m["uncovered"])


def test_covered_risk_names_its_indicators_and_cards():
    cardio = real()["covered"]["Risk of Cardiovascular Adaptations"]
    assert {e["card"] for e in cardio} == {"content/cards/heart_rate.json", "content/cards/systolic_bp.json"}
    indicators = {i for e in cardio for i in e["indicators"]}
    assert indicators == {"heart_rate", "resting_heart_rate", "systolic_bp"}
    text = hm.render(real())
    assert "content/cards/heart_rate.json" in text and "resting_heart_rate" in text


def test_no_claim_without_a_card():
    named = {}
    for path in CARDS.glob("*.json"):
        risk = json.loads(path.read_text(encoding="utf-8"))["why"]["hrp_risk"]
        if risk != cl.UNCOVERED:
            named.setdefault(risk, set()).add(f"content/cards/{path.name}")
    covered = real()["covered"]
    assert {r: {e["card"] for e in es} for r, es in covered.items()} == named


def test_a_card_set_with_one_card_covers_only_that_risk(tmp_path):
    card = json.loads((CARDS / "mood.json").read_text(encoding="utf-8"))
    (tmp_path / "mood.json").write_text(json.dumps(card), encoding="utf-8")
    m = hm.build(tmp_path)
    assert list(m["covered"]) == ["Risk of Behavioral Changes and Psychiatric Disorders"]
    assert len(m["uncovered"]) == 16


def test_uncovered_risks_are_listed_openly():
    m = real()
    text = hm.render(m)
    uncovered_part = text[text.index("## Risks the tool does not cover"):]
    for risk in m["uncovered"]:
        assert risk in uncovered_part, risk


def test_cards_with_no_hrp_risk_are_listed_with_their_reason():
    m = real()
    cards = {e["card"] for e in m["cards_without_risk"]}
    assert cards == {"content/cards/glucose.json", "content/cards/body_temperature.json"}
    text = hm.render(m)
    for e in m["cards_without_risk"]:
        assert e["reason"] in text


def test_an_unknown_risk_title_is_rejected(tmp_path):
    card = json.loads((CARDS / "mood.json").read_text(encoding="utf-8"))
    card["why"]["hrp_risk"] = "Risk of Something Made Up"
    (tmp_path / "mood.json").write_text(json.dumps(card), encoding="utf-8")
    try:
        hm.build(tmp_path)
    except ValueError as exc:
        assert "Risk of Something Made Up" in str(exc)
    else:
        raise AssertionError("an unknown risk title must not reach the map")


def test_committed_map_matches_the_cards():
    committed = (ROOT / "docs" / "hrp-risk-map.md").read_text(encoding="utf-8")
    assert committed == hm.render(real()), "run: python tools/hrp_map.py"
