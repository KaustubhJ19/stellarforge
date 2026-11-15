import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // contracts/ and content/ live at the repo root, shared with the other streams.
  server: {
    fs: { allow: [".", "../content", "../contracts"] },
    proxy: { "/api": "http://127.0.0.1:8000" }, // Spec 4's emergency service
  },
  // Two pages: the replay app (index.html) and Spec 4's emergency flow (emergency.html).
  build: { rollupOptions: { input: { main: "index.html", emergency: "emergency.html" } } },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"], // e2e/ runs under Playwright
    setupFiles: ["./src/test/setup.ts"],
  },
});
