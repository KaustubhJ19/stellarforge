# Spec 3 · Detection, Baseline, Status and Forecast

> **Role:** AI / detection lead · **Stream 2** · Anyone can pick this spec up.
> Parent plan: [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) · Vocabulary: `GLOSSARY.md` (Indicator, Reading, Anchor, Adaptive baseline, Status, Safety bound, Acute alert, Drift alert, Alert, Quarantine, Event, Label, Readiness)
> Deadline: Sun 15 Nov 2026, 11:59 PM Melbourne. Plan clock: H0 = build start, H24 = feature freeze.
> Triage: `ready-for-agent` (local file, no issue tracker).

## How to start (first 30 minutes)

1. Download **PMData** and read its readiness scale (Spike D). Download the OSDR ISS cabin file and the Inspiration4 blood values. Hand the verified files and notes to the data lead by H2.
2. Try **webcam heart rate** (Spike E) for 30 minutes. If it is not working, mark it P2.
3. Sketch the baseline on one PMData person in a notebook. Do not wait for contracts to understand the maths.

## Problem Statement

A health tool that compares everyone to a population average misses what matters in space: the same heart rate can be normal for one astronaut and a warning for another, and slow changes (insulin resistance, bone loss, sleep drift) get absorbed by a short window. The crew also needs the tool to notice an emergency without waiting for someone to type, and to say honestly how sure it is.

## Solution

Four parts, each with one job:

1. **Baseline A**: learns each person's own normal. A fixed pre-flight **Anchor** catches slow **Drift**. A 28-day **Adaptive baseline** catches sudden **Acute** change.
2. **Auto-detect rule**: watches the live stream and raises an emergency Trigger.
3. **Likely-cause ranking**: after any Trigger, lists 2–3 contributors from the person's history (a suggestion, never a diagnosis).
4. **Status**: one green / amber / red per Indicator, computed in one place.

P1 adds **Forecast B** (predicted readiness for tomorrow with a confidence range and an explanation view).

## Seam

Tested by **replaying a file and asserting the Alerts, Status values and Triggers that come out at set times** (golden replays). The data lead owns the replay seam.

## Contracts (shapes, frozen at H2)

You consume `Reading`, `CrewRecord`, `ReplayFile`. You produce `Alert`, `Trigger`, and the `Reading.state` changes (released / quarantined / event).

| Contract | Fields |
|---|---|
| `Reading` | crew, indicator, value, unit, t, source (sensor / camera / mic / manual / lab / sim), confidence, state (released / quarantined / event) |
| `Alert` | id, kind (acute / drift / emergency), crew, indicator, deviation, status (green / amber / red), urgency (ACT_NOW / ESCALATE_TO_GROUND / MONITOR / ROUTINE), likely_causes[{indicator, direction, note}], t |
| `CrewRecord` | id, sex, anchor{indicator: {mean, sd}}, missionProfile |
| `Trigger` | kind (auto / manual), crew, t, reason, confirmed? |

## User Stories

1. As an astronaut, I want my alerts judged against **my own** normal, so that a normal reading for me is not flagged.
2. As an astronaut, I want a Drift alert when something moves slowly away from my pre-flight values, so that creeping problems are not absorbed.
3. As an astronaut, I want an Acute alert when something changes suddenly against the last 4 weeks, so that sudden change is caught fast.
4. As an astronaut, I want abnormal days never to become my "new normal", so that illness does not hide itself.
5. As an astronaut, I want readings taken during an open alert held aside, so that they do not pollute my baseline.
6. As an astronaut, I want held readings released if I tag "false alarm" or after 24 hours with no confirmed event, so that normal days are not excluded forever.
7. As an astronaut, I want confirmed abnormal periods moved to an Event store, so that they teach the detectors, not the baseline.
8. As a crewmate, I want the app to detect a collapse by itself, so that help starts even if the patient cannot press anything.
9. As a crewmate, I want the same flow whether the app detected it or I pressed the button, so that there is one thing to learn.
10. As a crewmate, I want 2–3 likely contributors from the patient's history, so that I and the ground team understand what led here.
11. As a crewmate, I want likely causes labelled "suggestion, not diagnosis", so that no one over-trusts them.
12. As an astronaut, I want one Status colour per Indicator from one rule, so that colours never disagree between screens.
13. As an astronaut, I want a safety limit to turn an Indicator red even when my baseline has drifted, so that absolute danger is never normalised.
14. As an astronaut, I want an urgency verdict (ACT NOW / ESCALATE TO GROUND / MONITOR / ROUTINE) on every alert, so that I know how fast to act.
15. As an astronaut, I want a short morning briefing in words ("resting heart rate +6 bpm over 9 days"), so that I understand the Drift alert without reading charts.
16. As the integration lead, I want an accuracy page with real numbers, so that the pitch is honest.
17. As a judge, I want to see false alerts per crew-day, so that I can judge alert fatigue.
18. As an astronaut, I want a forecast of tomorrow's readiness with a range, so that I can plan my day. (P1)
19. As an astronaut, I want a wide range to trigger "re-measure", so that a shaky forecast is not trusted. (P1)
20. As an astronaut, I want to see what drove the forecast, so that the number is not a black box. (P1)
21. As an astronaut, I want a webcam heart rate during the morning check, so that I get a reading with no extra device. (P1)

