import { expect, test } from "@playwright/test";
import { openApp, scrubTo, statusPixels, waitForBody } from "./helpers";

test.describe("home screen in a real browser, no service", () => {
  test("loads the 3D body with no errors and no off-origin requests", async ({ page }) => {
    const problems = await openApp(page);
    await waitForBody(page);
    await expect(page.getByRole("region", { name: "Mission" })).toContainText("28.5 min");
    await expect(page.getByText("Decision support, not diagnosis.")).toBeVisible();
    expect(problems).toEqual([]);
  });

  test("loads only the base body model at start", async ({ page }) => {
    const models: string[] = [];
    page.on("request", (r) => r.url().includes("/models/") && models.push(r.url().split("/models/")[1]));
    await openApp(page);
    await waitForBody(page);
    expect(models).toEqual(["body-male.glb"]);
  });

  test("the body actually glows amber and green at the end of day 3", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    const px = await statusPixels(page);
    expect(px.amber).toBeGreaterThan(500); // brain, spine, hip
    expect(px.green).toBeGreaterThan(500); // lungs, heart
    expect(px.red).toBeLessThan(50);
  });

  test("scrubbing to the 14:00 acute event turns the heart red on screen", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    await scrubTo(page, 14);
    const px = await statusPixels(page);
    expect(px.red).toBeGreaterThan(300);
    await expect(
      page.getByRole("region", { name: "Physical health" }).getByRole("group", { name: "Heart rate" }),
    ).toContainText("Act now");
  });

  test("hiding a layer changes what is drawn", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    const before = await page.locator(".body-host canvas").screenshot();
    await page.getByRole("checkbox", { name: "Show muscles" }).uncheck();
    await page.waitForTimeout(300);
    const after = await page.locator(".body-host canvas").screenshot();
    expect(after.equals(before)).toBe(false);
  });

  test("zooming into the chest fetches its detail once and the heart fills more of the view", async ({ page }) => {
    const models: string[] = [];
    page.on("request", (r) => r.url().includes("/models/") && models.push(r.url().split("/models/")[1]));
    await openApp(page);
    await waitForBody(page);
    const wholeBody = await statusPixels(page);
    await page.getByRole("button", { name: "Chest" }).click();
    await page.waitForTimeout(1200);
    const chest = await statusPixels(page);
    expect(chest.green).toBeGreaterThan(wholeBody.green * 3);
    await page.getByRole("button", { name: "Back to whole body" }).click();
    await page.getByRole("button", { name: "Chest" }).click();
    await page.waitForTimeout(500);
    expect(models.filter((m) => m === "body-male.chest.glb")).toHaveLength(1);
  });

  test("every region zoom frames something that glows", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    for (const region of ["Head", "Chest", "Abdomen", "Pelvis and legs"]) {
      await page.getByRole("button", { name: region }).click();
      await page.waitForTimeout(1200);
      const px = await statusPixels(page);
      expect(px.green + px.amber + px.red, `${region} shows glowing structures`).toBeGreaterThan(1000);
      await page.getByRole("button", { name: "Back to whole body" }).click();
      await page.waitForTimeout(800);
    }
  });

  test("insight on stress: amber brain fills the view; exit restores the controls", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    await page.getByRole("button", { name: "Show stress on body" }).click();
    await page.waitForTimeout(1200);
    await expect(page.getByRole("heading", { name: "Insight: Stress" })).toBeVisible();
    const px = await statusPixels(page);
    expect(px.amber).toBeGreaterThan(20_000);
    expect(px.green).toBeLessThan(500); // the lungs' glow is off in insight
    await page.getByRole("button", { name: "Exit insight" }).click();
    await expect(page.getByRole("checkbox", { name: "Show muscles" })).toBeVisible();
  });

  test("the heart visibly beats when zoomed in", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    await page.getByRole("button", { name: "Chest" }).click();
    await page.getByRole("button", { name: "Heart", exact: true }).click();
    await page.waitForTimeout(1500);
    const frames = new Set<string>();
    for (let i = 0; i < 10; i++) {
      frames.add((await page.locator(".body-host canvas").screenshot()).toString("base64"));
      await page.waitForTimeout(60);
    }
    expect(frames.size).toBeGreaterThan(3);
  });

  test("trend chart hover shows time, value and Status", async ({ page }) => {
    await openApp(page);
    const svg = page.getByRole("region", { name: "Trends" }).locator("svg");
    await svg.scrollIntoViewIfNeeded();
    const box = (await svg.boundingBox())!;
    await page.mouse.move(box.x + box.width * 0.3, box.y + box.height / 2);
    await page.mouse.move(box.x + box.width * 0.62, box.y + box.height / 2, { steps: 4 });
    await expect(page.locator(".trend__tooltip")).toContainText("Day 3 15:00");
    await expect(page.locator(".trend__tooltip")).toContainText("96 bpm");
    await expect(page.locator(".trend__tooltip")).toContainText("Watch");
  });

  test("Emergency and Help reach the emergency-flow hook", async ({ page }) => {
    await openApp(page);
    const messages: string[] = [];
    page.on("dialog", (d) => {
      messages.push(d.message());
      void d.dismiss();
    });
    await page.getByRole("button", { name: "Emergency" }).click();
    await page.getByRole("button", { name: "Help a crewmate" }).click();
    expect(messages).toEqual([
      expect.stringContaining("emergency flow"),
      expect.stringContaining("help a crewmate flow"),
    ]);
  });

  test("a measurement card opens, traps focus and closes with Escape", async ({ page }) => {
    await openApp(page);
    const details = page.getByRole("button", { name: "Heart rate details" });
    await details.click();
    const card = page.getByRole("dialog", { name: "Heart rate" });
    await expect(card).toContainText("70 bpm");
    for (let i = 0; i < 4; i++) {
      await page.keyboard.press("Tab");
      expect(await card.evaluate((c) => c.contains(document.activeElement))).toBe(true);
    }
    await page.keyboard.press("Escape");
    await expect(card).toBeHidden();
    await expect(details).toBeFocused();
  });

  test("a malformed replay file shows a message, not a blank page", async ({ page }) => {
    await page.route((url) => url.pathname === "/bad.json", (r) => r.fulfill({ json: { readings: [] } }));
    await page.goto("/?replay=/bad.json");
    await expect(page.getByText("Could not load replay file: missing crew, profile, events")).toBeVisible();
  });

  test("a replay address that returns a web page gets a plain explanation", async ({ page }) => {
    await page.goto("/?replay=/does-not-exist.json"); // the static server answers with index.html
    await expect(page.getByText(/returned a web page, not a replay file/)).toBeVisible();
  });

  test("a replay from another address is refused without being fetched", async ({ page }) => {
    const offOrigin: string[] = [];
    page.on("request", (r) => !r.url().startsWith("http://localhost") && offOrigin.push(r.url()));
    await page.goto("/?replay=https://example.com/fake.json");
    await expect(page.getByText("replay files must come from this app's own address")).toBeVisible();
    expect(offOrigin).toEqual([]);
  });

  test("a missing replay file shows a message", async ({ page }) => {
    await page.goto("/?replay=/nope.json");
    await expect(page.getByText(/Could not load replay file/)).toBeVisible();
  });
});

test.describe("phone width", () => {
  test.use({ viewport: { width: 390, height: 844 } });

  test("Emergency stays on screen while scrolling", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    for (const y of [0, 1200, 3000]) {
      await page.evaluate((y) => scrollTo(0, y), y);
      await expect(page.getByRole("button", { name: "Emergency" })).toBeInViewport();
    }
  });
});
