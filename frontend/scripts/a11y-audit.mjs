// Accessibility audit of the running app: axe-core rules (contrast, names, roles)
// plus a tap-target check (every control at least 44 px; our token is 56 px).
// Usage: node scripts/a11y-audit.mjs <url>
import { chromium } from "playwright";
import { AxeBuilder } from "@axe-core/playwright";

const url = process.argv[2] ?? "http://localhost:5173/";
const MIN_TARGET = 44;
const browser = await chromium.launch({ args: ["--use-angle=metal", "--enable-gpu"] });
let failed = false;

for (const [w, h] of [[1440, 900], [1024, 768], [390, 844]]) {
  const context = await browser.newContext({ viewport: { width: w, height: h } });
  const page = await context.newPage();
  await page.goto(url);
  await page.waitForSelector('[data-loaded="true"]', { timeout: 30000 });

  const axe = await new AxeBuilder({ page }).withTags(["wcag2a", "wcag2aa", "wcag21aa", "wcag22aa"]).analyze();
  for (const v of axe.violations) {
    failed = true;
    console.log(`[${w}px] axe ${v.id} (${v.impact}): ${v.help}`);
    for (const n of v.nodes.slice(0, 5)) console.log(`    ${n.target.join(" ")}  ${n.failureSummary?.split("\n")[1] ?? ""}`);
  }

  // A control's target is its own box, or its <label>'s box when it sits inside one.
  const small = await page.evaluate((min) => {
    const out = [];
    for (const el of document.querySelectorAll("button, input, select, a[href]")) {
      const target = el.closest("label") ?? el;
      const r = target.getBoundingClientRect();
      if (r.width === 0 && r.height === 0) continue;
      if (r.height < min || r.width < min) out.push(`${el.tagName.toLowerCase()} "${el.getAttribute("aria-label") ?? el.textContent.trim()}" ${Math.round(r.width)}x${Math.round(r.height)}`);
    }
    return out;
  }, MIN_TARGET);
  for (const s of small) {
    failed = true;
    console.log(`[${w}px] small target: ${s}`);
  }

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth > innerWidth);
  if (overflow) {
    failed = true;
    console.log(`[${w}px] page scrolls sideways`);
  }
  console.log(`[${w}px] axe violations: ${axe.violations.length}, small targets: ${small.length}, sideways scroll: ${overflow}`);
  await context.close();
}
await browser.close();
process.exit(failed ? 1 : 0);
