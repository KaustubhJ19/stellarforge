# Emergency flow: rehearsal path

Everything runs locally. See the README for one-time setup. The service starts with the real CPR protocol, the Mars transit profile and crew A to D. It is decision support, not diagnosis, and the medical content is not yet clinically reviewed (`docs/medical-review.md`).

## Run the demo
```bash
cd frontend && npm run build && cd ..
SF_SIM=1 backend/.venv/bin/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
`SF_SIM=1` turns on the demo-clock and reset helpers (`/api/sim/*`); leave it off for anything else. Ollama starts by itself if it is installed (`docs/explainer.md`).

Open: `http://127.0.0.1:8000/emergency.html?crew=B` (patient), `?crew=A` (rescuer), `?crew=C` (Rescuer 2), `?view=console` (ground). The health app is at `/`.
Optional: `SF_HABITAT_URL=http://127.0.0.1:8765` to run against the habitat service (`backend/service.py`), which then owns the Mission clock.

## Script (about 3 minutes)
1. Patient tablet: **Emergency** → verdict "Urgency not assessed (manual start)", two questions, countdown.
2. Don't answer. After 15 s every other tablet rings **CREW ALARM**.
3. Rescuer: **Accept** → "Does the patient respond?" → **No response** → record (access logged) → contributors → one cited step per screen → **Why this step?** → ground report with "Expected reply at T+57 min".
4. Third tablet: **Join as Rescuer 2** → its own steps (role map).
5. Skip mission time for the delay (demo clock): (start the backend with `SF_SIM=1` for this and the reset step) `curl -X POST localhost:8000/api/sim/clock/advance -H "Content-Type: application/json" -d "{\"seconds\":1710}"`.
6. Console: report has arrived → type a reply (or **Send scripted fallback reply** if the console is too slow) → advance 1710 s again → reply shows on the rescuer's report and is stored as a Label.
7. Backend down: stop uvicorn → tablets show "Service unavailable — continuing offline" → **Help a crewmate** → offline cited steps. Restart → queue syncs.
8. Reset between runs: `POST /api/sim/reset`.

## Checks before going on stage
```bash
backend/.venv/Scripts/python -m pytest contracts backend/tests tools -q   # run each folder separately if conftest names clash
cd frontend && npx vitest run && npm run build && npx playwright test
```
- Run once with Wi-Fi physically off (not yet done on the rehearsal machine).
