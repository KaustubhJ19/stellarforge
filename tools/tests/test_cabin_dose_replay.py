"""Ticket 06 (Spec 1 task 1.6): cabin and dose replay from the OSDR Environmental Data App.

User stories 13 (ISS cabin temperature, CO2, humidity in a replay) and 14 (ISS radiation dose).
Test (a): the replay validates against its schema.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "contracts"))

from cabin_dose_replay import INDICATORS, build_replay, parse_dashboard, source_record  # noqa: E402
from validate import validate  # noqa: E402

REAL = ROOT / "data" / "osdr-eda" / "dashboard_RR-1.html"


def dashboard_html(telemetry, radiation, mission="RR-X"):
    data = {"telemetry_data": json.dumps(telemetry), "radiation_data": json.dumps(radiation),
            "mission": mission, "mission_title": "Test mission", "mission_link": "https://example.invalid/m"}
    return f'<html><body><script type="application/json" id="data">{json.dumps(data)}</script></body></html>'


TELEMETRY = {
    "time": ["2014-09-20 03:59:00", "2014-09-20 04:04:00"],
    "temperature_iss": [24.1, 24.2], "rh_iss": [39, 40], "co2_iss": [2641, 2650],
    "temperature_ground": [1, 1], "rh_ground": [1, 1], "co2_ground": [1, 1], "milestones": {},
}
RADIATION = {
    "time": ["2014-09-21"], "gcr": [0.13], "saa": [0.07], "total": [0.2], "accumulated": [0.2], "milestones": {},
}


@pytest.fixture
def data():
    return parse_dashboard(dashboard_html(TELEMETRY, RADIATION))


def readings(replay):
    return [e["payload"] for e in replay["events"]]


def test_parse_dashboard_reads_the_embedded_data(data):
    assert data["mission"] == "RR-X"
    assert data["telemetry"]["co2_iss"] == [2641, 2650]
    assert data["radiation"]["gcr"] == [0.13]


def test_parse_dashboard_without_data_block_fails_loudly():
    with pytest.raises(ValueError):
        parse_dashboard("<html></html>")


def test_a_replay_validates_and_every_reading_payload_is_a_valid_reading(data):
    replay = build_replay(data)
    validate("ReplayFile", replay)
    for payload in readings(replay):
        validate("Reading", {"schema_version": replay["schema_version"], **payload})
    assert all(e["type"] == "reading" for e in replay["events"])


def test_cabin_and_dose_indicators_with_units_from_the_eda_charts():
    assert INDICATORS == {
        "temperature_iss": ("cabin_temperature", "degC"),
        "rh_iss": ("cabin_relative_humidity", "%"),
        "co2_iss": ("cabin_co2", "ppm"),
        "gcr": ("radiation_dose_gcr", "mGy/day"),
        "saa": ("radiation_dose_saa", "mGy/day"),
        "total": ("radiation_dose_total", "mGy/day"),
        "accumulated": ("radiation_dose_accumulated", "mGy"),
    }


def test_values_are_copied_unchanged(data):
    got = {(r["indicator"], r["t"]): r["value"] for r in readings(build_replay(data))}
    assert got[("cabin_co2", 0)] == 2641
    assert got[("cabin_temperature", 300)] == 24.2
    assert got[("radiation_dose_gcr", 72060)] == 0.13  # 2014-09-21 00:00 is 20 h 01 min after the first sample


def test_t_is_seconds_since_the_first_telemetry_sample(data):
    times = sorted({r["t"] for r in readings(build_replay(data)) if r["indicator"] == "cabin_co2"})
    assert times == [0, 300]


def test_ground_control_series_are_not_included(data):
    assert all(r["value"] != 1 for r in readings(build_replay(data)))
    original = [r for r in readings(build_replay(data)) if not r["indicator"].startswith("cabin_pco2")]
    assert len(original) == 2 * 3 + 1 * 4


# ---- derived CO2 partial pressure (NASA-STD-3001 V2 6004 limits the 1-h average ppCO2 to 3 mmHg) ----

def co2_series(values, start="2014-09-20 00:00:00", step_min=5, times=None):
    import datetime as dt
    t0 = dt.datetime.fromisoformat(start)
    stamps = times or [(t0 + dt.timedelta(minutes=step_min * i)).strftime("%Y-%m-%d %H:%M:%S") for i in range(len(values))]
    n = len(values)
    return parse_dashboard(dashboard_html(
        {"time": stamps, "temperature_iss": [None] * n, "rh_iss": [None] * n, "co2_iss": values, "milestones": {}},
        {"time": [], "gcr": [], "saa": [], "total": [], "accumulated": [], "milestones": {}}))


def series(replay, indicator):
    return [(r["t"], r["value"]) for r in readings(replay) if r["indicator"] == indicator]


def test_pco2_is_ppm_times_iss_nominal_pressure(data):
    pco2 = series(build_replay(data), "cabin_pco2")
    assert pco2 == [(0, round(2641 * 760 / 1e6, 4)), (300, round(2650 * 760 / 1e6, 4))]
    r = next(r for r in readings(build_replay(data)) if r["indicator"] == "cabin_pco2")
    assert r["unit"] == "mmHg" and r["source"] == "sensor"


def test_one_hour_average_needs_at_least_9_of_12_samples():
    replay = build_replay(co2_series([3947] * 12))  # 3947 ppm at 760 mmHg = 3.0 mmHg
    avg = series(replay, "cabin_pco2_1h")
    assert [t for t, _ in avg] == [8 * 300, 9 * 300, 10 * 300, 11 * 300]  # from the 9th sample on
    assert all(v == pytest.approx(3947 * 760 / 1e6, abs=1e-4) for _, v in avg)


def test_one_hour_average_is_a_trailing_window():
    replay = build_replay(co2_series([2000] * 12 + [4000] * 12))
    avg = dict(series(replay, "cabin_pco2_1h"))
    assert avg[23 * 300] == pytest.approx(4000 * 760 / 1e6, abs=1e-4)   # only the last hour counts
    assert avg[17 * 300] == pytest.approx((6 * 2000 + 6 * 4000) / 12 * 760 / 1e6, abs=1e-4)


def test_a_gap_suppresses_the_one_hour_average_instead_of_faking_it():
    import datetime as dt
    t0 = dt.datetime(2014, 9, 20)
    minutes = [5 * i for i in range(12)] + [60 + 40 + 5 * i for i in range(12)]  # 40-min gap after the first hour
    times = [(t0 + dt.timedelta(minutes=m)).strftime("%Y-%m-%d %H:%M:%S") for m in minutes]
    replay = build_replay(co2_series([3000] * 24, times=times))
    avg_t = {t for t, _ in series(replay, "cabin_pco2_1h")}
    assert 105 * 60 not in avg_t           # just after the gap: too few samples in the last hour
    assert (60 + 40 + 55) * 60 in avg_t    # a full hour after the gap again


def test_missing_co2_gives_no_pco2():
    replay = build_replay(co2_series([None, 2650]))
    assert [t for t, _ in series(replay, "cabin_pco2")] == [300]


def test_source_record_documents_the_pressure_assumption(data):
    rec = source_record(data, raw_bytes=b"", url="u", downloaded="d")
    d = rec["derived"]
    assert d["pressure_mmHg"] == 760 and d["pressure_psia"] == 14.7
    assert d["window_s"] == 3600 and d["min_samples"] == 9
    assert "V2 6004" in d["limit_reference"]
    assert rec["units"]["cabin_pco2"] == "mmHg" and rec["units"]["cabin_pco2_1h"] == "mmHg"
    assert any("not the mission profile" in n for n in rec["notes"])


def test_missing_values_are_skipped_not_filled():
    tel = dict(TELEMETRY, co2_iss=[None, 2650])
    replay = build_replay(parse_dashboard(dashboard_html(tel, RADIATION)))
    co2 = [r for r in readings(replay) if r["indicator"] == "cabin_co2"]
    assert [r["value"] for r in co2] == [2650]


def test_events_are_ordered_by_t_and_match_their_payload_time(data):
    events = build_replay(data)["events"]
    assert [e["t"] for e in events] == sorted(e["t"] for e in events)
    assert all(e["t"] == e["payload"]["t"] for e in events)


def test_reading_fields(data):
    r = readings(build_replay(data, crew="habitat"))[0]
    assert r["crew"] == "habitat" and r["source"] == "sensor" and r["state"] == "released"


def test_crew_profile_and_offset_are_settable(data):
    replay = build_replay(data, crew="cabin", profile="iss", offset=1000)
    assert replay["crew"] == "cabin" and replay["profile"] == "iss"
    assert replay["events"][0]["t"] == 1000


def test_same_input_gives_identical_output(data):
    assert json.dumps(build_replay(data)) == json.dumps(build_replay(data))


def test_source_record_keeps_traceability(data):
    rec = source_record(data, raw_bytes=b"abc", url="https://visualization.osdr.nasa.gov/eda/dashboard_RR-X",
                        downloaded="2026-11-14")
    assert rec["dataset"] == "NASA OSDR Environmental Data App (EDA)"
    assert rec["mission"] == "RR-X" and rec["url"].endswith("dashboard_RR-X")
    assert rec["downloaded"] == "2026-11-14"
    assert rec["sha256"] == "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410ff61f20015ad"
    assert rec["t0_utc"] == "2014-09-20 03:59:00"
    assert rec["units"]["cabin_co2"] == "ppm"
    assert "visualization" in rec["citation"].lower()


def test_command_line_writes_replay_and_source_record(tmp_path):
    raw = tmp_path / "dashboard_RR-X.html"
    raw.write_text(dashboard_html(TELEMETRY, RADIATION), encoding="utf-8")
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "cabin_dose_replay.py"),
                             "--input", str(raw), "--out-dir", str(out), "--downloaded", "2026-11-14"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    replay = json.loads((out / "iss-cabin-dose-RR-X.json").read_text(encoding="utf-8"))
    validate("ReplayFile", replay)
    rec = json.loads((out / "iss-cabin-dose-RR-X.source.json").read_text(encoding="utf-8"))
    assert rec["readings"] == len(replay["events"]) == 10 + 2  # + one cabin_pco2 per CO2 sample (no 1-h yet)


@pytest.mark.skipif(not REAL.exists(), reason="real EDA download not present (data/ is git-ignored)")
def test_real_rr1_download_builds_a_valid_complete_replay():
    data = parse_dashboard(REAL.read_text(encoding="utf-8"))
    replay = build_replay(data)
    validate("ReplayFile", replay)
    by = {}
    for r in readings(replay):
        by.setdefault(r["indicator"], []).append(r)
    assert sum(len(v) for k, v in by.items() if not k.startswith("cabin_pco2")) == 12087 * 3 + 39 * 4
    assert len(by["cabin_pco2"]) == 12087
    # 1-h averages exist only where the window holds 9+ of 12 samples (the data has two long gaps)
    assert 12000 < len(by["cabin_pco2_1h"]) < 12087
    over = sum(r["value"] > 3.0 for r in by["cabin_pco2_1h"])
    assert 0.08 < over / len(by["cabin_pco2_1h"]) < 0.10  # about 9.2% at ISS nominal 14.7 psia
    first = {r["indicator"]: r["value"] for r in readings(replay) if r["t"] == 0}
    assert first == {"cabin_temperature": 24.1, "cabin_relative_humidity": 39, "cabin_co2": 2641,
                     "cabin_pco2": round(2641 * 760 / 1e6, 4)}
