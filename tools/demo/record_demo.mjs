// Backup demo recording (Spec 5 ticket 09): real app, real content, one continuous video.
// Run from the repo root: see docs/backup-demo.md.
import { createRequire } from "node:module";
const require = createRequire(new URL("../../frontend/package.json", import.meta.url));
const { chromium } = require("playwright");
import fs from "node:fs";
const [BASE, COLLAPSE, OUT] = process.argv.slice(2);
const collapse = JSON.parse(fs.readFileSync(COLLAPSE, "utf8"));
const api = async (path, body) => (await fetch(BASE + path, body ? { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify(body) } : {})).json();
const browser = await chromium.launch();
const ctx = await browser.newContext({ viewport: { width: 1280, height: 800 }, recordVideo: { dir: OUT, size: { width: 1280, height: 800 } } });
const page = await ctx.newPage();
const pause = (s) => page.waitForTimeout(s * 1000);
let shot = 0;
async function caption(text) { console.log("scene:", text.slice(0, 40)); setTimeout(() => page.screenshot({ path: `${OUT}/s${String(++shot).padStart(2, "0")}.png` }).catch(() => {}), 700);
  await page.evaluate((t) => {
    let d = document.getElementById("sf-caption");
    if (!d) { d = document.createElement("div"); d.id = "sf-caption"; document.body.appendChild(d); }
    Object.assign(d.style, { position: "fixed", left: "0", right: "0", bottom: "0", zIndex: "99999", padding: "14px 20px",
      background: "rgba(0,0,0,0.82)", color: "#fff", font: "600 20px system-ui, sans-serif", textAlign: "center" });
    d.textContent = t;
  }, text);
}
async function go(path, text) { await page.goto(BASE + path); await page.waitForLoadState("domcontentloaded"); await page.waitForTimeout(1500); await caption(text); }

await api("/api/sim/reset", {});
const crew = await api("/api/sim/crew");
console.log("server content:", crew.protocol, crew.profile, "stub:", crew.stub, "crew:", crew.crew);

await go("/?replay=/replay/shared/crew-B.json&cabin=/replay/shared/iss-cabin-dose-RR-1.json", "1  Home screen: crew B on Mars transit (28.5 min ground delay). Readings come from the team's replay.");
await pause(6);

const now = (await api("/api/sim/crew")).t;
for (const m of collapse) {
  const p = { ...m.payload, t: now };
  await api(m.type === "alert" ? "/api/stream/alert" : "/api/stream/trigger", p);
}
await page.waitForTimeout(800); await caption("2  Collapse: Spec 3 detection flagged ventricular tachycardia in crew B's replay -> automatic trigger, ACT NOW.");
await page.getByTestId("urgency").waitFor({ timeout: 10000 }).catch(() => {});
await pause(6);

await api("/api/sim/clock/advance", { seconds: 15 });
await go("/emergency.html?crew=A", "3  No answer from crew B in 15 s: the crew alarm sounds on crewmate A's tablet.");
await page.getByText(/CREW ALARM/).first().waitFor({ timeout: 10000 }).catch(() => {});
await pause(4);
await page.getByRole("button", { name: /Accept/ }).click(); await caption("4  A accepts and becomes Rescuer 1. Does crew B respond?"); await pause(3);
await page.getByRole("button", { name: "No response" }).click(); await caption("5  Crew B's record opens for the rescuer. The access is logged."); await pause(4);
await page.getByRole("button", { name: "Next" }).click(); await caption("6  Likely contributors (none from history yet, so none are invented)."); await pause(3);
await page.getByRole("button", { name: "Next" }).click(); await caption("7  Guidance: one cited step per screen (Hinkelbein et al. 2020, microgravity CPR guideline)."); await pause(5);
await page.getByRole("button", { name: "Why this step?" }).click(); await caption("8  'Why this step?' answered offline from the recorded answer and the cited excerpt."); await pause(6);
for (let i = 0; i < 20; i++) {
  if (await page.getByTestId("report").count()) break;
  const next = page.getByRole("button", { name: "Next" });
  if (!(await next.count())) break;
  await next.first().click(); await caption("9  Next cited step (a solo rescuer only sees one-rescuer steps)"); await pause(2.5);
}
await caption("10  Ground report sent: on Mars transit the reply is expected 57 min later."); await pause(6);

await go("/emergency.html?view=console", "11  Ground console: the report is still in transit (28.5 min one way).");
await pause(5);
await api("/api/sim/clock/advance", { seconds: 1710 });
await page.reload(); await page.waitForTimeout(1500);
await caption("12  28.5 min later the report arrives. The flight surgeon replies.");
await page.getByLabel("Reply").fill("Ground: report received. Flight surgeon is reviewing; continue per protocol.");
await pause(3);
await page.getByRole("button", { name: "Send reply" }).click(); await pause(3);
await api("/api/sim/clock/advance", { seconds: 1710 });
await go("/emergency.html?crew=A", "13  The reply reaches the crew 28.5 min later and is saved as a Label.");
await page.getByTestId("ground-reply").waitFor({ timeout: 10000 }).catch(() => {});
await pause(6);
const video = page.video();
await ctx.close(); await browser.close();
console.log("video:", await video.path());
