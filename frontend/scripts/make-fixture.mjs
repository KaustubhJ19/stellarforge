// Builds the hand-made Mars replay fixture used until Spec 1's first replay
// file lands (ticket 12). Deterministic: re-running gives the same file.
// Run: node scripts/make-fixture.mjs
import { writeFileSync } from "node:fs";

const DAY = 86400;
const HOUR = 3600;
const START = 2 * DAY; // mission day 3
const crew = "crew-a";

const events = [];
const reading = (h, indicator, value, unit, state, source = "wearable") =>
  events.push({
    t: START + h * HOUR,
    type: "reading",
    payload: { crew, indicator, value, unit, t: START + h * HOUR, source, confidence: 0.9, state },
  });
const alert = (h, id, kind, indicator, deviation, status) =>
  events.push({
    t: START + h * HOUR,
    type: "alert",
    payload: {
      id, kind, crew, indicator, deviation, status,
      urgency: status === "red" ? "now" : "today",
      likely_causes: [], t: START + h * HOUR,
    },
  });

const baselines = {
  heart_rate: [55, 75],
  respiratory_rate: [12, 18],
  spo2: [95, 100],
  stress: [20, 45],
  alertness: [70, 95],
};
for (const [indicator, [low, high]] of Object.entries(baselines)) {
  events.push({ t: START, type: "baseline", payload: { indicator, low, high } });
}

for (let h = 0; h < 24; h++) {
  // Heart rate: normal, then an acute spike at 14:00.
  const hr = h === 14 ? 128 : h === 15 ? 96 : 62 + ((h * 7) % 9);
  reading(h, "heart_rate", hr, "bpm", h === 14 ? "red" : h === 15 ? "amber" : "green");
  reading(h, "respiratory_rate", 14 + (h % 3), "breaths/min", "green");
  reading(h, "spo2", 97 + (h % 2), "%", "green");
  // Stress drifts upward through the day.
  const stress = 30 + h * 1.5;
  reading(h, "stress", stress, "score", stress > 45 ? "amber" : "green");
  reading(h, "alertness", 88 - h, "score", 88 - h < 70 ? "amber" : "green");
  reading(h, "radiation_dose", +(41.2 + h * 0.03).toFixed(2), "mSv", "green", "dosimeter");
}
reading(8, "mood", 3, "1-5", "amber", "self-report");
reading(8, "bone_density", -1.1, "T-score", "amber", "manual");

alert(11, "a-drift-stress", "drift", "stress", 1.8, "amber");
alert(14, "a-acute-hr", "acute", "heart_rate", 4.2, "red");

for (const [id, title, done] of [
  ["t1", "Morning check-in", true],
  ["t2", "Blood pressure", false],
  ["t3", "Attention test", false],
]) {
  events.push({ t: START, type: "task", payload: { id, title, done } });
}

events.sort((a, b) => a.t - b.t);

const replay = {
  crew: { id: crew, sex: "male", anchor: "earth-preflight", missionProfile: "mars-transit" },
  profile: { id: "mars-transit", name: "Mars transit", groundDelayMin: 28.5 },
  events,
};
writeFileSync(new URL("../src/fixtures/mars-day3.replay.json", import.meta.url), JSON.stringify(replay, null, 1) + "\n");
console.log(`wrote ${events.length} events`);
