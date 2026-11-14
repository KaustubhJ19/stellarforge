// Shapes consumed from Spec 1 (frozen at H2). Until the JSON Schemas land in
// contracts/, these mirror the fields listed in the Spec 2 contracts table.
// Assumptions are marked ASSUMED; ticket 12 swaps them for the frozen shapes.

/** Mission-elapsed time in seconds since mission start. ASSUMED unit. */
export type MissionTime = number;

/** Green / amber / red. ASSUMED spelling of Reading.state and Alert.status. */
export type Status = "green" | "amber" | "red";

export type IndicatorId = string;

export interface Reading {
  crew: string;
  indicator: IndicatorId;
  value: number;
  unit: string;
  t: MissionTime;
  source: string;
  confidence: number;
  state: Status;
}

export type AlertKind = "acute" | "drift" | "emergency";

export interface Alert {
  id: string;
  kind: AlertKind;
  crew: string;
  indicator: IndicatorId;
  deviation: number;
  status: Status;
  urgency: string;
  likely_causes: string[];
  t: MissionTime;
}

export interface CrewRecord {
  id: string;
  sex: "male" | "female";
  anchor: string;
  missionProfile: string;
}

/** ASSUMED: the profile payload carried by a ReplayFile. */
export interface MissionProfile {
  id: string;
  name: string;
  groundDelayMin: number;
}

/** ASSUMED: the personal baseline band for an Indicator (from Spec 3). */
export interface Baseline {
  indicator: IndicatorId;
  low: number;
  high: number;
}

/** ASSUMED: a check due today. */
export interface Task {
  id: string;
  title: string;
  done: boolean;
}

export type ReplayEvent =
  | { t: MissionTime; type: "reading"; payload: Reading }
  | { t: MissionTime; type: "alert"; payload: Alert }
  | { t: MissionTime; type: "baseline"; payload: Baseline }
  | { t: MissionTime; type: "task"; payload: Task };

export interface ReplayFile {
  crew: CrewRecord;
  profile: MissionProfile;
  events: ReplayEvent[];
}

/**
 * ASSUMED: one measurement card's content from Spec 5 (content/cards/).
 * Every field is optional so a card renders before its content is written.
 */
export interface CardContent {
  indicator: IndicatorId;
  how?: string;
  why?: string;
  ifAbnormal?: string;
  /** Honest labels, e.g. "team value", "Earth reference, no space data". */
  labels?: string[];
  /** Citations for the content. */
  sources?: string[];
}
