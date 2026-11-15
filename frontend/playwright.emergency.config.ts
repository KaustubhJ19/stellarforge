import { defineConfig } from "@playwright/test";
import path from "node:path";

// Set PYTHON to the interpreter with backend/requirements.txt installed (default: backend/.venv).
const PY = process.env.PYTHON ?? path.resolve(process.cwd(), "../backend/.venv/bin/python");

// Serves the BUILT app from the real backend (run `npm run build` first).
// The explainer points at a closed port so answers are deterministic (recorded / refused).
export default defineConfig({
  testDir: "e2e-emergency",
  timeout: 60_000,
  workers: 1,
  use: { baseURL: "http://127.0.0.1:8770", viewport: { width: 1024, height: 768 } },
  webServer: {
    command: `"${PY}" -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8770`,
    url: "http://127.0.0.1:8770/api/health",
    reuseExistingServer: false,
    env: { SF_PROTOCOL: "stub-protocol", SF_PROFILE: "stub-mars", SF_RECORDS: path.resolve(process.cwd(), "../replay/stub-crew-records.json"), SF_SIM: "1", SF_CLOCK_SPEED: "1", SF_OLLAMA_URL: "http://127.0.0.1:9" },
  },
});
