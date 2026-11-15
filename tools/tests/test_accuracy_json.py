"""content/accuracy.json (shown in the app) must not drift from docs/accuracy.md (the write-up)."""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DATA = json.loads((ROOT / "content" / "accuracy.json").read_text(encoding="utf-8"))
DOC = (ROOT / "docs" / "accuracy.md").read_text(encoding="utf-8")


def numbers(text):
    return set(re.findall(r"\d+(?:\.\d+)?", text))


def test_every_result_has_the_fields_the_page_shows():
    assert len(DATA["results"]) >= 5
    for row in DATA["results"]:
        assert {"what", "result", "measured_on", "rerun"} <= set(row)
        assert all(str(row[k]).strip() for k in row)


def test_every_number_in_the_page_is_in_the_write_up():
    missing = {n for row in DATA["results"] for n in numbers(row["result"])} - numbers(DOC)
    assert missing == set()


def test_every_limit_is_a_limit_in_the_write_up():
    flat = re.sub(r"\s+", " ", DOC)
    for limit in DATA["limits"]:
        assert limit in flat, f"limit not in docs/accuracy.md: {limit[:60]}"


def test_page_says_it_is_not_measured_on_astronauts():
    assert any("not on astronauts" in lim.lower() for lim in DATA["limits"])
