# StellarForge web app (Spec 2: 3D body, home screen, charts)

The astronaut-facing web app: a see-through 3D body that glows from each Indicator's
Status, physical and mental summaries, trend charts and a Mission-clock scrubber.
It runs entirely from replay files; no backend service is needed.

## Setup

Needs **Node.js 20 or newer** (built with Node 26 LTS).

```
cd frontend
npm install
npx playwright install chromium   # only for the browser tests and the audit
```

## Run

```
npm run dev          # http://localhost:5173 with the bundled Mars day-3 replay (male crew)
npm run dev:female   # same day for a female crew member, with the cabin replay: opens the female body
npm run dev:real     # the data lead's real replay: crew A (152 days) with the ISS RR-1 cabin
npm run dev:recorded # the same crew A after Spec 3's detection: real Alerts and forecasts
npm run build        # production build in dist/ (static files, works offline)
npm run preview      # serve the build
```

Load another replay file served by the app (for example one placed in `public/replay/`):
`http://localhost:5173/?replay=/replay/<file>.json`. Its Crew record is read from the
`crew-records.json` in the same folder, which is how Spec 1's generators write them
(`replay/generated/crew-A.json` beside `crew-records.json`). Add the habitat's cabin replay
(CO₂, temperature, humidity, dose) with `&cabin=/replay/<file>.json`; its events are merged in by
time. Files from other addresses are refused.

## Real replays (Spec 1)

`replay/` at the repo root holds the data lead's shared replays (copied from
`workstream-1-data-service`): `crew-A..D.json` with `crew-records.json`, `iss-cabin-dose-RR-1.json`
(cabin, use with `&cabin=`), `emergency-crew-B.json` (Pulse, starts day 152). `npm run dev`, `build`
and the browser tests copy them to `public/replay/shared/` (git-ignored), e.g.
`/?replay=/replay/shared/crew-A.json&cabin=/replay/shared/iss-cabin-dose-RR-1.json`.

What the real data needed: rounding long decimals, text values (`cardiac_rhythm`) shown in
words and kept out of charts, `degC` read as °C, `soreness` on the thigh muscles, day ticks on
long charts, and cabin data that stops early (RR-1 covers 42 days): the CO₂ banner shows only for
a Reading from the last hour and the dose says "as of …" when older than 36 h. All four real crew
are male, so the female body shows only with the sample.

`replay/recorded/` holds the same replays after Spec 3's recording script
(`tools/record_replays.py`) ran detection over them: they add Alerts, `reading_state` events and
forecasts, so Status colours, the readiness forecast and "Why this forecast?" show real output. Their
Crew records are read from `crew-records.json` one folder up. An emergency Alert (no Indicator) is
left to Spec 4's flow; its Safety-bound Alerts colour the Indicators they name.

## Data contracts

The app reads Spec 1's frozen shapes: the JSON Schemas in `contracts/` at the repo root.
`npm test` checks every sample replay and Crew record against them. What the app adds on top:

- **Status comes only from Alerts.** A Reading's `state` is a data state, not a Status. An
  Indicator shows the Status of its newest Alert at the scrubbed time; with no Alert it is
  Normal. Spec 3 sends one green Alert when a kind (drift, acute, Safety bound) returns to
  green; it ends only that kind, so an Indicator shows the worst of its open kinds. Status
  words are Spec 3's: Normal / Watch / Alert.
- **Quarantined Readings are shown.** Spec 3 holds Readings out of the baseline while an Alert
  is open; they are the abnormal values. `Alert.deviation` is Spec 3's object
  (`{sigma, cusum, combined}` or `{value, bound}`).
- **"Your normal" band** on a trend is the Crew record's anchor mean ± 2 SD, drawn only inside the
  scale's possible range (a 1-5 score stops at 1 and 5; SpO₂ stops at 100%); agreed with Spec 3.
  KNOWN GAP: it does not include Spec 3's expected space shift (body temperature +1 °C, building
  up over 75 days), so a healthy in-flight temperature can sit above the band while Normal.
  Revisit when body temperature data exists.
- **Mission profile** name and Earth delay come from Spec 5's `content/profiles/<id>.json`
  (`name`, `comm_delay`), with the delay's direction and "team value" label shown; an
  unknown profile shows its id and "Not known". A **Mission profile** dropdown in the mission
  bar lists every profile in `content/profiles/` (Mars transit, Space station (ISS)) and
  starts on the replay's own; switching it changes the name and ground delay shown. The
  mission bar comes after `main` in the page so Emergency stays first in the tab order; CSS
  shows it at the top.
- **Measurement cards** come from Spec 5's structured `content/cards/*.json` (How as steps,
  Why with the NASA HRP risk and space note, If abnormal in four parts). A card also covers
  its `related_indicators`. Fields in another shape read "Not added yet."
- **Habitat Readings** (`radiation_dose_*`, `cabin_*`) stay out of the health summaries; the
  mission bar shows `radiation_dose_accumulated`.
