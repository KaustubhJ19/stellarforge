# StellarForge

An offline, 3D-body health tool for non-doctor astronauts. Built for the **NASA Space Apps Challenge 2026**: *Create Health Monitoring Software for Astronauts on Space Missions*.

It learns each person's own normal, flags drift early, and walks the crew through an emergency (the Mars chest-pain collapse) one cited step per screen, with an automatic ground report that accounts for the Mars delay.

> **Decision support, not diagnosis.** Prototype for a hackathon. Not medical advice.

## What is in it

| Part | What it does | Where |
|---|---|---|
| Health app | See-through 3D body that glows from each Indicator's Status, trends, forecast, crew forms | `frontend/` (`index.html`) |
| Detection | Personal baseline, Acute and Drift alerts, readiness forecast | `backend/detection.py`, `baseline_a.py`, `forecast_b.py` |
| Habitat service | Mission clock, SQLite store, replays, Alerts and Triggers pushed to windows | `backend/service.py` |
| Emergency flow | Crew alarm, rescuer tasks, cited protocol steps, ground report and console, offline mode | `backend/app/`, `frontend/src/emergency/` (`emergency.html`) |
| Content | Protocols, measurement cards, mission profiles, detection cut-offs (every item sourced) | `content/` |

## Quick start

Needs Python 3.11+ and Node.js 20+.

```bash
# Backend (from the repo root)
python3 -m venv backend/.venv && source backend/.venv/bin/activate
pip install -r backend/requirements.txt -r contracts/requirements.txt
python -m pytest backend contracts tools          # unit and integration tests
python tools/lint_content.py                      # content linter: sources present, no doses

# Frontend
cd frontend
npm ci
npm run dev                                       # health app on http://localhost:5173 (replay files, no service)
npm test                                          # unit tests
npm run test:e2e                                  # browser tests (npx playwright install chromium first)
```

Emergency flow, which needs the service:

```bash
cd frontend && npm run build && cd ..
python -m uvicorn app.main:app --app-dir backend --port 8000
# open http://localhost:8000/emergency.html  (tablets: ?crew=<id>, ground console: ?view=console)
```

See [frontend/README.md](frontend/README.md) for the app's options and [docs/rehearsal.md](docs/rehearsal.md) for the demo script.

## Repo layout

```
backend/     Python: detection, habitat service (service.py), emergency service (app/)
frontend/    React + Three.js: health app (src/) and emergency flow (src/emergency/)
contracts/   Shared JSON Schemas. The only shapes that cross a stream boundary
content/     Protocols, measurement cards, mission profiles (protocols/, cards/, profiles/)
replay/      Pre-generated crew days, emergency episode, ISS cabin data (JSON)
tools/       Content linter, replay generators, golden-replay and accuracy tests
docs/        Datasets, accuracy, cut-offs, rehearsal script, AI-use log (see docs/README.md)
```

## Working rules

- **Contracts first.** Add a field to a contract only by agreement in the team chat. Never remove one.
- **One test seam.** A replay file goes in; the alerts, status and screens that come out are checked.
- **Cite everything.** Every protocol step and threshold needs a source. No drug names or doses, ever (`tools/lint_content.py` enforces it).
- **Honest labels.** Use "team value", "Earth reference, no space data", "estimate, not validated" where they apply.
- **Log AI use.** Add every use of an AI tool to `docs/si-log.md` (who, which tool, what for). The event requires a statement.
- **Commits:** `type: description` (feat, fix, docs, test, chore, refactor). Open a pull request; do not push to `main`.

## Known limitations

- No hardware. All live data is simulated or replayed.
- No open astronaut wearable stream exists. Normal days come from Earth wearable data (PMData).
- The collapse is a Pulse approximation, labelled "estimate, not validated".
- Published space guidance exists only for CPR. Partial-gravity CPR is not covered.
- Accuracy is measured on datasets, not real astronauts.
- The emergency service trusts who a tablet says it is (`crew=`, `actor=`, `viewer=` in the request). There is no sign-in, so it is for a trusted habitat network only; the record access log shows who asked, not who was verified. Demo helpers (`/api/sim/*`) are off unless the service starts with `SF_SIM=1`.

## Licence

Code: MIT (see [LICENSE](LICENSE)). Derived 3D assets: CC BY-SA 4.0. Every dataset, model and asset is credited in `docs/`.
