# Notes from integration (Spec 5) to the team

From the integration lead, 2026-11-15. Branch `specs-5-integration-and-submission`.

## For the data lead (Spec 1)

1. **Glucose readings from real astronauts (checked).** NASA OSDR **OSD-575** (Inspiration4), file `LSDS-8_Comprehensive_Metabolic_Panel_CMP.upload_SUBMITTED.csv` (25 KB, https://osdr.nasa.gov/bio/repo/data/studies/OSD-575). Same columns as the blood-count file you already read (`ANALYTE, VALUE, RANGE_MIN, RANGE_MAX, UNITS, TEST_TYPE, SUBJECT_ID, SEX, timepoint`).
   - The analyte is `GLUCOSE`, in mg/dL. Your `_indicator` turns it into `glucose`, the name detection uses for the personal baseline and the Safety bound.
   - 28 values: 4 crew (C001 to C004), 7 timepoints (L-92, L-44, L-3, R+1, R+45, R+82, R+194). Lab reference range 65 to 99 mg/dL.
   - **Caution:** 7 of the 28 values are below ADA's 70 mg/dL, and 3 of them are at R+45 (36, 43, 44 mg/dL). Values that low in healthy crew may come from how the samples were handled, but we have not verified that. Because of this, the glucose Safety bound uses ADA level 2 (54–250 mg/dL), so only the 3 lowest values (all at R+45) would alert; the personal baseline handles smaller changes.
2. **Body temperature from Pulse.** No open astronaut temperature data exists. Pulse can report core temperature (EnergySystemData `CoreTemperature`, https://pulse.kitware.com/group___energy_system_data___core_temperature.html). Request: add it to the crew B emergency replay's data requests and to `COLUMNS` in `tools/emergency_replay.py` as `body_temperature` in °C, labelled "estimate, not validated" like the rest of that replay. Please check the exact CSV column name Pulse writes.

## For detection (Spec 3)

Reviewed `content/profiles/detection-cut-offs.json` (Spec 5 ticket 05). Changes:

- **`glucose` Safety bound 54–250 mg/dL** (ADA 2025 Table 6.2, level 2), on top of the personal baseline (decision 2026-11-15). Level 1 (70) would fire on 7 of 28 Inspiration4 values; level 2 fires on 3, all at R+45.
- `body_temperature` bound 35–38 °C. The low is NASA-STD-3001 Volume 1 Rev C (hypothermia); the high is the CDC fever definition (Earth reference).
- `expected_shift` is now `{"body_temperature": 1.0}`. Stahn et al. 2017 (Sci Rep, PMC5701078) found resting core temperature rose about 1 °C over 2.5 months in flight. Without the shift, the 38 °C fever bound could fire on healthy crew.
- AHA links added to the `heart_rate` and `systolic_bp` sources.
- Please confirm detection reads `glucose` and `body_temperature` under those names.

## For the 3D / UI lead (Spec 2)

- **Measurement cards are in `content/cards/`**, one per Indicator: `heart_rate`, `systolic_bp`, `sleep_duration`, `glucose`, `body_temperature`, `mood`. They follow the Spec 5 card shape, not the flat `CardContent` strings your frontend assumes:
  - `how`: list of steps (join them for display)
  - `why`: `{text, hrp_risk, source}`, with `uncovered_reason` when `hrp_risk` is `"uncovered"`
  - `if_abnormal`: `{now, remeasure, tell_crew, tell_ground}`
  - `unit`, `space_note`, `labels` (list), `sources` (list)
- **Mission profile:** read `content/profiles/mars_transit.json`; your `groundDelayMin` is `comm_delay.value`.

## For everyone

Every protocol step and Safety bound is listed in `docs/medical-review.md` for a qualified clinician to sign. If nobody signs, the write-up says "Medical content not clinically reviewed."
