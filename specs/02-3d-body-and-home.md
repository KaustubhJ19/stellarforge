# Spec 2 · 3D Body, Home Screen and Charts

> **Role:** 3D / UI lead · **Stream 1** · Anyone can pick this spec up.
> Parent plan: [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) · Vocabulary: `GLOSSARY.md` (Crew record, Indicator, Reading, Status, Alert, Mission clock)
> Deadline: Sun 15 Nov 2026, 11:59 PM Melbourne. Plan clock: H0 = build start, H24 = feature freeze.
> Triage: `ready-for-agent` (local file, no issue tracker).

## How to start (first 30 minutes)

1. Read this spec and the contracts table.
2. Run **Spike B**: export a Z-Anatomy model as a compressed GLB and load it in a Three.js page.
3. While waiting for contracts (H2), build the page shell and layer toggles against a hard-coded Reading list.
4. Do not wait for the service. Run from replay files as soon as the data lead posts the first one (about H8).

## Problem Statement

An astronaut needs to see their health at a glance and understand which part of the body a number is about. A list of numbers is not enough, especially for a crewmate who is not a doctor and is under stress. The challenge also asks for clear presentation, colour coding, dynamic charts and an interactive body.

## Solution

A web app with a **layered, see-through 3D body** as the home screen. Body parts glow green, amber or red from each Indicator's Status. The astronaut can zoom body → region → structure. Beside the body: physical and mental summaries, today's tasks, a mission bar, and trend charts with the person's own baseline band and alert markers. A Mission-clock scrubber replays status over time. The heart pulses at the real heart rate.

## Seam

The web app is tested by **loading a ReplayFile and asserting what renders** (Status colours, alert markers, mission bar values), not how components are built.

## Contracts consumed (shapes, frozen at H2)

| Contract | Fields you use |
|---|---|
| `Reading` | crew, indicator, value, unit, t, source, confidence, state |
| `Alert` | id, kind (acute / drift / emergency), crew, indicator, deviation, status, urgency, likely_causes[], t |
| `CrewRecord` | id, sex, anchor, missionProfile |
| `ReplayFile` | crew, profile, events[{t, type, payload}] |

You produce no contracts. You display them.

## User Stories

1. As an astronaut, I want a 3D body whose parts glow green, amber or red, so that I see my health at a glance.
2. As an astronaut, I want status shown by colour **and** an icon or text, so that colour-blind crew are not left out.
3. As an astronaut, I want to fade every layer except the affected structure, so that I can see exactly what a flagged Indicator is about.
4. As an astronaut, I want separate layers (muscles, skeleton, vessels, organs, brain) with adjustable transparency, so that I can look inside.
5. As an astronaut, I want to zoom from whole body to a region to one structure, so that I can see detail without clutter.
6. As an astronaut, I want a heart that pulses at my real heart rate, so that the body feels alive and the data feels real.
7. As an astronaut, I want a trend chart per Indicator with my own baseline band shaded, so that I see what is normal for me.
8. As an astronaut, I want Acute and Drift alert markers on the chart, so that I see when something changed.
9. As an astronaut, I want a Mission-clock scrubber beside the charts, so that I can replay how my status evolved.
10. As an astronaut, I want a mission bar (day, profile, ground delay, radiation dose), so that I always know the mission context.
11. As an astronaut, I want physical and mental summaries side by side but separate, so that I can see each kind of health.
12. As an astronaut, I want today's tasks on the home screen, so that I know what checks are due.
13. As an astronaut, I want a large Emergency button and a "Help a crewmate" button, so that I can act without hunting.
14. As a crewmate under stress, I want large type and large tap targets, so that I can use the app with gloves or shaking hands.
15. As an astronaut, I want mood shown only in the mental view with no body glow, so that the app never invents a body location for a self-report.
16. As the integration lead, I want a card layout for How / Why / If abnormal, so that content can be dropped in without redesign.
17. As an astronaut, I want a sparkline on each measurement card, so that I see the trend at a glance.
18. As the presenter, I want the app to run from replay files with no server, so that the video survives a service crash.
19. As the AI / detection lead, I want a separate outline view for "Why this forecast?", so that explanation is never confused with status colour. (P1)
20. As an astronaut, I want a CO₂ banner when cabin CO₂ is high, so that I can act on the environment. (P1)
21. As an astronaut, I want a female model for organs, so that the body matches my Crew record. (P1)
22. As an astronaut, I want simple forms for the stand test and the post-spacewalk check, so that I can log them. (P1)

## Implementation Decisions

### Tasks and hours (plan clock)

| ID | Task | Hours |
|---|---|---|
| 2.1 | **Spike B**: Z-Anatomy GLB loads fast with mapped structures | H0–2 |
| 2.2 | Page shell, theme tokens, accessibility baseline (colour plus icon/text, large targets) | H2–5 |
| 2.3 | Male body: layers, per-layer transparency, three zoom levels | H2–8 |
| 2.4 | Status glow from Reading state; insight view that fades all but the affected structure | H6–10 |
| 2.5 | Home layout: mission bar, physical and mental summaries, tasks, Emergency and Help buttons | H6–10 |
| 2.6 | Trend chart: value over Mission clock, baseline band, Acute and Drift markers; sparklines for cards | H8–12 |
| 2.7 | Mission-clock scrubber beside the charts | H10–12 |
| 2.8 | Heart pulse at the real heart rate; lungs at respiratory rate if time | H10–12 |
| 2.9 | Integration #1 with the other specs | H10–14 |
| 2.10 | Measurement card layout (How / Why / If abnormal, value, source label, sparkline) | H12–16 |
| 2.11 | P0 polish: empty states, loading, responsiveness, the "decision support, not diagnosis" label | H14–18 |
| 2.12 | **P1** CO₂ banner; "Why this forecast?" outline view; stand test and post-EVA forms; profile switcher UI; check-in streaks; female organs | H18–24 |
| 2.13 | Bug fixing and rehearsal support | H24–28 |

