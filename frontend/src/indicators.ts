import type { IndicatorId, ReadingSource } from "./contracts";
import type { StructureId } from "./body/structures";

export type HealthKind = "physical" | "mental";

/**
 * Where on the body an Indicator glows (spec: Indicator-to-structure map).
 * "whole-body" tints the whole body; [] never glows (self-reports such as mood).
 */
export type BodyPlace = StructureId[] | "whole-body";

export interface IndicatorInfo {
  label: string;
  kind: HealthKind;
  place: BodyPlace;
  /** An honest label shown with every value, e.g. "sample, not real data". */
  note?: string;
}

/** Display facts about each Indicator the web app knows how to show. */
export const INDICATORS: Record<IndicatorId, IndicatorInfo> = {
  // Physical. Names follow Spec 1's replay generators (tools/*.py on the data branch).
  heart_rate: { label: "Heart rate", kind: "physical", place: ["heart", "vessels.carotids"] },
  resting_heart_rate: { label: "Resting heart rate", kind: "physical", place: ["heart", "vessels.carotids"] },
  systolic_bp: { label: "Blood pressure (systolic)", kind: "physical", place: ["heart", "vessels.carotids"] },
  diastolic_bp: { label: "Blood pressure (diastolic)", kind: "physical", place: ["heart", "vessels.carotids"] },
  mean_arterial_pressure: { label: "Mean arterial pressure", kind: "physical", place: ["heart", "vessels.carotids"] },
  stroke_volume: { label: "Stroke volume", kind: "physical", place: ["heart"] },
  cardiac_output: { label: "Cardiac output", kind: "physical", place: ["heart"] },
  ecg: { label: "ECG", kind: "physical", place: ["heart", "vessels.carotids"] },
  cardiac_rhythm: { label: "Heart rhythm", kind: "physical", place: ["heart"] },
  respiration_rate: { label: "Respiration", kind: "physical", place: ["lungs"] },
  spo2: { label: "SpO₂", kind: "physical", place: ["lungs"] },
  etco2: { label: "Exhaled CO₂", kind: "physical", place: ["lungs"] },
  steps: { label: "Steps", kind: "physical", place: [] },
  glucose: { label: "Glucose", kind: "physical", place: ["liver", "muscle.thigh"] },
  insulin_resistance: { label: "Insulin resistance", kind: "physical", place: ["liver", "muscle.thigh"] },
  // No open source for bone density (data lead, 2026-11-15): sample only.
  bone_density: { label: "Bone density", kind: "physical", place: ["bone.hip", "bone.spine"], note: "sample, not real data" },
  soreness: { label: "Muscle soreness", kind: "physical", place: ["muscle.thigh"] },
  muscle_strength: { label: "Muscle strength", kind: "physical", place: ["muscle.thigh"] },
  kidney_stones: { label: "Kidney stone risk", kind: "physical", place: ["kidneys"] },
  eyes_sans: { label: "Eyes (SANS)", kind: "physical", place: ["eye.optic"] },
  balance: { label: "Balance", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  motion_sickness: { label: "Motion sickness", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  // Stand test (logged by the crew; Apollo AP005 measures)
  standing_heart_rate: { label: "Standing heart rate", kind: "physical", place: ["heart", "vessels.carotids"] },
  standing_systolic_bp: { label: "Standing systolic BP", kind: "physical", place: ["heart", "vessels.carotids"] },
  // Post-EVA check (self-reports; no body place)
  post_eva_heart_rate: { label: "Heart rate after EVA", kind: "physical", place: [] },
  hand_pain: { label: "Hand or finger pain", kind: "physical", place: [] },
  joint_pain: { label: "Joint pain", kind: "physical", place: [] },
  skin_irritation: { label: "Skin itch or rash", kind: "physical", place: [] },
  tingling: { label: "Tingling", kind: "physical", place: [] },
  // Post-EVA warning signs: NASA's Type II decompression sickness signs (OCHMO-TB-037 Rev D, p. 3)
  numbness: { label: "Numbness", kind: "physical", place: [] },
  weakness: { label: "Weakness", kind: "physical", place: [] },
  confusion: { label: "Confusion", kind: "physical", place: [] },
  dizziness: { label: "Dizziness or ear problems", kind: "physical", place: [] },
  chest_or_breathing: { label: "Chest pain or trouble breathing", kind: "physical", place: [] },
  radiation_dose_accumulated: { label: "Radiation dose", kind: "physical", place: "whole-body" },
  body_temperature: { label: "Body temperature", kind: "physical", place: "whole-body" },
  // Mental
  stress: { label: "Stress", kind: "mental", place: ["brain.prefrontal", "brain.amygdala"] },
  fatigue: {
    label: "Fatigue",
    kind: "mental",
    place: ["brain.prefrontal", "brain.parietal", "brain.occipital", "brain.thalamus"],
  },
  readiness: {
    label: "Readiness",
    kind: "mental",
    place: ["brain.prefrontal", "brain.parietal", "brain.occipital", "brain.thalamus"],
  },
  sleep_duration: { label: "Sleep", kind: "mental", place: ["brain.hypothalamus"] },
  sleep_score: { label: "Sleep score", kind: "mental", place: ["brain.hypothalamus"] },
  sleep_quality: { label: "Sleep quality", kind: "mental", place: ["brain.hypothalamus"] },
  mood: { label: "Mood", kind: "mental", place: [] },
};

/**
 * Habitat Readings (cabin air, dose rates): the mission bar shows the accumulated dose;
 * these are not a crew member's health and stay out of the summaries.
 */
export const HABITAT_INDICATORS: IndicatorId[] = [
  "radiation_dose_accumulated",
  "radiation_dose_total",
  "radiation_dose_gcr",
  "radiation_dose_saa",
  "cabin_temperature",
  "cabin_relative_humidity",
  "cabin_co2",
];

/** "CoarseVentricularFibrillation" -> "Coarse ventricular fibrillation". */
function words(text: string): string {
  const spaced = text.replace(/([a-z])([A-Z])/g, "$1 $2").replace(/_/g, " ").toLowerCase();
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

/**
 * Few enough decimals to read: one at 10 and above, two from 1 to 10 (a T-score of -1.15),
 * two significant figures below 1 so small values never read as 0 (0.004 mGy/day).
 */
export function formatNumber(value: number): string {
  const a = Math.abs(value);
  if (a === 0) return "0";
  if (a < 1) return String(+value.toPrecision(2));
  return String(+value.toFixed(a >= 10 ? 1 : 2));
}
const rounded = formatNumber;

/**
 * Value and unit for display: a "score 1-5" self-report reads "3 of 5", a 0-1 "fraction"
 * (Pulse SpO2) reads as a percentage, text values (cardiac rhythm) read as words.
 */
export function formatValue(value: number | string, unit: string): { value: string; unit: string } {
  if (typeof value === "string") return { value: words(value), unit: "" };
  const scale = /^(?:score )?\d+-(\d+)$/.exec(unit);
  if (scale) return { value: rounded(value), unit: `of ${scale[1]}` };
  if (unit === "yes/no") return { value: value ? "Yes" : "No", unit: "" };
  if (unit === "1/min") return { value: rounded(value), unit: "/min" }; // Pulse's per-minute rates
  if (unit === "degC") return { value: rounded(value), unit: "°C" };
  if (unit === "fraction") return { value: String(+(value * 100).toFixed(1)), unit: "%" };
  return { value: rounded(value), unit };
}

const ORDER = Object.keys(INDICATORS);

/** Sort comparator: the display order of INDICATORS; unknown Indicators go last. */
export function byIndicatorOrder(a: IndicatorId, b: IndicatorId): number {
  const rank = (id: IndicatorId) => (ORDER.includes(id) ? ORDER.indexOf(id) : ORDER.length);
  return rank(a) - rank(b);
}

/** Reading.source in plain words; simulated values always say so. */
export const SOURCE_TEXT: Record<ReadingSource, string> = {
  sensor: "Sensor",
  camera: "Camera",
  mic: "Microphone",
  manual: "Self-report",
  lab: "Lab test",
  sim: "Simulated",
};

/** A 0-1 fraction becomes a percentage for display (tiles, charts, bands); other units are as given. */
export function displayScale(unit: string): { factor: number; unit: string } {
  if (unit === "fraction") return { factor: 100, unit: "%" };
  return { factor: 1, unit: UNIT_TEXT[unit] ?? unit };
}

/** Units as the crew reads them (charts; tiles use formatValue). */
const UNIT_TEXT: Record<string, string> = { degC: "°C", "1/min": "/min" };

/** The possible range of a bounded unit ("score 1-5", "fraction", "%"); null if open-ended. */
export function scaleRange(unit: string): [number, number] | null {
  const scale = /^(?:score )?(\d+)-(\d+)$/.exec(unit);
  if (scale) return [Number(scale[1]), Number(scale[2])];
  if (unit === "fraction") return [0, 1];
  if (unit === "%") return [0, 100];
  return null;
}

export function sourceLabel(source: string): string {
  return SOURCE_TEXT[source as ReadingSource] ?? source;
}

export function indicatorLabel(id: IndicatorId): string {
  return INDICATORS[id]?.label ?? id;
}
