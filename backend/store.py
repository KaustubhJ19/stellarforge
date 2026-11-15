"""SQLite store (Spec 1 task 1.9).

Stores: Reading, Alert, Label, Event store, Ground report, Access log;
indexed by crew, indicator, time. Each row keeps the full document as JSON.
Reading, Alert, Event store (Readings) and Ground report are checked against
the shared contracts. Label and Access log have no contract in Spec 1, so
only the indexed fields (crew, t) are required.
"""
import json
import numbers
import sqlite3
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "contracts"))
from validate import validate  # noqa: E402

# kind -> (contract used for validation or None, time field, has indicator column)
KINDS = {
    "reading": ("Reading", "t", True),
    "alert": ("Alert", "t", True),
    "label": (None, "t", True),
    "event": ("Reading", "t", True),
    "ground_report": ("GroundReport", "sent_t", False),
    "access_log": (None, "t", False),
}


def _kind(kind):
    if kind not in KINDS:
        raise ValueError(f"Unknown store {kind!r}; expected one of {sorted(KINDS)}")
    return KINDS[kind]


class Store:
    def __init__(self, path, check_same_thread=True):
        # The service (ticket 09) shares one connection across threads behind its own lock.
        self.conn = sqlite3.connect(str(path), check_same_thread=check_same_thread)
        with self.conn:
            for kind, (_, _, has_indicator) in KINDS.items():
                self.conn.execute(
                    f"CREATE TABLE IF NOT EXISTS {kind} ("
                    "id INTEGER PRIMARY KEY, crew TEXT NOT NULL, indicator TEXT, t REAL NOT NULL, doc TEXT NOT NULL)"
                )
                cols = "crew, indicator, t" if has_indicator else "crew, t"
                self.conn.execute(f"CREATE INDEX IF NOT EXISTS {kind}_lookup ON {kind} ({cols})")

    def add(self, kind, doc, commit=True):
        """Validate and insert. With commit=False the caller commits or rolls back (one transaction for many rows)."""
        contract, time_field, _ = _kind(kind)
        if contract:
            validate(contract, doc)
        else:
            if "crew" not in doc:
                raise ValueError(f"{kind} needs a crew field")
            t = doc.get(time_field)
            if isinstance(t, bool) or not isinstance(t, numbers.Real):
                raise ValueError(f"{kind} needs a numeric {time_field} field")
        row = (str(doc["crew"]), doc.get("indicator"), doc[time_field], json.dumps(doc))
        sql = f"INSERT INTO {kind} (crew, indicator, t, doc) VALUES (?, ?, ?, ?)"
        if commit:
            with self.conn:
                self.conn.execute(sql, row)
        else:
            self.conn.execute(sql, row)

    def query(self, kind, crew=None, indicator=None, t_from=None, t_to=None):
        """Documents matching the filters, ordered by time."""
        _kind(kind)
        where, args = [], []
        for clause, value in (("crew = ?", crew), ("indicator = ?", indicator), ("t >= ?", t_from), ("t <= ?", t_to)):
            if value is not None:
                where.append(clause)
                args.append(value)
        sql = f"SELECT doc FROM {kind}" + (" WHERE " + " AND ".join(where) if where else "") + " ORDER BY t, id"
        return [json.loads(row[0]) for row in self.conn.execute(sql, args)]

    def close(self):
        self.conn.close()
