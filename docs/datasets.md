# Datasets: verification notes and credits (Spike D, ticket 01)

Checked 2026-11-14 by the AI / detection lead. Raw files are kept **outside the repo** (`~/Vedant/Claude/Nasa/datasets/`) and are never committed.

## Credits and licences

| Dataset | Used for | Source | Licence |
|---|---|---|---|
| PMData | Normal days; Readiness target (Forecast B) | https://datasets.simula.no/pmdata/ | CC BY 4.0 |
| OSDR Environmental Data App, mission RR-1 | ISS cabin temperature, humidity, CO₂ replay | https://visualization.osdr.nasa.gov/eda/ (page `dashboard_RR-1`) | Open download; cite as visualization. Terms: https://www.nasa.gov/reference/osdr-help-terms-and-conditions/ |
| OSDR Inspiration4, OSD-569 | Complete blood count (lab Readings) | https://osdr.nasa.gov/bio/repo/data/studies/OSD-569 | Processed data public |
| OSDR Inspiration4, OSD-575 | Comprehensive metabolic panel (lab Readings) | https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 | Processed data public |
| UBFC-rPPG, DATASET_2 (subjects 1, 3, 4, 5, 8) | Webcam heart-rate accuracy (Spike E, ticket 12) | https://sites.google.com/view/ybenezeth/ubfcrppg (downloaded from the authors' OneDrive mirror) | Research use only ("shared for research purpose"). Cite: S. Bobbia, R. Macwan, Y. Benezeth, A. Mansouri, J. Dubois, "Unsupervised skin tissue segmentation for remote photoplethysmography", Pattern Recognition Letters, 2017. |

## UBFC-rPPG (webcam heart rate)

- Per subject: `vid.avi` (uncompressed, 640×480, 30 fps, about 1.3–1.9 GB) and `ground_truth.txt` (line 1 PPG waveform, line 2 oximeter heart rate in bpm, line 3 time in s; one value per frame).
- Consent: the dataset's `Agreement.xlsx` records each volunteer's consent. We use only subjects who agreed to both data sharing and image use (1, 3, 4, 5, 8). **Never show these faces in the pitch; report error numbers only.**
- Spike E result (2026-11-14, `tools/test_webcam_hr_ubfc.py`, classic POS method, no training): 12 windows of 20 s from 5 people, **mean absolute error 4.9 bpm**, 67 % of windows within 5 bpm. One person (subject 3) had errors of 8–20 bpm. Small sample: "estimate, not validated".

## PMData

- File: `pmdata.zip`, 1,416,129,266 bytes, from https://datasets.simula.no/downloads/pmdata.zip
- Readiness scale (from the dataset page): `wellness.csv` holds `readiness` on a **0–10** scale (0 = not ready at all, 10 = ready for anything). Fatigue, mood, sleep quality, soreness and stress use a **1–5** scale where 3 is normal; sleep duration is in hours.
- Checked in the files: 16 participants (`p01`–`p16`), one `pXX/pmsys/wellness.csv` each, 1,747 rows from 2019-11-01 to 2020-03-30. Columns: `effective_time_frame` (ISO 8601, UTC), `fatigue`, `mood`, `readiness`, `sleep_duration_h`, `sleep_quality`, `soreness`, `soreness_area`, `stress`.
- `readiness` takes whole values 0–10 in the data, matching the documented scale. **Verified; the fallback (readiness from fatigue and sleep) is not needed.**
- Data quirk: a few rows have 0 on every 1–5 field (fatigue 2, mood 3, stress 4 rows), which is outside the documented scale. Treat a row as a blank submission and drop it when its 1–5 fields are 0. A `readiness` of 0 on its own is valid (74 rows).
- Participant details: `participant-overview.xlsx` in the zip root.
- Forecast B result (2026-11-14, `tools/test_forecast_b.py`, ticket 11): 16 people, 4 folds; each fold trains on 9 people, calibrates the range on 3 and forecasts 4 people never used to train, day by day from day 8. 1,307 forecasts: **mean error 1.12 readiness points** (0-10 scale), the same as simply saying "tomorrow = today" (1.12). **Range coverage 89.6 %** (target about 90 %), mean range width 5.1 points. The tree size was picked after comparing two settings on these same people. "Estimate, not validated".

