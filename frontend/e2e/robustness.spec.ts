import { expect, test } from "@playwright/test";
import { openApp, waitForBody } from "./helpers";

/** A big replay like Spec 1 may produce: 1 Hz heart rate plus minute-level Readings over 3 days. */
function bigReplay(days = 3) {
  const events: unknown[] = [];
  const reading = (t: number, indicator: string, value: number, unit: string, source = "sensor") =>
    events.push({
      t,
      type: "reading",
      payload: { crew: "A", indicator, value, unit, t, source, confidence: 0.9, state: "released" },
    });
  const alert = (t: number, status: string) =>
    events.push({
      t,
      type: "alert",
      payload: {
        id: `hr-${t}`, kind: "acute", crew: "A", indicator: "heart_rate", status,
        deviation: { sigma: 5, cusum: null, combined: 3 },
        urgency: status === "red" ? "ESCALATE_TO_GROUND" : "ROUTINE", likely_causes: [], t,
      },
    });
  for (let t = 0; t < days * 86400; t++) {
    reading(t, "heart_rate", 60 + (t % 17), "bpm");
    if (t % 50000 === 0) alert(t, "red");
    if (t % 50000 === 600) alert(t, "green");
    if (t % 60 === 0) {
      reading(t, "spo2", 0.97, "fraction");
      reading(t, "respiration_rate", 15, "1/min");
      reading(t, "stress", 1 + (t % 5), "score 1-5", "manual");
    }
  }
  return { schema_version: "1.0.0", crew: "A", profile: "mars_transit", events };
}

const CREW_RECORDS = JSON.stringify([
  {
    schema_version: "1.0.0", id: "A", sex: "male", missionProfile: "mars_transit",
    anchor: { heart_rate: { mean: 65, sd: 5 } },
  },
]);

test.describe("large replay", () => {
  test("renders a ~270k-event, 3-day replay and stays responsive to the scrubber", async ({ page }) => {
    const body = JSON.stringify(bigReplay());
    console.log(`replay size: ${(body.length / 1e6).toFixed(1)} MB`);
    // openApp installs a catch-all route; routes added later win, so it must not shadow this one.
    const problems = await openApp(page, "about:blank");
    await page.route((url) => url.pathname === "/big.json", (r) => r.fulfill({ body, contentType: "application/json" }));
    await page.route(
      (url) => url.pathname === "/crew-records.json",
      (r) => r.fulfill({ body: CREW_RECORDS, contentType: "application/json" }),
    );
    await page.goto("/?replay=/big.json");

    const t0 = Date.now();
    await expect(page.getByRole("region", { name: "Mission" })).toContainText("Day 3", { timeout: 30_000 });
    const firstRender = Date.now() - t0;

    // One scrub step: from the moment of input until the mission bar shows the new day.
    const slider = page.getByRole("slider", { name: "Mission clock" });
    const s0 = Date.now();
    await slider.fill(String(86400 + 3600));
    await expect(page.getByRole("region", { name: "Mission" })).toContainText("Day 2");
    const scrubStep = Date.now() - s0;

    console.log(`first render ${firstRender} ms, one scrub step ${scrubStep} ms`);
    expect(problems).toEqual([]);
    expect(firstRender, "first render").toBeLessThan(5000);
    expect(scrubStep, "a scrub step should feel immediate").toBeLessThan(300);
  });
});

test.describe("slow device", () => {
  test("body frame rate with the CPU slowed 4x", async ({ page }) => {
    await openApp(page);
    const cdp = await page.context().newCDPSession(page);
    await cdp.send("Emulation.setCPUThrottlingRate", { rate: 4 });
    await waitForBody(page);
    const fps = await page.evaluate(
      () =>
        new Promise<number>((done) => {
          let frames = 0;
          const start = performance.now();
          (function tick() {
            frames++;
            if (performance.now() - start < 3000) requestAnimationFrame(tick);
            else done(frames / ((performance.now() - start) / 1000));
          })();
        }),
    );
    console.log(`fps with 4x CPU slowdown: ${fps.toFixed(0)}`);
    expect(fps).toBeGreaterThan(30);
  });
});
