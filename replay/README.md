# Replays

Shared replay files from Workstream 1 (Spec 1). Every file validates against `contracts/` (`ReplayFile`;
`crew-records.json` is a list of `CrewRecord`). Each has a `.source.json` record with dataset, link,
licence, download date, file hash and notes. Generated on 2026-11-14/15; rebuild commands below.

| File | What it is | Mission time | Source and licence |
|---|---|---|---|
| `crew-A.json` … `crew-D.json` | Four synthetic crew (A–C male, 152 days; D female, 115 days from PMData p10 at the team's request, days 6–120) of daily readings: resting HR, sleep, steps, sleep score, fatigue, mood, readiness, sleep quality, stress, soreness. Crew A has a planted drift on days 143–151 (source `sim`) | days 0–151 (crew D: days 6–120) | PMData (Simula), CC BY 4.0, see credit below |
| `crew-records.json` | Crew records A–D: sex (D female), Anchor (first 14 days), Mars transit profile | — | as above |
| `emergency-crew-B.json` | Crew B's collapse: stepwise stroke-volume drop, sinus tachycardia, unstable VT, VF and arrest, compressions; 1 s readings incl. `cardiac_rhythm` and `body_temperature`; chest pain as a `crew_report`. **Estimate, not validated** | starts day 152 (t = 13,132,800 s) | Pulse Physiology Engine 4.3.1 (Kitware), Apache 2.0 |
| `iss-cabin-dose-RR-1.json` | Real ISS cabin temperature, humidity, CO₂ in ppm (5 min) and radiation dose (daily), crew `habitat`; plus derived `cabin_pco2` and `cabin_pco2_1h` (mmHg, trailing 1-h average, only when 9+ of 12 samples) for the NASA-STD-3001 V2 6004 limit of 3 mmHg, converted at ISS nominal 14.7 psia (760 mmHg) where the air was measured, not at the mission profile's pressure | t = 0 at the first sample; use `--offset` to align | NASA OSDR Environmental Data App, mission RR-1; radiation cited as visualization |
| `inspiration4-labs-I4-C001.json` … `C004` | Real Inspiration4 blood counts (5 analytes, 7 timepoints), source `lab`, crew `I4-C00n` | t = 0 at L-92 | NASA OSDR OSD-569 (LSDS-7), public |

## Credit (required by CC BY 4.0 for PMData)
Thambawita V. et al., *PMData: A Sports Logging Dataset*, MMSys '20, doi:10.1145/3339825.3394926.
Licence: https://creativecommons.org/licenses/by/4.0/ . Changes: daily values reshaped into StellarForge
Readings; crew A has a planted drift; per-minute steps summed per day.

## Honest limits
- Crew data is Earth wearable data shaped to look like a crew; no open astronaut wearable stream exists.
- The emergency is a Pulse model (no ischemia model; heart rate reads 0 during VF and compressions; core temperature stays near 37.0–37.1 °C).
- Cabin data is from a 2014 ISS rodent mission; Inspiration4 reference ranges are Earth clinical ranges (one subject has inconsistent ranges in the source file; see its source record).

## Rebuild (needs the git-ignored `data/` downloads)
```bash
python tools/crew_replays.py --overview data/pmdata/participant-overview.xlsx --assign D=p10
python tools/emergency_replay.py --bundle data/pulse/PulseExplorer-3.3.0-Windows-AMD64 --offset 13132800
python tools/cabin_dose_replay.py --fetch RR-1
python tools/inspiration4_labs.py
```
Outputs go to `replay/generated/`; copy them here to update the shared set.

`recorded/` holds replays recorded through the service with detection output (Spec 3).
