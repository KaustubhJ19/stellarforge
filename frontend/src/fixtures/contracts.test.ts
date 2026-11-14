// The app's sample replays must be valid Spec 1 documents, checked against the
// shared JSON Schemas in contracts/ (the same ones contracts/validate.py uses).
import Ajv2020 from "ajv/dist/2020";

type Json = Record<string, unknown>;
const load = (files: Record<string, unknown>) =>
  Object.entries(files).map(([path, doc]) => [path.replace(/^(\.\.\/)+/, ""), doc] as [string, Json]);
const schemas = Object.fromEntries(
  load(import.meta.glob("../../../contracts/*.schema.json", { eager: true, import: "default" }))
    .map(([path, doc]) => [path.split("/").pop()!, doc]),
);
const replayDocs = load({
  ...import.meta.glob("./mars-day3.replay.json", { eager: true, import: "default" }),
  ...import.meta.glob(["../../public/replay/*.json", "!../../public/replay/crew-records.json"], { eager: true, import: "default" }),
});
const crewDocs = load({
  ...import.meta.glob("./crew-records.json", { eager: true, import: "default" }),
  ...import.meta.glob("../../public/replay/crew-records.json", { eager: true, import: "default" }),
});

const ajv = new Ajv2020({ allErrors: true, strict: false });
const compile = (file: string) => {
  if (!schemas[file]) throw new Error(`contracts/${file} not found`);
  return ajv.compile(schemas[file] as Json);
};
const replayFile = compile("replay-file.schema.json");
const crewRecord = compile("crew-record.schema.json");
const reading = compile("reading.schema.json");
const alert = compile("alert.schema.json");

function problems(check: ReturnType<typeof ajv.compile>, doc: unknown): string {
  return check(doc) ? "" : ajv.errorsText(check.errors);
}

it("finds the replays and Crew records to check", () => {
  expect(replayDocs.length).toBeGreaterThanOrEqual(3);
  expect(crewDocs).toHaveLength(2);
});

describe.each(replayDocs)("%s", (_name, raw) => {
  const doc = raw as { schema_version: string; events: { t: number; type: string; payload: Json }[] };

  it("is a valid ReplayFile with events ordered by t", () => {
    expect(problems(replayFile, doc)).toBe("");
    const times = doc.events.map((e) => e.t);
    expect(times).toEqual([...times].sort((a, b) => a - b));
  });

  it("carries complete Readings and Alerts (schema_version taken from the file)", () => {
    for (const e of doc.events) {
      const payload = { schema_version: doc.schema_version, ...e.payload };
      if (e.type === "reading") expect(problems(reading, payload)).toBe("");
      if (e.type === "alert") expect(problems(alert, payload)).toBe("");
    }
  });
});

describe.each(crewDocs)("%s", (_name, records) => {
  it("holds valid CrewRecords", () => {
    expect(Array.isArray(records)).toBe(true);
    for (const r of records as unknown as Json[]) expect(problems(crewRecord, r)).toBe("");
  });
});

/** Spec 3 (backend/baseline_a.py urgency): only a red Acute escalates; emergency is always ACT_NOW. */
function spec3Urgency(kind: string, status: string): string {
  if (kind === "emergency") return "ACT_NOW";
  if (kind === "acute" && status === "red") return "ESCALATE_TO_GROUND";
  return status === "amber" || status === "red" ? "MONITOR" : "ROUTINE";
}

describe.each(replayDocs)("%s Alerts as Spec 3 emits them", (_name, raw) => {
  const alerts = (raw as { events: { type: string; payload: Json }[] }).events
    .filter((e) => e.type === "alert")
    .map((e) => e.payload);

  const isCabin = (raw as { crew: string }).crew === "habitat";
  it("has Alerts to check (a cabin replay has none)", () => expect(alerts.length > 0).toBe(!isCabin));

  it("gives deviation as an object: {sigma, cusum, combined} or {value, bound}", () => {
    for (const a of alerts) {
      const keys = Object.keys(a.deviation as Json).sort();
      expect([["combined", "cusum", "sigma"], ["bound", "value"]]).toContainEqual(keys);
    }
  });

  it("sets urgency by Spec 3's rule", () => {
    for (const a of alerts) expect(a.urgency, String(a.id)).toBe(spec3Urgency(String(a.kind), String(a.status)));
  });
});
