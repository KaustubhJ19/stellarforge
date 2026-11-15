# StellarForge

**Decision support, not diagnosis.** A hackathon prototype for the NASA Space Apps Challenge 2026, *Create Health Monitoring Software for Astronauts on Space Missions*. It is not medical advice.

## The problem

On the way to Mars there is no doctor on board, no quick way home, and Earth answers late: a message takes up to 20 minutes each way (NASA), and this project assumes 28.5 min. When a crewmember gets sick, the crew is on its own. They need to notice early that someone is drifting from their own normal. If it turns into an emergency, they need to know exactly what to do, one step at a time, from guidance they can trust.

## What StellarForge does

- **Learns each person's own normal** from their daily readings (heart rate, sleep, mood and others) and flags drift early, before it becomes an emergency.
- **Shows the whole crew on a 3D body**, so a non-doctor can see at a glance what is normal, what to watch and what needs action. A measurement card explains each reading: how to take it, why it matters in space (in NASA's own risk terms) and what to do if it is abnormal.
- **Walks the crew through an emergency** one cited step per screen. Every step comes from a published guideline (CPR in microgravity, Hinkelbein et al. 2020) and shows its source. "Why this step?" explains it from the guideline, even with no network.
- **Sends a ground report** automatically and shows when the reply can arrive, given the Mars delay.
- **Never names a drug or a dose.** Medication is always "per flight surgeon / onboard medical checklist".

## The story: a Mars chest-pain collapse

Day 152 of the Mars transit. Crew B reports chest pain. Minutes later their heart goes into a dangerous rhythm (unstable ventricular tachycardia). StellarForge's detection spots it in the live readings and raises **ACT NOW**. Crew B does not answer within 15 seconds, so the crew alarm sounds on crewmate A's tablet. A accepts, confirms crew B does not respond, and opens their record (the access is logged). Then A follows the steps: start CPR, the Evetts-Russomano compression method, and so on, each one citing the guideline. A ground report goes out at once. On Mars transit the reply is expected 57 minutes later, so the screen says to act on your own meanwhile. When the flight surgeon's reply arrives, it is saved with the event.

Watch it: [backup demo video](media/backup-demo-2026-11-15.webm) (real app and content, about 2 minutes).

## How accurate is it?

Measured on datasets, not on astronauts. Full numbers and how to re-run them: [accuracy page](accuracy.md).

- **False alerts:** 0.16 per crew-day, about one every 6 days per crew, on the four shared crew replays built from Earth wearable data (PMData). Most of them come from the daily self-reported wellness scores.
- **Slow drift:** a +10 bpm rise over 9 days is caught on day 8. Smaller drifts can hide inside normal life swings.
- **Emergency trigger:** fires at the first dangerous heart rhythm, or at a very fast or very slow heart rate with low blood pressure.
- **Webcam heart rate:** 4.9 bpm mean error on 5 consenting people (research data).
- **Tomorrow's readiness forecast:** 1.12 points mean error on a 0 to 10 scale, no better than "tomorrow = today". Its range covers the true answer 89.6 % of the time. The value is in the range and the explanation, not the number.

## What it covers, honestly

- **NASA risks:** StellarForge covers 3 of NASA's 17 Human Research Program risks (cardiovascular, sleep, behavioral health) and does not cover the other 14. Full map: [HRP risk map](hrp-risk-map.md).
- **Where the emergency guidance applies:** weightlessness only (spacecraft and station). Published guidance exists only for CPR in microgravity; CPR in partial gravity (Moon base, Mars base, rover) is not covered, and the app says so.
- **Every number has a label:** sourced, "team value", "Earth reference, no space data" or "estimate, not validated".
- **Medical review:** every step, Safety bound, card and recorded answer is listed for a clinician in the [medical review sheet](medical-review.md). At the time of writing: Medical content not clinically reviewed.

## Limitations

- No hardware. All live data is simulated or replayed.
- No open astronaut wearable stream exists. Normal days come from Earth wearable data (PMData), shaped to look like a crew.
- The collapse is a Pulse Physiology Engine simulation with no model of a blocked heart artery and a template ECG, labelled "estimate, not validated". Chest pain is crew-reported, not simulated.
- Accuracy is measured on datasets, not on astronauts. The detection cut-offs were tuned on the same four crews they are measured on, so the false-alert number is optimistic.
- Published space guidance exists only for CPR. CPR in partial gravity is not covered. The chest-pain steps for an ECG and a ready defibrillator come from an Earth guideline (ESC 2023).
- Most in-flight vital-sign shifts have no real source and are labelled "team value"; none is applied. The one exception is body temperature: +1 °C from a study of astronauts on long missions (Stahn 2017).
- The Mars delay default (28.5 min one way) exceeds NASA's stated 20 min maximum, by team choice.
- The female body's muscle, skeleton and vessel layers are approximate (resized from the male model).
- The demo runs in a laptop browser, with one local service standing in for the habitat network.
- **Future scope: the Collapse Copilot.** Its architecture is built and tested (briefing, rescuer choice, hash-chained decision record, ground-report section, L0 airway rule, L3 investigator, HotSummary adapter), but it is **off by default** (`content/copilot/copilot.json`). It needs training data and evaluation (scenario generator, L1/L2 ranking, golden replays, degraded modes) before it may advise a rescuer. With it off, routing and the approved protocols work as without it.

## Credits and AI use

- **Credits:** every dataset, model and asset, with its source and licence, is on the [Credits page](credits.md).
- **AI use:** every use of an AI tool is logged in the [AI-use log](si-log.md).
- **Code:** MIT. Derived 3D files: CC BY-SA 4.0.
