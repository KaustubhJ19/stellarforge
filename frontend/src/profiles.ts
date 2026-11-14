import { CONTENT_PROFILES, type ProfileContent } from "./content";

/** What the mission bar shows for a profile. */
export interface ProfileView {
  name: string;
  /** e.g. "28.5 min", or null if the profile gives no delay. */
  delay: string | null;
  /** e.g. "one way, team value": direction and how sure the value is. */
  delayNote: string | null;
}

/**
 * A profile file (Spec 5's content/profiles/<id>.json) as the mission bar shows it. The delay
 * is `comm_delay.value` in its own unit; anything not marked "sourced" is labelled.
 */
export function profileView(p: ProfileContent): ProfileView {
  const d = p.comm_delay;
  if (!d || typeof d.value !== "number") return { name: p.name, delay: null, delayNote: null };
  const unit = d.unit ?? "";
  const shortUnit = unit.split(" ")[0] || "";
  const sure =
    !d.status || d.status === "sourced" ? null : d.status.includes("team value") ? "team value" : d.status;
  const note = [unit.includes("one way") ? "one way" : unit.includes("round trip") ? "round trip" : null, sure]
    .filter(Boolean)
    .join(", ");
  return { name: p.name, delay: `${d.value}${shortUnit ? ` ${shortUnit}` : ""}`, delayNote: note || null };
}

/** Mission profile by id (ReplayFile.profile, CrewRecord.missionProfile); unknown ids show as given. */
export function profileFor(id: string): ProfileView {
  const p = CONTENT_PROFILES.find((c) => c.id === id);
  return p ? profileView(p) : { name: id, delay: null, delayNote: null };
}

/** Profiles the switcher offers: every content profile, plus the replay's own if it is unknown. */
export function profileChoices(replayProfile: string): { id: string; name: string }[] {
  const known = CONTENT_PROFILES.map((p) => ({ id: p.id, name: p.name }));
  return known.some((p) => p.id === replayProfile) ? known : [{ id: replayProfile, name: replayProfile }, ...known];
}
