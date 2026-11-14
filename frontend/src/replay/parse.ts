import type { ReplayFile } from "../contracts";

export type ParseResult = { ok: true; replay: ReplayFile } | { ok: false; error: string };

const isObject = (v: unknown): v is Record<string, unknown> => typeof v === "object" && v !== null;

/** Fields each event payload needs before the app can show it. */
const PAYLOAD_FIELDS: Record<string, string[]> = {
  reading: ["indicator", "value", "unit", "t", "state"],
  alert: ["id", "kind", "indicator", "status", "t"],
  baseline: ["indicator", "low", "high"],
  task: ["id", "title", "done"],
};

/**
 * Checks a replay file loaded from outside (e.g. `?replay=`) has the shape the app reads,
 * so a wrong file shows a message instead of a blank page. Unknown event types are kept;
 * the app ignores them.
 */
export function parseReplay(json: unknown): ParseResult {
  if (!isObject(json)) return { ok: false, error: "not a JSON object" };
  const missing = ["crew", "profile", "events"].filter((k) => !(k in json));
  if (missing.length) return { ok: false, error: `missing ${missing.join(", ")}` };
  if (!isObject(json.profile) || typeof json.profile.name !== "string") {
    return { ok: false, error: "profile needs a name" };
  }
  if (!Array.isArray(json.events)) return { ok: false, error: "events is not a list" };
  for (const [i, e] of json.events.entries()) {
    if (!isObject(e) || typeof e.t !== "number" || typeof e.type !== "string") {
      return { ok: false, error: `event ${i} needs t and type` };
    }
    const need = PAYLOAD_FIELDS[e.type];
    if (!need) continue;
    const payload = e.payload;
    const lacking = isObject(payload) ? need.filter((f) => !(f in payload)) : need;
    if (lacking.length) return { ok: false, error: `event ${i} (${e.type}) is missing ${lacking.join(", ")}` };
  }
  return { ok: true, replay: json as unknown as ReplayFile };
}
