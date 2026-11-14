import { extent } from "../charts/scale";
import type {
  Alert,
  CrewRecord,
  IndicatorId,
  MissionTime,
  Reading,
  ReplayEvent,
  ReplayFile,
  Status,
  Task,
} from "../contracts";
import { HABITAT_INDICATORS } from "../indicators";

const DAY = 86400;

/** A Reading with the health Status known at its time (from Alerts; no Alert is green). */
export interface ShownReading extends Reading {
  status: Status;
}

/** The person's own normal band for an Indicator. */
export interface Baseline {
  low: number;
  high: number;
}

/** What the crew sees at one Mission-clock time: the replay folded up to `t`. */
export interface MissionState {
  t: MissionTime;
  missionDay: number;
  latest: Map<IndicatorId, ShownReading>;
  alerts: Alert[];
  tasks: Task[];
}

export function replayRange(replay: ReplayFile): [MissionTime, MissionTime] {
  return extent(replay.events.map((e) => e.t));
}

/**
 * Whether an event's payload belongs on this crew member's screen: their own, plus the
 * habitat's (cabin, dose). Quarantined Readings are shown: Spec 3 holds Readings out of the
 * baseline while an Alert is open, so they are the abnormal values the crew must see.
 */
function shows(replay: ReplayFile, e: ReplayEvent): boolean {
  if (e.type !== "reading" && e.type !== "alert") return true;
  return e.payload.crew === replay.crew || HABITAT_INDICATORS.includes(e.payload.indicator);
}

export function missionStateAt(replay: ReplayFile, t: MissionTime): MissionState {
  const latest = new Map<IndicatorId, Reading>();
  const status = new Map<IndicatorId, Status>();
  const tasks = new Map<string, Task>();
  const alerts: Alert[] = [];
  for (const e of replay.events) {
    if (e.t > t || !shows(replay, e)) continue;
    switch (e.type) {
      case "reading": {
        const prev = latest.get(e.payload.indicator);
        if (!prev || prev.t <= e.t) latest.set(e.payload.indicator, e.payload);
        break;
      }
      case "alert":
        alerts.push(e.payload);
        // Events are ordered by t, so the last Alert seen is the newest.
        status.set(e.payload.indicator, e.payload.status);
        break;
      case "task":
        tasks.set(e.payload.id, e.payload);
        break;
    }
  }
  const shown = new Map<IndicatorId, ShownReading>();
  for (const [id, r] of latest) shown.set(id, { ...r, status: status.get(id) ?? "green" });
  return {
    t,
    missionDay: Math.floor(t / DAY) + 1,
    latest: shown,
    alerts,
    tasks: [...tasks.values()],
  };
}

/** All Readings of one Indicator, oldest first, each with the Status known at its time. */
export function seriesOf(replay: ReplayFile, indicator: IndicatorId): ShownReading[] {
  const readings: Reading[] = [];
  const alerts: Alert[] = [];
  for (const e of replay.events) {
    if (!shows(replay, e)) continue;
    if (e.type === "reading" && e.payload.indicator === indicator) readings.push(e.payload);
    if (e.type === "alert" && e.payload.indicator === indicator) alerts.push(e.payload);
  }
  readings.sort((a, b) => a.t - b.t);
  alerts.sort((a, b) => a.t - b.t);
  // An Alert applies to Readings at or after its time (including one at the same second).
  let next = 0;
  let status: Status = "green";
  return readings.map((r) => {
    while (next < alerts.length && alerts[next].t <= r.t) status = alerts[next++].status;
    return { ...r, status };
  });
}

/** "Your normal": the Crew record's anchor mean ± 2 SD; none if the anchor lacks the Indicator. */
export function baselineFor(crew: CrewRecord, indicator: IndicatorId): Baseline | undefined {
  const a = Object.hasOwn(crew.anchor, indicator) ? crew.anchor[indicator] : undefined;
  if (!a || !Number.isFinite(a.mean) || !Number.isFinite(a.sd)) return undefined;
  const round = (n: number) => +n.toFixed(3);
  return { low: round(a.mean - 2 * a.sd), high: round(a.mean + 2 * a.sd) };
}
