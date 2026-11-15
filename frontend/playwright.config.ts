import { defineConfig } from "@playwright/test";
import path from "node:path";

const PY = path.resolve(process.cwd(), "../backend/.venv/Scripts/python.exe");

// Two suites, two servers:
// - "home" (Spec 2): the production build served as static files, no backend service.
// - "emergency" (Spec 4): the built app served by the Spec 4 backend; the explainer points at a
//   closed port so answers are deterministic (recorded / refused).
export default defineConfig({
  timeout: 60_000,
  retries: 0,
  workers: 1,
  reporter: [["list"]],
  projects: [
    {
      name: "home",
      testDir: "./e2e",
      testMatch: ["journeys.spec.ts", "accessibility.spec.ts", "robustness.spec.ts"],
      use: {
        baseURL: "http://localhost:4173",
        viewport: { width: 1440, height: 900 },
        launchOptions: { args: ["--use-angle=metal", "--enable-gpu"] },
      },
    },
    {
      name: "emergency",
      testDir: "./e2e",
      testMatch: ["emergency.spec.ts", "glove.spec.ts"],
      use: { baseURL: "http://127.0.0.1:8770", viewport: { width: 1024, height: 768 } },
    },
  ],
  webServer: [
    {
      command: "npx vite build && npx vite preview --port 4173 --strictPort",
      url: "http://localhost:4173",
      reuseExistingServer: false,
      timeout: 120_000,
    },
    {
      command: `"${PY}" -m uvicorn app.main:app --app-dir ../backend --host 127.0.0.1 --port 8770`,
      url: "http://127.0.0.1:8770/api/health",
      reuseExistingServer: false,
      env: { SF_CLOCK_SPEED: "1", SF_OLLAMA_URL: "http://127.0.0.1:9" },
    },
  ],
});
