import { defineConfig } from "@playwright/test";

// End-to-end tests run against the production build served as static files,
// so they exercise the real app with no backend service.
export default defineConfig({
  testDir: "./e2e",
  timeout: 60_000,
  retries: 0,
  reporter: [["list"]],
  use: {
    baseURL: "http://localhost:4173",
    viewport: { width: 1440, height: 900 },
    launchOptions: { args: ["--use-angle=metal", "--enable-gpu"] },
  },
  webServer: {
    command: "npx vite build && npx vite preview --port 4173 --strictPort",
    url: "http://localhost:4173",
    reuseExistingServer: false,
    timeout: 120_000,
  },
});
