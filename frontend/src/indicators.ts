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
  respiration_rate: { label: "Respiration", kind: "physical", place: ["lungs"] },
  spo2: { label: "SpO₂", kind: "physical", place: ["lungs"] },
  etco2: { label: "Exhaled CO₂", kind: "physical", place: ["lungs"] },
  steps: { label: "Steps", kind: "physical", place: [] },
  glucose: { label: "Glucose", kind: "physical", place: ["liver", "muscle.thigh"] },
  insulin_resistance: { label: "Insulin resistance", kind: "physical", place: ["liver", "muscle.thigh"] },
  bone_density: { label: "Bone density", kind: "physical", place: ["bone.hip", "bone.spine"] },
  muscle_strength: { label: "Muscle strength", kind: "physical", place: ["muscle.thigh"] },
  kidney_stones: { label: "Kidney stone risk", kind: "physical", place: ["kidneys"] },
  eyes_sans: { label: "Eyes (SANS)", kind: "physical", place: ["eye.optic"] },
  balance: { label: "Balance", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  motion_sickness: { label: "Motion sickness", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  radiation_dose_accumulated: { label: "Radiation dose", kind: "physical", place: "whole-body" },
  temperature: { label: "Temperature", kind: "physical", place: "whole-body" },
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

/**
 * Value and unit for display: a "score 1-5" self-report reads "3 of 5", and a 0-1
 * "fraction" (Pulse SpO2) reads as a percentage.
 */
export function formatValue(value: number, unit: string): { value: string; unit: string } {
  const scale = /^(?:score )?\d+-(\d+)$/.exec(unit);
  if (scale) return { value: String(value), unit: `of ${scale[1]}` };
  if (unit === "fraction") return { value: String(+(value * 100).toFixed(1)), unit: "%" };
  return { value: String(value), unit };
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
  return unit === "fraction" ? { factor: 100, unit: "%" } : { factor: 1, unit };
}

export function sourceLabel(source: string): string {
  return SOURCE_TEXT[source as ReadingSource] ?? source;
}

export function indicatorLabel(id: IndicatorId): string {
  return INDICATORS[id]?.label ?? id;
}
