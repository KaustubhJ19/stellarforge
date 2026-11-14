// Builds the hand-made Mars replay fixture in Spec 1's contract shapes (contracts/ at the
// repo root), used until the data lead's first generated replay arrives. Deterministic:
// re-running gives the same files. Indicator names follow tools/*.py on the data branch.
// Run: node scripts/make-fixture.mjs
//   src/fixtures/mars-day3.replay.json   crew A (male), bundled as the default replay
//   src/fixtures/crew-records.json       Crew records A and B
//   public/replay/mars-day3.json         same as the bundled replay, served
//   public/replay/mars-day3-female.json  the same day for crew B (female)
//   public/replay/crew-records.json      served next to the replays, as the generators write it
import { mkdirSync, writeFileSync } from "node:fs";

const SCHEMA_VERSION = "1.0.0";
const DAY = 86400;
const HOUR = 3600;
const START = 2 * DAY; // mission day 3
const PROFILE = "mars_transit";
const HABITAT = "habitat"; // cabin and dose Readings are the habitat's, not a crew member's

function day3(crew) {
  const events = [];
  const at = (h) => START + h * HOUR;
  const reading = (t, indicator, value, unit, source = "sensor", who = crew) =>
    events.push({
      t,
      type: "reading",
      payload: { crew: who, indicator, value, unit, t, source, confidence: 0.9, state: "released" },
    });
  const alert = (h, id, kind, indicator, deviation, status, urgency, likely_causes = []) =>
    events.push({
      t: at(h),
      type: "alert",
      payload: { id, kind, crew, indicator, deviation, status, urgency, likely_causes, t: at(h) },
    });

  // Daily wearable values at 07:00 (as tools/crew_replays.py writes them).
  reading(at(7), "resting_heart_rate", 59, "bpm");
  reading(at(7), "sleep_duration", 360, "min");
  reading(at(7), "steps", 8000, "steps");
  // Team-made scan value: no generator produces bone density yet.
  reading(at(8), "bone_density", -1.1, "T-score", "lab");

  for (let h = 0; h < 24; h++) {
    // Heart rate: normal, then an acute spike at 14:00.
    const hr = h === 14 ? 128 : h === 15 ? 96 : 62 + ((h * 7) % 9);
    reading(at(h), "heart_rate", hr, "bpm");
    reading(at(h), "respiration_rate", 14 + (h % 3), "1/min");
    reading(at(h), "spo2", h % 2 ? 0.98 : 0.97, "fraction");
    reading(at(h), "radiation_dose_accumulated", +(41.2 + h * 0.03).toFixed(2), "mGy", "sensor", HABITAT);
  }
  // Self-reports through the day; stress drifts up.
  for (const [h, stress, fatigue] of [[2, 2, 2], [6, 2, 2], [10, 3, 3], [14, 4, 3], [18, 4, 4], [22, 4, 4]]) {
    reading(at(h), "stress", stress, "score 1-5", "manual");
    reading(at(h), "fatigue", fatigue, "score 1-5", "manual");
  }
  reading(at(8), "mood", 3, "score 1-5", "manual");

  // Alerts as Spec 3 would emit them (placeholders, not medical content).
  alert(11, "a-drift-stress", "drift", "stress", 1.8, "amber", "MONITOR", [
    { indicator: "sleep_duration", direction: "down", note: "Example: shorter sleep over three days" },
  ]);
  alert(14, "a-acute-hr", "acute", "heart_rate", 4.2, "red", "ACT_NOW");
  alert(15, "a-acute-hr-2", "acute", "heart_rate", 2.1, "amber", "MONITOR");
  // ASSUMED: Spec 3 clears an Indicator with a green Alert.
  alert(16, "a-acute-hr-3", "acute", "heart_rate", 0.4, "green", "ROUTINE");
  alert(8, "a-drift-bone", "drift", "bone_density", 1.2, "amber", "ROUTINE");
  alert(18, "a-drift-fatigue", "drift", "fatigue", 1.6, "amber", "MONITOR");

  // APP-SIDE: today's checks (no contract carries tasks yet).
  for (const [id, title, done] of [
    ["t1", "Morning check-in", true],
    ["t2", "Blood pressure", false],
    ["t3", "Attention test", false],
  ]) {
    events.push({ t: START, type: "task", payload: { id, title, done } });
  }

  events.sort((a, b) => a.t - b.t);
  return { schema_version: SCHEMA_VERSION, crew, profile: PROFILE, events };
}

// Anchor: the person's own Earth normal, mean and SD per Indicator (team values).
const anchor = {
  heart_rate: { mean: 65, sd: 5 },
  resting_heart_rate: { mean: 58, sd: 3 },
  respiration_rate: { mean: 15, sd: 1.5 },
  spo2: { mean: 0.975, sd: 0.01 },
  sleep_duration: { mean: 420, sd: 30 },
  steps: { mean: 8000, sd: 1500 },
  stress: { mean: 2, sd: 0.6 },
  fatigue: { mean: 2.2, sd: 0.6 },
  mood: { mean: 3, sd: 0.5 },
};
const crewRecords = [
  { schema_version: SCHEMA_VERSION, id: "A", sex: "male", anchor, missionProfile: PROFILE },
  { schema_version: SCHEMA_VERSION, id: "B", sex: "female", anchor, missionProfile: PROFILE },
];

const write = (path, doc) => writeFileSync(new URL(path, import.meta.url), JSON.stringify(doc, null, 1) + "\n");
const male = day3("A");
const female = day3("B");
mkdirSync(new URL("../public/replay/", import.meta.url), { recursive: true });
write("../src/fixtures/mars-day3.replay.json", male);
write("../src/fixtures/crew-records.json", crewRecords);
write("../public/replay/mars-day3.json", male);
write("../public/replay/mars-day3-female.json", female);
write("../public/replay/crew-records.json", crewRecords);
console.log(`wrote ${male.events.length} events per crew member (A male, B female) and their Crew records`);
