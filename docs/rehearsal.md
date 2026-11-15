# Emergency flow — rehearsal path (Spec 4)

Everything runs locally. STUB protocol content is non-clinical test data until Spec 5 delivers.

## One-time setup
```bash
python -m venv backend/.venv
backend/.venv/Scripts/python -m pip install fastapi "uvicorn[standard]" pydantic jsonschema httpx pytest
cd frontend && npm install && npx playwright install chromium && npm run build
```
Ollama with `llama3.2:3b` pulled (`ollama pull llama3.2:3b`). Without it, "Why this step?" shows labelled recorded answers.

## Run the demo
```bash
backend/.venv/Scripts/python -m uvicorn app.main:app --app-dir backend --host 127.0.0.1 --port 8000
```
Open: `http://127.0.0.1:8000/?crew=cmdr` (patient), `/?crew=eng` (rescuer), `/?crew=sci` (Rescuer 2), `/console` (ground).
Optional: `SF_HABITAT_URL=http://127.0.0.1:8765` to run against Spec 1's habitat service (it then owns the Mission clock).

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
