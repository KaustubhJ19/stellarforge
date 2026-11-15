# Demo video: script and failure plan (ticket 13)

About 3 minutes. Check the length against the Submission Guide (ticket 01). Every claim in the narration is backed by `docs/write-up.md` and the pages it links. Say "Decision support, not diagnosis" once, on screen or aloud.

## Before recording

1. **Freeze:** after H24 only bug fixes. The integration lead calls it in the team chat.
2. **Start the demo with the real content** (macOS / Linux; on Windows use `.venv\Scripts\python`):
   ```bash
   cd frontend && npx vite build && cd ..
   SF_SIM=1 SF_PROTOCOL=microgravity-cpr SF_PROFILE=mars_transit SF_RECORDS=$PWD/replay/crew-records.json \
     .venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
   ```
   Tablets: `http://127.0.0.1:8000/?crew=B` (patient), `/?crew=A` (rescuer), `/?crew=C` (Rescuer 2), `/console` (ground). Reset between takes: `curl -X POST localhost:8000/api/sim/reset -H 'content-type: application/json' -d '{}'`.
3. **Collapse:** run `.venv/bin/python tools/demo/demo_collapse.py out/collapse.json` (Spec 3 detection on the real crew B replay). Then post the Alert and the Trigger from that file to `/api/stream/alert` and `/api/stream/trigger`, or let `tools/demo/record_demo.mjs` do it.
4. **Check:** `python tools/content_lint.py` is clean, and the first CPR step shows "Hinkelbein … Recommendation 14".

## Script

| Time | Scene | On screen | Narration (plain words) |
|---|---|---|---|
| 0:00 | Hook | Home screen, crew B: mission bar "Mars transit", "Ground delay 28.5 min, team value", 3D body | "Six months from Mars, no doctor on board, and Earth answers 57 minutes late. StellarForge helps a crew of non-doctors keep each other alive." |
| 0:20 | Morning check | Home: Physical and Mental health tiles with Normal / Watch, a trend chart, a measurement card | "Every morning it compares each person with their own normal, not an average. Amber means watch; red means act. Each card says how to measure, why it matters in NASA's own risk terms, and what to do." |
| 0:50 | Collapse | Patient tablet: **ACT NOW** after Spec 3 detection flags ventricular tachycardia in crew B's replay; no answer for 15 s, then **CREW ALARM** on A's tablet | "Day 152. Crew B reported chest pain; now the rhythm turns dangerous. Detection raises ACT NOW. No answer, so the crew alarm sounds and crewmate A takes over." |
| 1:20 | Guidance | A: record opens (access logged), contributors (none invented), "Step 1 of 9" with the Hinkelbein citation, **Why this step?** | "One step per screen, each from the published guideline for CPR in microgravity, with its source. 'Why this step?' explains it, even offline. It never names a drug or a dose; that stays with the flight surgeon." |
| 2:00 | Ground | Ground report "Expected reply at T+57 min"; console: in transit, then arrives; reply reaches A and is saved | "A report goes to Earth at once. On Mars transit the reply takes 57 minutes, so the crew acts on its own meanwhile. When the flight surgeon answers, the reply is saved with the event." |
| 2:30 | Close | `docs/accuracy.md`, `docs/hrp-risk-map.md`, `docs/credits.md` (repo pages); disclaimer | "Measured on datasets, not on astronauts: 0.16 false alerts per crew-day. It covers 3 of NASA's 17 health risks, and we list the 14 it does not. Decision support, not diagnosis. The same engine could serve a remote clinic on Earth." |

## Failure plan

| If this fails during the demo | Do this |
|---|---|
| Backend / service down | The tablets continue offline with the real cited steps ("Help a crewmate"); restart uvicorn and the queue syncs. Or run from the replay files with `tools/demo/record_demo.mjs`. |
| Explainer slow or no Ollama | Leave it: "Why this step?" shows the labelled recorded answer from `content/protocols/*.recorded.json`. |
| Webcam fails | Not in this demo: the webcam heart rate is not wired into the app. Skip it and quote the accuracy number (4.9 bpm mean error). |
| Total failure | Play the backup recording: `docs/media/backup-demo-2026-11-15.webm`. |

## Known gaps before the final take

- **Blocked on `main` (Spec 1 / Spec 4):** Spec 4 on `main` no longer reads `SF_RECORDS`, so the demo server loads the stub crew records (`cmdr`, `eng`, …), and its `load_records` needs `{"records": [...]}` while Spec 1's `replay/crew-records.json` is a bare list. Until Spec 4 accepts a records path again and the two formats agree, the real crew A–D cannot be served, so `record_demo.mjs` cannot be re-run as written. The committed video was recorded before that change. The demo endpoints also need `SF_SIM=1`.

- **Measurement cards are empty in the app:** Spec 2's `main.tsx` does not pass `cards` yet. Wire `content/cards-frontend.json` (see `docs/notes-from-integration.md`), or skip the card close-up in the morning-check scene.
- **No Accuracy or Credits page in the app:** show the repo pages (`docs/accuracy.md`, `docs/credits.md`) in the close.
- **Spec 4 defaults to the stub content:** always start with the `SF_PROTOCOL` / `SF_PROFILE` / `SF_RECORDS` settings above.
