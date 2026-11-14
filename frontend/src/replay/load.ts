import { parseReplay, type ParseResult } from "./parse";

/**
 * Fetches a replay file named by `?replay=`. Only files served from the app's own
 * address are accepted, so a link cannot make the app show readings from elsewhere.
 * Every failure comes back as a plain-language message.
 */
export async function loadReplay(
  address: string,
  appOrigin: string,
  fetchFn: typeof fetch = fetch,
): Promise<ParseResult> {
  let url: URL;
  try {
    url = new URL(address, appOrigin);
  } catch {
    return { ok: false, error: "that is not a valid address" };
  }
  if (url.origin !== new URL(appOrigin).origin) {
    return { ok: false, error: "replay files must come from this app's own address" };
  }

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
    return { ok: false, error: "that address returned a web page, not a replay file (is the file name right?)" };
  }
  let json: unknown;
  try {
    json = JSON.parse(text);
  } catch {
    return { ok: false, error: "the file is not valid JSON" };
  }
  return parseReplay(json);
}
