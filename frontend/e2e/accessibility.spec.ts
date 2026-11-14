import { expect, test, type Page } from "@playwright/test";
import { openApp, waitForBody } from "./helpers";

/** Press Tab until `name` has focus; returns how many presses it took (or Infinity). */
async function tabsTo(page: Page, name: string, max = 80) {
  for (let i = 1; i <= max; i++) {
    await page.keyboard.press("Tab");
    const focused = await page.evaluate(() => {
      const el = document.activeElement as HTMLElement | null;
      return el?.getAttribute("aria-label") ?? el?.textContent?.trim() ?? "";
    });
    if (focused === name) return i;
  }
  return Infinity;
}

test.describe("keyboard only", () => {
  test("Emergency is reachable early in the tab order", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    const presses = await tabsTo(page, "Emergency");
    console.log(`Tab presses to reach Emergency: ${presses}`);
    expect(presses).toBeLessThanOrEqual(5);
  });

  test("every control shows a visible focus ring", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    const missing: string[] = [];
    for (let i = 0; i < 60; i++) {
      await page.keyboard.press("Tab");
      const ring = await page.evaluate(() => {
        const el = document.activeElement as HTMLElement;
        if (!el || el === document.body) return null;
        const s = getComputedStyle(el);
        const visible = (s.outlineStyle !== "none" && parseFloat(s.outlineWidth) > 0) || s.boxShadow !== "none";
        return { visible, name: el.getAttribute("aria-label") ?? el.textContent?.trim().slice(0, 30) ?? el.tagName };
      });
      if (ring && !ring.visible) missing.push(ring.name);
    }
    expect([...new Set(missing)]).toEqual([]);
  });

  test("insight, zoom and the scrubber work from the keyboard", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    await page.getByRole("button", { name: "Show stress on body" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("heading", { name: "Insight: Stress" })).toBeVisible();
    await page.getByRole("button", { name: "Exit insight" }).focus();
    await page.keyboard.press("Enter");
    await page.getByRole("button", { name: "Chest" }).focus();
    await page.keyboard.press("Enter");
    await expect(page.getByRole("button", { name: "Back to whole body" })).toBeVisible();
    const slider = page.getByRole("slider", { name: "Mission clock" });
    await slider.focus();
    const before = await slider.inputValue();
    for (let i = 0; i < 10; i++) await page.keyboard.press("ArrowLeft");
    const after = await slider.inputValue();
    console.log(`10 ArrowLeft presses moved the Mission clock by ${Number(before) - Number(after)} s`);
    expect(Number(before) - Number(after)).toBeGreaterThanOrEqual(600); // at least 10 minutes
  });
});

test.describe("forced colours (Windows high contrast)", () => {
  test.use({ forcedColors: "active" });

  test("Status words and icons survive when colours are overridden", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    const hr = page.getByRole("region", { name: "Physical health" }).getByRole("group", { name: "Bone density" });
    await expect(hr).toContainText("Watch");
    await expect(hr.getByTestId("status-icon")).toBeVisible();
    // axe checks authored colours, not the forced ones, so it is not used here (false positives).
  });

  test("Emergency still stands out from other buttons when colours are overridden", async ({ page }) => {
    await openApp(page);
    const look = (name: string) =>
      page.getByRole("button", { name, exact: true }).evaluate((el) => {
        const s = getComputedStyle(el);
        return `${s.backgroundColor}|${s.color}|${s.borderWidth}|${el.textContent}`;
      });
    expect(await look("Emergency")).not.toEqual((await look("Head")).replace("Head", "Emergency"));
  });
});

test.describe("reduced motion", () => {
  test.use({ reducedMotion: "reduce" });

  test("respects a reduced-motion preference for the beating heart and camera flights", async ({ page }) => {
    await openApp(page);
    await waitForBody(page);
    await page.getByRole("button", { name: "Chest" }).click();
    await page.getByRole("button", { name: "Heart", exact: true }).click();
    await page.waitForTimeout(1500);
    const frames = new Set<string>();
    for (let i = 0; i < 8; i++) {
      frames.add((await page.locator(".body-host canvas").screenshot()).toString("base64"));
      await page.waitForTimeout(80);
    }
    console.log(`distinct frames with reduced motion: ${frames.size} of 8`);
    expect(frames.size).toBe(1);
  });
});
