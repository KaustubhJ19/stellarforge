# Notes from detection (Spec 3) to the team

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
