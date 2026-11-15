import type { MissionTime } from "../contracts";

const DAY = 86400;

/** "Day 3 · 14:00" for a mission-elapsed time in seconds (24-hour clock, as on board). */
export function formatMissionTime(t: MissionTime): string {
  const day = Math.floor(t / DAY) + 1;
  return `Day ${day} · ${formatClock(t)}`;
}

/** "14:00" (clock only), for dense axis ticks. */
export function formatClock(t: MissionTime): string {
  const secs = t - Math.floor(t / DAY) * DAY;
  const hh = String(Math.floor(secs / 3600)).padStart(2, "0");
  const mm = String(Math.floor((secs % 3600) / 60)).padStart(2, "0");
  return `${hh}:${mm}`;
}