## ISS cabin (OSDR Environmental Data App)

- The app has no CSV link; each mission page (`/eda/dashboard_<mission>`) embeds its data as JSON. Saved: `dashboard_RR-1.html` (706,969 bytes).
- RR-1 (Rodent Research 1, SpaceX-4): 12,087 rows every 5 minutes, 2014-09-20 03:59 to 2014-11-01 03:54.
- Fields: `temperature_iss`, `rh_iss`, `co2_iss` and the matching `_ground` control, plus radiation (`gcr`, `saa`, `total`, `accumulated`) and mission milestones.
- Units (from the app's plot script `telemetry_plots.js`): temperature °C, relative humidity %, CO₂ ppm.
- RR-1 ISS ranges: temperature 18.5–26.8 °C (median 22.6); RH 31–76 % (median 43); CO₂ 1,862–4,667 ppm (median 3,192).
- The app describes these as "recorded in the ISS cabin". The mission is a rodent experiment and the app also mentions hardware telemetry, so treat the values as ISS cabin values as labelled by NASA, not as crew-measured data.
- Other missions available in the app: RR-3 to RR-28, APEX-03-1, APEX-03-2, APEX-04, VEG-01C.

## Inspiration4 blood values: OSD ID to panel mapping

| OSD ID | Sample type | Panel | File |
|---|---|---|---|
| OSD-569 | Whole blood | Complete blood count (CBC) | `LSDS-7_Complete_Blood_Count_CBC_TRANSFORMED.csv` (9,317 bytes) |
| OSD-575 | Blood serum | Comprehensive metabolic panel (CMP) | `LSDS-8_Comprehensive_Metabolic_Panel_CMP_TRANSFORMED.csv` (8,506 bytes) |
| OSD-575 | Blood serum | Cardiovascular and immune multiplex panels | not downloaded (not needed) |

- Rows: 4 crew (C001–C004) × 7 timepoints: L-92, L-44, L-3 (days before launch), R+1, R+45, R+82, R+194 (days after return). No in-flight samples (3-day mission).
- Columns: for each test, `<test>_value_<unit>`, `<test>_range_min_<unit>`, `<test>_range_max_<unit>`; the unit is in the column name. Missing values appear as `NA` or `N/A`.
- Other Inspiration4 studies (from https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/): OSD-570 PBMC, OSD-571 plasma, OSD-572 swabs, OSD-573 Dragon capsule environment, OSD-574 skin biopsies, OSD-630 stool, OSD-656 urine, OSD-687 T-cells. Raw (genetic) data needs an application; processed data is public.

## Go / no-go

**GO** (2026-11-14). All three sources downloaded; no fallback used.

| Check | Result |
|---|---|
| PMData downloaded | Yes, full zip (1,416,129,266 bytes) |
| PMData readiness scale | Verified 0–10 in the data and on the dataset page |
| ISS cabin file | Yes, RR-1 page with embedded data; units confirmed |
| Inspiration4 values | Yes, CBC and CMP CSVs downloaded (no typing from paper tables needed) |
| OSD ID-to-panel mapping | Verified from the OSDR file listing: OSD-569 → CBC, OSD-575 → CMP |

**For the data lead (Spec 1):** files are at `~/Vedant/Claude/Nasa/datasets/` (`pmdata/`, `osdr-eda/`, `inspiration4/`) on Vedant's machine; ask Vedant to share them. Use the notes above to build the cabin replay (task 1.6) and the Inspiration4 lab Readings with `source = lab` (task 1.7).
