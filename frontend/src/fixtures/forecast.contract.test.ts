// Forecasts the app reads must match Spec 1's provisional Forecast schema
// (contracts/provisional/forecast.schema.json, following Spec 3's forecast_b.py).
// Checked in the sample replays and in Spec 3's recorded replays.
import Ajv2020 from "ajv/dist/2020";

type Json = Record<string, unknown>;
type Replay = { schema_version?: string; events: { type: string; payload: Json }[] };

const [schema] = Object.values(
  import.meta.glob<Json>("../../../contracts/provisional/forecast.schema.json", { eager: true, import: "default" }),
);
const replays = Object.entries({
  ...import.meta.glob<Replay>("./mars-day3.replay.json", { eager: true, import: "default" }),
  ...import.meta.glob<Replay>(["../../public/replay/mars-day3*.json"], { eager: true, import: "default" }),
  ...import.meta.glob<Replay>("../../../replay/recorded/crew-*.json", { eager: true, import: "default" }),
}).map(([path, doc]) => [path.replace(/^(\.\.\/)+/, ""), doc] as const);

const forecastsIn = (doc: Replay) => doc.events.filter((e) => e.type === "forecast").map((e) => e.payload);

it("has the provisional Forecast schema and replays with forecasts to check", () => {
  expect(schema, "contracts/provisional/forecast.schema.json not found").toBeDefined();
  expect(replays.filter(([path]) => path.startsWith("replay/recorded/"))).toHaveLength(4);
});

describe.each(replays)("%s", (_path, doc) => {
  it("carries forecasts that match the provisional Forecast schema", () => {
    const check = new Ajv2020({ allErrors: true, strict: false }).compile(schema);
    const forecasts = forecastsIn(doc);
    expect(forecasts.length).toBeGreaterThan(0);
    for (const f of forecasts) {
      const ok = check({ schema_version: doc.schema_version, ...f });
      expect(ok ? "" : JSON.stringify(check.errors)).toBe("");
    }
  });

  it("keeps Spec 3's sums: base + drivers = population, population + personal correction = value", () => {
    for (const f of forecastsIn(doc) as unknown as {
      base: number; drivers: Record<string, number>; population: number; personal_correction: number; value: number;
    }[]) {
      const drivers = Object.values(f.drivers).reduce((a, b) => a + b, 0);
      expect(f.base + drivers).toBeCloseTo(f.population, 1);
      expect(f.population + f.personal_correction).toBeCloseTo(f.value, 1);
    }
  });
});
