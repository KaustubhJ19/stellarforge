"""Adapter to Spec 1's habitat-network service (ticket 15). Optional: set SF_HABITAT_URL.

In:  SSE /events?window=rescuer -> Readings, Alerts (after Spec 3's hook), Triggers. An Alert or Trigger
     message may carry a Spec 2 "hot_summary" beside its payload; the latest per crew is kept on the engine
     (eng.hot_summaries) so the emergency service needs no history store of its own.
Out: manual Triggers -> POST /trigger; ground reply -> POST /ground_reply (Spec 1 stores the
     report and its Label together); emergency record opening -> GET /crew/<id>?emergency=1
     (Spec 1 logs it). The local access log is still written first, for the owner's view.
Clock: Spec 1's Mission clock (GET /clock), extrapolated locally between syncs.
"""
from __future__ import annotations

import json
import threading
import time

import httpx


class HabitatClock:
    """Read-only view of Spec 1's Mission clock."""

    def __init__(self, url: str):
        self.url = url
        self._t, self._speed, self._wall = 0.0, 1.0, time.monotonic()
        self.speed = None  # engine sim controls are disabled: the service owns time
        self.sync()

    def sync(self) -> None:
        c = httpx.get(f"{self.url}/clock", timeout=2).json()
        self._t, self._speed, self._wall = float(c["t"]), float(c["speed"]), time.monotonic()

    def now(self) -> float:
        return self._t + (time.monotonic() - self._wall) * self._speed

    def advance(self, dt: float) -> float:
        raise RuntimeError("the Mission clock is owned by the Spec 1 service")

    set = advance


class Habitat:
    def __init__(self, eng, url: str, timeout: float = 3.0):
        self.eng, self.url, self.timeout = eng, url.rstrip("/"), timeout
        self._stop = threading.Event()
        self.connected = threading.Event()
        self.errors: list[str] = []

    # ------------------------------------------------------------------ in
    def start(self) -> None:
        threading.Thread(target=self._sse_loop, daemon=True).start()
        if isinstance(self.eng.clock, HabitatClock):
            threading.Thread(target=self._clock_loop, daemon=True).start()

    def stop(self) -> None:
        self._stop.set()

    def _clock_loop(self) -> None:
        while not self._stop.wait(1.0):
            try:
                self.eng.clock.sync()
            except httpx.HTTPError as e:
                self.errors.append(f"clock: {e}")

    def _sse_loop(self) -> None:
        backoff = 0.5
        while not self._stop.is_set():
            try:
                with httpx.stream("GET", f"{self.url}/events", params={"window": "rescuer"}, timeout=None) as r:
                    self.connected.set()
                    backoff = 0.5
                    for line in r.iter_lines():
                        if self._stop.is_set():
                            return
                        if line.startswith("data: "):
                            self.handle(json.loads(line[6:]))
            except httpx.HTTPError as e:
                self.connected.clear()
                self.errors.append(f"events: {e}")
                self._stop.wait(backoff)
                backoff = min(backoff * 2, 5.0)

    def handle(self, msg: dict) -> None:
        kind, payload = msg.get("type"), msg.get("payload") or {}
        summary = msg.get("hot_summary")
        if kind in ("alert", "trigger") and isinstance(summary, dict) and summary.get("crew") == payload.get("crew"):
            try:  # a summary the copilot cannot read never blocks the Alert or Trigger itself
                self.eng.hot_summaries.update(summary)
            except ValueError as e:
                self.errors.append(f"hot_summary: {e}")
                self.eng.emit("habitat_message_rejected", message_type="hot_summary", error=str(e))
        try:
            if kind in ("alert", "trigger") and "hot_summary" in payload:  # Spec 2 snapshot rides on the push
                payload = dict(payload)
                self.eng.hot_summaries.update(payload.pop("hot_summary"))
            if kind == "hot_summary":
                self.eng.hot_summaries.update(payload)
            elif kind in ("reading", "reading_state"):
                self.eng.ingest_reading(payload)
            elif kind == "alert":
                self.eng.ingest_alert(payload)
            elif kind == "trigger":
                self.eng.trigger(payload)  # an echo of our own manual Trigger is de-duplicated
        except Exception as e:  # noqa: BLE001 — a bad message must not stop the stream
            self.errors.append(f"{kind}: {e}")
            self.eng.emit("habitat_message_rejected", message_type=kind, error=str(e))

    # ----------------------------------------------------------------- out
    def post_trigger(self, trig: dict) -> None:
        r = httpx.post(f"{self.url}/trigger", json=trig, timeout=self.timeout)
        r.raise_for_status()

    def post_ground_reply(self, report: dict) -> None:
        r = httpx.post(f"{self.url}/ground_reply", json=report, timeout=self.timeout)
        r.raise_for_status()

    def record(self, crew: str, requester: str, emergency: bool) -> dict:
        try:
            r = httpx.get(f"{self.url}/crew/{crew}", params={"requester": requester, "emergency": int(emergency)},
                          timeout=self.timeout)
        except httpx.HTTPError as e:
            raise ConnectionError(f"habitat service unreachable: {e}") from None
        if r.status_code == 403:
            raise PermissionError(r.json().get("error", "refused"))
        r.raise_for_status()
        return r.json()
