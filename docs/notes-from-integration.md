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

**Measurement cards, ready in your `CardContent` shape.** No change to your types or components is needed.

- `content/cards-frontend.json` is a `CardContent[]` with exactly your fields: `indicator`, `how`, `why`, `ifAbnormal`, `labels`, `sources` (all text, labels and sources as lists).
- 7 entries: `heart_rate`, `resting_heart_rate`, `systolic_bp`, `sleep_duration`, `glucose`, `body_temperature`, `mood`.
- `why` includes the NASA HRP risk and the space note. `ifAbnormal` reads "Now: … Measure again: … Tell the crew: … Tell the ground: …".
- It is generated from the structured cards in `content/cards/*.json` by `python tools/export_cards.py`. A test fails if it falls out of step. Don't edit it by hand.

To use it, change one line in `frontend/src/main.tsx` (line 56):

```tsx
import cards from "../../content/cards-frontend.json";
// ...
return <App replay={mission.replay} crew={mission.crew} cards={cards as CardContent[]} />;
```

If the Vite dev server refuses a file outside `frontend/`, add `server: { fs: { allow: [".."] } }` to `vite.config.ts`, or copy the file into `frontend/src/` at build time.

**Needed before the final video:** the cards are not wired yet (`main.tsx` passes no `cards`), so measurement cards show no How / Why / If abnormal. There is also no Accuracy or Credits page in the app; the video shows the repo pages instead.

**Mission profile:** read `content/profiles/mars_transit.json`; your `groundDelayMin` is `comm_delay.value`.

## For the emergency-flow lead (Spec 4)

**Real protocol content is ready to replace the stubs** (Spec 5 ticket 08). Checked against your engine on `integrate/spec2-into-emergency-services` in a scratch copy:

- `content/protocols/microgravity-cpr.json` (13 steps) and `content/protocols/chest-pain.json` (5 steps), each with its companion files:
  - `<id>.roles.json`: Rescuer 1 / Rescuer 2 split. This is a team value; the guideline does not assign roles. Unmapped steps show to everyone.
  - `<id>.excerpts.json`: verbatim excerpts from the cited source for every step.
  - `<id>.recorded.json`: a recorded "Why this step?" answer for every step.
- `content/profiles/mars_transit.json` and `station.json` now carry your fields: `crew`, `equipment`, `delay_one_way_s`, `delay_label`. Both pass `contracts/provisional/mission_profile.schema.json`.
- `tools/drug-denylist.txt`: 64 names (ISS crew-kit drugs plus emergency drugs). Your file is empty, so take ours when merging.

Results with your loader and tests:
- `load_protocol`: 0 steps refused for either protocol. `runtime.build(protocol="microgravity-cpr", profile="mars_transit")` works.
- With one rescuer, steps that need 2 or more (airway, venous access) are hidden, as the guideline requires.
- Your linter with our deny-list: 0 issues. Your backend tests: 214 passed, 1 failed. The failure (`test_no_external_urls_in_runtime_code`) fails the same way on your branch without our files.

To switch: set `SF_PROTOCOL=microgravity-cpr` (or change `DEFAULT_PROTOCOL` / `DEFAULT_PROFILE` in `backend/app/runtime.py` to `microgravity-cpr` / `mars_transit`).

**Two things to agree:**
- **Crew ids:** your stubs use `cmdr`, `eng`, `sci`, `cmo`. The data lead's replays use `A` to `D`, so the profiles use `A` to `D`.
- **Equipment:** both profiles list every item the protocols use, so no step is hidden. On a Mars vehicle that is a team value; on the ISS the defibrillator is sourced (part of the crew health care system).

## Integration #1 result (Spec 5 ticket 08)

`tools/tests/test_integration_1.py` runs the real chain on real content: Spec 1 service + replay, Spec 3 detection, Spec 4 flow, Spec 5 protocol, profile and recorded answers.
- **Auto trigger:** the crew B emergency replay, played through Spec 1's service, reaches the arrest (CoarseVentricularFibrillation). Spec 3's detection raises an emergency Alert and an auto Trigger, about 20 s into the test run.
- **Then the flow:** ACT NOW, verdict, crew alarm after 15 mission seconds, the rescuer accepts, record, contributors, and the first real cited step (`cpr-1-start`).
- **Manual trigger:** reaches the same real steps. A solo rescuer sees only one-rescuer steps.
- **Offline:** "Why this step?" uses the recorded answers, and the ground delay is 1710 s.

**Still open:**
- **Spec 4:** `backend/app/runtime.py` still defaults to `stub-protocol` / `stub-mars`. Switch the defaults to `microgravity-cpr` / `mars_transit` (or set `SF_PROTOCOL` and the profile) for the demo.
- **Spec 2 and Spec 4:** `test_no_external_urls_in_runtime_code` fails on `frontend/src/references.ts` (link to `https://nlsp.nasa.gov`). Agree whether reference links may appear in the frontend, or move them to content.
- **Browser tests (Playwright):** all 37 pass as committed, on the stub content.
  - With the real content and crew ids, the real steps, citations, the auto Trigger and the offline steps all render.
  - The emergency e2e specs still assert the stub's texts, crew ids (`cmdr`/`eng`/`sci`) and 3-step length, so they need updating for the real content (Spec 4).
  - The glove check fails on real UI: a home "Head" zoom button is 56 px, below the 64 px team value (Spec 2 and Spec 4 to agree).
  - `frontend/playwright.config.ts` hard-codes a Windows Python path (`../backend/.venv/Scripts/python.exe`), so it won't start on macOS or Linux.

## Found when merging `main` into the Spec 5 branch (PR prep)

- **Crew records format (Spec 1 and Spec 4):** Spec 4's `load_records` on `main` expects `{"records": [...]}`, but Spec 1's `replay/crew-records.json` is a bare list. So the real crew A–D cannot be loaded; `tools/tests/test_integration_1.py` wraps the list to test.
- **Records setting (Spec 4):** `main` dropped `SF_RECORDS` (and the comma list), so the server always uses `replay/stub-crew-records.json`. The demo needs a way to choose the real records.
- **Demo endpoints (Spec 4):** `/api/sim/*` now exist only with `SF_SIM=1`. Our demo docs now say so.
- **Accuracy changed (Spec 3):** false alerts are now 0.16 per crew-day, not 0.11. The write-up and video script are updated, and `tools/tests/test_write_up.py` caught it.
- **Stale files dropped:** 39 Spec 4 files from the old integration branch that `main` moved (`frontend/src/emergency/`, `frontend/e2e-emergency/`) or removed are deleted on this branch, so the PR does not re-add them.

## For everyone

Every protocol step and Safety bound is listed in `docs/medical-review.md` for a qualified clinician to sign. If nobody signs, the write-up says "Medical content not clinically reviewed."
