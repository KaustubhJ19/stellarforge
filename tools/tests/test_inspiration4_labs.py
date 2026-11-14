"""Ticket 07 (Spec 1 task 1.7): a few Inspiration4 blood values as source = lab Readings.

User story 15: lab-entry cards show real astronaut data. Source: NASA OSDR OSD-569,
LSDS-7 Complete Blood Count (processed, public).
"""
import csv
import io
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "contracts"))

import inspiration4_labs as i4  # noqa: E402
from validate import validate  # noqa: E402

REAL = ROOT / "data" / "inspiration4" / "LSDS-7_Complete_Blood_Count_CBC.upload_SUBMITTED.csv"
DAY = 86400
HEADER = ["ANALYTE", "VALUE", "RANGE_MIN", "RANGE_MAX", "UNITS", "TEST_TYPE", "SUBJECT_ID", "SEX", "TEST_DATE"]
ROWS = [
    ["HEMOGLOBIN", "14.1", "13.2", "17.1", "g/dL", "CBC", "C001", "M", "L-92"],
    ["HEMOGLOBIN", "14.9", "13.2", "17.1", "g/dL", "CBC", "C001", "M", "L-3"],
    ["HEMOGLOBIN", "15.2", "13.2", "17.1", "g/dL", "CBC", "C001", "M", "R+1"],
    ["MCV", "92.8", "80", "100", "fL", "CBC", "C001", "M", "L-92"],  # not one of the chosen few
    ["WHITE BLOOD CELL COUNT", "5.4", "3.8", "10.8", "Thousand/uL", "CBC", "C001", "M", "L-92"],
    ["HEMOGLOBIN (FEMALE)", "12.9", "11.7", "15.5", "g/dL", "CBC", "C002", "F", "L-92"],
    ["PLATELET COUNT", "241", "140", "400", "Thousand/uL", "CBC", "C002", "F", "R+45"],
]


def csv_text(rows=ROWS):
    out = io.StringIO()
    w = csv.writer(out)
    w.writerow(HEADER)
    w.writerows(rows)
    return "﻿" + out.getvalue()  # the real file starts with a BOM


@pytest.fixture
def rows():
    return i4.read_rows(csv_text())


def payloads(replay):
    return [e["payload"] for e in replay["events"]]


def test_days_from_launch_for_l_and_r_timepoints():
    assert i4.days_from_launch("L-92") == -92
    assert i4.days_from_launch("L-3") == -3
    assert i4.days_from_launch("R+1") == 3 + 1  # Inspiration4 flew 3 days; R+1 is one day after return
    with pytest.raises(ValueError):
        i4.days_from_launch("FD2")


def test_one_replay_per_subject_with_only_the_chosen_analytes(rows):
    replays = i4.build_replays(rows)
    assert sorted(replays) == ["I4-C001", "I4-C002"]
    indicators = {p["indicator"] for r in replays.values() for p in payloads(r)}
    assert indicators == {"hemoglobin", "white_blood_cell_count", "platelet_count"}  # MCV not chosen
    assert i4.ANALYTES == ("WHITE BLOOD CELL COUNT", "RED BLOOD CELL COUNT", "HEMOGLOBIN", "HEMATOCRIT",
                           "PLATELET COUNT")


def test_every_replay_validates_and_every_payload_is_a_lab_reading(rows):
    for replay in i4.build_replays(rows).values():
        validate("ReplayFile", replay)
        for p in payloads(replay):
            validate("Reading", {"schema_version": replay["schema_version"], **p})
            assert p["source"] == "lab" and p["state"] == "released"


def test_values_and_units_are_copied_unchanged(rows):
    got = {(p["crew"], p["indicator"], p["t"]): (p["value"], p["unit"])
           for r in i4.build_replays(rows).values() for p in payloads(r)}
    assert got[("I4-C001", "hemoglobin", 7 * 3600)] == (14.1, "g/dL")
    assert got[("I4-C001", "white_blood_cell_count", 7 * 3600)] == (5.4, "Thousand/uL")
    assert got[("I4-C002", "platelet_count", (92 + 3 + 45) * DAY + 7 * 3600)] == (241, "Thousand/uL")


def test_female_analyte_rows_map_to_the_same_indicator(rows):
    c002 = payloads(i4.build_replays(rows)["I4-C002"])
    assert [p["value"] for p in c002 if p["indicator"] == "hemoglobin"] == [12.9]


