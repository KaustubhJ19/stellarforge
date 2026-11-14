import type { ReplayFile } from "../contracts";
import marsDay3 from "../fixtures/mars-day3.replay.json";

/** The hand-made Mars mission-day-3 replay. Swapped for Spec 1's file in ticket 12. */
export function marsReplay(): ReplayFile {
  return structuredClone(marsDay3) as ReplayFile;
}
