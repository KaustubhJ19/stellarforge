"""Integrated team app (local): Spec 4 flow for crew A-D, Spec 2 home in the frontend.

Run:  backend/.venv/Scripts/python -m uvicorn app.integrated:app --app-dir backend --port 8000
Crew records: Spec 2's bundled Spec 1-shaped fixture (A, B) + STUB records for C, D.
Optional: SF_HABITAT_URL=http://127.0.0.1:8765 to use Spec 1's service (with Spec 3 detection).
"""
import os
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
os.environ.setdefault("SF_PROFILE", "stub-mars_transit")
os.environ.setdefault("SF_RECORDS", ",".join([
    str(REPO / "frontend" / "src" / "fixtures" / "crew-records.json"),
    str(REPO / "replay" / "stub-crew-records-CD.json"),
]))
os.environ["SF_NO_APP"] = "1"

from .main import create_app  # noqa: E402

app = create_app()