def test_t_starts_at_the_earliest_sample_at_0700_and_offset_shifts_it(rows):
    hb = [p["t"] for p in payloads(i4.build_replays(rows)["I4-C001"]) if p["indicator"] == "hemoglobin"]
    assert hb == [7 * 3600, (92 - 3) * DAY + 7 * 3600, (92 + 4) * DAY + 7 * 3600]
    shifted = [p["t"] for p in payloads(i4.build_replays(rows, offset=1000)["I4-C001"]) if p["indicator"] == "hemoglobin"]
    assert shifted == [t + 1000 for t in hb]


def test_events_are_ordered_and_deterministic(rows):
    for replay in i4.build_replays(rows).values():
        times = [e["t"] for e in replay["events"]]
        assert times == sorted(times)
    assert json.dumps(i4.build_replays(rows)) == json.dumps(i4.build_replays(rows))


def test_subjects_can_be_mapped_to_crew_ids(rows):
    replays = i4.build_replays(rows, crew_map={"C001": "B"})
    assert sorted(replays) == ["B", "I4-C002"]
    assert all(p["crew"] == "B" for p in payloads(replays["B"]))


def test_reference_ranges_are_kept_in_the_source_record(rows):
    rec = i4.source_record(rows, raw_bytes=b"abc", downloaded="2026-11-14")
    assert rec["reference_ranges"]["hemoglobin"] == {
        "M": [{"min": 13.2, "max": 17.1, "unit": "g/dL", "rows": 3}],
        "F": [{"min": 11.7, "max": 15.5, "unit": "g/dL", "rows": 1}]}
    assert rec["range_inconsistencies"] == []
    assert rec["study"] == "OSD-569" and "LSDS-7" in rec["file"]
    assert rec["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert rec["launch_day_mapping"]["R+n"] == "3 + n days after launch"
    assert any("Earth clinical reference" in n for n in rec["notes"])


def test_different_ranges_for_one_sex_are_all_kept_and_flagged():
    rows = i4.read_rows(csv_text(ROWS + [["HEMOGLOBIN", "13.0", "13.2", "17.1", "g/dL", "CBC", "C003", "F", "R+1"]]))
    rec = i4.source_record(rows, raw_bytes=b"", downloaded="x")
    assert rec["reference_ranges"]["hemoglobin"]["F"] == [
        {"min": 11.7, "max": 15.5, "unit": "g/dL", "rows": 1},
        {"min": 13.2, "max": 17.1, "unit": "g/dL", "rows": 1}]
    assert rec["range_inconsistencies"] == ["hemoglobin F: 2 different reference ranges in the source file"]


def test_non_numeric_value_fails_loudly():
    with pytest.raises(ValueError):
        i4.build_replays(i4.read_rows(csv_text([["HEMOGLOBIN", "n/a", "13", "17", "g/dL", "CBC", "C001", "M", "L-3"]])))


def test_command_line_writes_replays_and_source(tmp_path):
    src = tmp_path / "cbc.csv"
    src.write_text(csv_text(), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "inspiration4_labs.py"), "--input", str(src),
                             "--out-dir", str(out), "--downloaded", "2026-11-14"], capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for crew in ("I4-C001", "I4-C002"):
        validate("ReplayFile", json.loads((out / f"inspiration4-labs-{crew}.json").read_text(encoding="utf-8")))
    rec = json.loads((out / "inspiration4-labs.source.json").read_text(encoding="utf-8"))
    assert rec["readings"] == 6


@pytest.mark.skipif(not REAL.exists(), reason="Inspiration4 CBC file not downloaded (data/ is git-ignored)")
def test_real_osd569_file():
    rows = i4.read_rows(REAL.read_text(encoding="utf-8-sig"))
    replays = i4.build_replays(rows)
    assert sorted(replays) == ["I4-C001", "I4-C002", "I4-C003", "I4-C004"]
    for replay in replays.values():
        validate("ReplayFile", replay)
    first = {p["indicator"]: p["value"] for p in payloads(replays["I4-C001"]) if p["t"] == 7 * 3600}
    assert first == {"white_blood_cell_count": 5.4, "red_blood_cell_count": 4.58, "hemoglobin": 14.1,
                     "hematocrit": 42.5, "platelet_count": 241}
