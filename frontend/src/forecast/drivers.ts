import { STRUCTURES, type StructureId } from "../body/structures";

/** Spec 3's forecast drivers (PMData wellness answers): a label and where each sits on the body. */
export const DRIVERS: Record<string, { label: string; place: StructureId[] }> = {
  readiness: { label: "Yesterday's readiness", place: ["brain.prefrontal", "brain.parietal", "brain.occipital", "brain.thalamus"] },
  fatigue: { label: "Fatigue", place: ["brain.prefrontal", "brain.parietal", "brain.occipital", "brain.thalamus"] },
  stress: { label: "Stress", place: ["brain.prefrontal", "brain.amygdala"] },
  sleep_duration_h: { label: "Sleep length", place: ["brain.hypothalamus"] },
  sleep_quality: { label: "Sleep quality", place: ["brain.hypothalamus"] },
  soreness: { label: "Muscle soreness", place: ["muscle.thigh"] },
  // Mood never glows on the body (Spec 2), so it is listed only.
  mood: { label: "Mood", place: [] },
};

export function driverLabel(key: string): string {
  return DRIVERS[key]?.label ?? key.replace(/_/g, " ");
}

/**
 * Heat-map weight per structure: the summed size of the drivers placed there, scaled so the
 * strongest is 1. Direction (raised or lowered) is told in words, not colour.
 */
export function explainWeights(drivers: Record<string, number>): Partial<Record<StructureId, number>> {
  const sums: Partial<Record<StructureId, number>> = {};
  for (const [key, shap] of Object.entries(drivers)) {
    for (const id of DRIVERS[key]?.place ?? []) {
      if (id in STRUCTURES) sums[id] = (sums[id] ?? 0) + Math.abs(shap);
    }
  }
  const max = Math.max(0, ...Object.values(sums));
  if (max === 0) return {};
  return Object.fromEntries(Object.entries(sums).map(([id, v]) => [id, v / max]));
}
