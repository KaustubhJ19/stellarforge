import { CONTRACT_VERSION, type MissionTime, type Reading } from "../contracts";

/**
 * A Reading the crew typed in (Reading.source "manual"). Complete on its own, with
 * schema_version, because the data service checks each POST /reading against the schema.
 */
export function manualReading(crew: string, indicator: string, value: number, unit: string, t: MissionTime): Reading {
  return { schema_version: CONTRACT_VERSION, crew, indicator, value, unit, t, source: "manual", confidence: 1, state: "released" };
}
