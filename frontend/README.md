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
npm run dev          # http://localhost:5173 with the bundled Mars day-3 replay
npm run build        # production build in dist/ (static files, works offline)
npm run preview      # serve the build
```

Load another replay file served by the app (for example one placed in `public/replay/`):
`http://localhost:5173/?replay=/replay/<file>.json`. Files from other addresses are refused.

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
  contracts.ts        shapes consumed from Spec 1 (ASSUMED fields marked until frozen)
  indicators.ts       Indicator labels, physical/mental, and where each glows on the body
  replay/             fold a replay up to a Mission-clock time; load and check replay files
  body/               3D body: view model, Three.js renderer, layers, zoom, insight, glow
  charts/             trend chart, sparkline, scrubber
  home/               mission bar, summaries, tasks, Emergency/Help, measurement card
  fixtures/           hand-made Mars replay used until Spec 1's replay lands
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

When the replay's Crew record has `sex: "female"`, the app loads `body-female.glb`: female
organs from the Human Reference Atlas, with muscles, skeleton and vessels resized from the
male model and labelled approximate on screen.

## Anatomy is approximate

The body comes from Z-Anatomy. Where the model has no mesh for a structure in the spec's
map, the nearest containing structure glows instead: prefrontal cortex → frontal lobe,
suprachiasmatic nucleus → hypothalamus, optic disc → optic nerve and retina,
visual cortex → occipital lobe; there is no fat mesh, so glucose lights liver and thigh
muscle only. See `tools/anatomy/README.md`.
