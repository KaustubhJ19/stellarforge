import type { LayerId } from "./view";

/** Structure nodes in body-male.glb (see tools/anatomy/export_body.py). */
export const STRUCTURES = {
  "brain.prefrontal": { label: "Prefrontal cortex", layer: "brain" },
  "brain.amygdala": { label: "Amygdala", layer: "brain" },
  "brain.parietal": { label: "Parietal cortex", layer: "brain" },
  "brain.occipital": { label: "Visual cortex", layer: "brain" },
  "brain.thalamus": { label: "Thalamus", layer: "brain" },
  "brain.hypothalamus": { label: "Body clock (hypothalamus)", layer: "brain" },
  "brain.cerebellum": { label: "Cerebellum", layer: "brain" },
  "ear.vestibular": { label: "Inner ear balance organ", layer: "brain" },
  "eye.optic": { label: "Optic nerve", layer: "brain" },
  heart: { label: "Heart", layer: "organs" },
  "vessels.carotids": { label: "Carotid arteries", layer: "vessels" },
  lungs: { label: "Lungs", layer: "organs" },
  liver: { label: "Liver", layer: "organs" },
  kidneys: { label: "Kidneys", layer: "organs" },
  "bone.hip": { label: "Hip", layer: "skeleton" },
  "bone.spine": { label: "Spine", layer: "skeleton" },
  "muscle.thigh": { label: "Thigh muscles", layer: "muscles" },
} as const satisfies Record<string, { label: string; layer: LayerId }>;

export type StructureId = keyof typeof STRUCTURES;

export const STRUCTURE_IDS = Object.keys(STRUCTURES) as StructureId[];
