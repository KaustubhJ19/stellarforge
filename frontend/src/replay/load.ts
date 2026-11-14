import type { CrewRecord, ReplayFile } from "../contracts";
import { parseReplay, pickCrewRecord } from "./parse";

export type MissionResult = { ok: true; replay: ReplayFile; crew: CrewRecord } | { ok: false; error: string };

const CREW_RECORDS = "crew-records.json";

/**
 * Fetches a replay file named by `?replay=` and its Crew record from the crew-records.json
 * beside it (where Spec 1's generators write both). Only files served from the app's own
 * address are accepted, so a link cannot make the app show readings from elsewhere.
 * Every failure comes back as a plain-language message.
 */
export async function loadMission(
  address: string,
  appOrigin: string,
  fetchFn: typeof fetch = fetch,
): Promise<MissionResult> {
  let url: URL;
  try {
    url = new URL(address, appOrigin);
  } catch {
    return { ok: false, error: "that is not a valid address" };
  }
  if (url.origin !== new URL(appOrigin).origin) {
    return { ok: false, error: "replay files must come from this app's own address" };
  }

  const replayJson = await fetchJson(url, fetchFn, "a replay file");
  if (!replayJson.ok) return replayJson;
  const parsed = parseReplay(replayJson.json);
  if (!parsed.ok) return parsed;

  const where = `${CREW_RECORDS} beside the replay`;
  const crewJson = await fetchJson(new URL(CREW_RECORDS, url), fetchFn, CREW_RECORDS, "is it there?");
  if (!crewJson.ok) return { ok: false, error: `${where}: ${crewJson.error}` };
  return missionFrom(parsed.replay, crewJson.json, where);
}

/**
 * Checks a replay and finds its Crew record in a crew-records document. Used for loaded
 * files and for the bundled sample, so a mismatch is a message, never a crash.
 */
export function missionFrom(replayJson: unknown, crewRecordsJson: unknown, where: string): MissionResult {
  const parsed = parseReplay(replayJson);
  if (!parsed.ok) return parsed;
  const crew = pickCrewRecord(crewRecordsJson, parsed.replay.crew, where);
  if (!crew.ok) return crew;
  return { ok: true, replay: parsed.replay, crew: crew.crew };
}

async function fetchJson(
  url: URL,
  fetchFn: typeof fetch,
  what: string,
  hint = "is the file name right?",
): Promise<{ ok: true; json: unknown } | { ok: false; error: string }> {
  let response: Response;
  try {
    response = await fetchFn(url.href);
  } catch {
    return { ok: false, error: "the file could not be reached" };
  }
  if (response.status === 404) return { ok: false, error: "file not found (404)" };
  if (!response.ok) return { ok: false, error: `the file could not be loaded (${response.status})` };

  const text = await response.text();
  const type = response.headers.get("content-type") ?? "";
  if (type.includes("text/html") || /^\s*</.test(text)) {
    return { ok: false, error: `that address returned a web page, not ${what} (${hint})` };
  }
  try {
    return { ok: true, json: JSON.parse(text) };
  } catch {
    return { ok: false, error: "the file is not valid JSON" };
  }
}
