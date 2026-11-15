import { CONTENT_PROFILES, type ProfileContent } from "./content";

/** What the mission bar shows for a profile. */
export interface ProfileView {
  name: string;
  /** e.g. "28.5 min", or null if the profile gives no delay. */
  delay: string | null;
  /** e.g. "one way, team value": direction and how sure the value is. */
  delayNote: string | null;
  /** Cabin CO₂ limit, or null if the profile gives none (then no CO₂ banner can show). */
  co2Limit: Co2Limit | null;
}

export interface Co2Limit {
  mmHg: number;
  /** e.g. "1-hour average", or null if the profile does not say. */
  window: string | null;
  /** The source if sourced, otherwise how sure the value is (e.g. "not confirmed: team value"). */
  basis: string | null;
}

function co2LimitOf(p: ProfileContent): Co2Limit | null {
  const c = p.co2_limit;
  if (!c || typeof c.value !== "number") return null;
  const min = c.averaging_window_min;
  const window =
    typeof min !== "number" ? null : min % 60 === 0 ? `${min / 60}-hour average` : `${min}-minute average`;
  const basis = !c.status || c.status === "sourced" ? (c.source ?? null) : c.status;
  return { mmHg: c.value, window, basis };
}

/**
 * A profile file (Spec 5's content/profiles/<id>.json) as the mission bar shows it. The delay
 * is `comm_delay.value` in its own unit; anything not marked "sourced" is labelled.
 */
export function profileView(p: ProfileContent): ProfileView {
  const d = p.comm_delay;
  const co2Limit = co2LimitOf(p);
  if (!d || typeof d.value !== "number") return { name: p.name, delay: null, delayNote: null, co2Limit };
  const unit = d.unit ?? "";
  const shortUnit = unit.split(" ")[0] || "";
  const sure =
    !d.status || d.status === "sourced" ? null : d.status.includes("team value") ? "team value" : d.status;
  const note = [unit.includes("one way") ? "one way" : unit.includes("round trip") ? "round trip" : null, sure]
    .filter(Boolean)
    .join(", ");
  return { name: p.name, delay: `${d.value}${shortUnit ? ` ${shortUnit}` : ""}`, delayNote: note || null, co2Limit };
}

/** Mission profile by id (ReplayFile.profile, CrewRecord.missionProfile); unknown ids show as given. */
export function profileFor(id: string, profiles: ProfileContent[] = CONTENT_PROFILES): ProfileView {
  const p = profiles.find((c) => c.id === id);
  return p ? profileView(p) : { name: id, delay: null, delayNote: null, co2Limit: null };
}

/** Profiles the switcher offers: every content profile, plus the replay's own if it is unknown. */
export function profileChoices(
  replayProfile: string,
  profiles: ProfileContent[] = CONTENT_PROFILES,
): { id: string; name: string }[] {
  const known = profiles.map((p) => ({ id: p.id, name: p.name }));
  return known.some((p) => p.id === replayProfile) ? known : [{ id: replayProfile, name: replayProfile }, ...known];
}
