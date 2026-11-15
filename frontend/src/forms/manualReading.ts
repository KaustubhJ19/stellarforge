import type { MissionTime, Reading } from "../contracts";

/** A Reading the crew typed in (Reading.source "manual"). */
export function manualReading(crew: string, indicator: string, value: number, unit: string, t: MissionTime): Reading {
  return { crew, indicator, value, unit, t, source: "manual", confidence: 1, state: "released" };
}
