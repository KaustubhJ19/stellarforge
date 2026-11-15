"""Flatten content/cards/*.json into Spec 2's CardContent shape (content/cards-frontend.json).

Spec 2's App takes cards: CardContent[] = {indicator, how, why, ifAbnormal, labels, sources}, all text.
The structured cards stay the source of truth; this file is generated from them.

Command line:
    python tools/export_cards.py   # rewrites content/cards-frontend.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
CARDS = ROOT / "content" / "cards"
OUT = ROOT / "content" / "cards-frontend.json"
STEPS = (("now", "Now"), ("remeasure", "Measure again"), ("tell_crew", "Tell the crew"), ("tell_ground", "Tell the ground"))


def flatten(card):
    why = card["why"]
    risk = (f"NASA HRP: {why['hrp_risk']}." if why["hrp_risk"] != "uncovered"
            else f"NASA HRP: not covered. {why['uncovered_reason']}")
    return {
        "indicator": card["indicator"],
        "how": " ".join(card["how"]),
        "why": f"{why['text']} {risk} In space: {card['space_note']}",
        "ifAbnormal": " ".join(f"{label}: {card['if_abnormal'][key]}" for key, label in STEPS),
        "labels": list(card.get("labels", [])),
        "sources": list(card.get("sources", [])),
    }


def flatten_all(cards_dir=CARDS):
    out = []
    for path in sorted(Path(cards_dir).glob("*.json")):
        card = json.loads(path.read_text(encoding="utf-8"))
        flat = flatten(card)
        out.append(flat)
        out += [{**flat, "indicator": rel} for rel in card.get("related_indicators", [])]
    return out


def main():
    OUT.write_text(json.dumps(flatten_all(), indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
