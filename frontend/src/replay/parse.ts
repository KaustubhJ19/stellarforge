import type { CrewRecord, ReplayFile } from "../contracts";

export type ParseResult = { ok: true; replay: ReplayFile } | { ok: false; error: string };

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

/** Fields each event payload needs before the app can show it. Other event types are ignored. */
const PAYLOAD_FIELDS: Record<string, string[]> = {
  reading: ["indicator", "value", "unit", "t"],
  alert: ["id", "kind", "indicator", "status", "t"],
  task: ["id", "title", "done"],
  forecast: ["crew", "t", "value", "low", "high"],
};

/** The forecast schema is only provisional, so check the fields its views do arithmetic on. */
function forecastReadable(p: Record<string, unknown>): boolean {
  const nums = ["value", "low", "high", "population", "personal_correction"].every((k) => typeof p[k] === "number");
  return nums && isObject(p.drivers) && Object.values(p.drivers).every((v) => typeof v === "number");
}

/**
 * Checks a replay file loaded from outside (e.g. `?replay=`) has the shape the app reads
 * (Spec 1's ReplayFile), so a wrong file shows a message instead of a blank page.
 * The full contract check is contracts/validate.py; this is only what the app relies on.
 */
export function parseReplay(json: unknown): ParseResult {
  if (!isObject(json)) return { ok: false, error: "not a JSON object" };
  const missing = ["crew", "profile", "events"].filter((k) => !(k in json));
  if (missing.length) return { ok: false, error: `missing ${missing.join(", ")}` };
  if (typeof json.crew !== "string") return { ok: false, error: 'crew should be a crew id, e.g. "A"' };
  if (typeof json.profile !== "string") return { ok: false, error: 'profile should be a profile id, e.g. "mars_transit"' };
  if (!Array.isArray(json.events)) return { ok: false, error: "events is not a list" };
  let lastT = -Infinity;
  for (const [i, e] of json.events.entries()) {
    if (!isObject(e) || typeof e.t !== "number" || typeof e.type !== "string") {
      return { ok: false, error: `event ${i} needs t and type` };
    }
    const need = PAYLOAD_FIELDS[e.type];
    if (!need) continue;
    const payload = e.payload;
    const lacking = isObject(payload) ? need.filter((f) => !(f in payload)) : need;
    if (lacking.length) return { ok: false, error: `event ${i} (${e.type}) is missing ${lacking.join(", ")}` };
    if (e.type === "forecast" && !forecastReadable(payload as Record<string, unknown>)) {
      return {
        ok: false,
        error: `event ${i} (forecast) needs numbers for value, population, personal_correction and drivers as a set of numbers`,
      };
    }
  }
  for (const [i, e] of (json.events as { t: number }[]).entries()) {
    if (e.t < lastT) return { ok: false, error: `event ${i} is out of time order` };
    lastT = e.t;
  }
  return { ok: true, replay: json as unknown as ReplayFile };
}

export type CrewResult = { ok: true; crew: CrewRecord } | { ok: false; error: string };

/** Finds one crew member in a crew-records.json (a list, as the generators write it, or one record). */
export function pickCrewRecord(json: unknown, crewId: string, where: string): CrewResult {
  const records = Array.isArray(json) ? json : [json];
  const found = records.find((r) => isObject(r) && r.id === crewId);
  if (!isObject(found)) return { ok: false, error: `${where} has no Crew record for crew ${crewId}` };
  if (found.sex !== "male" && found.sex !== "female") {
    return { ok: false, error: `${where}: crew ${crewId}'s sex should be "male" or "female"` };
  }
  if (!isObject(found.anchor)) return { ok: false, error: `${where}: crew ${crewId} has no anchor` };
  return { ok: true, crew: found as unknown as CrewRecord };
}
