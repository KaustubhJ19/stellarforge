import type { IndicatorId, Status } from "../contracts";
import type { ShownReading } from "../replay/state";
import { INDICATORS } from "../indicators";
import { STRUCTURE_IDS, type StructureId } from "./structures";

/** Severity order: higher is worse. */
export const STATUS_RANK: Record<Status, number> = { green: 0, amber: 1, red: 2 };

export function worse(a: Status | null, b: Status | null): Status | null {
  if (a === null) return b;
  if (b === null) return a;
  return STATUS_RANK[b] > STATUS_RANK[a] ? b : a;
}

export interface Glow {
  structures: Record<StructureId, Status | null>;
  /** Whole-body Indicators (dose, temperature) glow only when not green. */
  wholeBody: Status | null;
}

/** Status glow from the latest Reading of each Indicator. Status comes from Alerts, never recomputed. */
export function glowFrom(latest: Map<IndicatorId, ShownReading>): Glow {
  const structures = Object.fromEntries(STRUCTURE_IDS.map((id) => [id, null])) as Glow["structures"];
  let wholeBody: Status | null = null;
  for (const reading of latest.values()) {
    const place = INDICATORS[reading.indicator]?.place;
    if (!place) continue;
    if (place === "whole-body") {
      if (reading.status !== "green") wholeBody = worse(wholeBody, reading.status);
      continue;
    }
    for (const id of place) structures[id] = worse(structures[id], reading.status);
  }
  return { structures, wholeBody };
}