- **Readiness forecast** (`forecast` events, Spec 3's recorded output, checked against Spec 1's
  provisional `contracts/provisional/forecast.schema.json`) shows tomorrow's readiness with its
  range and label. "Why this forecast?" draws what drove the general model as a violet
  heat-map on the body (`--explain`, never a Status colour) with the drivers in words; it says
  the personal adjustment comes on top.
- **Stand test** compares with the astronaut's own pre-flight test, then the Apollo AP005
  after-landing group shift, read from Spec 3's `content/profiles/detection-cut-offs.json`
  (`return_to_gravity_shift`) with its label and source.
- **CO₂ banner** shows while the cabin's trailing 1-hour CO₂ average (`cabin_pco2_1h`, mmHg,
  from the cabin replay) is over the Mission profile's `co2_limit.value` (Spec 5: 3 mmHg,
  NASA-STD-3001 Vol 2 [V2 6004]). Both are mmHg, so the app converts nothing. The limit comes
  from the profile chosen in the mission bar, with its averaging window and source, or its
  status when not sourced. A profile with no `co2_limit` shows no banner.
- **Tasks** (`task` events) are app-side; no contract carries them yet. `trigger` and
  `crew_report` events are ignored here (Spec 4).

Rebuild the samples with `npm run fixtures`; check them with the data team's validator too:
`python contracts/validate.py ReplayFile frontend/public/replay/mars-day3.json`.

## Test

| Command | What it checks |
|---|---|
| `npm test` | Unit and integration tests (Vitest + jsdom): load a replay, check what renders |
| `npm run typecheck` | TypeScript |
| `npm run test:e2e` | Browser tests (Playwright) against the production build, offline: pixels on the 3D body, zoom, insight, scrubber, keyboard, high-contrast, reduced motion, a 270k-event replay, a 4x-slowed CPU |
| `npm run audit:a11y -- http://localhost:5173/` | axe-core WCAG 2.2 AA, tap targets of at least 44 px, no sideways scroll, at 1440 / 1024 / 390 px (needs `npm run dev` running) |

Tests use one seam: a replay file goes in, and what the crew would see is checked.
jsdom has no WebGL, so unit tests swap the Three.js renderer for a recorder
(`src/test/fakeBodyScene.ts`); the browser tests cover the real renderer.

## Layout

```
src/
  App.tsx             home screen: wires replay state, body, summaries, charts
  contracts.ts        Spec 1 shapes (mirror the JSON Schemas in ../contracts/)
  profiles.ts         mission profile names and Earth delay by id (until Spec 5)
  indicators.ts       Indicator labels, physical/mental, and where each glows on the body
  replay/             fold a replay up to a Mission-clock time; load and check replay files
  body/               3D body: view model, Three.js renderer, layers, zoom, insight, glow
  charts/             trend chart, sparkline, scrubber
  home/               mission bar, summaries, tasks, Emergency/Help, measurement card
  fixtures/           hand-made Mars replay and Crew records in Spec 1's shapes
e2e/                  Playwright browser tests
public/models/        male and female body GLBs built by tools/anatomy/export_body.py (CC BY-SA 4.0)
public/draco/         vendored Draco decoder so models load offline (Google, Apache 2.0, see its LICENSE)
```

## Hooks for other specs

- **Spec 4 (emergency flow):** pass `onEmergency` to `<App>`; it receives `"emergency"` or
  `"help-crewmate"`. Until then a placeholder alert shows. The post-EVA check also calls it
  with `"emergency"` when the crew answers Yes to any warning sign: NASA's Type II
  decompression sickness signs (numbness, weakness, confusion, dizziness or ear problems,
  chest pain or trouble breathing; OCHMO-TB-037 Rev D, p. 3). The Readings are saved first.
  The question wording awaits the medical reviewer.
- **Readings logged on screen** (stand test, post-EVA check from today's tasks): pass
  `onReadings` to `<App>`; it receives a list of Readings (`source: "manual"`) and the
  optional post-EVA note. Each Reading is complete on its own (with `schema_version`) and
  passes `contracts/reading.schema.json`. The service's `POST /reading` takes one Reading per
  request and refuses a list, so send one POST per Reading. Until that is wired they live only
  on the page and are gone on reload.
- **Spec 5 (content):** pass `cards` to `<App>` (shape `CardContent` in `contracts.ts`);
  missing sections read "Not added yet".

## Female body

When the Crew record has `sex: "female"`, the app loads `body-female.glb`
(try it with `npm run dev:female`, or open `/?replay=/replay/mars-day3-female.json`): female
organs from the Human Reference Atlas, with muscles, skeleton and vessels resized from the
male model and labelled approximate on screen.

## Anatomy is approximate

The body comes from Z-Anatomy. Where the model has no mesh for a structure in the spec's
map, the nearest containing structure glows instead: prefrontal cortex → frontal lobe,
suprachiasmatic nucleus → hypothalamus, optic disc → optic nerve and retina,
visual cortex → occipital lobe; there is no fat mesh, so glucose lights liver and thigh
muscle only. See `tools/anatomy/README.md`.
