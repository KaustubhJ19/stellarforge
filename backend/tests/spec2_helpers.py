"""Shared builders for the Spec 2 tests: a habitat service with detection and the daily loop, fed by replays."""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
for p in (ROOT, ROOT / "backend", ROOT / "contracts"):
    if str(p) not in sys.path:
        sys.path.insert(0, str(p))

from backend.daily_loop import build_loop  # noqa: E402
from service import HabitatService  # noqa: E402

SV = "1.0.0"
DAY = 86_400
ANCHOR = {"resting_heart_rate": {"mean": 60.0, "sd": 3.0}, "sleep_duration": {"mean": 450.0, "sd": 90.0}}


class FakeMonotonic:
    def __init__(self):
        self.value = 0.0

    def __call__(self):
        return self.value

    def advance(self, s):
        self.value += s


def record(crew="A", anchor=ANCHOR):
    return {"schema_version": SV, "id": crew, "sex": "female", "missionProfile": "mars_transit", "anchor": anchor}


def reading(crew, indicator, value, unit, t, source="sensor"):
    return {"t": t, "type": "reading", "payload": {"crew": crew, "indicator": indicator, "value": value, "unit": unit,
                                                    "t": t, "source": source, "confidence": 1, "state": "released"}}


def form(crew, kind, t, **answers):
    return {"t": t, "type": "form", "payload": {"crew": crew, "form": kind, "t": t, "answers": answers}}


def location(crew, cabin, t):
    return {"t": t, "type": "location", "payload": {"crew": crew, "cabin": cabin, "t": t}}


def replay(crew, events):
    return {"schema_version": SV, "crew": crew, "profile": "mars_transit",
            "events": sorted(events, key=lambda e: e["t"])}


def play(tmp_path, replays, records=None, **loop_kw):
    """Play every replay to its end through a real HabitatService; returns (service, pushed messages)."""
    records = records or [record("A")]
    real = FakeMonotonic()
    svc = HabitatService(tmp_path / "habitat.sqlite", list(replays), records, monotonic=real,
                         detection=build_loop(records, **loop_kw))
    got = []
    svc.subscribe("ground", got.append)
    end = max((e["t"] for rp in replays for e in rp["events"]), default=0)
    real.advance(end + 1)
    svc.tick()
    return svc, got


def of_type(messages, kind):
    return [m for m in messages if m["type"] == kind]


def load(path):
    return json.loads(Path(path).read_text(encoding="utf-8"))
