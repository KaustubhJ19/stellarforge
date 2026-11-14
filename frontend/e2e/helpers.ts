import { expect, type Page } from "@playwright/test";

/** Open the app, fail on any page error or off-origin request, and wait for the 3D body. */
export async function openApp(page: Page, path = "/") {
  const problems: string[] = [];
  page.on("pageerror", (e) => problems.push(`pageerror: ${e.message}`));
  page.on("console", (m) => m.type() === "error" && problems.push(`console: ${m.text()}`));
  await page.route("**/*", (route) => {
    const url = new URL(route.request().url());
    if (url.hostname !== "localhost") {
      problems.push(`off-origin request: ${url.href}`);
      return route.abort();
    }
    return route.continue();
  });
  await page.goto(path);
  return problems;
}

export async function waitForBody(page: Page) {
  await expect(page.locator('.body-host[data-loaded="true"]')).toBeVisible({ timeout: 30_000 });
  await page.waitForTimeout(700); // let the camera settle
}

/** Count canvas pixels near each Status colour (and the "Why this forecast?" violet) in a screenshot of the body. */
export async function statusPixels(page: Page) {
  const png = await page.locator(".body-host canvas").screenshot();
  return page.evaluate(async (b64) => {
    const img = new Image();
    img.src = `data:image/png;base64,${b64}`;
    await img.decode();
    const c = new OffscreenCanvas(img.width, img.height);
    const ctx = c.getContext("2d")!;
    ctx.drawImage(img, 0, 0);
    const d = ctx.getImageData(0, 0, img.width, img.height).data;
    // Lit surfaces vary in brightness, so classify by hue and saturation.
    const counts = { green: 0, amber: 0, red: 0, explain: 0 };
    for (let i = 0; i < d.length; i += 4) {
      const [r, g, b] = [d[i] / 255, d[i + 1] / 255, d[i + 2] / 255];
      const max = Math.max(r, g, b), min = Math.min(r, g, b), l = max - min;
      if (max < 0.35 || l / max < 0.45) continue;
      let h = max === r ? ((g - b) / l) % 6 : max === g ? (b - r) / l + 2 : (r - g) / l + 4;
      h *= 60;
      if (h < 0) h += 360;
      if (h >= 160 && h <= 185) counts.green++; // teal-green #29c0b1
      else if (h >= 38 && h <= 56) counts.amber++; // #ffcc33
      else if (h <= 10 || h >= 350) counts.red++;
      else if (h >= 255 && h <= 290) counts.explain++; // --explain #b48cff
    }
    return counts;
  }, png.toString("base64"));
}

export const DAY3 = 2 * 86400;
export async function scrubTo(page: Page, hour: number) {
  await page.getByRole("slider", { name: "Mission clock" }).fill(String(DAY3 + hour * 3600));
  await page.waitForTimeout(300);
}
