import { expect, test, type BrowserContext, type Page } from "@playwright/test";

const ONE_WAY = 1710; // STUB Mars profile, team value
const DISCLAIMER = "Decision support, not diagnosis.";

// Block and record every request that leaves the machine (test j: network off).
async function offlineNetwork(ctx: BrowserContext) {
  const external: string[] = [];
  await ctx.route("**/*", (route) => {
    const host = new URL(route.request().url()).hostname;
    if (host === "127.0.0.1" || host === "localhost") return route.continue();
    external.push(route.request().url());
    return route.abort();
  });
  return external;
}

async function disclaimerShown(p: Page) {
  await expect(p.getByTestId("disclaimer")).toHaveText(DISCLAIMER);
}

test.beforeEach(async ({ request }) => {
  await request.post("/api/sim/reset");
});

test("golden UI run: manual press -> alarm -> rescuer -> steps -> report -> delayed ground reply (network blocked)", async ({ browser, request }) => {
  const ctx = await browser.newContext();
  const external = await offlineNetwork(ctx);
  const [cmdr, eng, sci, ground] = await Promise.all([ctx.newPage(), ctx.newPage(), ctx.newPage(), ctx.newPage()]);
  await cmdr.goto("/?crew=cmdr");
  await eng.goto("/?crew=eng");
  await sci.goto("/?crew=sci");
  await ground.goto("/console");

  // manual trigger -> verdict
  await cmdr.getByRole("button", { name: "Emergency" }).click();
  await expect(cmdr.getByTestId("urgency")).toHaveText("Urgency not assessed (manual start)");
  await disclaimerShown(cmdr);

  // no answer in 15 s -> alarm on other tablets
  await request.post("/api/sim/clock/advance", { data: { seconds: 15 } });
  await expect(eng.getByText(/CREW ALARM/)).toBeVisible();
  await expect(sci.getByText(/CREW ALARM/)).toBeVisible();
  await disclaimerShown(eng);
  await expect(cmdr.getByText("Crew alarm raised")).toBeVisible();

  // first to accept = Rescuer 1, observer question
  await eng.getByRole("button", { name: /Accept/ }).click();
  await expect(eng.getByText("Does the patient respond?").first()).toBeVisible();
  await expect(sci.getByRole("button", { name: "Join as Rescuer 2" })).toBeVisible();
  await eng.getByRole("button", { name: "No response" }).click();

  // record (logged) -> contributors -> steps
  await expect(eng.getByText(/This access is logged/)).toBeVisible();
  await disclaimerShown(eng);
  await eng.getByRole("button", { name: "Next" }).click();
  await expect(eng.getByText("No history-based contributors available.")).toBeVisible();
  await eng.getByRole("button", { name: "Next" }).click();
  await expect(eng.getByTestId("step-text")).toHaveCount(1);
  await expect(eng.getByTestId("step-source")).toContainText("STUB-S1");
  await disclaimerShown(eng);
  await eng.getByRole("button", { name: "Why this step?" }).click();
  await expect(eng.getByTestId("why")).toContainText("recorded answer"); // model unreachable -> labelled recorded answer
  const stepBefore = await eng.getByTestId("step-text").textContent();
  expect(stepBefore).toContain("STUB step 1");
  await eng.getByRole("button", { name: "Next" }).click();
  await expect(eng.getByTestId("step-source")).toContainText("STUB-S2");
  await eng.getByRole("button", { name: "Next" }).click();

  // ground report with expected reply time
  await expect(eng.getByTestId("report")).toContainText("Expected reply at T+57 min");
  await disclaimerShown(eng);

  // console: in transit, then arrives after one-way delay; reply reaches crew after another
  await expect(ground.getByText(/In transit/)).toBeVisible();
  await request.post("/api/sim/clock/advance", { data: { seconds: ONE_WAY } });
  await ground.getByLabel("Reply").fill("E2E flight surgeon reply.");
  await ground.getByRole("button", { name: "Send reply" }).click();
  await expect(ground.getByText("Reply sent.")).toBeVisible();
  await expect(eng.getByTestId("ground-reply")).toHaveCount(0);
  await request.post("/api/sim/clock/advance", { data: { seconds: ONE_WAY } });
  await expect(eng.getByTestId("ground-reply")).toContainText("E2E flight surgeon reply.");
  const labels = await (await request.get("/api/labels?crew=cmdr")).json();
  expect(labels[0].text).toBe("E2E flight surgeon reply.");

  // patient sees who opened the record
  const log = await (await request.get("/api/access-log?crew=cmdr&viewer=cmdr")).json();
  expect(log.map((x: { actor: string }) => x.actor)).toEqual(["eng"]);

  expect(external).toEqual([]);
  await ctx.close();
});

test("auto Trigger reaches the same first screen as the button", async ({ browser, request }) => {
  const ctx = await browser.newContext();
  const external = await offlineNetwork(ctx);
  const cmdr = await ctx.newPage();
  await cmdr.goto("/?crew=cmdr");
  await request.post("/api/stream/alert", { data: { schema_version: "1.0.0", id: "al-e2e", kind: "emergency", crew: "cmdr", indicator: "STUB",
    deviation: { sigma: 4 }, status: "red", urgency: "ACT_NOW", t: 0,
    likely_causes: [{ indicator: "STUB", direction: "down", note: "STUB cause 1 (suggestion, not diagnosis)" }] } });
  await request.post("/api/stream/trigger", { data: { schema_version: "1.0.0", kind: "auto", crew: "cmdr", t: 0, reason: "STUB collapse (test double)" } });
  await expect(cmdr.getByTestId("urgency")).toHaveText("ACT NOW");
  await expect(cmdr.getByRole("button", { name: "I need help" })).toBeVisible();
  await disclaimerShown(cmdr);
  expect(external).toEqual([]);
  await ctx.close();
});

test("backend down: offline steps, record access logged on the tablet and synced once when back", async ({ browser, request }) => {
  const ctx = await browser.newContext();
  const eng = await ctx.newPage();
  await eng.goto("/?crew=eng");
  await expect(eng.getByRole("button", { name: "Emergency" })).toBeVisible();
  await eng.waitForFunction(() => !!localStorage.getItem("sf-offline-bundle"));

  await ctx.route("**/api/**", (r) => r.abort()); // backend unreachable
  await expect(eng.getByText(/Service unavailable/)).toBeVisible();
  await eng.getByRole("button", { name: "Help a crewmate" }).click();
  await eng.getByRole("button", { name: "Crew cmdr" }).click();
  await expect(eng.getByText(/logged on this tablet/)).toBeVisible();
  await disclaimerShown(eng);
  await eng.getByRole("button", { name: "Next" }).click();
  await expect(eng.getByTestId("step-source")).toContainText("STUB-S1");
  await eng.getByRole("button", { name: "Next" }).click();
  await eng.getByRole("button", { name: "Next" }).click();
  await eng.getByRole("button", { name: "End offline session" }).click();

  await ctx.unroute("**/api/**"); // backend back
  await expect.poll(async () => eng.evaluate(() => JSON.parse(localStorage.getItem("sf-offline-queue") ?? "[]").length)).toBe(0);
  const log = await (await request.get("/api/access-log?crew=cmdr&viewer=cmdr")).json();
  expect(log).toHaveLength(1);
  expect(log[0].reason).toContain("offline");
  await ctx.close();
});
