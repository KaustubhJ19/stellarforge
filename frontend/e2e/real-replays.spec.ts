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

// Spec 3's recorded replays (replay/recorded/, tools/record_replays.py): the real crew data plus
// detection output (alert, reading_state) and daily forecasts.
const RECORDED_A = "/?replay=/replay/shared/recorded/crew-A.json&cabin=/replay/shared/iss-cabin-dose-RR-1.json";

test.describe("recorded replays from Spec 3", () => {
  test("crew A: real Alerts colour the tiles, and the forecast panel fills", async ({ page }) => {
    const problems = await openApp(page, RECORDED_A);
    await waitForBody(page);
    const physical = page.getByRole("region", { name: "Physical health" });
    await expect(physical.getByRole("group", { name: "Steps", exact: true })).toHaveAttribute("data-status", "amber");
    const forecast = page.getByRole("region", { name: "Readiness forecast" });
    await expect(forecast).toContainText("of 10");
    await expect(forecast).toContainText("Re-measure: the range is too wide to trust.");
    await page.getByRole("button", { name: "Why this forecast?" }).click();
    await expect(page.getByRole("list", { name: "Drivers" }).getByRole("listitem")).toHaveCount(7);
    await page.getByRole("button", { name: "Back to body" }).click();
    // Day 55 (t = 4,690,800 s): resting heart rate's drift Alert is red.
    await page.getByRole("slider", { name: "Mission clock" }).fill(String(4_690_800 + 3600));
    await expect(physical.getByRole("group", { name: "Resting heart rate", exact: true })).toHaveAttribute("data-status", "red");
    await expect(physical.getByRole("group", { name: "Resting heart rate", exact: true })).toContainText("Alert");
    await page.screenshot({ path: "test-results/recorded-crew-A.png" });
    expect(problems).toEqual([]);
  });

  test("emergency crew B: the Safety-bound Alert turns heart rate red", async ({ page }) => {
    const problems = await openApp(page, "/?replay=/replay/shared/recorded/emergency-crew-B.json");
    await waitForBody(page);
    await page.getByRole("slider", { name: "Mission clock" }).fill(String(13_134_941 + 5));
    const physical = page.getByRole("region", { name: "Physical health" });
    await expect(physical.getByRole("group", { name: "Heart rate", exact: true })).toHaveAttribute("data-status", "red");
    await expect(physical.getByRole("group", { name: "Systolic", exact: false })).toHaveAttribute("data-status", "red");
    expect(problems).toEqual([]);
  });
});

test.describe("real female crew member (crew D, PMData p10)", () => {
  for (const [label, replay] of [
    ["Spec 1's replay", "/replay/shared/crew-D.json"],
    ["Spec 3's recording", "/replay/shared/recorded/crew-D.json"],
  ] as const) {
    test(`${label} opens the female body and ends on day 121`, async ({ page }) => {
      const models: string[] = [];
      page.on("request", (r) => r.url().includes("/models/") && models.push(r.url().split("/models/")[1]));
      const problems = await openApp(page, `/?replay=${replay}`);
      await expect(page.locator('.body-host[data-model="female"][data-loaded="true"]')).toBeVisible({ timeout: 30_000 });
      await expect(page.getByText(/Female organs\. Muscles, skeleton and vessels are approximate/)).toBeVisible();
      expect(models).toEqual(["body-female.glb"]);
      // Crew D's data runs from day 6 to day 120 (mission clock days, shown 1-based).
      await expect(page.getByRole("region", { name: "Mission" })).toContainText("Day 121");
      expect(problems).toEqual([]);
    });
  }

  test("Spec 3's recording of crew D carries real Alerts and a forecast", async ({ page }) => {
    const problems = await openApp(page, "/?replay=/replay/shared/recorded/crew-D.json");
    await waitForBody(page);
    await expect(page.getByRole("region", { name: "Readiness forecast" })).toContainText("of 10");
    expect(problems).toEqual([]);
  });
});
