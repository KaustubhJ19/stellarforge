/**
 * Cited reference values (not team values). Copied from Spec 3's content file
 * (content/profiles/detection-cut-offs.json, return_to_gravity_shift) on the
 * spec-3-detection-baseline branch; read it from content/ once that is merged.
 */
export const APOLLO_RETURN_SHIFT = {
  /** First postflight minus preflight, group means (24 crew at rest, 9 standing). */
  shift: { resting_heart_rate: 8.1, standing_heart_rate: 23.4, standing_systolic_bp: -13.0 } as Record<string, number>,
  label: "group averages after landing, not limits",
  source:
    "NASA Apollo AP005, Table 6 (61.6→69.7, 76.4→99.8, 118.8→105.8): https://nlsp.nasa.gov/search/data/details/e1fa5c55-ddfe-5548-91ba-864080319f44?dataType=EXPERIMENTS",
};