## Implementation Decisions

### Tasks and hours (plan clock)

| ID | Task | Hours |
|---|---|---|
| 3.1 | **Spike D**: download PMData, ISS cabin data and Inspiration4 values; verify readiness scale and OSD ID-to-panel mapping; hand notes to the data lead | H0–2 |
| 3.2 | **Spike E**: webcam heart rate works (classic signal processing, no training) | H0–2 |
| 3.3 | Baseline A: Anchor, 28-day Adaptive baseline, combined multi-signal deviation score, CuSum alarm, constant time per reading | H2–8 |
| 3.4 | Auto-detect rule on the stream; emits a `Trigger` | H4–7 |
| 3.5 | Status in one place = worse of A's level and the Safety bound check | H6–8 |
| 3.6 | Quarantine manager: hold, release on tag or 24 h, move to Event store | H6–9 |
| 3.7 | Likely-cause ranking (rule-based, template text) | H8–11 |
| 3.8 | Daily briefing text from A's numbers | H10–12 |
| 3.9 | Golden replay tests: planted drift alert, auto-trigger on the Pulse event, quarantine release | H10–14 |
| 3.10 | Accuracy numbers and the "How accurate is this" page content | H14–18 |
| 3.11 | **P1** Forecast B: gradient-boosted trees on PMData readiness, conformal range (MAPIE), explanation view data (SHAP) | H18–22 |
| 3.12 | **P1** Webcam heart rate in the morning check; UBFC-rPPG accuracy | H18–22 |
| 3.13 | Bug fixing and threshold tuning | H24–28 |

### Baseline A

