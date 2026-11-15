# Notes from detection (Spec 3) to the team (archived hand-off)

> Historical. The service hook below is applied in `backend/service.py` and its patch file was removed.

From the AI / detection lead, 2026-11-15. Branch `spec-3-detection-baseline` (includes the data lead's Spec 1 branch, merged).

## For the data lead

1. **Service hook (ready, tested).** `docs/service-detection-hook.patch` adds detection to `backend/service.py`:
   - adds an optional `detection` argument;
   - calls `on_message` for every delivered or posted event and `on_label` for Labels, then pushes what comes back;
   - wires it up in `main()` from the content file.

   Apply with:
   ```bash
   git apply docs/service-detection-hook.patch
   ```
   Checked: your 80 `backend/tests` still pass, and on the crew-A replay the service pushes 5 alerts and 28 reading-state updates. New message types: `alert` (Alert), `trigger` (Trigger), `reading_state` (Reading).
2. **Crew A's planted drift is too small to detect.** The plan is +6 bpm and −90 min over 9 days on p09. But p09's own resting heart rate swings 60 → 66 bpm around days 46–75, and the real values dip under the ramp, so the last day is only about +3 bpm above normal. Detection cannot tell it from normal life. Request, either:
   - **+10 bpm over 9 days** on crew A (caught on day 8 in our test), or
   - put the planted drift on the calmest participant (p01, now crew B).

   Measured with `tools/test_detection.py` and the tuning notes in ticket 13.
3. **Anchor window.** 14 days gives an Anchor spread of about 1 bpm, too tight for five months of real data. Detection now applies a minimum spread from content, so no change is needed, but a longer Anchor window would be more honest.
4. **Ticket 01 hand-over.** Dataset notes are in `docs/datasets.md`. Your replay tools already read the same files: PMData, OSDR EDA RR-1, Inspiration4 CBC/CMP.

## For the integration lead

1. **Cut-offs and Safety bounds.** `content/profiles/detection-cut-offs.json` holds every detection value with a label and source. It is a proposal: move or rename it if you prefer, and change `CONTENT` in `backend/detection.py` to match.
2. **Accuracy page and limits text.** `docs/accuracy.md` has the numbers and the "honest limits" wording for the write-up.
3. **Label format.** Detection reads crew tags from the Label's `note`: "false alarm", "normal" or "confirmed event". Label is not one of the seven contracts, so please confirm with the emergency-flow lead.

## For the emergency-flow and 3D / UI leads

- An `alert` with kind `emergency` carries urgency `ACT_NOW` and 2–3 `likely_causes`, each note ending "(suggestion, not diagnosis)".
- `deviation` is an object, not a number:
  - drift and acute alerts: `{sigma, cusum, combined}`;
  - Safety-bound alerts: `{value, bound}`.

  Show `deviation.sigma`, or the bound's label.
- Webcam heart rate for the morning check: `backend.webcam_hr.morning_check_reading(crew, t)` returns a Reading (source `camera`) to POST to `/reading`.

## For the 3D / home-screen lead (Spec 2)

- **Clearing a Status.** When a drift, acute or Safety-bound tier returns to green, detection sends one Alert with status `green` and urgency `ROUTINE` for that indicator and kind. Treat it as "this Alert is over". A green Alert never quarantines Readings.
- **Status words.** Normal / Watch / Alert. "ACT NOW" is the urgency word for emergencies only: a red Drift is red but MONITOR.
- **"Your normal" band.** Trimming mean ± 2 SD to the scale's limits is fine; it is display only. The SD floor (`min_anchor_sd`) is used inside detection; the crew record's Anchor SD is unchanged.

## For the integration lead (Spec 5), after your ticket 05 review

- **Names confirmed.** Detection reads `glucose` (mg/dL, from `tools/inspiration4_labs.py`) and `body_temperature` (°C, once the Pulse replay has it) under those names. A glucose Reading of 36 mg/dL gives a red Safety-bound Alert.
- **The shift does not move the Safety bound.** `expected_shift` only changes the Drift check against the Anchor. The 38 °C bound stays absolute, so healthy crew at about 37.8 °C in flight sit just under it. Raise the high bound or accept this; your call.
- **Shift now builds up from launch.** Applied in full on day 0, the +1 °C shift made a normal early-mission 36.8 °C look 1 °C low and raised a false drift alert after 3 days. Added `expected_shift_ramp_days` = 75 (Stahn 2017, "2.5 months") to the content file: the shift grows in a straight line from 0 at launch. Mission time `t` is taken as seconds from launch. Your content linter is clean on the file.

## Recorded replays (Spec 2, Spec 5, data lead)

`tools/record_replays.py` plays the shared replays through detection and Forecast B and writes them to `replay/recorded/` (same file names). Re-run after any replay or cut-off change:

```bash
python tools/record_replays.py --pmdata <PMData extracted folder> replay/crew-A.json replay/crew-B.json replay/emergency-crew-B.json replay/crew-C.json replay/crew-D.json
```

- **Added events** sit right after the event that caused them: `alert`, `trigger`, `reading_state` (quarantined, released or event) and `forecast` (provisional schema). An added event's `t` is its cause's time, so the file stays in time order. A Reading released a day later keeps its own time in `payload.t`: match it to the original Reading by `payload.t` and `payload.indicator`.
- **Crew B and its emergency** are played through one detection, so the emergency is judged against crew B's normal days.
- **Forecasts:** one per crew per day once all seven answers have arrived. Each crew's model is trained on PMData people other than that crew's own participant. A normal day's forecast has no label from the model, so the file says "estimate, not validated" (the provisional schema needs text).
- **Without PMData** (`--pmdata` left out), the files have no forecast events.

### Found while recording

- **New Anchors raised false alerts.** The shared crew records now have `steps` and `soreness` Anchors. Soreness had no minimum spread (B's spread is near 0) and steps swings by thousands a day. Added floors to the content file (soreness 1, like the other 1-5 scores; steps 4000, team value). False alerts were 0.13 per crew-day after the floors. With crew D now PMData p10 (female, answers the wellness questions), they are 0.16 per crew-day; most extra alerts are on self-reported scores (readiness, fatigue, stress). Not re-tuned, to avoid tuning again on the same four crews; `docs/accuracy.md` is updated.
- **"re-measure" on almost every day for crews A, C and D.** The conformal range has one fixed width per model, so the 6-point rule is all-or-nothing per crew: B's model is under 6 points, A, C and D's are over. To be fixed in Forecast B (a range that varies by day, or a different rule); not changed yet.
- **The emergency's only likely cause is `steps`.** Crew B has no planted drift, so nothing else is more than 1 Anchor spread off on that day. It is labelled "suggestion, not diagnosis" but looks odd in a demo. Crew A's drift is still +6 bpm (see item 2 for the data lead above).
