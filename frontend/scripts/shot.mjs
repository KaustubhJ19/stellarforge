// Screenshot the running app for a visual check.
// Usage: node scripts/shot.mjs <url> <out.png> [width] [height]
import { chromium } from "playwright";
const [url, out, w = "1440", h = "960"] = process.argv.slice(2);
const browser = await chromium.launch({ args: ["--use-angle=metal", "--enable-gpu"] });
const page = await browser.newPage({ viewport: { width: +w, height: +h } });
page.on("pageerror", (e) => console.error("pageerror:", e.message));
page.on("console", (m) => m.type() === "error" && console.error("console:", m.text()));
await page.goto(url);
await page.waitForSelector('[data-loaded="true"], .body-host__error, [data-error]', { timeout: 30000 }).catch(() => console.error("body never loaded"));
await page.waitForTimeout(800);
await page.screenshot({ path: out, fullPage: true });
await browser.close();
