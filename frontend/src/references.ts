import cutOffs from "../../content/profiles/detection-cut-offs.json";

/**
 * Cited reference values (not team values), read from Spec 3's content file
 * content/profiles/detection-cut-offs.json (cut-off `return_to_gravity_shift`).
 */
interface CutOff {
  name: string;
  value: unknown;
  label: string;
  source: string;
}

function cutOff(name: string): CutOff {
  const found = (cutOffs.cutoffs as CutOff[]).find((c) => c.name === name);
  if (!found) throw new Error(`content/profiles/detection-cut-offs.json has no cut-off "${name}"`);
  return found;
}

const shift = cutOff("return_to_gravity_shift");

/** Apollo AP005 group-mean change from before flight to first after landing (bpm / mmHg). */
export const APOLLO_RETURN_SHIFT = {
  shift: shift.value as Record<string, number>,
  label: shift.label,
  source: shift.source,
};
