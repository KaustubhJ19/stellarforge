import { parseReplay } from "./parse";
import { marsReplay } from "../test/replay";

describe("checking a replay file before showing it", () => {
  it("accepts a replay in the contract shape", () => {
    const result = parseReplay(marsReplay());
    expect(result.ok).toBe(true);
  });

  it("names what is missing from a file in the wrong shape", () => {
    const result = parseReplay({ readings: [] });
    expect(result).toEqual({ ok: false, error: expect.stringMatching(/crew.*profile.*events/) });
  });

  it("rejects an event it cannot read", () => {
    const bad = marsReplay() as unknown as { events: unknown[] };
    bad.events.push({ t: 5, type: "reading", payload: { indicator: "heart_rate" } });
    expect(parseReplay(bad)).toEqual({ ok: false, error: expect.stringMatching(/event 156/) });
  });
});
