"""Ticket 11: the write-up (docs/write-up.md) keeps the claims honest and linked.

Observable rules: every spec limitation is stated, the accuracy numbers match docs/accuracy.md,
the pages it relies on are linked, the disclaimer is there, no drug or dose, and the medical
review status is stated truthfully.
"""
import re
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
import content_lint as cl  # noqa: E402

DOC = ROOT / "docs" / "write-up.md"


def text():
    return DOC.read_text(encoding="utf-8")


# The nine limitations from Spec 5, each as phrases that must all appear.
LIMITATIONS = {
    "no hardware": ["No hardware", "simulated or replayed"],
    "no astronaut wearable stream": ["No open astronaut wearable stream", "PMData"],
    "Pulse collapse": ["Pulse", "estimate, not validated", "crew-reported"],
    "datasets not astronauts": ["measured on datasets, not on astronauts"],
    "CPR-only guidance": ["only for CPR", "partial gravity"],
    "team-value shifts": ["team value", "in-flight"],
    "Mars delay": ["28.5 min", "20 min"],
    "female layers": ["female", "approximate"],
    "laptop demo": ["laptop", "local service"],
}


@pytest.mark.parametrize("name", LIMITATIONS)
def test_states_every_spec_limitation(name):
    t = text()
    missing = [p for p in LIMITATIONS[name] if p.lower() not in t.lower()]
    assert not missing, (name, missing)


@pytest.mark.parametrize("target", ["accuracy.md", "credits.md", "hrp-risk-map.md", "medical-review.md",
                                    "media/backup-demo-2026-11-15.webm", "si-log.md"])
def test_links_the_pages_it_relies_on(target):
    assert f"]({target})" in text()


def test_states_the_disclaimer():
    assert "Decision support, not diagnosis" in text()


@pytest.mark.parametrize("number", ["0.16 per crew-day", "4.9 bpm", "1.12 points", "89.6 %"])
def test_accuracy_numbers_match_the_accuracy_page(number):
    assert number in (ROOT / "docs" / "accuracy.md").read_text(encoding="utf-8")
    assert number in text()


def test_hrp_coverage_matches_the_risk_map():
    m = re.search(r"covers (\d+) of them", (ROOT / "docs" / "hrp-risk-map.md").read_text(encoding="utf-8"))
    assert m and f"{m.group(1)} of NASA's 17" in text()


def test_medical_review_status_is_stated_truthfully():
    sheet = (ROOT / "docs" / "medical-review.md").read_text(encoding="utf-8")
    unsigned = re.search(r"^- Name:\s*$", sheet, re.M) is not None
    assert ("not clinically reviewed" in text().lower()) == unsigned


def test_no_drug_name_or_dose():
    t = text()
    assert not cl.DRUG_RE.search(t) and not cl.DOSE_RE.search(t)
