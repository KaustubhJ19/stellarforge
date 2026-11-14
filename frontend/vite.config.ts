import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // Dev only: the Spec 4 backend (FastAPI) serves /api; in production it serves the built app too.
  server: { proxy: { "/api": "http://127.0.0.1:8000" } },
  // `vite preview` must not inherit the dev proxy: Spec 2's e2e suite runs it with no service.
  preview: { proxy: {} },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"], // e2e/ runs under Playwright
    setupFiles: ["./src/test/setup.ts"],
  },
});
