import type { IndicatorId } from "./contracts";
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
  // Physical
  heart_rate: { label: "Heart rate", kind: "physical", place: ["heart", "vessels.carotids"] },
  ecg: { label: "ECG", kind: "physical", place: ["heart", "vessels.carotids"] },
  blood_pressure: { label: "Blood pressure", kind: "physical", place: ["heart", "vessels.carotids"] },
  respiratory_rate: { label: "Respiration", kind: "physical", place: ["lungs"] },
  spo2: { label: "SpO₂", kind: "physical", place: ["lungs"] },
  glucose: { label: "Glucose", kind: "physical", place: ["liver", "muscle.thigh"] },
  insulin_resistance: { label: "Insulin resistance", kind: "physical", place: ["liver", "muscle.thigh"] },
  bone_density: { label: "Bone density", kind: "physical", place: ["bone.hip", "bone.spine"] },
  muscle_strength: { label: "Muscle strength", kind: "physical", place: ["muscle.thigh"] },
  kidney_stones: { label: "Kidney stone risk", kind: "physical", place: ["kidneys"] },
  eyes_sans: { label: "Eyes (SANS)", kind: "physical", place: ["eye.optic"] },
  balance: { label: "Balance", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  motion_sickness: { label: "Motion sickness", kind: "physical", place: ["brain.cerebellum", "ear.vestibular"] },
  radiation_dose: { label: "Radiation dose", kind: "physical", place: "whole-body" },
  temperature: { label: "Temperature", kind: "physical", place: "whole-body" },
  // Mental
  stress: { label: "Stress", kind: "mental", place: ["brain.prefrontal", "brain.amygdala"] },
  alertness: {
    label: "Alertness",
    kind: "mental",
    place: ["brain.prefrontal", "brain.parietal", "brain.occipital", "brain.thalamus"],
  },
  sleep: { label: "Sleep / body clock", kind: "mental", place: ["brain.hypothalamus"] },
  mood: { label: "Mood", kind: "mental", place: [] },
};

/** Value and unit for display; a "1-5" self-report scale reads "3 of 5". */
export function formatValue(value: number, unit: string): { value: string; unit: string } {
  const scale = /^1-(\d+)$/.exec(unit);
  return scale ? { value: String(value), unit: `of ${scale[1]}` } : { value: String(value), unit };
}

const ORDER = Object.keys(INDICATORS);

/** Sort comparator: the display order of INDICATORS; unknown Indicators go last. */
export function byIndicatorOrder(a: IndicatorId, b: IndicatorId): number {
  const rank = (id: IndicatorId) => (ORDER.includes(id) ? ORDER.indexOf(id) : ORDER.length);
  return rank(a) - rank(b);
}

export function indicatorLabel(id: IndicatorId): string {
  return INDICATORS[id]?.label ?? id;
}
