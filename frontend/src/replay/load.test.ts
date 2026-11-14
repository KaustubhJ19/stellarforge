import { loadMission, missionFrom } from "./load";
import { marsMission } from "../test/replay";

const ORIGIN = "http://localhost:4173";
const { replay, crew } = marsMission();
const CREW_RECORDS = JSON.stringify([crew]);

/** Serves the replay body for any address, and the Crew records for crew-records.json. */
function respond(body: string, contentType: string, status = 200, crewRecords = CREW_RECORDS): typeof fetch {
  return async (input) => {
    if (String(input).endsWith("/crew-records.json")) {
      return new Response(crewRecords, { headers: { "content-type": "application/json" } });
    }
    return new Response(body, { status, headers: { "content-type": contentType } });
  };
}
const loadReplay = (address: string, origin: string, fetchFn: typeof fetch) => loadMission(address, origin, fetchFn);

describe("loading a replay file from ?replay=", () => {
  it("loads a replay and its Crew record from crew-records.json beside it", async () => {
    const asked: string[] = [];
    const fetchFn: typeof fetch = async (input) => {
      asked.push(String(input));
      return respond(JSON.stringify(replay), "application/json")(input);
    };
    const result = await loadReplay("/replay/day3.json", ORIGIN, fetchFn);
    expect(result).toEqual({ ok: true, replay, crew });
    expect(asked).toEqual([`${ORIGIN}/replay/day3.json`, `${ORIGIN}/replay/crew-records.json`]);
  });

  it("says when crew-records.json has no record for the replay's crew", async () => {
    const other = JSON.stringify([{ ...crew, id: "Z" }]);
    const result = await loadReplay("/replay/day3.json", ORIGIN, respond(JSON.stringify(replay), "application/json", 200, other));
    expect(result).toEqual({ ok: false, error: "crew-records.json beside the replay has no Crew record for crew A" });
  });

  it("names crew-records.json, not the replay, when it comes back as a web page", async () => {
    const fetchFn: typeof fetch = async (input) =>
      String(input).endsWith("/crew-records.json")
        ? new Response("<!doctype html>", { headers: { "content-type": "text/html" } })
        : new Response(JSON.stringify(replay), { headers: { "content-type": "application/json" } });
    const result = await loadReplay("/replay/day3.json", ORIGIN, fetchFn);
    expect(result).toEqual({
      ok: false,
      error: "crew-records.json beside the replay: that address returned a web page, not crew-records.json (is it there?)",
    });
  });

  it("explains when crew-records.json is missing", async () => {
    const fetchFn: typeof fetch = async (input) =>
      String(input).endsWith("/crew-records.json")
        ? new Response("", { status: 404 })
        : new Response(JSON.stringify(replay), { headers: { "content-type": "application/json" } });
    const result = await loadReplay("/replay/day3.json", ORIGIN, fetchFn);
    expect(result).toEqual({ ok: false, error: "crew-records.json beside the replay: file not found (404)" });
  });

  it("refuses a replay from another address, without fetching it", async () => {
    const fetchSpy = vi.fn();
    const result = await loadReplay("https://example.com/fake.json", ORIGIN, fetchSpy);
    expect(result).toEqual({ ok: false, error: "replay files must come from this app's own address" });
    expect(fetchSpy).not.toHaveBeenCalled();
  });

  it("refuses other schemes", async () => {
    const result = await loadReplay("javascript:alert(1)", ORIGIN, vi.fn());
    expect(result.ok).toBe(false);
  });

  it("explains when the address returns a web page instead of a replay", async () => {
    const result = await loadReplay("/missing.json", ORIGIN, respond("<!doctype html><html></html>", "text/html"));
    expect(result).toEqual({
      ok: false,
      error: "that address returned a web page, not a replay file (is the file name right?)",
    });
  });

  it("explains when the file is not valid JSON", async () => {
    const result = await loadReplay("/broken.json", ORIGIN, respond("{ not json", "application/json"));
    expect(result).toEqual({ ok: false, error: "the file is not valid JSON" });
  });

  it("reports a missing file", async () => {
    const result = await loadReplay("/nope.json", ORIGIN, respond("", "text/plain", 404));
    expect(result).toEqual({ ok: false, error: "file not found (404)" });
  });
});

describe("the bundled sample replay and Crew records", () => {
  it("pairs up when the crew ids match", () => {
    expect(missionFrom(replay, [crew], "bundled crew-records.json")).toEqual({ ok: true, replay, crew });
  });

  it("gives a clear message instead of crashing when the crew ids do not match", () => {
    const result = missionFrom(replay, [{ ...crew, id: "Z" }], "bundled crew-records.json");
    expect(result).toEqual({ ok: false, error: "bundled crew-records.json has no Crew record for crew A" });
  });
});
