import type { Reading, ReplayFile } from "../contracts";
import marsDay3 from "../fixtures/mars-day3.replay.json";

/** The hand-made Mars mission-day-3 replay. Swapped for Spec 1's file in ticket 12. */
export function marsReplay(): ReplayFile {
  return structuredClone(marsDay3) as ReplayFile;
}

type ReadingInput = Pick<Reading, "indicator" | "value" | "state"> & Partial<Reading>;

/** A minimal replay holding just the given Readings (all at mission day 1, 08:00 unless set). */
export function replayWith(readings: ReadingInput[]): ReplayFile {
  const base = marsReplay();
  return {
    ...base,
    events: readings.map((r) => {
      const t = r.t ?? 8 * 3600;
      const payload: Reading = { crew: base.crew.id, unit: "", t, source: "test", confidence: 1, ...r };
      return { t, type: "reading" as const, payload };
    }),
  };
}
