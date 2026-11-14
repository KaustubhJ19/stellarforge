# AI-use log

Every use of an AI tool on this project: who, which tool, what for.

| Date | Who (stream) | Tool | What for |
|---|---|---|---|
| 2026-11-14 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | Broke Spec 2 into tickets; wrote the Z-Anatomy body export script (Spike B) and the Spec 2 web app (3D body, home screen, charts) test-first, with human review |
| 2026-11-14 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | Tested the Spec 2 web app (coverage, Playwright browser tests, large-replay and slow-device runs, keyboard / high-contrast / reduced-motion checks, colour-blind palette validation, security review) and fixed the issues found, with human review and decisions |
| 2026-11-15 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | Switched the Spec 2 web app to Spec 1's frozen contracts (ticket 12): Status from Alerts, Crew record loading, anchor-based normal band, profile table, fixtures checked against the shared schemas, with human decisions and review |
| 2026-11-15 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | P1 tickets 14-16 (CO₂ banner, forms, forecast view), Spec 5 cards and profile, Spec 3 alignment, real Spec 1 replays end to end, and the merge branch for emergency_services, test-first with human decisions and review |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 01 (Spike D): found PMData, OSDR ISS cabin (RR-1) and Inspiration4 CBC/CMP files, checked licences, readiness scale, OSD ID-to-panel mapping and cabin units; drafted `docs/datasets.md`. All findings checked against the source files. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 02 (Spike E): wrote the classic webcam heart-rate method (POS, Wang 2017) in `backend/webcam_hr.py` and its test in `tools/test_webcam_hr_spike.py`. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 02 (Spike E) go/no-go: found and downloaded 5 consenting UBFC-rPPG subjects, wrote `tools/test_webcam_hr_ubfc.py` and `bpm_from_video`, measured mean error 4.9 bpm → GO. Result to be checked by Vedant. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 11 (Forecast B, P1): wrote `backend/forecast_b.py` (gradient-boosted trees, MAPIE range, SHAP drivers, personal residual correction) and `tools/test_forecast_b.py`; measured on held-out PMData people: mean error 1.12, coverage 89.6 %. Result to be checked by Vedant. |
