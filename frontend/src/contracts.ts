// Shapes consumed from Spec 1. The JSON Schemas are in contracts/ at the repo root
// (copied from the data service branch); these types mirror them. Anything not in those
// schemas is marked APP-SIDE.

/** Mission clock seconds. */
export type MissionTime = number;

/** Green / amber / red: only ever set by an Alert (Alert.status). */
export type Status = "green" | "amber" | "red";

export type IndicatorId = string;

/** Data state of a Reading (not a health Status). */
export type ReadingState = "released" | "quarantined" | "event";

export type ReadingSource = "sensor" | "camera" | "mic" | "manual" | "lab" | "sim";

export interface Reading {
  /** May be omitted inside a ReplayFile event; it takes the file's. */
  schema_version?: string;
  crew: string;
  indicator: IndicatorId;
  value: number;
  unit: string;
  t: MissionTime;
  source: ReadingSource;
  confidence: number;
  state: ReadingState;
}

export type AlertKind = "acute" | "drift" | "emergency";

export type Urgency = "ACT_NOW" | "ESCALATE_TO_GROUND" | "MONITOR" | "ROUTINE";

export interface LikelyCause {
  indicator: IndicatorId;
  direction: string;
  note: string;
}

/**
 * Alert.deviation as Spec 3 sends it (the schema leaves it open): drift and acute Alerts
 * carry sigmas and the CuSum level; Safety-bound Alerts carry the value and the bound.
 */
export type Deviation =
  | { sigma: number; cusum: number | null; combined: number | null }
  | { value: number; bound: Record<string, unknown> };

export interface Alert {
  schema_version?: string;
  id: string;
  kind: AlertKind;
  crew: string;
  indicator: IndicatorId;
  deviation: Deviation;
  status: Status;
  urgency: Urgency;
  likely_causes: LikelyCause[];
  t: MissionTime;
}

/** The person's own Earth normal for one Indicator. */
export interface AnchorEntry {
  mean: number;
  sd: number;
}

export interface CrewRecord {
  schema_version: string;
  id: string;
  sex: "male" | "female";
  anchor: Record<IndicatorId, AnchorEntry>;
  missionProfile: string;
}

/** APP-SIDE: a check due today. No contract carries tasks yet. */
export interface Task {
  id: string;
  title: string;
  done: boolean;
}

/**
 * Event types the web app reads. A ReplayFile may carry others (trigger, crew_report);
 * the app ignores them. "alert" events carry Spec 3's Alerts; "task" is APP-SIDE.
 */
export type ReplayEvent =
  | { t: MissionTime; type: "reading"; payload: Reading }
  | { t: MissionTime; type: "alert"; payload: Alert }
  | { t: MissionTime; type: "task"; payload: Task };

export interface ReplayFile {
  schema_version: string;
  /** Crew id; the CrewRecord itself comes from crew-records.json. */
  crew: string;
  /** Mission profile id, e.g. "mars_transit". */
  profile: string;
  events: ReplayEvent[];
}

/**
 * One measurement card from Spec 5 (content/cards/*.json at the repo root, the structured
 * source of truth). Every field but `indicator` is optional so a card renders before its
 * content is written.
 */
export interface CardContent {
  indicator: IndicatorId;
  /** Other Indicators this card also explains, e.g. resting_heart_rate on heart_rate's card. */
  related_indicators?: IndicatorId[];
  unit?: string;
  /** Steps, in order. */
  how?: string[];
  why?: {
    text: string;
    /** A NASA HRP risk name, or "uncovered" with `uncovered_reason`. */
    hrp_risk?: string;
    uncovered_reason?: string;
    source?: string;
  };
  if_abnormal?: { now?: string; remeasure?: string; tell_crew?: string; tell_ground?: string };
  space_note?: string;
  /** Honest labels, e.g. "team value", "Earth reference, no space data". */
  labels?: string[];
  /** Citations for the content. */
  sources?: string[];
}
