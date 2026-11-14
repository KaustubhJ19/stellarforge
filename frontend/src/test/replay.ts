import type { Alert, CrewRecord, Reading, ReplayEvent, ReplayFile, Status } from "../contracts";
import marsDay3 from "../fixtures/mars-day3.replay.json";
import crewRecords from "../fixtures/crew-records.json";

/** What the app is given: a replay and the Crew record it belongs to. */
export interface Mission {
  replay: ReplayFile;
  crew: CrewRecord;
}

/** The hand-made Mars mission-day-3 replay (crew A) and its Crew record. */
export function marsMission(): Mission {
  const replay = structuredClone(marsDay3) as ReplayFile;
  const crew = structuredClone((crewRecords as CrewRecord[]).find((c) => c.id === replay.crew)!);
  return { replay, crew };
}

export interface ReadingInput extends Partial<Reading> {
  indicator: string;
  value: number;
  /** Health Status, given by an Alert at the Reading's time. Omitted or green: no Alert. */
  status?: Status;
}

/** Same crew and profile as the Mars replay, holding just these Readings (day 1, 08:00 unless set). */
export function missionWith(readings: ReadingInput[]): Mission {
  const { replay, crew } = marsMission();
  const events: ReplayEvent[] = [];
  readings.forEach(({ status, ...r }, i) => {
    const t = r.t ?? 8 * 3600;
    const reading: Reading = {
      crew: crew.id, unit: "", source: "sensor", confidence: 1, state: "released", ...r, t,
    };
    events.push({ t, type: "reading", payload: reading });
    if (status && status !== "green") events.push({ t, type: "alert", payload: alertFor(reading, status, i) });
  });
  return { replay: { ...replay, events }, crew };
}

export function alertFor(reading: Reading, status: Status, n = 0, kind: Alert["kind"] = "acute"): Alert {
  return {
    id: `test-${n}`, kind, crew: reading.crew, indicator: reading.indicator,
    deviation: { sigma: 5, cusum: null, combined: 3 }, status,
    urgency: kind === "acute" && status === "red" ? "ESCALATE_TO_GROUND" : status === "green" ? "ROUTINE" : "MONITOR",
    likely_causes: [], t: reading.t,
  };
}
