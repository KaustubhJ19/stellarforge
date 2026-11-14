import type { LayerId } from "./view";

export const REGIONS = {
  head: "Head",
  chest: "Chest",
  abdomen: "Abdomen",
  legs: "Pelvis and legs",
} as const;
export type RegionId = keyof typeof REGIONS;

/** Structure nodes in body-male.glb (see tools/anatomy/export_body.py). */
export const STRUCTURES = {
  "brain.prefrontal": { label: "Prefrontal cortex", layer: "brain", region: "head" },
  "brain.amygdala": { label: "Amygdala", layer: "brain", region: "head" },
  "brain.parietal": { label: "Parietal cortex", layer: "brain", region: "head" },
  "brain.occipital": { label: "Visual cortex", layer: "brain", region: "head" },
  "brain.thalamus": { label: "Thalamus", layer: "brain", region: "head" },
  "brain.hypothalamus": { label: "Body clock (hypothalamus)", layer: "brain", region: "head" },
  "brain.cerebellum": { label: "Cerebellum", layer: "brain", region: "head" },
  "ear.vestibular": { label: "Inner ear balance organ", layer: "brain", region: "head" },
  "eye.optic": { label: "Optic nerve", layer: "brain", region: "head" },
  heart: { label: "Heart", layer: "organs", region: "chest" },
  "vessels.carotids": { label: "Carotid arteries", layer: "vessels", region: "chest" },
  lungs: { label: "Lungs", layer: "organs", region: "chest" },
  liver: { label: "Liver", layer: "organs", region: "abdomen" },
  kidneys: { label: "Kidneys", layer: "organs", region: "abdomen" },
  "bone.hip": { label: "Hip", layer: "skeleton", region: "legs" },
  "bone.spine": { label: "Spine", layer: "skeleton", region: "abdomen" },
  "muscle.thigh": { label: "Thigh muscles", layer: "muscles", region: "legs" },
} as const satisfies Record<string, { label: string; layer: LayerId; region: RegionId }>;

export type StructureId = keyof typeof STRUCTURES;

export const STRUCTURE_IDS = Object.keys(STRUCTURES) as StructureId[];

export function structuresIn(region: RegionId): StructureId[] {
  return STRUCTURE_IDS.filter((id) => STRUCTURES[id].region === region);
}
