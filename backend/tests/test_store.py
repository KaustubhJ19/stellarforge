"""Ticket 08 (Spec 1 task 1.9): SQLite store.

Spec: SQLite store: Reading, Alert, Label, Event store, Ground report, Access log;
indexed by crew, indicator, time.
"""
import json
import sqlite3
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "backend"))
sys.path.insert(0, str(ROOT / "contracts"))

from store import KINDS, Store  # noqa: E402
from validate import ContractError  # noqa: E402

EXAMPLES = ROOT / "contracts" / "examples"


def example(name, **changes):
    doc = json.loads((EXAMPLES / f"{name}.example.json").read_text(encoding="utf-8"))
    doc.update(changes)
    return doc


@pytest.fixture
def store(tmp_path):
    s = Store(tmp_path / "habitat.sqlite")
    yield s
    s.close()


def test_has_the_six_spec_stores():
    spec1 = {"reading", "alert", "label", "event", "ground_report", "access_log"}
    assert spec1 <= set(KINDS)
    assert set(KINDS) - spec1 == {"form", "location"}  # Spec 2 provisional shapes, add-only


def test_creates_one_table_per_store(store):
    tables = {r[0] for r in store.conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert set(KINDS) <= tables


@pytest.mark.parametrize("kind", ["reading", "alert", "label", "event"])
def test_crew_indicator_time_index_exists(store, kind):
    cols = _indexed_columns(store, kind)
    assert ["crew", "indicator", "t"] in cols


@pytest.mark.parametrize("kind", ["ground_report", "access_log"])
def test_crew_time_index_exists_for_stores_without_indicator(store, kind):
    assert ["crew", "t"] in _indexed_columns(store, kind)


def _indexed_columns(store, table):
    out = []
    for idx in store.conn.execute(f"PRAGMA index_list({table})"):
        out.append([c[2] for c in store.conn.execute(f"PRAGMA index_info({idx[1]})")])
    return out


def test_crew_indicator_time_query_uses_the_index(store):
    plan = store.conn.execute(
        "EXPLAIN QUERY PLAN SELECT doc FROM reading WHERE crew=? AND indicator=? AND t BETWEEN ? AND ?",
        ("A", "hr", 0, 10),
    ).fetchall()
    assert "USING INDEX" in " ".join(str(r) for r in plan)


def test_reading_round_trip(store):
    doc = example("Reading")
    store.add("reading", doc)
    assert store.query("reading") == [doc]


def test_query_filters_by_crew_indicator_and_time_and_orders_by_t(store):
    store.add("reading", example("Reading", crew="A", indicator="hr", t=30))
    store.add("reading", example("Reading", crew="A", indicator="hr", t=10))
    store.add("reading", example("Reading", crew="A", indicator="sleep", t=20))
    store.add("reading", example("Reading", crew="B", indicator="hr", t=15))
    got = store.query("reading", crew="A", indicator="hr")
    assert [d["t"] for d in got] == [10, 30]
    got = store.query("reading", crew="A", t_from=15, t_to=25)
    assert [d["t"] for d in got] == [20]
    assert [d["t"] for d in store.query("reading")] == [10, 15, 20, 30]


def test_invalid_reading_is_rejected_and_not_written(store):
    with pytest.raises(ContractError):
        store.add("reading", example("Reading", confidence=5))
    assert store.query("reading") == []


def test_alert_is_validated_and_stored(store):
    store.add("alert", example("Alert"))
    assert store.query("alert", crew="A") == [example("Alert")]
    with pytest.raises(ContractError):
        store.add("alert", example("Alert", urgency="SOON"))


def test_ground_report_is_validated_and_indexed_by_sent_t(store):
    store.add("ground_report", example("GroundReport", sent_t=50))
    store.add("ground_report", example("GroundReport", sent_t=20))
    assert [d["sent_t"] for d in store.query("ground_report", crew="B")] == [20, 50]
    with pytest.raises(ContractError):
        store.add("ground_report", {"schema_version": "1.0.0"})


def test_event_store_holds_readings(store):
    doc = example("Reading", state="event")
    store.add("event", doc)
    assert store.query("event") == [doc]
    with pytest.raises(ContractError):
        store.add("event", {"crew": "A", "t": 1})


@pytest.mark.parametrize("kind", ["label", "access_log"])
def test_label_and_access_log_need_crew_and_t(store, kind):
    store.add(kind, {"crew": "B", "t": 5, "note": "anything else is kept"})
    assert store.query(kind, crew="B") == [{"crew": "B", "t": 5, "note": "anything else is kept"}]
    for bad in [{"t": 5}, {"crew": "B"}, {"crew": "B", "t": "later"}]:
        with pytest.raises(ValueError):
            store.add(kind, bad)


def test_label_indicator_is_optional_and_queryable(store):
    store.add("label", {"crew": "A", "t": 1, "indicator": "hr"})
    store.add("label", {"crew": "A", "t": 2})
    assert len(store.query("label", crew="A", indicator="hr")) == 1


def test_unknown_store_is_rejected_including_sql_like_names(store):
    for kind in ["nope", "reading; DROP TABLE reading"]:
        with pytest.raises(ValueError):
            store.add(kind, {})
        with pytest.raises(ValueError):
            store.query(kind)
    assert store.conn.execute("SELECT count(*) FROM reading").fetchone()[0] == 0


def test_text_values_are_stored_safely(store):
    nasty = "A'); DROP TABLE reading; --"
    store.add("reading", example("Reading", crew=nasty))
    assert store.query("reading", crew=nasty)[0]["crew"] == nasty


def test_add_without_commit_can_be_rolled_back(store):
    store.add("reading", example("Reading"), commit=False)
    store.conn.rollback()
    assert store.query("reading") == []
    store.add("reading", example("Reading"), commit=False)
    store.conn.commit()
    assert len(store.query("reading")) == 1


def test_data_survives_closing_and_reopening(tmp_path):
    path = tmp_path / "habitat.sqlite"
    s = Store(path)
    s.add("reading", example("Reading"))
    s.close()
    s2 = Store(path)
    assert s2.query("reading") == [example("Reading")]
    s2.close()
    raw = sqlite3.connect(path)  # it is a plain SQLite file other tools can open
    assert raw.execute("SELECT count(*) FROM reading").fetchone() == (1,)
    raw.close()
