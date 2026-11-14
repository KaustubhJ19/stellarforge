"""Ticket 04 (Spec 1 task 1.4): replay generator, 4 synthetic crew from PMData.

Spec: 4 synthetic crew from PMData normal days, about 5 months each, one planted drift
(crew A: resting HR up about 6 bpm and sleep down about 1.5 h over 9 days), Anchor from the
first weeks; crew B collapses; record sex per crew; lead Mission profile Mars transit.
Tests (a) every replay validates; (b) a replay generated twice from one seed is identical.
"""
import csv
import datetime
import json
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT / "contracts"))

import crew_replays as cr  # noqa: E402
from validate import validate  # noqa: E402

REAL = ROOT / "data" / "pmdata"
DAY = 86400


def write_person(root, pid, days, rhr=60.0, sleep_min=420, start=1, wellness=True, steps=True, zero_rhr_day=None):
    """Write a tiny PMData-format participant folder (test data, real file layout)."""
    fit = root / pid / "fitbit"
    sys_ = root / pid / "pmsys"
    fit.mkdir(parents=True)
    sys_.mkdir(parents=True)
    first = datetime.date(2019, 11, start)
    dates = [(first + datetime.timedelta(days=i)).isoformat() for i in range(days)]
    (fit / "resting_heart_rate.json").write_text(json.dumps([
        {"dateTime": f"{d} 00:00:00",
         "value": {"date": "x", "value": 0 if i == zero_rhr_day else rhr + i, "error": 6.7}}
        for i, d in enumerate(dates)]), encoding="utf-8")
    sleep = []
    for i, d in enumerate(dates):
        sleep.append({"dateOfSleep": d, "minutesAsleep": sleep_min + i, "mainSleep": True})
        sleep.append({"dateOfSleep": d, "minutesAsleep": 30, "mainSleep": False})  # nap: not counted
    (fit / "sleep.json").write_text(json.dumps(sleep), encoding="utf-8")
    if steps:
        (fit / "steps.json").write_text(json.dumps(
            [{"dateTime": f"{d} 0{h}:00:00", "value": str(100 * (h + 1))} for d in dates for h in range(3)]),
            encoding="utf-8")
    with open(fit / "sleep_score.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["timestamp", "sleep_log_entry_id", "overall_score", "composition_score", "revitalization_score",
                    "duration_score", "deep_sleep_in_minutes", "resting_heart_rate", "restlessness"])
        for i, d in enumerate(dates):
            w.writerow([f"{d}T06:00:00Z", i, 70 + i, 1, 1, 1, 1, 1, 0.1])
    if wellness:
        with open(sys_ / "wellness.csv", "w", newline="", encoding="utf-8") as f:
            w = csv.writer(f)
            w.writerow(["effective_time_frame", "fatigue", "mood", "readiness", "sleep_duration_h", "sleep_quality",
                        "soreness", "soreness_area", "stress"])
            for i, d in enumerate(dates):
                w.writerow([f"{d}T08:30:00.000Z", 3, 3, 7, 7, 3, 2, "[1]", 2 + i % 2])


@pytest.fixture
def pm(tmp_path):
    root = tmp_path / "pmdata"
    write_person(root, "p01", 40)
    write_person(root, "p02", 40, rhr=50)
    write_person(root, "p03", 30, rhr=55)          # shorter
    write_person(root, "p04", 40, rhr=65, wellness=False)  # no wellness: less complete
    write_person(root, "p05", 40, rhr=70)
    return root


# ---- reading PMData --------------------------------------------------------------------

def test_reads_daily_indicators_from_the_pmdata_files(pm):
    daily = cr.read_person(pm / "p01")
    day = daily["2019-11-03"]
    assert day["resting_heart_rate"] == 62.0
    assert day["sleep_duration"] == 422          # main sleep only, minutes
    assert day["steps"] == 600                   # per-minute steps summed per day
    assert day["sleep_score"] == 72
    assert (day["fatigue"], day["mood"], day["readiness"], day["sleep_quality"], day["stress"]) == (3, 3, 7, 3, 2)
    assert day["soreness"] == 2  # PMData wellness soreness, 1-5 (Spec 3 request 2026-11-15)


def test_zero_resting_heart_rate_means_no_reading(tmp_path):
    write_person(tmp_path, "p09", 5, zero_rhr_day=2)
    daily = cr.read_person(tmp_path / "p09")
    assert "resting_heart_rate" not in daily["2019-11-03"]


def test_missing_steps_file_is_allowed(tmp_path):
    write_person(tmp_path, "p09", 5, steps=False)
    assert all("steps" not in d for d in cr.read_person(tmp_path / "p09").values())


def test_chooses_people_by_resting_heart_rate_then_sleep_coverage(pm):
    chosen = cr.choose_people(pm, n=4)
    assert chosen == ["p01", "p02", "p04", "p05"]  # 40 days each (ties keep id order); p03 has 30


