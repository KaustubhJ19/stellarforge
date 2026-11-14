"""Ticket 03 (Spec 1 task 1.3): Mission clock.

Spec: one time source; 1x, 60x, skip to next event; labelled "demo time".
Test (c): the Mission clock never goes backwards and honours speed changes.
User story 11: every component reads the Mission clock, never the wall clock.
"""
import re
import sys
from pathlib import Path

import pytest

BACKEND = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND))

from mission_clock import MissionClock  # noqa: E402


class FakeMonotonic:
    """Controllable stand-in for a monotonic real-time source."""

    def __init__(self, start=1000.0):
        self.value = start

    def __call__(self):
        return self.value

    def advance(self, seconds):
        self.value += seconds


@pytest.fixture
def real():
    return FakeMonotonic()


def test_is_labelled_demo_time(real):
    assert MissionClock(monotonic=real).label == "demo time"


def test_starts_at_zero_by_default(real):
    assert MissionClock(monotonic=real).now() == 0


def test_can_start_at_a_given_mission_time(real):
    assert MissionClock(start=500, monotonic=real).now() == 500


def test_at_1x_advances_one_second_per_real_second(real):
    clock = MissionClock(monotonic=real)
    real.advance(10)
    assert clock.now() == 10


def test_at_60x_advances_sixty_seconds_per_real_second(real):
    clock = MissionClock(speed=60, monotonic=real)
    real.advance(10)
    assert clock.now() == 600


def test_speed_change_applies_from_the_moment_of_change_without_a_jump(real):
    clock = MissionClock(monotonic=real)
    real.advance(10)          # 10 s at 1x
    clock.set_speed(60)
    assert clock.now() == 10  # no jump at the change
    real.advance(2)           # 120 s at 60x
    assert clock.now() == 130
    clock.set_speed(1)
    real.advance(5)
    assert clock.now() == 135
    assert clock.speed == 1


@pytest.mark.parametrize("speed", [0, 2, -1, 30, "60", True])
def test_rejects_speeds_other_than_1x_and_60x(real, speed):
    clock = MissionClock(monotonic=real)
    with pytest.raises(ValueError):
        clock.set_speed(speed)
    with pytest.raises(ValueError):
        MissionClock(speed=speed, monotonic=real)


def test_skip_jumps_to_the_next_event_after_now(real):
    clock = MissionClock(start=100, monotonic=real)
    assert clock.skip_to_next_event([50, 100, 400, 900]) == 400
    assert clock.now() == 400


def test_skip_then_keeps_running_at_current_speed(real):
    clock = MissionClock(speed=60, monotonic=real)
    clock.skip_to_next_event([3600])
    real.advance(1)
    assert clock.now() == 3660


def test_skip_accepts_unsorted_event_times(real):
    clock = MissionClock(monotonic=real)
    assert clock.skip_to_next_event([900, 300, 600]) == 300


def test_skip_with_no_later_event_stays_put_and_returns_none(real):
    clock = MissionClock(start=1000, monotonic=real)
    assert clock.skip_to_next_event([10, 1000]) is None
    assert clock.now() == 1000
    assert clock.skip_to_next_event([]) is None


def test_never_goes_backwards_across_speed_changes_and_skips(real):
    clock = MissionClock(monotonic=real)
    seen = [clock.now()]
    for step in range(20):
        real.advance(0.5)
        if step % 5 == 0:
            clock.set_speed(60 if clock.speed == 1 else 1)
        if step % 7 == 0:
            clock.skip_to_next_event([step * 100.0])
        seen.append(clock.now())
    assert seen == sorted(seen)


def test_never_goes_backwards_even_if_the_real_source_steps_back(real):
    clock = MissionClock(monotonic=real)
    real.advance(10)
    assert clock.now() == 10
    real.advance(-5)          # misbehaving source
    assert clock.now() == 10
    real.advance(10)          # source recovers past its old high point
    assert clock.now() >= 10


def test_clock_module_does_not_read_the_wall_clock():
    source = (BACKEND / "mission_clock.py").read_text(encoding="utf-8")
    assert not re.search(r"time\.time\(|datetime|time\.localtime|time\.gmtime", source)
