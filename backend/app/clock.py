"""Mission clock stand-in. Spec 1 owns the real Mission clock; this test double
gives mission time in seconds and can be advanced manually (tests, replays) or
run in real time with a speed-up factor (demo)."""
from __future__ import annotations

import time


class MissionClock:
    def __init__(self, start: float = 0.0, speed: float | None = None):
        self._t = float(start)
        self.speed = speed  # None = manual; otherwise real seconds * speed
        self._wall = time.monotonic()

    def now(self) -> float:
        if self.speed is None:
            return self._t
        return self._t + (time.monotonic() - self._wall) * self.speed

    def advance(self, dt: float) -> float:
        if dt < 0:
            raise ValueError("mission clock cannot go backwards")
        self._t = self.now() + dt
        self._wall = time.monotonic()
        return self._t

    def set(self, t: float) -> float:
        if t < self.now():
            raise ValueError("mission clock cannot go backwards")
        return self.advance(t - self.now())
