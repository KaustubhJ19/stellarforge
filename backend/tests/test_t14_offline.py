"""Ticket 14: backend-down support (offline bundle, idempotent sync) and no external calls."""
import re
from pathlib import Path

from app import replay
from app.flow import DISCLAIMER

REPO = Path(__file__).resolve().parents[2]


def test_bundle_has_solo_filtered_cited_steps_and_disclaimer(client):
    b = client.get("/api/offline-bundle").json()
    assert [s["id"] for s in b["protocol"]["steps"]] == ["stub-1", "stub-2"]  # stub-3 needs 2 rescuers
    assert all(s["source"]["guideline"] and s["source"]["section"] for s in b["protocol"]["steps"])
    assert b["protocol"]["stub"] is True and b["disclaimer"] == DISCLAIMER
    assert set(b["records"]) == {"cmdr", "eng", "sci", "cmo"}


def test_sync_is_idempotent_and_keeps_original_times(client, eng):
    items = [
        {"id": "eng-1", "type": "trigger", "t": 120.5, "data": {"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 120.5, "reason": "offline: Help a crewmate"}},
        {"id": "eng-2", "type": "record_access", "t": 121, "data": {"actor": "eng", "subject": "cmdr"}},
        {"id": "eng-3", "type": "step_completed", "t": 140, "data": {"step": "stub-1", "patient": "cmdr"}},
    ]
    r = client.post("/api/sync", json={"tablet": "eng", "items": items}).json()
    assert r == {"accepted": 3, "duplicates": 0}
    assert client.post("/api/sync", json={"tablet": "eng", "items": items}).json() == {"accepted": 0, "duplicates": 3}
    log = eng.store.access_log("cmdr")
    assert len(log) == 1 and log[0]["t"] == 121 and "offline" in log[0]["reason"] and log[0]["actor"] == "eng"
    assert next(e for e in eng.events if e["type"] == "offline_trigger")["original_t"] == 120.5


def test_synced_trigger_does_not_start_a_live_flow_or_alarm(client, eng):
    client.post("/api/sync", json={"tablet": "cmdr", "items": [
        {"id": "c-1", "type": "trigger", "t": 5, "data": {"schema_version": "1.0.0", "kind": "manual", "crew": "cmdr", "t": 5, "reason": "offline"}}]})
    replay.run(eng, {"id": "t", "events": []}, until=60)
    assert eng.emergencies == {} and "crew_alarm" not in replay.types(eng)


def test_bad_sync_item_rejected_and_not_marked(client, eng):
    bad = {"id": "x-1", "type": "record_access", "t": 1, "data": {"actor": "ghost", "subject": "cmdr"}}
    assert client.post("/api/sync", json={"tablet": "eng", "items": [bad]}).status_code == 422
    fixed = bad | {"data": {"actor": "eng", "subject": "cmdr"}}
    assert client.post("/api/sync", json={"tablet": "eng", "items": [fixed]}).json()["accepted"] == 1
    assert client.post("/api/sync", json={"tablet": "eng", "items": [{"id": "y", "type": "hack", "t": 1}]}).status_code == 422


def test_no_external_urls_in_runtime_code():
    """Offline: our runtime code references no non-local hosts."""
    pat = re.compile(r"https?://(?!127\.0\.0\.1|localhost|json-schema\.org)[\w.-]+", re.I)
    files = list((REPO / "backend/app").glob("*.py")) + [f for f in (REPO / "frontend/src").rglob("*.ts*") if ".test." not in f.name]
    files += [REPO / "frontend/index.html"]
    # The built bundle is checked by the Playwright network-off test (real requests, not strings).
    hits = {str(f.relative_to(REPO)): pat.findall(f.read_text(encoding="utf-8", errors="ignore")) for f in files}
    assert {k: v for k, v in hits.items() if v} == {}
