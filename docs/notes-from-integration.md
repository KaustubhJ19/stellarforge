# Notes from integration (Spec 5) to the team

From the integration lead, 2026-11-15. Branch `specs-5-integration-and-submission`.

## For the data lead (Spec 1)

1. **Glucose readings from real astronauts.** NASA OSDR **OSD-575** (Inspiration4) has a Comprehensive Metabolic Panel next to the blood-count file you already use from OSD-569:
   - `LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv` (25 KB)
   - https://osdr.nasa.gov/bio/repo/data/studies/OSD-575

   If you add its glucose analyte the same way as the blood counts in `tools/inspiration4_labs.py`, `_indicator` should turn the analyte name into `glucose`, which is the name the Safety bound uses. Please check the analyte's exact name in the file; we have not downloaded it.
2. **Body temperature.** We found no open astronaut temperature data. The Safety bound (35–38 °C) and the +1 °C in-flight shift are ready if a source appears; until then no Reading uses `body_temperature`.

## For detection (Spec 3)

Reviewed `content/profiles/detection-cut-offs.json` (Spec 5 ticket 05). Changes:

- `glucose` bound 70–200 mg/dL. The low is ADA 2025 Section 6, a diabetes-care cut-off; the high is ADA 2025 Section 2, the diagnosis threshold for people without a diagnosis.
- `body_temperature` bound 35–38 °C. The low is NASA-STD-3001 Volume 1 Rev C (hypothermia); the high is the CDC fever definition (Earth reference).
- `expected_shift` is now `{"body_temperature": 1.0}`. Stahn et al. 2017 (Sci Rep, PMC5701078) found resting core temperature rose about 1 °C over 2.5 months in flight. Without the shift, the 38 °C fever bound could fire on healthy crew.
- AHA links added to the `heart_rate` and `systolic_bp` sources.
- Please confirm detection reads `glucose` and `body_temperature` under those names.

## For everyone

Every protocol step and Safety bound is listed in `docs/medical-review.md` for a qualified clinician to sign. If nobody signs, the write-up says "Medical content not clinically reviewed."
