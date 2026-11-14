# Spec 5 · Integration, Content, Video and Submission

> **Role:** Integration lead (Team Owner) · Anyone can pick this spec up. This spec owns the **content** (protocols, cards, profiles) and the **submission**. If it slips, nothing ships.
> Parent plan: [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) · Vocabulary: `GLOSSARY.md` (Mission profile, Protocol, Indicator, Ground report, Credits)
> Deadline: **Sun 15 Nov 2026, 11:59 PM Melbourne.** Plan clock: H0 = build start, H24 = feature freeze, **aim to submit by H28**.
> Triage: `ready-for-agent` (local file, no issue tracker).

## How to start (first 30 minutes)

1. Create the repo skeleton, add an MIT licence, and start `docs/si-log.md` (who used which AI tool, for what). Log from now on.
2. Ask the **Local Lead** for the Submission and Judging guides (they were not found publicly). Confirm submission format and video length.
3. Open the Hinkelbein 2020 CPR guideline and start extracting the protocol steps with exact citations.

## Problem Statement

Four people can build brilliant parts that never join up, and a project that is not submitted does not exist. Judges may only see the video. The protocol and card content must be accurate and cited, because the app must never invent medical steps. The event also requires a written statement of how AI tools were used.

## Solution

This spec delivers:

1. **Content** that the other specs render: cited protocol steps, measurement cards (How / Why / If abnormal), Mission profile values, and the NASA HRP risk map.
2. **Integration**: lead integration #1 (H10–14) and keep the contracts honest.
3. **The submission package**: demo video (plus a backup recording from day 1), public repo, short write-up, SI-use statement, Credits page, contact information.

## Seam

Content is tested by the **content linter** (every step and threshold has a source; no drug name or dose). Integration is tested at the shared seam: a ReplayFile goes in and the expected screens come out.

## Contracts (shapes, frozen at H2)

You produce content that fits these shapes.

| Contract | Fields |
|---|---|
| `Protocol` | id, title, steps[{id, text, source{guideline, section}, equipment[], rescuers}] |
| `GroundReport` | id, crew, summary, history[], timeline[], actions[], sent_t, reply_t?, reply? |

Content you also author (shapes agreed with Specs 2 and 4):

| Content | Fields |
|---|---|
| Measurement card | indicator, how[], why{text, hrp_risk, source}, if_abnormal{now, remeasure, tell_crew, tell_ground}, unit, space_note |
| Mission profile | id, gravity, radiation_rate, comm_delay, evacuation, medical_kit[], exercise_kit, crew_size, duration, dust, closed_habitat, source labels (each value marked sourced or "not confirmed: team value") |
| Safety bound | indicator, low, high, label ("Earth reference, no space data" or a space/personal source), source |

## User Stories

1. As a rescuer, I want every emergency step to be taken from a published guideline, so that I can trust it under stress.
2. As a judge, I want every step to show its citation, so that I can verify it.
3. As a rescuer, I want no step to name a drug or dose, so that medication stays with the flight surgeon.
4. As an astronaut, I want a card for each measurement that says how to take it, why it matters in space, and what to do if it is abnormal, so that I do not need to be a doctor.
5. As a judge, I want each card's "Why" to name the NASA HRP risk it guards against, so that the tool answers the challenge's questions in NASA's own terms.
6. As an astronaut, I want Mission profile values that match the environment (spacecraft transit, station, Moon base, Mars base, rover), so that guidance fits where I am.
7. As the team, I want every unconfirmed value labelled "not confirmed: team value", so that we never present a guess as fact.
8. As a judge, I want to see which of NASA's 17 HRP risks are covered and which are not, so that the claim is honest.
9. As the team, I want one clean integration pass at H10–14, so that cross-stream bugs surface early.
10. As the team, I want a backup screen recording by the end of day 1, so that a late failure cannot erase the demo.
11. As a judge, I want a 3-minute video that tells one clear story, so that I understand the product without running it.
12. As a judge, I want an accuracy page and a Credits page in the app and the write-up, so that the work is honest and properly attributed.
13. As the event, I want a statement of how AI tools were used, so that the rules are met.
14. As the team, I want a feature freeze at H24, so that the last hours go to fixing, rehearsing and recording.
15. As the team, I want a submission checklist and one named owner, so that nothing is missed at 11:59 PM.
16. As a judge, I want the limitations written openly, so that I trust the claims.
17. As the team, I want the optional hosted replay on GitHub Pages if we are ahead, so that judges can click through with no install. (P1)

## Implementation Decisions

### Tasks and hours (plan clock)

