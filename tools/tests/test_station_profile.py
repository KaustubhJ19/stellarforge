"""Ticket 04 (P1): a second Mission profile, Station (ISS), so Spec 2's profile switcher has a choice.

Spec 2 reads content/profiles/*.json directly ({id, name, comm_delay{value (number), unit, status}}).
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import content_lint as cl  # noqa: E402

PROFILES = ROOT / "content" / "profiles"


def load(name):
    return json.loads((PROFILES / name).read_text(encoding="utf-8"))


def mission_profiles():
    return [load(p.name) for p in sorted(PROFILES.glob("*.json")) if p.name != cl.BOUNDS_FILE]


def test_station_profile_exists_and_lints_clean():
    station = load("station.json")
    assert station["id"] == "station" and "ISS" in station["name"]
    assert cl.lint_profile(station) == []


def test_profile_ids_are_unique_and_there_are_at_least_two():
    ids = [p["id"] for p in mission_profiles()]
    assert len(ids) >= 2 and len(ids) == len(set(ids))


def test_spec2_can_show_the_station_delay():
    delay = load("station.json")["comm_delay"]
    assert isinstance(delay["value"], (int, float)) and not isinstance(delay["value"], bool)
    assert delay["unit"].startswith("min")  # same unit as Mars, so the switcher compares like with like
    assert delay["value"] < load("mars_transit.json")["comm_delay"]["value"]


def test_station_radiation_is_sourced_and_below_mars_transit():
    rad, mars = load("station.json")["radiation_rate"], load("mars_transit.json")["radiation_rate"]
    assert rad["status"] == cl.SOURCED and rad["unit"] == mars["unit"] == "mSv/day"
    assert rad["value"] < mars["value"]


def test_station_values_that_have_a_nasa_source_are_marked_sourced():
    station = load("station.json")
    for field in ("gravity", "radiation_rate", "comm_delay", "evacuation", "exercise_kit", "crew_size",
                  "duration", "closed_habitat"):
        assert station[field]["status"] == cl.SOURCED, field
        assert "nasa.gov" in station[field]["source"], field
