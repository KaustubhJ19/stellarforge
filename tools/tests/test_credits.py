"""Ticket 10: Credits page content.

content/credits.json lists every dataset, model and asset with name, link and licence.
Test (e): the linter fails if any manifest item is missing from the Credits. Spec 1 has no single
manifest file yet, so the manifest is the data lead's per-replay records: replay/*.source.json
(user decision 2026-11-15). Each must be named in some Credits entry's "manifest" list.
"""
import copy
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import content_lint as cl  # noqa: E402
import credits_page as cp  # noqa: E402

CREDITS = ROOT / "content" / "credits.json"

GOOD = {
    "entries": [
        {"name": "PMData", "kind": "dataset", "link": "https://datasets.simula.no/pmdata/",
         "licence": "CC BY 4.0", "used_for": "Normal days", "manifest": ["crew-replays.source.json"]},
        {"name": "CGMacros", "kind": "dataset", "link": "https://registry.opendata.aws/cgmacros/",
         "licence": "CC BY-NC-SA 4.0", "restriction": "Non-commercial use only.", "used_for": "Glucose"},
    ]
}


def real():
    return json.loads(CREDITS.read_text(encoding="utf-8"))


def by_name(doc, name):
    return next(e for e in doc["entries"] if e["name"].startswith(name))


# --- rule: name, link and licence on every entry -------------------------------------------

def test_good_credits_lint_clean():
    assert cl.lint_credits(GOOD, {"crew-replays.source.json"}) == []


def test_entry_without_licence_fails():
    doc = copy.deepcopy(GOOD)
    del doc["entries"][0]["licence"]
    assert any("licence" in p for p in cl.lint_credits(doc, set()))


def test_entry_without_a_web_link_fails():
    doc = copy.deepcopy(GOOD)
    doc["entries"][0]["link"] = "see the team chat"
    assert any("link" in p for p in cl.lint_credits(doc, set()))


def test_empty_credits_fail():
    assert cl.lint_credits({"entries": []}, set())


# --- rule: restrictive licences stated plainly ----------------------------------------------

def test_non_commercial_licence_without_restriction_fails():
    doc = copy.deepcopy(GOOD)
    del doc["entries"][1]["restriction"]
    assert any("restriction" in p for p in cl.lint_credits(doc, set()))


def test_research_only_licence_without_restriction_fails():
    doc = copy.deepcopy(GOOD)
    doc["entries"][0]["licence"] = "Research use only"
    assert any("restriction" in p for p in cl.lint_credits(doc, {"crew-replays.source.json"}))


# --- test (e): every manifest item is in the Credits ----------------------------------------

def test_manifest_item_missing_from_credits_fails():
    problems = cl.lint_credits(GOOD, {"crew-replays.source.json", "new-replay.source.json"})
    assert any("new-replay.source.json" in p for p in problems)


def test_lint_dir_reads_the_manifest_from_replay_source_records(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "content" / "credits.json").write_text(json.dumps(GOOD), encoding="utf-8")
    (tmp_path / "replay").mkdir()
    (tmp_path / "replay" / "crew-replays.source.json").write_text("{}", encoding="utf-8")
    assert cl.lint_dir(tmp_path / "content") == {}
    (tmp_path / "replay" / "cabin.source.json").write_text("{}", encoding="utf-8")
    failures = cl.lint_dir(tmp_path / "content")
    assert any("cabin.source.json" in p for ps in failures.values() for p in ps)


def test_lint_dir_requires_credits_when_the_manifest_has_items(tmp_path):
    (tmp_path / "content").mkdir()
    (tmp_path / "replay").mkdir()
    (tmp_path / "replay" / "crew-replays.source.json").write_text("{}", encoding="utf-8")
    assert cl.lint_dir(tmp_path / "content")


# --- the real Credits -------------------------------------------------------------------------

def test_real_credits_lint_clean_against_the_data_leads_records():
    records = {"crew-replays.source.json", "emergency-crew-B.source.json",
               "inspiration4-labs.source.json", "iss-cabin-dose-RR-1.source.json"}
    assert cl.lint_credits(real(), records) == []


def test_real_credits_name_everything_the_ticket_lists():
    names = " ".join(e["name"] for e in real()["entries"])
    for item in ("PMData", "Pulse", "OSDR Environmental Data App", "Inspiration4", "Apollo", "AP005",
                 "CGMacros", "UBFC-rPPG", "Z-Anatomy", "Human Reference Atlas", "StellarForge code",
                 "StellarForge 3D", "Space Apps"):
        assert item in names, item


def test_restrictive_licences_are_stated_plainly():
    doc = real()
    assert "non-commercial" in by_name(doc, "CGMacros")["restriction"].lower()
    assert "research" in by_name(doc, "UBFC-rPPG")["restriction"].lower()


def test_our_licences():
    doc = real()
    assert by_name(doc, "StellarForge code")["licence"] == "MIT"
    assert by_name(doc, "StellarForge 3D")["licence"] == "CC BY-SA 4.0"


# --- the page text (docs/credits.md) ---------------------------------------------------------

def test_page_shows_every_entry_with_link_and_licence():
    doc = real()
    text = cp.render(doc)
    for e in doc["entries"]:
        assert e["name"] in text and e["link"] in text and e["licence"] in text


def test_committed_page_matches_the_credits():
    committed = (ROOT / "docs" / "credits.md").read_text(encoding="utf-8")
    assert committed == cp.render(real()), "run: python tools/credits_page.py"