### Indicator-to-structure map (what glows)

| Indicator | Structure | Evidence |
|---|---|---|
| Stress | Prefrontal cortex + amygdala | Arnsten 2009: https://pmc.ncbi.nlm.nih.gov/articles/PMC2907136/ |
| Alertness / attention lapses | Frontal and parietal control regions, visual cortex, thalamus | Chee 2008: https://pmc.ncbi.nlm.nih.gov/articles/PMC6670628/ |
| Sleep / body clock | Suprachiasmatic nucleus | NIH NIGMS: https://www.nigms.nih.gov/education/fact-sheets/Pages/circadian-rhythms.aspx |
| Balance / motion sickness | Cerebellum + vestibular system | Koppelmans 2016: https://pmc.ncbi.nlm.nih.gov/articles/PMC5460234/ |
| Heart rate, ECG, BP | Heart + carotid arteries | NASA Standard Measures |
| Respiration, SpO₂ | Lungs | NASA Standard Measures |
| Glucose, insulin resistance | Liver, skeletal muscle, fat | Hughson 2016 |
| Bone density | Hip and spine | NASA Standard Measures |
| Muscle strength | Thigh muscles | NASA Standard Measures |
| Kidney stones | Kidneys | NASA Standard Measures |
| Eyes (SANS) | Optic disc / optic nerve | Roberts 2017: https://www.nejm.org/doi/full/10.1056/NEJMoa1705129 |
| Radiation dose, temperature | Whole body | NASA HRP |
| **Mood** | **No structure lights up** | Self-reported; shown in the mental view only |

Status glow (green / amber / red) appears only in the default view. SHAP-style explanation (P1) uses an outline or heat-map and is labelled "what drove the model", never a status colour.

### Rendering decisions

- Export **only the structures in the map above**, plus one simplified outline per layer. Load region detail only on zoom. 5,000+ structures are too heavy for a browser.
- Female muscle, skeleton and vessel layers are resized from male and labelled "approximate". Female organs only for P1.
- Skin shell is a later goal, not in scope.
- The default layer transparency in insight view: muscles, skeleton and vessels faint; organs and brain solid when relevant. One calm neutral colour per layer.

## 3D assets (links and licences)

| Use | Model | Link | Licence |
|---|---|---|---|
| Inner layers, both sexes | Z-Anatomy (5,000+ structures) | https://github.com/Z-Anatomy/Models-of-human-anatomy | CC BY-SA 4.0 |
| Brain detail | Human Reference Atlas brain (141 structures) | https://humanatlas.io/3d-reference-library · https://3d.nih.gov/collections/hra | CC BY 4.0 |
| Female organs | HRA "Body, Female" | https://3d.nih.gov/collections/hra | CC BY 4.0 |
| Z-Anatomy source | BodyParts3D | https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html | CC BY 4.0 |

Derived 3D files must be released under CC BY-SA 4.0 (share-alike). Add every model to the Credits page via the integration lead.

## Spike go/no-go (decide by H2)

| Spike | If it fails |
|---|---|
| B: Z-Anatomy GLB loads fast with mapped structures | Use a simplified body outline plus highlighted organ meshes only. Do not spend more than 1 extra hour |
| Layers do not align (male/female) | Ship male only; female is P1 |
| Frame rate poor on a laptop | Drop to one zoom level plus flat region panel |

## Dependencies

- **Needs from Spec 1:** contracts (H2) and the first replay file (about H8). Until then, use a hard-coded list that matches the contract.
- **Needs from Spec 3:** Status and Alert values (use contract fields; do not recompute Status).
- **Needs from Spec 5:** measurement card content (How / Why / If abnormal) and Mission profile values.
- **Gives to Spec 4:** the Emergency and Help buttons, which open the emergency flow.

## Testing Decisions

- A good test loads a ReplayFile and asserts what is **visible**, not component internals.
- Tests: (a) a red Status colours the matching structure and also shows an icon or text; (b) the baseline band and an Acute and a Drift marker appear on the chart at the right times; (c) the scrubber changes the displayed Status to the value at that time; (d) mood never glows a structure; (e) the mission bar shows the Mars delay (28.5 min) and the dose from the replay; (f) the app renders from replay files with the service stopped.
- Add an accessibility check: contrast, tap target size, status never by colour alone.
- Prior art: none (no code yet).

## Acceptance Criteria

- [ ] Male body loads with layers, transparency and three zoom levels (or the documented fallback).
- [ ] Status glow and insight view work from replayed Readings.
- [ ] Home layout shows mission bar, physical and mental summaries, tasks, Emergency and Help buttons.
- [ ] Trend charts show the baseline band and alert markers; scrubber works.
- [ ] Heart pulses at the real heart rate.
- [ ] Card layout renders How / Why / If abnormal from content.
- [ ] Runs from replay files with no server.
- [ ] "Decision support, not diagnosis" label is visible.

## Out of Scope

- Computing Status, baseline or alerts (Spec 3). Emergency screens (Spec 4). Protocol and card content (Spec 5).
- Skin layer, full body fit inside skin, camera and microphone UI beyond the webcam heart-rate preview.

## Further Notes

- Visual style (colours, typography) is open; decide quickly and keep to the tokens in 2.2.
- Say honestly in the pitch: the demo "tablet" is a browser on a laptop.