| ID | Task | Hours |
|---|---|---|
| 5.1 | Repo skeleton, MIT licence, `docs/si-log.md`, issue the Submission Guide request to the Local Lead | H0–2 |
| 5.2 | Post the three Space Apps Connect questions (daily attention-test data; recommended in-flight thresholds; whether a laptop demo is acceptable) | H0–2 |
| 5.3 | Protocol content from the microgravity CPR guideline, every step cited; non-drug chest-pain phase | H2–10 |
| 5.4 | Measurement cards for a few Indicators (heart rate, blood pressure, sleep, glucose, temperature, mood), each Why naming its HRP risk | H4–12 |
| 5.5 | Mission profile content (Mars transit first; others P1) with every value sourced or labelled "team value" | H4–10 |
| 5.6 | Safety bounds content with sources or the "Earth reference, no space data" label | H6–10 |
| 5.7 | HRP risk map (which of the 17 risks each Indicator covers; list the uncovered ones) | H8–12 |
| 5.8 | **Integration #1**: full emergency flow on real replay, both triggers; first golden tests | H10–14 |
| 5.9 | **Backup screen recording** at the end of day 1 | H13–14 |
| 5.10 | Credits page content (every dataset, model and asset with its source and licence) | H14–18 |
| 5.11 | Write-up draft including the limitations (below) | H14–20 |
| 5.12 | **P1** Hosted replay on GitHub Pages (with the data lead) | H18–24 |
| 5.13 | **Feature freeze at H24**; bug triage | H24 |
| 5.14 | Rehearse the video script twice; record the video | H24–28 |
| 5.15 | SI-use statement from the log; fill in Team Contact Information; submit | H26–28 |

### Protocol content rules

- Source for the CPR sequence: Hinkelbein et al. 2020, https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/ . Outline: no response → start compressions (Evetts-Russomano method) → restrain on the Crew Medical Restraint System → handstand method → Rescuer 2: AED → airway only with two or more rescuers.
- Chest-pain phase is **non-drug only**: stop activity, restrain, attach ECG/AED pads, prepare AED, start the ground report. Medication steps read "per flight surgeon / onboard medical checklist".
- Every step stores its source (guideline, section). **Do not paraphrase beyond what the source says.** If you cannot cite it, do not include it.
- Partial-gravity CPR (Moon, Mars) is **not** covered by published guidance. Say so; do not guess.

### Mission profile starting values (Mars transit; label anything unconfirmed)

| Parameter | Value | Status |
|---|---|---|
| Gravity | Weightless in transit; Mars base = three-eighths of Earth | NASA HRP |
| Radiation (inside spacecraft) | about 1.8 mSv/day | Sourced (JPL / SwRI) |
| Communication delay | 28.5 min one way (57 min round trip); NASA says up to 20 min | Team value, conservative |
| Evacuation | Effectively none mid-transit | Sourced |
| Medical kit | Not confirmed for a Mars vehicle | "not confirmed: team value" |
| Exercise kit | Not confirmed for a Mars vehicle (Orion flywheel about 30 min/day as reference) | "not confirmed: team value" |
| Crew size | 4 (Artemis II reference) | Reference |
| Duration | about 3 years total mission | Sourced |

Sources: https://www.nasa.gov/hrp/hazards/ · https://www.nasa.gov/hrp/hazard-distance-from-earth/ · https://www.jpl.nasa.gov/news/data-from-nasa-rovers-voyage-to-mars-aids-planning/ · https://www.nasa.gov/humans-in-space/life-encapsulated-inside-nasas-orion-for-artemis-ii-moon-mission/

### Video script (about 3 minutes; length per the Submission Guide)

| Time | Scene | What the viewer sees |
|---|---|---|
| 0:00 | Hook | Mars transit, delay 28.5 min, home screen, living 3D body |
| 0:20 | Morning check | Webcam heart rate (if built), Drift alert on the charts, briefing text |
| 0:50 | Collapse | Auto-detect fires, urgency ACT NOW, crew alarm, a crewmate takes over |
| 1:20 | Guidance | Likely contributors, one cited step per screen, "Why this step?" answered |
| 2:00 | Ground | Report with 57 min round trip; reply arrives on the console and becomes a Label |
| 2:30 | Close | Accuracy page, Credits page, one line: "same engine, a remote clinic on Earth" |

Rehearsal failure table: service down → run from replay files; explainer slow → recorded answer; webcam fails → recorded clip; total failure → play the backup recording.

### Limitations to state in the write-up

- No hardware; all live data is simulated or replayed.
- No open astronaut wearable stream exists; normal days come from Earth wearable data (PMData).
- The collapse is a Pulse approximation with no ischemia model and a template ECG, labelled "estimate, not validated". Chest pain is crew-reported.
- Accuracy is measured on datasets, not real astronauts.
- Published space guidance exists only for CPR; partial-gravity CPR is not covered.
- In-flight vital-sign shifts have no real source and are labelled "team value".
- The Mars delay default exceeds NASA's stated 20 min maximum, by team choice.
- Female muscle, skeleton and vessel layers are approximate.
- The demo runs on a laptop browser with one local service standing in for the habitat network.

## Sources and licences to list on the Credits page

