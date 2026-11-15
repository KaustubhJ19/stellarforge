# How accurate is this? (Spec 3, ticket 10)

Measured 2026-11-14/15 by the AI / detection lead. For the write-up and the accuracy page (Spec 5).
Every number below comes from a test or report in `tools/` that anyone can re-run.

## The numbers

| What | Result | Measured on | How to re-run |
|---|---|---|---|
| False alerts (drift + acute) | **0.16 per crew-day**, about one every 6 days per crew (91 alerts in 567 crew-days; crew A 0.05, B 0.15, C 0.25, D 0.20). Was 0.11 before the shared replays added steps and soreness and crew D became PMData p10, who also answers the daily wellness questions; most extra alerts are on those self-reported scores | 4 shared crew replays in `replay/` built from PMData (Earth wearable data, 16 people, CC BY 4.0) | `PYTHONPATH=. python tools/test_detection.py` |
| Same, before tuning | starting values in `tools/test_detection.py` (0.20 on the first replays) | same | same |
| Drift caught before the event | A +10 bpm rise over 9 days is caught on day 8. The planned +6 bpm over 9 days is not reliably caught: it is smaller than normal life swings in this data. | Calm crew (PMData p01) with the drift added | `tools/test_golden_replays.py` (synthetic); tuning notes in ticket 13 |
| Emergency auto Trigger | Fires at the first VT/VF/PEA/asystole reading, or heart rate ≥150 or <50 bpm for 30 s with systolic BP <90 mmHg | Stream in the Pulse emergency replay's format | `tools/test_detection.py`, `tools/test_emergency.py` |
| Webcam heart rate | **4.9 bpm mean error**; 67 % of 20 s windows within 5 bpm | 5 consenting UBFC-rPPG people, 12 windows (research use only) | `PYTHONPATH=. python tools/test_webcam_hr_ubfc.py` |
| Tomorrow's readiness forecast (P1) | Mean error **1.12 points** on a 0–10 scale, the same as "tomorrow = today" (1.12); range covers the true answer **89.6 %** of the time (target about 90 %) | 16 PMData people, each forecast only for people never used to train | `PYTHONPATH=. python tools/test_forecast_b.py` |
| Joint-pattern alert (Spec 2) | **0.009 false joint alerts per crew-day** (4 in 462 crew-days after its 28 learning days), against 0.175 for today's per-indicator detector (81) on the same days. Combined small drift (resting heart rate up, sleep down, mood down, 1 sd each, ramped over 7 days from day 60): joint caught it on day 11, 11 and 12 for crews B, D and C, and day 41 for crew A; today's detector on day 2, 27, 8 and 17. Joint is earlier on 1 of 4 crews (D); its gain is being about 20 times quieter, not faster | 4 shared PMData crew replays with injected drifts (alerts the clean replay also raises are not counted) | `PYTHONPATH=. python tools/test_joint_pattern.py` |
| Action-plan learning (Spec 2) | Per-person bandit reversed **64 %** of drifts (68 % in the second half of the mission) against **52 %** for the best single fixed plan. "learns per person; demonstrated on simulated response, not proven" | 12 simulated people x 60 drift episodes, 5 seeds, made-up response model (`tools/sim_response.py`) | `PYTHONPATH=. python tools/test_bandit.py` |
| What-if warm start for the bandit (Spec 2) | The readiness what-if forecast predicts less than 0.11 readiness points of change (0–10) for every action, so the warm start is nearly flat: the driver weights and the person's own results do the work | 16 PMData people | `PMDATA_DIR=... python tools/plan_warm_start.py` |

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
- The joint-pattern detector and the action-plan learning were measured on Earth data with injected drifts and on a made-up response model. Action plans are placeholders until the team writes and approves them.
