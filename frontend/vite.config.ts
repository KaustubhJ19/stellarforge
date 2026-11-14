import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  // contracts/ and content/ live at the repo root, shared with the other streams.
  server: { fs: { allow: [".", "../content", "../contracts"] } },
  test: {
    environment: "jsdom",
    globals: true,
    include: ["src/**/*.test.{ts,tsx}"], // e2e/ runs under Playwright
    setupFiles: ["./src/test/setup.ts"],
  },
});
