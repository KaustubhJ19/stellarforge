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
  /** A number, or text for categorical Indicators (e.g. cardiac_rhythm "NormalSinus"). */
  value: number | string;
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
  /** null for an emergency Alert about the whole person (Spec 3); Spec 4's flow shows those. */
  indicator: IndicatorId | null;
  /** null for an emergency Alert. */
  deviation: Deviation | null;
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
 * UN-CONTRACTED: tomorrow's readiness forecast (0-10) as Spec 3 proposes to record it into
 * replay files, one per crew per day (their message of 2026-11-15). `base` + the drivers =
 * `population`, the general model's forecast; `value` adds `personal_correction` on top.
 * Replace with the Forecast schema if the data lead adds one.
 */
export interface Forecast {
  crew: string;
  t: MissionTime;
  value: number;
  low: number;
  high: number;
  /** "" (normal), "learning your pattern" (range is the whole 0-10) or "re-measure" (range too wide). */
  label: string | null;
  population: number;
  personal_correction: number;
  base: number;
  /** SHAP value per driver, in readiness points. */
  drivers: Record<string, number>;
}

/**
 * Event types the web app reads. A ReplayFile may carry others (trigger, crew_report);
 * the app ignores them. "alert" events carry Spec 3's Alerts; "forecast" is Spec 3's proposed
 * recorded event (un-contracted); "task" is APP-SIDE.
 */
export type ReplayEvent =
  | { t: MissionTime; type: "reading"; payload: Reading }
  | { t: MissionTime; type: "alert"; payload: Alert }
  | { t: MissionTime; type: "task"; payload: Task }
  | { t: MissionTime; type: "forecast"; payload: Forecast };

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