| Item | Link | Licence |
|---|---|---|
| PMData | https://datasets.simula.no/pmdata/ | CC BY 4.0 |
| Pulse Physiology Engine | https://pulse.kitware.com/ | Apache 2.0 |
| OSDR Environmental Data App (ISS cabin, radiation) | https://visualization.osdr.nasa.gov/eda/ | Open; cite as visualization |
| OSDR Inspiration4 (blood values) | https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/ | Processed data public |
| Apollo AP005 (return-to-gravity group means) | https://nlsp.nasa.gov/search/data/details/e1fa5c55-ddfe-5548-91ba-864080319f44?dataType=EXPERIMENTS | Open summarized tables |
| CGMacros (separate file) | https://registry.opendata.aws/cgmacros/ | CC BY-NC-SA 4.0 |
| UBFC-rPPG (accuracy only) | https://sites.google.com/view/ybenezeth/ubfcrppg | Research use only |
| Z-Anatomy | https://github.com/Z-Anatomy/Models-of-human-anatomy | CC BY-SA 4.0 |
| Human Reference Atlas models | https://humanatlas.io/3d-reference-library | CC BY 4.0 |
| Our code | the repo | MIT |
| Our derived 3D files | the repo | CC BY-SA 4.0 |

Other challenge sources to cite: NASA HRP hazards https://www.nasa.gov/hrp/hazards/ · risks https://www.nasa.gov/hrp/risks/ · ARCHeR https://www.nasa.gov/reference/archer/ · CSA radiation monitoring https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp · NASA-STD-3001 https://www.nasa.gov/reference/3-0-health-and-medical-care/ · NASA Standard Measures https://www.nasa.gov/reference/standard-measures/

## Spike go/no-go

This spec has no technical spike. The decision points are:

| Decision | Rule |
|---|---|
| Protocol step cannot be cited | Drop the step. Do not include an uncited step |
| Submission Guide still missing at H12 | Use the Challenge page and FAQ; submit video, repo and write-up; ask the Local Lead again |
| Integration #1 fails at H14 | Stop all P1 work; fix the P0 path first |
| Behind at H24 | Freeze anyway; ship the P0 path; cut P1 to pitch |

## Dependencies

- **Needs from Spec 1:** contracts and the data manifest; replays for the video.
- **Needs from Spec 2:** a card layout and the home screen to record.
- **Needs from Spec 3:** accuracy numbers.
- **Needs from Spec 4:** the working emergency flow.
- **Gives to Spec 2:** card content and Mission profile values.
- **Gives to Spec 4:** cited protocol content and equipment lists.
- **Gives to Spec 3:** Safety bounds and the "team value" labels.

## Testing Decisions

- A good content test checks **observable rules**, not wording taste.
- Tests: (a) the linter fails on any protocol step or threshold with no source; (b) the linter fails on any drug name or dose in protocol content; (c) every card's Why names an HRP risk or is flagged as uncovered; (d) every Mission profile value is sourced or labelled "not confirmed: team value"; (e) the Credits page lists every dataset, model and asset in the data manifest.
- Integration check at H10–14: the full emergency flow runs end to end from a replay file, with both triggers, offline.
- Prior art: none (no code yet).

## Acceptance Criteria

- [ ] Every protocol step cited; no drug name or dose; linter green.
- [ ] Cards for the chosen Indicators with HRP risk named.
- [ ] Mars transit profile complete, unconfirmed values labelled.
- [ ] HRP risk map published, uncovered risks listed.
- [ ] Integration #1 done by H14; backup recording made.
- [ ] Credits page complete; SI-use log kept; SI statement written.
- [ ] Demo video recorded; repo public (code MIT, 3D assets CC BY-SA 4.0); write-up on the Project tab.
- [ ] **Submitted by Sun 15 Nov 2026, 11:59 PM Melbourne.**

## Submission checklist

- [ ] Ask the Local Lead for the Submission and Judging guides; confirm format and video length
- [ ] Post the three Space Apps Connect questions
- [ ] Keep the SI-use log from now (who, which tool, what for)
- [ ] Demo video, plus a backup recording from end of day 1
- [ ] Public repo: code MIT, derived 3D assets CC BY-SA 4.0
- [ ] Short write-up on the Project tab, including the limitations above
- [ ] SI-use statement written from the log (mandatory)
- [ ] Credits page: every dataset, model and asset with its source and licence
- [ ] Fill in Team Contact Information
- [ ] **Submit by Sun 15 Nov 2026, 11:59 PM Melbourne time**

## Out of Scope

- Building screens, detection or the service (Specs 1–4).
- Partial-gravity CPR; any claim of diagnosis; any drug or dose.

## Further Notes

- Plan two sleep shifts across the 30 hours. The integration lead owns the clock and calls the freeze at H24.
- Submit early (H28) rather than at 11:59 PM; the page may be slow.
