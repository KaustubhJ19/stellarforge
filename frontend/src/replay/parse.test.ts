import { parseReplay } from "./parse";
import { marsMission } from "../test/replay";

const marsReplay = () => marsMission().replay;

describe("checking a replay file before showing it", () => {
  it("accepts a replay in the contract shape", () => {
    const result = parseReplay(marsReplay());
    expect(result.ok).toBe(true);
  });

  it("names what is missing from a file in the wrong shape", () => {
    const result = parseReplay({ readings: [] });
    expect(result).toEqual({ ok: false, error: expect.stringMatching(/crew.*profile.*events/) });
  });

  it("rejects a replay from before the contracts were frozen (crew as an object)", () => {
    const old = { ...marsReplay(), crew: { id: "A", sex: "male" } };
    expect(parseReplay(old)).toEqual({ ok: false, error: "crew should be a crew id, e.g. \"A\"" });
  });

  it("rejects events out of time order, as the contract requires", () => {
    const bad = marsReplay();
    bad.events.push({ ...bad.events[0], t: 0 });
    expect(parseReplay(bad)).toEqual({ ok: false, error: `event ${bad.events.length - 1} is out of time order` });
  });

  it("rejects a forecast event missing what the forecast view reads", () => {
    const bad = marsReplay() as unknown as { events: unknown[] };
    bad.events.push({ t: 1e9, type: "forecast", payload: { crew: "A", t: 1e9, value: null, low: 1, high: 2 } });
    expect(parseReplay(bad)).toEqual({
      ok: false,
      error: `event ${bad.events.length - 1} (forecast) needs numbers for value, population, personal_correction and drivers as a set of numbers`,
    });
  });

  it("rejects an event it cannot read", () => {
    const bad = marsReplay() as unknown as { events: unknown[] };
    bad.events.push({ t: 5, type: "reading", payload: { indicator: "heart_rate" } });
    const last = bad.events.length - 1;
    expect(parseReplay(bad)).toEqual({ ok: false, error: `event ${last} (reading) is missing value, unit, t` });
  });
});
