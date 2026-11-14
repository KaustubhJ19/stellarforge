"""Mission clock (Spec 1 task 1.3).

One simulated time source that every component reads instead of the wall clock.
Speeds: 1x and 60x. Can skip to the next event. Labelled "demo time".
Mission time is in seconds and never goes backwards.
"""
import time

SPEEDS = (1, 60)


def _check_speed(speed):
    if isinstance(speed, bool) or speed not in SPEEDS:
        raise ValueError(f"speed must be one of {SPEEDS}, got {speed!r}")


class MissionClock:
    label = "demo time"

    def __init__(self, start=0.0, speed=1, monotonic=time.monotonic):
        _check_speed(speed)
        self._monotonic = monotonic
        self._speed = speed
        self._base_t = start
        self._base_real = monotonic()
        self._last = start

    @property
    def speed(self):
        return self._speed

    def now(self):
        """Current Mission clock time in seconds (never decreases)."""
        elapsed = max(0.0, self._monotonic() - self._base_real)
        self._last = max(self._last, self._base_t + elapsed * self._speed)
        return self._last

    def _rebase(self, t):
        self._base_t = t
        self._base_real = self._monotonic()
        self._last = max(self._last, t)

    def set_speed(self, speed):
        """Change speed from this moment on, without a jump in mission time."""
        _check_speed(speed)
        self._rebase(self.now())
        self._speed = speed

    def skip_to_next_event(self, event_times):
        """Jump to the earliest event time later than now. Returns it, or None if there is none."""
        current = self.now()
        later = [t for t in event_times if t > current]
        if not later:
            return None
        target = min(later)
        self._rebase(target)
        return target
