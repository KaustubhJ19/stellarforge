# How accurate is this? (Spec 3, ticket 10)

Measured 2026-11-14/15 by the AI / detection lead. For the write-up and the accuracy page (Spec 5).
Every number below comes from a test or report in `tools/` that anyone can re-run.

## The numbers

| What | Result | Measured on | How to re-run |
|---|---|---|---|
| False alerts (drift + acute) | **0.11 per crew-day**, about one every 9 days per crew (68 alerts in 603 crew-days) | 4 crew replays built from PMData (Earth wearable data, 16 people, CC BY 4.0) | `PYTHONPATH=. python tools/test_detection.py` |
| Same, before tuning | 0.20 per crew-day | same | same |
| Drift caught before the event | A +10 bpm rise over 9 days is caught on day 8. The planned +6 bpm over 9 days is not reliably caught: it is smaller than normal life swings in this data. | Calm crew (PMData p01) with the drift added | `tools/test_golden_replays.py` (synthetic); tuning notes in ticket 13 |
| Emergency auto Trigger | Fires at the first VT/VF/PEA/asystole reading, or heart rate ≥150 or <50 bpm for 30 s with systolic BP <90 mmHg | Stream in the Pulse emergency replay's format | `tools/test_detection.py`, `tools/test_emergency.py` |
| Webcam heart rate | **4.9 bpm mean error**; 67 % of 20 s windows within 5 bpm | 5 consenting UBFC-rPPG people, 12 windows (research use only) | `PYTHONPATH=. python tools/test_webcam_hr_ubfc.py` |
| Tomorrow's readiness forecast (P1) | Mean error **1.12 points** on a 0–10 scale, the same as "tomorrow = today" (1.12); range covers the true answer **89.6 %** of the time (target about 90 %) | 16 PMData people, each forecast only for people never used to train | `PYTHONPATH=. python tools/test_forecast_b.py` |

Labels: every detection cut-off is a "team value" or an "Earth reference, no space data" (sources in `content/profiles/detection-cut-offs.json`). The forecast and webcam numbers are "estimate, not validated".

## Honest limits (use this text)

- Accuracy is measured on datasets, not on astronauts. Real-time performance with real astronauts may differ.
- No open astronaut wearable stream exists. Normal days come from Earth wearable data (PMData) shaped to look like a crew.
- Detection has no training step, so no person was "seen in training". But the cut-offs were tuned on the same four crews they are measured on, so the false-alert number is optimistic.
- On real Earth data, people's resting heart rate moves by several bpm over weeks without any illness. A slow drift has to be larger than that to be caught reliably.
- The emergency is a Pulse Physiology Engine simulation ("estimate, not validated"). Chest pain is crew-reported, not simulated.
- Safety limits are Earth clinical references (AHA). There are no published in-flight limits. A low heart rate can be normal for fit people, so the low limit is applied to the live heart rate only, not to resting heart rate.
- Webcam heart rate was measured on 5 people in good light, sitting still. One person had errors of 8–20 bpm.
- The readiness forecast is no more accurate than assuming tomorrow equals today. Its value is the range and the explanation, not the number.
