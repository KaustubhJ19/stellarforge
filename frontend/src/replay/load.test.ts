import { loadReplay } from "./load";
import { marsReplay } from "../test/replay";

const ORIGIN = "http://localhost:4173";

function respond(body: string, contentType: string, status = 200): typeof fetch {
  return async () => new Response(body, { status, headers: { "content-type": contentType } });
}

describe("loading a replay file from ?replay=", () => {
  it("loads a replay from the app's own address", async () => {
    const result = await loadReplay("/replay/day3.json", ORIGIN, respond(JSON.stringify(marsReplay()), "application/json"));
    expect(result.ok).toBe(true);
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
