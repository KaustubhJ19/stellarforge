"""SQLite store: emitted events, record-access log, Labels and ground reports."""
from __future__ import annotations

import json
import sqlite3
import threading


class StoreError(RuntimeError):
    pass


class Store:
    def __init__(self, path: str = ":memory:"):
        self._db = sqlite3.connect(path, check_same_thread=False, isolation_level=None)
        self._lock = threading.RLock()
        self.fail_access_log = False  # fault injection for tests (ticket 07)
        with self._lock:
            self._db.executescript(
                """
                CREATE TABLE IF NOT EXISTS events(id INTEGER PRIMARY KEY, t REAL, type TEXT, data TEXT);
                CREATE TABLE IF NOT EXISTS access_log(id INTEGER PRIMARY KEY, t REAL, actor TEXT, subject TEXT,
                    emergency_id TEXT, allowed INTEGER, reason TEXT);
                CREATE TABLE IF NOT EXISTS labels(id TEXT PRIMARY KEY, crew TEXT, data TEXT);
                CREATE TABLE IF NOT EXISTS reports(id TEXT PRIMARY KEY, crew TEXT, data TEXT);
                CREATE TABLE IF NOT EXISTS synced(id TEXT PRIMARY KEY);
                """
            )

    # events -------------------------------------------------------------
    def add_event(self, ev: dict) -> None:
        with self._lock:
            self._db.execute("INSERT INTO events(t,type,data) VALUES(?,?,?)", (ev["t"], ev["type"], json.dumps(ev)))

    def events(self) -> list[dict]:
        with self._lock:
            return [json.loads(r[0]) for r in self._db.execute("SELECT data FROM events ORDER BY id")]

    # access log ---------------------------------------------------------
    def log_access(self, t, actor, subject, emergency_id, allowed: bool, reason: str) -> int:
        with self._lock:
            if self.fail_access_log:
                raise StoreError("access log write failed")
            cur = self._db.execute(
                "INSERT INTO access_log(t,actor,subject,emergency_id,allowed,reason) VALUES(?,?,?,?,?,?)",
                (t, actor, subject, emergency_id, int(allowed), reason),
            )
            return cur.lastrowid

    def access_log(self, subject: str | None = None) -> list[dict]:
        q = "SELECT id,t,actor,subject,emergency_id,allowed,reason FROM access_log"
        args: tuple = ()
        if subject:
            q += " WHERE subject=?"
            args = (subject,)
        with self._lock:
            rows = self._db.execute(q + " ORDER BY id", args).fetchall()
        keys = ("id", "t", "actor", "subject", "emergency_id", "allowed", "reason")
        return [dict(zip(keys, r)) | {"allowed": bool(r[5])} for r in rows]

    def mark_synced(self, item_id: str) -> bool:
        """True the first time an offline item id is seen (idempotent sync)."""
        with self._lock:
            return self._db.execute("INSERT OR IGNORE INTO synced(id) VALUES(?)", (item_id,)).rowcount == 1

    # labels / reports ---------------------------------------------------
    def put_label(self, label: dict) -> None:
        with self._lock:
            self._db.execute("INSERT INTO labels(id,crew,data) VALUES(?,?,?)", (label["id"], label["crew"], json.dumps(label)))

    def labels(self, crew: str | None = None) -> list[dict]:
        with self._lock:
            rows = self._db.execute("SELECT data FROM labels" + (" WHERE crew=?" if crew else ""), (crew,) if crew else ()).fetchall()
        return [json.loads(r[0]) for r in rows]

    def put_report(self, report: dict) -> None:
        with self._lock:
            self._db.execute("INSERT OR REPLACE INTO reports(id,crew,data) VALUES(?,?,?)", (report["id"], report["crew"], json.dumps(report)))

    def reports(self) -> list[dict]:
        with self._lock:
            return [json.loads(r[0]) for r in self._db.execute("SELECT data FROM reports")]
