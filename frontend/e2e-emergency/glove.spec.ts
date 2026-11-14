import { expect, test, type Page } from "@playwright/test";

// Ticket 16 / story 12. Proposed TEAM VALUES (not from a source): touch targets at least
// 64 x 64 CSS px (gloves; above WCAG 2.2's 24 px minimum and 44 px enhanced) and body text
// at least 20 px. Checked on a tablet-sized viewport.
const MIN_TARGET = 64;
const MIN_TEXT = 20;

async function checkSizes(p: Page, where: string) {
  const buttons = p.locator("button:visible");
  const n = await buttons.count();
  expect(n, `${where}: buttons`).toBeGreaterThan(0);
  for (let i = 0; i < n; i++) {
    const box = await buttons.nth(i).boundingBox();
    const label = await buttons.nth(i).innerText();
    expect(box!.height, `${where}: "${label}" height`).toBeGreaterThanOrEqual(MIN_TARGET);
    expect(box!.width, `${where}: "${label}" width`).toBeGreaterThanOrEqual(MIN_TARGET);
  }
  const body = await p.locator("main").evaluate((el) => parseFloat(getComputedStyle(el).fontSize));
  expect(body, `${where}: text size`).toBeGreaterThanOrEqual(MIN_TEXT);
}

test.use({ viewport: { width: 1024, height: 768 } });

test.beforeEach(async ({ request }) => {
  await request.post("/api/sim/reset");
});

test("emergency screens meet the glove-size team values", async ({ browser, request }) => {
  const ctx = await browser.newContext();
  const cmdr = await ctx.newPage();
  const eng = await ctx.newPage();
  await cmdr.goto("/emergency.html?crew=cmdr");
  await eng.goto("/emergency.html?crew=eng");
  await checkSizes(cmdr, "home");
  await cmdr.getByRole("button", { name: "Emergency" }).click();
  await expect(cmdr.getByTestId("urgency")).toBeVisible();
  await checkSizes(cmdr, "verdict");
  await request.post("/api/sim/clock/advance", { data: { seconds: 15 } });
  await expect(eng.getByText(/CREW ALARM/)).toBeVisible();
  await checkSizes(eng, "alarm");
  await eng.getByRole("button", { name: /Accept/ }).click();
  await expect(eng.getByRole("button", { name: "No response" })).toBeVisible();
  await checkSizes(eng, "observer");
  await eng.getByRole("button", { name: "No response" }).click();
  await expect(eng.getByText(/This access is logged/)).toBeVisible();
  await checkSizes(eng, "record");
  await eng.getByRole("button", { name: "Next" }).click();
  await eng.getByRole("button", { name: "Next" }).click();
  await expect(eng.getByTestId("step-text")).toBeVisible();
  await checkSizes(eng, "step");
  await ctx.close();
});
