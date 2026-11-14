import type { IndicatorId } from "./contracts";

export type HealthKind = "physical" | "mental";

export interface IndicatorInfo {
  label: string;
  kind: HealthKind;
}

/** Display facts about each Indicator the web app knows how to show. */
export const INDICATORS: Record<IndicatorId, IndicatorInfo> = {
  heart_rate: { label: "Heart rate", kind: "physical" },
  respiratory_rate: { label: "Respiration", kind: "physical" },
  spo2: { label: "SpO₂", kind: "physical" },
  radiation_dose: { label: "Radiation dose", kind: "physical" },
  bone_density: { label: "Bone density", kind: "physical" },
  stress: { label: "Stress", kind: "mental" },
  alertness: { label: "Alertness", kind: "mental" },
  mood: { label: "Mood", kind: "mental" },
};

export function indicatorLabel(id: IndicatorId): string {
  return INDICATORS[id]?.label ?? id;
}
