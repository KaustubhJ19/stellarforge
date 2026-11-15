# Plan coverage

The implementation plan (`IMPLEMENTATION-PLAN.md`, kept outside the repo) against what is in `main`. Checked on 2026-11-15 by reading the code, running the full test suites and recording the demo end to end.

Legend: **Done** is in the repo and tested. **Partial** exists but not as the plan describes. **Missing** is not in the repo.

## P0 (must exist for the video)

| Plan item | Status | Where / note |
|---|---|---|
| Seven frozen contracts | Done | `contracts/*.schema.json`, validated by `contracts/validate.py` |
| Replay data | Done | `replay/` (crew A to D, Pulse emergency, ISS cabin, Inspiration4 labs) |
| Mission clock (1x, 60x, skip) | Done | `backend/mission_clock.py`, `backend/app/clock.py` |
| Habitat service, SQLite, replay player | Done | `backend/service.py`, `backend/store.py` |
| Home screen: 3D body, status glow, mission bar, living heart | Done | `frontend/src/` (`body/`, `home/`) |
| Trend charts with baseline band, alert markers, scrubber | Done | `frontend/src/charts/` |
| Baseline A: Acute and Drift alerts, Anchor, CuSum | Done | `backend/baseline_a.py`, `backend/detection.py` |
| Quarantine | Done | `backend/baseline_a.py` |
| **Daily briefing text** ("resting heart rate +6 bpm over 9 days") | **Missing** | No code found for it. Alerts and likely causes exist, but no morning briefing sentence. |
| Auto-detect rule, manual Emergency button, same flow | Done | `backend/detection.py`, `backend/app/flow.py`, Spec 4 e2e |
| Urgency verdict, 15 s crew alarm (sound plus visual) | Done | `backend/app/flow.py`, `frontend/src/emergency/alarm.ts` |
| Rescuer takeover, access log, likely contributors | Done | `backend/app/flow.py` |
| Cited protocol, one step per screen, equipment and rescuer filters | Done | `content/protocols/microgravity-cpr.json`, `chest-pain.json` |
| "Why this step?" explainer (Ollama, cites, refuses) | Done | `backend/app/explainer.py`, `backend/app/ollama_boot.py` |
| Ground report with delay, ground console, reply stored as Label | Done | `backend/app/ground.py`, `frontend/src/emergency/Console.tsx` |
| Content linter (every step sourced, no drugs or doses) | Done | `tools/content_lint.py`, `tools/lint_content.py` |
| Measurement cards (How / Why / If abnormal, NASA HRP risk) | Done | `content/cards/` (6 cards) |
| Accuracy page inside the app | Done | Footer button "How accurate is this?" (`frontend/src/about/AccuracyPage.tsx`, data in `content/accuracy.json`, kept in step with `docs/accuracy.md` by `tools/tests/test_accuracy_json.py`) |
| Credits page inside the app | Done | Footer button "Credits" (`frontend/src/about/CreditsPage.tsx`), read directly from `content/credits.json` |
| "Decision support, not diagnosis" labels | Done | Every emergency screen, README, write-up |

## P1 (after the P0 slice)

| Plan item | Status | Where / note |
|---|---|---|
| Webcam heart rate | Partial | Algorithm and accuracy test done (`backend/webcam_hr.py`, mean error 4.9 bpm on UBFC-rPPG). **No morning-check screen uses it.** |
| Readiness forecast B, conformal range, SHAP "Why this forecast?" | Done | `backend/forecast_b.py`, `frontend/src/forecast/` |
| ISS cabin replay and CO2 banner | Done | `replay/iss-cabin-dose-RR-1.json`, `frontend/src/home/Co2Banner.tsx` |
| Stand test and post-EVA forms (Apollo reference) | Done | `frontend/src/forms/` |
| Profile switcher (delay, kit, Safety bounds) | Done | `content/profiles/`, `frontend/src/profiles.ts` |
| **Check-in streaks** | **Missing** | Not found in code. |
| Female model | Done | `frontend/public/models/body-female*.glb` |
| **Hosted replay on GitHub Pages** | **Missing** | No `.github/` workflow. The app is built (`npm run build`) and could be hosted as static files. |

## Data sets

The generated replays are in the repo, so **running the app needs no raw data**. The raw downloads are kept out of the repo on purpose (`data/` is git-ignored; sizes and licences in `docs/datasets.md`). They are only needed to regenerate replays or to run the 7 data-dependent tests (skipped by default).

| Data | In the repo? | Needed to run? | Needed to rebuild or test? |
|---|---|---|---|
| PMData (normal days, forecast target) | Replays only (`replay/crew-*.json`) | No | Yes, 1.4 GB from `datasets.simula.no/pmdata/` |
| Pulse emergency episode | Replay only (`replay/emergency-crew-B.json`) | No | Yes, Windows Pulse bundle (`STELLARFORGE_RUN_PULSE=1`) |
| ISS cabin and radiation (OSDR EDA, RR-1) | Replay only | No | Yes, fetch with `tools/cabin_dose_replay.py --fetch RR-1` |
| Inspiration4 blood counts (OSD-569) | Replays only (blood counts) | No | Yes, download from OSDR |
| Inspiration4 metabolic panel (OSD-575) | No (numbers cited in the glucose Safety bound) | No | No |
| Apollo AP005 return-to-gravity values | Yes, in `content/profiles/detection-cut-offs.json` (group means) | Yes | No |
| 3D body (Z-Anatomy, HRA) | Yes, `frontend/public/models/` (credits in `LICENSE.md`) | Yes | Blender export: `tools/anatomy/` |
| UBFC-rPPG (webcam accuracy) | No, results only (`docs/datasets.md`) | No | Yes (`UBFC_DIR`) |
| **CGMacros (simulated glucose stream)** | **No** | No | Not used: glucose is a manual entry card and a Safety bound only |
| Optional extras (MMASH, SleepAccel, others) | No | No | Not used |

## Submission checklist

| Item | Status |
|---|---|
| Code licence MIT, assets CC BY-SA 4.0 | Done (`LICENSE`, `frontend/public/models/LICENSE.md`) |
| SI-use log | Done (`docs/si-log.md`). The final SI-use statement for the submission form is still to be written from it. |
| Write-up | Draft done (`docs/write-up.md`) |
| Credits | Done as a document (`docs/credits.md`) |
| Backup recording | Done (`docs/media/backup-demo-2026-11-15.webm`). The recorder script was re-run on 2026-11-15 and completes all 13 scenes (`docs/backup-demo.md`); the committed video is the earlier one. |
| **Clinical review of protocol and Safety bounds** | **Not done.** `docs/medical-review.md` needs a qualified reviewer's sign-off. |
| Demo video, team contact details, final submission | Owner's task, not in the repo |
| **Deadline** | Sun 15 Nov 2026, 11:59 PM Melbourne time |

## Known engineering gaps

- The emergency service trusts who a tablet says it is (no sign-in); see the README limits.
- Two content linters overlap (`tools/lint_content.py`, `tools/content_lint.py`).
- The emergency backend (`backend/app/`) has its own store, clock and replay code beside Spec 1's (`backend/store.py`, `mission_clock.py`).
- The auto-detect Trigger reaches the emergency service through the demo driver (`tools/demo/demo_collapse.py`) or the habitat service wiring (`SF_HABITAT_URL`), not through the health app.
