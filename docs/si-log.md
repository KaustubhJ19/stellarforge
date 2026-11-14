# SI-use log

Every use of an AI tool on this project: who, which tool, what for.

| Date | Who | Tool | What for |
|---|---|---|---|
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 01 (Spike D): found PMData, OSDR ISS cabin (RR-1) and Inspiration4 CBC/CMP files, checked licences, readiness scale, OSD ID-to-panel mapping and cabin units; drafted `docs/datasets.md`. All findings checked against the source files. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 02 (Spike E): wrote the classic webcam heart-rate method (POS, Wang 2017) in `backend/webcam_hr.py` and its test in `tools/test_webcam_hr_spike.py`. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 02 (Spike E) go/no-go: found and downloaded 5 consenting UBFC-rPPG subjects, wrote `tools/test_webcam_hr_ubfc.py` and `bpm_from_video`, measured mean error 4.9 bpm → GO. Result to be checked by Vedant. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Ticket 11 (Forecast B, P1): wrote `backend/forecast_b.py` (gradient-boosted trees, MAPIE range, SHAP drivers, personal residual correction) and `tools/test_forecast_b.py`; measured on held-out PMData people: mean error 1.12, coverage 89.6 %. Result to be checked by Vedant. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Tickets 03, 04, 06, 07, 09 (Baseline A core): wrote `backend/baseline_a.py` (Anchor CuSum drift, 28-day Adaptive acute check, quarantine with Label hooks, Status and urgency rule, briefing text) and `tools/test_baseline_a.py`, before Spec 1 contracts exist. Result to be checked by Vedant. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Tickets 05 and 08: wrote `backend/emergency.py` (auto-detect rule, manual Trigger, emergency Alert) and `likely_causes()` in `backend/baseline_a.py`, with `tools/test_emergency.py`, before Spec 1 contracts exist. Result to be checked by Vedant. |
| 2026-11-14 | Vedant (AI / detection lead) | Claude Code (Claude Opus 5.5) | Listed every detection cut-off that needs a team value in `docs/cut-offs-needed.md`, with suggested start values and possible sources (not yet checked). To be checked by Vedant and the integration lead. |