- **Anchor:** fixed pre-flight mean and spread per person and Indicator. Drives Drift alerts. Slow shifts (days to weeks) compare to the Anchor plus an expected space shift. The in-flight shift has no real source and is labelled "team value". The only real astronaut numbers are the return-to-gravity shift (see below).
- **Adaptive baseline:** 28-day sliding window of released Readings. Drives Acute alerts.
- **Combined score:** multi-signal deviation across Indicators, with a CuSum alarm and a two-tier warning (amber, red).
- **Quarantine:** while an Alert is open, new Readings are held. Release on a "false alarm" or "normal" tag, or after 24 h of Mission-clock time with no confirmed Event. A confirmed Event moves the held Readings to the Event store. **Abnormal data never updates A.**
- **Confidence:** A reports its deviation score (σ and CuSum level). Perception models report dataset accuracy. B (P1) reports a conformal interval.
- References: Mishra 2020 (https://www.nature.com/articles/s41551-020-00640-6); Alavi 2022 (https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/).

### Auto-detect rule (team values; tune on replays)

Raise an emergency `Trigger` when **either**:
- rhythm state is one of VT, VF, PEA, asystole; **or**
- heart rate is extreme (very high or very low) for a sustained period **and** blood pressure is low.

Thresholds are labelled "Earth reference / team value" and held in content, not code. The demo stream is the Pulse replay; the rule works on rhythm state, HR and BP, not on an ECG waveform (Pulse's ECG is a template). Chest pain is crew-reported, not simulated.

### Likely-cause ranking

- Input: the person's recent history and the live Readings.
- Output: 2–3 contributors, for example "resting heart rate +6 bpm over 9 days", "sleep 1.5 h below your normal", "glucose off baseline". Template text from A's numbers.
- Label: "suggestion, not diagnosis". It does **not** choose the protocol steps; the confirmed trigger does.

### Status and urgency

- **Status** = the worse of A's level and the **Safety bound** check. Safety bounds come from space or personal values first; where none exists, an Earth clinical limit is used and labelled "Earth reference, no space data". Colour is never the only signal (icon or text too).
- **Urgency:** emergency Trigger → ACT_NOW; red Acute alert → ESCALATE_TO_GROUND; amber → MONITOR; green → ROUTINE.

### Real astronaut reference values you can cite

NASA Apollo AP005, open Table 6, group means after landing (24 crew at rest, 9 standing). Source: https://nlsp.nasa.gov/search/data/details/e1fa5c55-ddfe-5548-91ba-864080319f44?dataType=EXPERIMENTS

| Measure | Preflight | 1st postflight |
|---|---|---|
| Resting heart rate (bpm) | 61.6 | 69.7 |
| Standing heart rate (bpm) | 76.4 | 99.8 |
| Standing systolic BP (mm Hg) | 118.8 | 105.8 |

Use for the expected return-to-gravity shift only. These are group averages after landing, not limits.

### Forecast B (P1)

- Gradient-boosted trees; target = **Readiness**, predicted self-reported readiness for tomorrow, trained on PMData. The in-app attention test is an input, not the target.
- Population model personalised per person by calibration and residual correction. Until enough days exist, show a wide range labelled "learning your pattern".
- Wrappers: conformal interval (MAPIE); SHAP explanation. Output labelled "estimate, not validated" where it is a what-if.
- Libraries: https://github.com/scikit-learn-contrib/MAPIE · https://github.com/shap/shap · SHAP paper https://arxiv.org/abs/1705.07874 · conformal prediction https://arxiv.org/abs/2107.07511

## Datasets (links and licences)

| Need | Dataset | Link | Licence |
|---|---|---|---|
| Normal days; readiness target | PMData | https://datasets.simula.no/pmdata/ | CC BY 4.0 |
| Extra 24 h HR/HRV, sleep, stress | MMASH | https://physionet.org/content/mmash/ | ODbL |
| Extra sleep, Apple Watch | SleepAccel | https://physionet.org/content/sleep-accel/1.0.0/ | Open |
| Glucose (separate file) | CGMacros | https://registry.opendata.aws/cgmacros/ | CC BY-NC-SA 4.0 |
| Webcam heart-rate accuracy | UBFC-rPPG | https://sites.google.com/view/ybenezeth/ubfcrppg | Research use only |
| ECG classifier (future, pitch only) | PTB-XL · MIT-BIH | https://www.physionet.org/content/ptb-xl/1.0.3/ · https://registry.opendata.aws/mitdb/ | CC BY 4.0 · ODC-By |

## Spike go/no-go (decide by H2)

| Spike | If it fails |
|---|---|
| D: datasets download and map | Use whatever downloaded; type Inspiration4 blood values in from the paper tables |
| D: PMData readiness scale unclear | Define readiness from fatigue and sleep columns and document it |
| E: webcam heart rate unreliable | Drop to P2; show a recorded heart-rate clip |

## Dependencies

- **Needs from Spec 1:** contracts (H2), crew replays with a planted drift (H8), the Pulse emergency (H6).
- **Gives to Spec 2:** Status and Alert values and Mission-clock timings for chart markers.
- **Gives to Spec 4:** the `Trigger`, the likely causes, the urgency value and the quarantine hooks (Label → release or move to Event store).
- **Gives to Spec 5:** accuracy numbers and the limitations text.

## Testing Decisions

- A good test replays a file and asserts **what comes out** at set times, not the maths inside.
- Tests: (a) the planted drift raises a Drift alert before the emergency; (b) the Pulse emergency raises an auto Trigger and the manual button raises an equivalent one; (c) a held Reading is released after a "false alarm" tag or 24 h and never updates the Adaptive baseline while held; (d) a confirmed Event moves Readings to the Event store; (e) Status is the worse of A's level and the Safety bound; (f) likely causes appear and are labelled; (g) a safety limit turns Status red even when the baseline has drifted.
- **Held-out people:** report accuracy on people never used to train (alerts raised before known Events; false alerts per crew-day; forecast mean error and interval coverage target about 90%; webcam mean error in bpm).
- Coverage target 80% on this service.
- Prior art: none (no code yet).

## Acceptance Criteria

- [ ] Drift alert fires on the planted drift in a golden replay.
- [ ] Auto Trigger fires on the Pulse emergency; manual and auto produce the same flow.
- [ ] Quarantine works and abnormal data never updates the baseline.
- [ ] Status is computed in one place and is never by colour alone.
- [ ] Likely causes shown and labelled "suggestion, not diagnosis".
- [ ] Accuracy page content with real numbers and clear limits.
- [ ] (P1) Forecast with a range and an explanation view; webcam heart rate in the morning check.

## Out of Scope

- Rendering (Spec 2), emergency screens and protocol (Spec 4), content writing (Spec 5).
- A trained ECG classifier, federated learning, smart sensing, what-if mode (pitch only).
- Claims on real astronauts. Accuracy is measured on datasets; real-time performance with real astronauts may differ.

## Further Notes

- Be honest in labels: "Earth reference, no space data", "team value", "estimate, not validated".
- No open astronaut wearable stream exists; say so in the write-up.