def test_lots_of_wellness_entries_cannot_make_up_for_missing_resting_heart_rate(tmp_path):
    write_person(tmp_path, "p01", 40)
    write_person(tmp_path, "p02", 40)
    write_person(tmp_path, "p03", 40)
    write_person(tmp_path, "p04", 30)
    rhr = tmp_path / "p02" / "fitbit" / "resting_heart_rate.json"
    rhr.write_text(json.dumps(json.loads(rhr.read_text())[:5]))  # p02: only 5 days of resting HR
    assert cr.choose_people(tmp_path, n=3) == ["p01", "p03", "p04"]


def test_crew_assignment_is_seeded_and_deterministic():
    people = ["p01", "p02", "p04", "p05"]
    assert cr.assign_crew(people, seed=1) == cr.assign_crew(people, seed=1)
    assert sorted(cr.assign_crew(people, seed=1)) == ["A", "B", "C", "D"]
    assert sorted(cr.assign_crew(people, seed=1).values()) == sorted(people)


# ---- replays ----------------------------------------------------------------------

def build(pm, seed=1, **kw):
    return cr.build_all(pm, seed=seed, sexes={"p01": "male", "p02": "female", "p03": "male", "p04": "female",
                                              "p05": "female"}, **kw)


def test_a_every_crew_replay_validates_and_readings_are_valid(pm):
    out = build(pm)
    assert sorted(out["replays"]) == ["A", "B", "C", "D"]
    for crew, replay in out["replays"].items():
        validate("ReplayFile", replay)
        assert replay["crew"] == crew and replay["profile"] == "mars_transit"
        for e in replay["events"]:
            assert e["type"] == "reading"
            validate("Reading", {"schema_version": replay["schema_version"], **e["payload"]})


def test_b_same_seed_gives_identical_output(pm):
    assert json.dumps(build(pm, seed=7)) == json.dumps(build(pm, seed=7))


def test_t_is_mission_seconds_from_the_common_start_at_0700(pm):
    out = build(pm)
    person = out["mapping"]["C"]
    first_day = min(cr.read_person(pm / person))
    offset_days = (cr.parse_date(first_day) - cr.parse_date(out["start_date"])).days
    first = out["replays"]["C"]["events"][0]
    assert first["t"] == offset_days * DAY + 7 * 3600


def test_units_and_sources(pm):
    payloads = [e["payload"] for r in build(pm)["replays"].values() for e in r["events"]]
    units = {p["indicator"]: p["unit"] for p in payloads}
    assert units == {"resting_heart_rate": "bpm", "sleep_duration": "min", "steps": "steps", "sleep_score": "score 0-100",
                     "fatigue": "score 1-5", "mood": "score 1-5", "readiness": "score 0-10",
                     "sleep_quality": "score 1-5", "stress": "score 1-5", "soreness": "score 1-5"}
    sources = {p["indicator"]: p["source"] for p in payloads}
    assert sources["resting_heart_rate"] == "sensor" and sources["fatigue"] == "manual"
    assert all(p["state"] == "released" for p in payloads)


def test_values_are_copied_unchanged_for_crew_without_drift(pm):
    out = build(pm)
    person = out["mapping"]["C"]
    daily = cr.read_person(pm / person)
    got = {(p["indicator"], p["t"]): p["value"] for p in (e["payload"] for e in out["replays"]["C"]["events"])}
    start = cr.parse_date(out["start_date"])
    for date, values in daily.items():
        t = (cr.parse_date(date) - start).days * DAY + 7 * 3600
        for ind, v in values.items():
            assert got[(ind, t)] == v


# ---- planted drift (crew A) ------------------------------------------------------------

def test_crew_a_gets_the_planted_drift_over_the_last_9_days(pm):
    out = build(pm)
    person = out["mapping"]["A"]
    daily = cr.read_person(pm / person)
    dates = sorted(d for d in daily if "resting_heart_rate" in daily[d])
    events = [e["payload"] for e in out["replays"]["A"]["events"]]
    start = cr.parse_date(out["start_date"])
    t_of = lambda d: (cr.parse_date(d) - start).days * DAY + 7 * 3600
    rhr = {p["t"]: p for p in events if p["indicator"] == "resting_heart_rate"}
    sleep = {p["t"]: p for p in events if p["indicator"] == "sleep_duration"}
    last = dates[-1]
    assert rhr[t_of(last)]["value"] == pytest.approx(daily[last]["resting_heart_rate"] + 6)
    assert sleep[t_of(last)]["value"] == pytest.approx(daily[last]["sleep_duration"] - 90)
    assert rhr[t_of(last)]["source"] == "sim"  # planted values are marked as simulated
    before = dates[-10]
    assert rhr[t_of(before)]["value"] == daily[before]["resting_heart_rate"]
    assert rhr[t_of(before)]["source"] == "sensor"
    # rises step by step across the 9 days
    planted = [rhr[t_of(d)]["value"] - daily[d]["resting_heart_rate"] for d in dates[-9:]]
    assert planted == sorted(planted) and planted[0] > 0


