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
npm run dev:female   # same day for a female crew member: opens the female body
npm run build        # production build in dist/ (static files, works offline)
npm run preview      # serve the build
```

Load another replay file served by the app (for example one placed in `public/replay/`):
`http://localhost:5173/?replay=/replay/<file>.json`. Its Crew record is read from the
`crew-records.json` in the same folder, which is how Spec 1's generators write them
(`replay/generated/crew-A.json` beside `crew-records.json`). Files from other addresses are refused.

## Data contracts

The app reads Spec 1's frozen shapes: the JSON Schemas in `contracts/` at the repo root.
`npm test` checks every sample replay and Crew record against them. What the app adds on top:

- **Status comes only from Alerts.** A Reading's `state` is a data state, not a Status. An
  Indicator shows the Status of its newest Alert at the scrubbed time; with no Alert it is
  Normal. ASSUMED: Spec 3 clears an Indicator with a green Alert.
- **"Your normal" band** on a trend is the Crew record's anchor mean ± 2 SD.
- **Mission profile** name and Earth delay come from `src/profiles.ts` (team values) until
  Spec 5's profiles exist; an unknown profile shows its id and "Not known".
- **Habitat Readings** (`radiation_dose_*`, `cabin_*`) stay out of the health summaries; the
  mission bar shows `radiation_dose_accumulated`.
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
public/draco/         vendored Draco decoder so models load offline
```

## Hooks for other specs

- **Spec 4 (emergency flow):** pass `onEmergency` to `<App>`; it receives `"emergency"` or
  `"help-crewmate"`. Until then a placeholder alert shows.
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
