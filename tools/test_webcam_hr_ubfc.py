"""Ticket 02 (Spike E) go/no-go: webcam heart rate on real videos (UBFC-rPPG, DATASET_2).

A recorded clip goes in; a heart rate comes out and is compared with the pulse oximeter.
Data is not in the repo (research use only). Point UBFC_DIR at a folder of subjectN/
directories (vid.avi + ground_truth.txt). Only subjects who consented to data sharing are used.
Run the report from the repo root: PYTHONPATH=. python tools/test_webcam_hr_ubfc.py
"""
import os
from pathlib import Path

import numpy as np
import pytest

from backend.webcam_hr import bpm_from_video

UBFC_DIR = Path(os.environ.get("UBFC_DIR", Path.home() / "Vedant/Claude/Nasa/datasets/ubfc-rppg"))
SUBJECTS = ["subject1", "subject3", "subject4", "subject5", "subject8"]
WINDOW_S = 20.0
GO_MAE_BPM = 5.0


def oximeter_bpm(subject: Path, start_s: float, end_s: float) -> float:
    """Mean oximeter heart rate in [start_s, end_s): line 2 is bpm, line 3 is time in s."""
    _, hr, t = (np.array(line.split(), dtype=float) for line in open(subject / "ground_truth.txt"))
    return float(hr[(t >= start_s) & (t < end_s)].mean())


def evaluate() -> list[tuple[str, float, float, float]]:
    """(subject, window start s, webcam bpm, oximeter bpm) for every full 20 s window."""
    rows = []
    for name in SUBJECTS:
        subject = UBFC_DIR / name
        last_t = float(open(subject / "ground_truth.txt").read().splitlines()[2].split()[-1])
        start = 0.0
        while start + WINDOW_S <= last_t:
            bpm, _ = bpm_from_video(subject / "vid.avi", start, WINDOW_S)
            rows.append((name, start, bpm, oximeter_bpm(subject, start, start + WINDOW_S)))
            start += WINDOW_S
    return rows


def _video_ok(name: str) -> bool:
    video = UBFC_DIR / name / "vid.avi"
    return video.exists() and video.stat().st_size > 10**8  # a 2 KB file is a download error page


@pytest.mark.skipif(not all(map(_video_ok, SUBJECTS)), reason="UBFC-rPPG videos not downloaded (set UBFC_DIR)")
def test_every_window_of_every_subject_gives_a_plausible_heart_rate():
    rows = evaluate()
    assert {r[0] for r in rows} == set(SUBJECTS)
    assert all(42.0 <= r[2] <= 240.0 for r in rows)


if __name__ == "__main__":
    rows = evaluate()
    for name, start, est, ref in rows:
        print(f"{name:9s} {start:4.0f}-{start + WINDOW_S:.0f} s  webcam {est:6.1f}  oximeter {ref:6.1f}  error {abs(est - ref):5.1f}")
    errors = np.array([abs(r[2] - r[3]) for r in rows])
    print(f"\n{len(rows)} windows, {len(SUBJECTS)} people. Mean absolute error {errors.mean():.1f} bpm; "
          f"within 5 bpm: {np.mean(errors <= 5) * 100:.0f}% of windows.")
    print("Decision:", "GO (ticket 12 proceeds)" if errors.mean() <= GO_MAE_BPM else "DROP TO P2")
