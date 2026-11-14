"""Ticket 02 (Spike E): classic webcam heart rate, no training.

A recorded clip goes in (as the mean skin colour per frame); a heart rate comes out.
The clip here is synthetic: a known pulse hidden in camera noise and slow lighting drift.
"""
import numpy as np
import pytest

from backend.webcam_hr import estimate_bpm

FPS = 30.0


def synthetic_clip(bpm: float, seconds: float = 20.0, seed: int = 0) -> np.ndarray:
    """Mean R, G, B of a face region per frame, with a pulse at `bpm`."""
    rng = np.random.default_rng(seed)
    t = np.arange(int(seconds * FPS)) / FPS
    pulse = np.sin(2 * np.pi * bpm / 60.0 * t)
    drift = 3.0 * np.sin(2 * np.pi * 0.05 * t)  # slow lighting change
    base = np.array([150.0, 110.0, 90.0])
    strength = np.array([0.2, 0.5, 0.1])  # pulse is strongest in green
    return base + drift[:, None] + pulse[:, None] * strength + rng.normal(0, 0.3, (t.size, 3))


@pytest.mark.parametrize("true_bpm", [52.0, 72.0, 110.0])
def test_known_pulse_is_recovered_within_3_bpm(true_bpm):
    bpm, confidence = estimate_bpm(synthetic_clip(true_bpm), FPS)
    assert abs(bpm - true_bpm) <= 3.0
    assert 0.0 <= confidence <= 1.0


def test_clip_without_pulse_has_low_confidence():
    rng = np.random.default_rng(1)
    noise = np.array([150.0, 110.0, 90.0]) + rng.normal(0, 0.3, (600, 3))
    _, confidence = estimate_bpm(noise, FPS)
    _, good = estimate_bpm(synthetic_clip(72.0), FPS)
    assert confidence < good


def test_too_short_clip_is_rejected():
    with pytest.raises(ValueError):
        estimate_bpm(synthetic_clip(72.0, seconds=3.0), FPS)
