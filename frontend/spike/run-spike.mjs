// Opens the Spike B page in Chromium and prints its measurements.
// Usage: node spike/run-spike.mjs <base-url> [--headed]
import { chromium } from "playwright";
const base = process.argv[2] ?? "http://localhost:5173";
const browser = await chromium.launch({ headless: !process.argv.includes("--headed"), args: ["--use-angle=metal", "--enable-gpu"] });
const page = await browser.newPage({ viewport: { width: 1280, height: 800 } });
page.on("pageerror", (e) => console.error("pageerror", e.message));
await page.goto(`${base}/spike/body.html`);
await page.waitForFunction(() => window.spikeResult, null, { timeout: 60000 });
console.log(JSON.stringify(await page.evaluate(() => window.spikeResult), null, 1));
await page.screenshot({ path: process.env.SHOT ?? "spike-body.png" });
await browser.close();
