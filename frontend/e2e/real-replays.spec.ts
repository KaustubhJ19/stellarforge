import { expect, test } from "@playwright/test";
import { openApp, waitForBody } from "./helpers";

// Ticket 12: the data lead's real replays (replay/ on workstream-1-data-service, copied to
// public/replay/shared/ by scripts/sync-replays.mjs), rendered end to end with no service.
const CREW_A = "/?replay=/replay/shared/crew-A.json&cabin=/replay/shared/iss-cabin-dose-RR-1.json";

test.describe("real replays from Spec 1", () => {
  test("crew A (152 days) with the RR-1 cabin: home, body, charts and mission bar", async ({ page }) => {
    const t0 = Date.now();
    const problems = await openApp(page, CREW_A);
    await waitForBody(page);
    const bar = page.getByRole("region", { name: "Mission" });
    await expect(bar).toContainText("Day 152");
    await expect(bar).toContainText("Mars transit");
    // The cabin data stops early (last dose on day 39), so the dose says how old it is and no
    // CO₂ banner shows.
    await expect(bar).toContainText(/as of Day \d+/);
    await expect(page.getByRole("status", { name: "Cabin CO₂" })).toHaveCount(0);
    const physical = page.getByRole("region", { name: "Physical health" });
    for (const name of ["Resting heart rate", "Steps", "Muscle soreness"]) {
      await expect(physical.getByRole("group", { name, exact: true })).toBeVisible();
    }
    const mental = page.getByRole("region", { name: "Mental health" });
    for (const name of ["Stress", "Fatigue", "Sleep", "Mood", "Readiness"]) {
      await expect(mental.getByRole("group", { name, exact: true })).toBeVisible();
    }
    await expect(physical.getByRole("group", { name: "Resting heart rate", exact: true })).toContainText(/\d+(\.\d)? bpm/);
    const trends = page.getByRole("region", { name: "Trends" });
    await trends.getByRole("button", { name: "Resting heart rate" }).click();
    await expect(page.getByRole("figure", { name: "Resting heart rate trend" })).toBeVisible();
    await expect(page.getByRole("figure", { name: "Resting heart rate trend" }).getByLabel(/Your normal/)).toBeVisible();
    console.log(`crew A + cabin: home ready in ${Date.now() - t0} ms`);
    await page.getByRole("figure", { name: "Resting heart rate trend" }).screenshot({ path: "test-results/real-crew-A-trend.png" });
    await page.screenshot({ path: "test-results/real-crew-A.png", fullPage: false });
    expect(problems).toEqual([]);
  });

  test("crew A scrubbed into the cabin's 42 days: dose current, CO₂ checked live", async ({ page }) => {
    const problems = await openApp(page, CREW_A);
    await page.getByRole("slider", { name: "Mission clock" }).fill(String(20 * 86400 + 12 * 3600));
    const bar = page.getByRole("region", { name: "Mission" });
    await expect(bar).toContainText("Day 21");
    await expect(bar).toContainText("mGy");
    await expect(bar).not.toContainText("as of");
    expect(problems).toEqual([]);
  });

  test("crew B's emergency (Pulse, 1 s readings): rhythm in words, temperature in °C", async ({ page }) => {
    const t0 = Date.now();
    const problems = await openApp(page, "/?replay=/replay/shared/emergency-crew-B.json");
    await waitForBody(page);
    const physical = page.getByRole("region", { name: "Physical health" });
    await expect(physical.getByRole("group", { name: "Heart rhythm" })).toContainText(/[A-Z][a-z]+( [a-z]+)*/);
    await expect(physical.getByRole("group", { name: "Body temperature" })).toContainText("°C");
    await expect(physical.getByRole("group", { name: "Heart rate", exact: true })).toContainText("/min");
    await expect(page.getByRole("region", { name: "Mission" })).toContainText("Day 153");
    console.log(`emergency crew B: home ready in ${Date.now() - t0} ms`);
    await page.screenshot({ path: "test-results/real-emergency-B.png", fullPage: false });
    expect(problems).toEqual([]);
  });
});
