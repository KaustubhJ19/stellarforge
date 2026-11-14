"""Ticket 06 follow-up: flat card file for Spec 2's frontend.

Spec 2's App takes cards: CardContent[] with flat strings {indicator, how, why, ifAbnormal, labels, sources}.
content/cards-frontend.json is generated from content/cards/*.json and must stay in step with them.
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import export_cards as ec  # noqa: E402

KEYS = {"indicator", "how", "why", "ifAbnormal", "labels", "sources"}


def flat():
    return ec.flatten_all(ROOT / "content" / "cards")


def test_every_entry_has_exactly_the_frontend_shape():
    cards = flat()
    assert cards, "no cards exported"  # an empty list would pass the loop below vacuously
    for c in cards:
        assert set(c) == KEYS
        assert all(isinstance(c[k], str) and c[k].strip() for k in ("indicator", "how", "why", "ifAbnormal"))
        assert all(isinstance(c[k], list) for k in ("labels", "sources"))


def test_one_entry_per_card_plus_related_indicators():
    indicators = [c["indicator"] for c in flat()]
    assert len(indicators) == len(set(indicators))
    for path in (ROOT / "content" / "cards").glob("*.json"):
        assert path.stem in indicators
    assert "resting_heart_rate" in indicators  # the home screen shows daily resting heart rate


def test_why_carries_the_hrp_risk_and_space_note():
    hr = next(c for c in flat() if c["indicator"] == "heart_rate")
    assert "Risk of Cardiovascular Adaptations" in hr["why"] and "Apollo" in hr["why"]


def test_if_abnormal_keeps_all_four_steps_in_order():
    text = next(c for c in flat() if c["indicator"] == "glucose")["ifAbnormal"]
    positions = [text.index(p) for p in ("Now:", "Measure again:", "Tell the crew:", "Tell the ground:")]
    assert positions == sorted(positions)


def test_committed_file_matches_the_cards():
    committed = json.loads((ROOT / "content" / "cards-frontend.json").read_text(encoding="utf-8"))
    assert committed == flat(), "run: python tools/export_cards.py"
