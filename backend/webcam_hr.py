"""Webcam heart rate with classic signal processing (no training).

Method: POS, "plane orthogonal to skin" (Wang et al. 2017, IEEE TBME,
https://doi.org/10.1109/TBME.2016.2609282), then the strongest frequency in 42-240 bpm.
Status: Spike E (ticket 02). Accuracy "estimate, not validated" until measured on UBFC-rPPG (ticket 12).

Run `python -m backend.webcam_hr` to try it on your own webcam for 20 seconds.
"""
import time

import numpy as np

MIN_SECONDS = 10.0
LOW_HZ, HIGH_HZ = 0.7, 4.0  # 42-240 bpm


def estimate_bpm(rgb: np.ndarray, fps: float) -> tuple[float, float]:
    """Heart rate from the mean R, G, B of a skin region per frame.

    Returns (bpm, confidence); confidence is the share of in-band power at the peak (0-1).
    """
    rgb = np.asarray(rgb, dtype=float)
    if rgb.ndim != 2 or rgb.shape[1] != 3:
        raise ValueError("rgb must have shape (frames, 3)")
    if rgb.shape[0] < MIN_SECONDS * fps:
        raise ValueError(f"need at least {MIN_SECONDS:.0f} s of frames")

    n, win = rgb.shape[0], int(1.6 * fps)
    pulse = np.zeros(n)
    for start in range(n - win + 1):
        c = rgb[start:start + win]
        c = c / c.mean(axis=0)
        s1 = c[:, 1] - c[:, 2]
        s2 = c[:, 1] + c[:, 2] - 2 * c[:, 0]
        h = s1 + (s1.std() / (s2.std() + 1e-12)) * s2
        pulse[start:start + win] += h - h.mean()

    pulse = (pulse - pulse.mean()) * np.hanning(n)
    power = np.abs(np.fft.rfft(pulse)) ** 2
    freqs = np.fft.rfftfreq(n, d=1.0 / fps)
    band = (freqs >= LOW_HZ) & (freqs <= HIGH_HZ)
    p = power[band]
    peak = int(np.argmax(p))
    bpm = float(freqs[band][peak] * 60.0)
    # Count the peak and its two neighbours, since the Hann window spreads it.
    confidence = float(p[max(peak - 1, 0):peak + 2].sum() / (p.sum() + 1e-12))
    return bpm, confidence


def _skin_means(cap, n_frames: int) -> tuple[np.ndarray, list[float]]:
    """Mean R, G, B of the forehead/cheek area for up to n_frames frames, plus capture times."""
    import cv2

    faces = cv2.CascadeClassifier(cv2.data.haarcascades + "haarcascade_frontalface_default.xml")
    means, stamps, box = [], [], None
    try:
        while len(means) < n_frames:
            ok, frame = cap.read()
            if not ok:
                break
            found = faces.detectMultiScale(cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY), 1.2, 5)
            if len(found):
                box = max(found, key=lambda f: f[2] * f[3])
            if box is None:
                continue
            x, y, w, h = box
            roi = frame[y + h // 10:y + h // 2, x + w // 4:x + 3 * w // 4]  # forehead to upper cheeks
            b, g, r = roi.reshape(-1, 3).mean(axis=0)
            means.append((r, g, b))
            stamps.append(time.monotonic())
    finally:
        cap.release()
    if len(means) < 2:
        raise RuntimeError("no face found; face the camera in good light")
    return np.array(means), stamps


def bpm_from_video(path, start_s: float, seconds: float) -> tuple[float, float]:
    """Heart rate from a recorded clip, using `seconds` of video from `start_s`."""
    import cv2

    cap = cv2.VideoCapture(str(path))
    if not cap.isOpened():
        raise RuntimeError(f"cannot open video {path}")
    fps = cap.get(cv2.CAP_PROP_FPS)  # a recorded file's frame rate is fixed, unlike a live webcam
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(start_s * fps))
    rgb, _ = _skin_means(cap, int(seconds * fps))
    return estimate_bpm(rgb, fps)


def _capture(seconds: float = 20.0) -> tuple[np.ndarray, float]:
    """Mean colour of the forehead/cheek area from the default webcam."""
    import cv2

    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("no webcam found (on macOS, allow camera access for your terminal)")
    rgb, stamps = _skin_means(cap, int(seconds * (cap.get(cv2.CAP_PROP_FPS) or 30.0)))
    # The camera's nominal FPS is often wrong once face detection slows the loop; use the measured rate.
    return rgb, (len(stamps) - 1) / (stamps[-1] - stamps[0])


if __name__ == "__main__":
    print("Sit still, face the camera in good light. Recording 20 s...")
    rgb, fps = _capture()
    bpm, conf = estimate_bpm(rgb, fps)
    print(f"Webcam heart rate: {bpm:.0f} bpm (confidence {conf:.2f}, {len(rgb)} frames at {fps:.0f} fps)")
