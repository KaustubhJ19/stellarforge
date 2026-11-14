"""Integrated app connected to Spec 1's habitat service (with Spec 3 detection) on :8765.

Start the service first:
  backend/.venv/Scripts/python backend/service.py --db habitat.sqlite \
      --crew frontend/src/fixtures/crew-records.json --crew replay/stub-crew-records-CD.json
Then:  backend/.venv/Scripts/python -m uvicorn app.integrated_habitat:app --app-dir backend --port 8000
The Mission clock then belongs to the service (POST :8765/clock/speed {"speed": 60} to speed it up).
"""
import os

os.environ.setdefault("SF_HABITAT_URL", "http://127.0.0.1:8765")

from .integrated import app  # noqa: E402,F401