def test_planted_sleep_never_goes_below_zero(tmp_path):
    for pid in ("p01", "p02", "p03", "p04"):
        write_person(tmp_path, pid, 40, sleep_min=20)  # very short main sleeps (tracking gaps happen)
    out = cr.build_all(tmp_path, seed=1, sexes={p: "male" for p in ("p01", "p02", "p03", "p04")})
    sleep = [e["payload"]["value"] for e in out["replays"]["A"]["events"] if e["payload"]["indicator"] == "sleep_duration"]
    assert min(sleep) >= 0


def test_only_crew_a_has_planted_values(pm):
    out = build(pm)
    for crew in "BCD":
        assert all(e["payload"]["source"] != "sim" for e in out["replays"][crew]["events"])


# ---- crew records -------------------------------------------------------------------

def test_crew_records_are_valid_with_sex_and_anchor_from_the_first_14_days(pm):
    out = build(pm)
    records = {r["id"]: r for r in out["crew_records"]}
    assert sorted(records) == ["A", "B", "C", "D"]
    for crew, rec in records.items():
        validate("CrewRecord", {"schema_version": "1.0.0", **rec} if "schema_version" not in rec else rec)
        assert rec["missionProfile"] == "mars_transit"
        assert rec["sex"] in ("male", "female")
    person = out["mapping"]["C"]
    daily = cr.read_person(pm / person)
    first14 = [daily[d]["resting_heart_rate"] for d in sorted(daily)[:14]]
    anchor = records["C"]["anchor"]["resting_heart_rate"]
    assert anchor["mean"] == pytest.approx(sum(first14) / 14)
    assert anchor["sd"] > 0


def test_source_record_names_the_dataset_licence_and_planted_drift(pm):
    rec = build(pm)["source"]
    assert "PMData" in rec["dataset"] and rec["licence"] == "CC BY 4.0"
    assert "10.1145/3339825.3394926" in rec["citation"]
    assert rec["planted_drift"]["crew"] == "A" and rec["planted_drift"]["days"] == 9
    assert rec["seed"] == 1 and sorted(rec["mapping"]) == ["A", "B", "C", "D"]
    assert any("team value" in n for n in rec["notes"])


def test_command_line_writes_replays_records_and_source(pm, tmp_path):
    out = tmp_path / "out"
    result = subprocess.run([sys.executable, str(ROOT / "tools" / "crew_replays.py"), "--pmdata", str(pm),
                             "--out-dir", str(out), "--sex", "p01=male,p02=female,p03=male,p04=female,p05=female"],
                            capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    for crew in "ABCD":
        validate("ReplayFile", json.loads((out / f"crew-{crew}.json").read_text(encoding="utf-8")))
    records = json.loads((out / "crew-records.json").read_text(encoding="utf-8"))
    for r in records:
        validate("CrewRecord", r)
    assert json.loads((out / "crew-replays.source.json").read_text(encoding="utf-8"))["licence"] == "CC BY 4.0"


def test_reads_sex_from_the_participant_overview_spreadsheet(tmp_path):
    import zipfile
    path = tmp_path / "participant-overview.xlsx"
    shared = ('<sst xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
              '<si><t>Participant ID</t></si><si><t>Gender</t></si><si><t>p01</t></si><si><t>male</t></si>'
              '<si><t>p04</t></si><si><t>female</t></si></sst>')
    row = lambda r, a, b: f'<row r="{r}"><c t="s"><v>{a}</v></c><c t="s"><v>{b}</v></c></row>'
    sheet = ('<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main"><sheetData>'
             + row(1, 0, 1) + row(2, 2, 3) + row(3, 4, 5) + '</sheetData></worksheet>')
    with zipfile.ZipFile(path, "w") as z:
        z.writestr("xl/sharedStrings.xml", shared)
        z.writestr("xl/worksheets/sheet1.xml", sheet)
    assert cr.read_overview_sexes(path) == {"p01": "male", "p04": "female"}


def test_missing_sex_fails_loudly_instead_of_guessing(pm):
    with pytest.raises(ValueError):
        cr.build_all(pm, seed=1, sexes={})


@pytest.mark.skipif(not (REAL / "p01" / "fitbit" / "resting_heart_rate.json").exists(), reason="PMData not downloaded")
def test_real_pmdata_gives_about_five_months_per_crew():
    people = sorted(p.name for p in REAL.iterdir() if p.is_dir() and (p / "fitbit" / "resting_heart_rate.json").exists())
    sexes = {p: "male" for p in people}
    out = cr.build_all(REAL, seed=1, sexes=sexes)
    for crew, replay in out["replays"].items():
        validate("ReplayFile", replay)
        days = {e["t"] // DAY for e in replay["events"]}
        assert len(days) >= 120, (crew, len(days))
