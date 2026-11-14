# Spec 1 · Data, Replay, Mission Clock, Contracts and Service

> **Role:** Data lead · **Stream 4** · Anyone can pick this spec up. **Start first (H0): everyone else waits on the contracts.**
> Parent plan: [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) · Vocabulary: `GLOSSARY.md` (Crew record, Mission profile, Indicator, Reading, Anchor, Status, Alert, Quarantine, Event, Label, Mission clock, Protocol, Ground report)
> Deadline: Sun 15 Nov 2026, 11:59 PM Melbourne. Plan clock: H0 = build start, H24 = feature freeze, aim to submit by H28.
> Triage: `ready-for-agent` (local file, no issue tracker).

## How to start (first 30 minutes)

1. Read this spec and the contracts table below.
2. Draft the seven JSON Schemas and post them to the team for a quick check.
3. In parallel, run **Spike A** (Pulse produces arrest plus CPR output).
4. Freeze the contracts by **H2** and tell the team.

## Problem Statement

Four other streams build screens, detection, emergency flow and the submission at the same time. If each invents its own data format, integration fails at H10. There is also **no open astronaut wearable stream** (checked: NASA OSDR Inspiration4 holds only blood, microbiome, skin, stool, urine and T-cell data; Skylab and astronaut sleep sets are restricted). The team needs believable crew histories, one shared clock and one emergency episode to build against, all made from free data.

## Solution

Deliver four things in this order:

1. **Frozen contracts** (H2): seven small JSON Schemas. They are the only thing that crosses a stream boundary.
2. **Mission clock**: one simulated time that every component reads.
3. **Replay files**: pre-generated crew histories, one Pulse emergency episode, and ISS cabin and radiation data, all in the ReplayFile contract.
4. **Local service ("habitat network")**: plays replay files on the Mission clock, stores everything in SQLite, and pushes events to three browser windows (patient tablet, rescuer tablet, ground console).

The web app can run from replay files alone. The service adds the live layer. If Pulse or the service breaks, the demo still plays from files.

## Seam (the one test seam, shared by all five specs)

**A ReplayFile goes in; the sequence of Readings, Alerts, Status values and Ground reports that comes out is asserted.** This spec owns that seam.

## Contracts (shapes; frozen at H2)

| Contract | Fields |
|---|---|
| `Reading` | crew, indicator, value, unit, t (Mission clock seconds), source (sensor / camera / mic / manual / lab / sim), confidence (0–1), state (released / quarantined / event) |
| `Alert` | id, kind (acute / drift / emergency), crew, indicator, deviation, status (green / amber / red), urgency (ACT_NOW / ESCALATE_TO_GROUND / MONITOR / ROUTINE), likely_causes[{indicator, direction, note}], t |
| `CrewRecord` | id, sex, anchor{indicator: {mean, sd}}, missionProfile |
| `ReplayFile` | crew, profile, events[{t, type, payload}] ordered by t |
| `Protocol` | id, title, steps[{id, text, source{guideline, section}, equipment[], rescuers}] |
| `GroundReport` | id, crew, summary, history[], timeline[], actions[], sent_t, reply_t?, reply? |
| `Trigger` | kind (auto / manual), crew, t, reason, confirmed? |

Rules: add a field only by agreement in the team chat; never remove one. Include a `schema_version` field.

## User Stories

1. As the 3D / UI lead, I want the Reading and Alert shapes frozen at H2, so that I can build the status glow without waiting for detection code.
2. As the AI / detection lead, I want 4 synthetic crew with months of normal days, so that I can build and test the baseline on realistic data.
3. As the AI / detection lead, I want one crew member to have a planted slow drift, so that I can prove a Drift alert fires before the emergency.
4. As the AI / detection lead, I want each Crew record to carry an Anchor (pre-flight mean and spread per Indicator), so that Drift alerts have a fixed reference.
5. As the emergency-flow lead, I want a Pulse emergency episode (deterioration, arrhythmia, arrest, CPR) as a replay, so that the auto-detect rule has something to catch.
6. As the emergency-flow lead, I want the emergency labelled "estimate, not validated", so that we never overclaim.
7. As the emergency-flow lead, I want to post a manual Trigger to the service, so that the Emergency button works with no sensors.
8. As the emergency-flow lead, I want events pushed to a patient window, a rescuer window and a ground console window, so that takeover and the delayed reply can be demoed.
9. As the integration lead, I want a data manifest listing every dataset, link and licence, so that the Credits page is complete.
10. As the presenter, I want 1×, 60× and "skip to next event", so that a 24-hour quarantine, a 28-day window and a 57-minute ground reply fit a 3-minute video.
11. As any developer, I want every component to read the same Mission clock and never the wall clock, so that replays are reproducible.
12. As any developer, I want replays reproducible from a seed, so that golden tests do not flake.
13. As the 3D / UI lead, I want ISS cabin temperature, CO₂ and humidity in a replay, so that the CO₂ banner shows real values.
14. As the 3D / UI lead, I want ISS radiation dose in a replay, so that the mission bar shows a real figure.
15. As the integration lead, I want a few real Inspiration4 blood values as lab Readings, so that lab-entry cards show real astronaut data.
16. As the AI / detection lead, I want a simulated glucose stream kept in its own file, so that the share-alike licence does not spread to the rest.
17. As a crewmate, I want every Crew record on every tablet, so that another tablet can open the patient's record in an emergency.
18. As the integration lead, I want every emergency opening of another Crew record logged, so that privacy is shown honestly.
19. As the team, I want schema validation on every replay file and event, so that bad data fails loudly at the boundary.
20. As the integration lead, I want replay files exportable as static JSON, so that the optional hosted replay needs no server.
21. As the emergency-flow lead, I want ground replies stored as Labels, so that they flow back to the baseline.
22. As the team, I want the service restartable mid-demo without losing state, so that a crash costs seconds, not the video.

## Implementation Decisions

### Tasks and hours (plan clock)

| ID | Task | Hours |
|---|---|---|
| 1.1 | Seven JSON Schemas plus one shared validator used by every stream | H0–2 |
| 1.2 | **Spike A**: run Pulse; confirm arrest plus CPR output and CSV export | H0–2 |
| 1.3 | Mission clock: one time source; 1×, 60×, skip to next event; labelled "demo time" | H2–4 |
| 1.4 | Replay generator: 4 synthetic crew from PMData normal days, about 5 months each, one planted drift, Anchor from the first weeks | H2–8 |
| 1.5 | Emergency replay from Pulse: stepwise stroke-volume drop, sinus tachycardia, unstable VT, VF, arrest, CPR. Chest pain is crew-reported, not simulated | H2–6 |
| 1.6 | Cabin and dose replay from the OSDR Environmental Data App | H6–8 |
| 1.7 | A few Inspiration4 blood values as `source = lab` Readings | H6–8 |
| 1.8 | Service: plays replays on the clock; accepts manual Readings, Triggers, Labels, ground replies; pushes events to three windows; holds all Crew records | H4–10 |
| 1.9 | SQLite store: Reading, Alert, Label, Event store, Ground report, Access log; indexed by crew, indicator, time | H4–10 |
| 1.10 | Integration support: fix cross-stream format issues with the integration lead | H10–14 |
| 1.11 | **P1** glucose stream (separate file) | H18–20 |
| 1.12 | **P1** static JSON export for the hosted replay | H22–24 |
| 1.13 | Bug fixing; hold the seam steady after freeze | H24–28 |

### Crew design for the replay generator

- 4 synthetic crew mapped from the 16 PMData people. Record `sex` per crew (organ models differ).
- **Crew A:** a planted slow drift (for example resting heart rate up about 6 bpm and sleep down about 1.5 h over 9 days) that a Drift alert must catch before the emergency.
- **Crew B:** the person who collapses in the emergency replay.
- Two more crew with ordinary histories, so the crew alarm has other tablets to ring.
- Lead Mission profile is **Mars transit**. Other profiles are P1 and only change profile parameters.

### Service decisions

- The service plays the "habitat network". Real tablet-to-tablet sync is pitch only.
- Keep every Reading for the whole replay, numbers only (never raw camera or audio).
- Push events to windows ordered by Mission-clock time.
- The stream's auto Trigger and the manual button produce the same `Trigger` event; downstream differs only by `kind`.

## Datasets (links and licences)

| Need | Dataset | Link | Licence |
|---|---|---|---|
| Normal days | PMData (16 people × 5 months, Fitbit) | https://datasets.simula.no/pmdata/ | CC BY 4.0 |
| Emergency episode | Pulse Physiology Engine | https://pulse.kitware.com/ | Apache 2.0 |
| Cabin air and ISS radiation | OSDR Environmental Data App | https://visualization.osdr.nasa.gov/eda/ | Open download; cite as visualization |
| Lab values | OSDR Inspiration4 (OSD-569 includes a complete blood count) | https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/ · https://pmc.ncbi.nlm.nih.gov/articles/PMC11094041 | Processed data public |
| Glucose (P1) | CGMacros | https://registry.opendata.aws/cgmacros/ | CC BY-NC-SA 4.0 (keep separate) |
| Optional sleep extras | MMASH · SleepAccel | https://physionet.org/content/mmash/ · https://physionet.org/content/sleep-accel/1.0.0/ | ODbL · open |
| Mars radiation (P1) | MSL RAD, PDS id `MSL-M-RAD-3-RDR-V1.0` | NASA PDS catalogues; not yet opened | Public |

The AI / detection lead downloads and verifies the PMData readiness scale and the Inspiration4 ID-to-panel mapping at H0–2 (Spec 3). Consume their verified files.

## Spike go/no-go (decide by H2)

| Spike | If it fails |
|---|---|
| A: Pulse produces arrest and CPR output | Hand-author the emergency replay from published waveform values; label it "illustrative". Spend at most 1 extra hour |
| Pulse environment action accepts cabin gas and pressure | Skip it; cabin values only drive the banner and mission bar |
| Pulse ECG field name unknown | Detection uses rhythm state, HR and BP only (no waveform) |

## Dependencies

- **Upstream:** none. This spec needs nothing from the others to start.
- **Downstream:** all four other specs consume the contracts (H2) and replay files (first versions by H8).
- **Hand-offs in:** verified dataset notes from Spec 3 (H2); repo skeleton from Spec 5 (H2).

## Testing Decisions

- A good test replays a file and asserts **what comes out**, not how the generator is written.
- Tests: (a) every replay validates against its schema; (b) a replay generated twice from one seed is identical; (c) the Mission clock never goes backwards and honours speed changes; (d) the service delivers events in time order to all three windows; (e) a manual Trigger and an auto Trigger differ only in `kind`; (f) restarting mid-replay resumes from stored state.
- Prior art: none (no code yet). The golden-replay pattern comes from the plan.

## Acceptance Criteria

- [ ] Seven contracts frozen and published by H2.
- [ ] Four crew replays exist, with a planted drift on crew A.
- [ ] Emergency replay exists for crew B (Pulse, or hand-authored and labelled).
- [ ] Mission clock supports 1×, 60× and skip to next event.
- [ ] Service pushes events to three windows and survives a restart.
- [ ] Data manifest lists every dataset, link and licence.
- [ ] Replays export as static JSON.

## Out of Scope

- Detection logic, status colours, screens, protocols, explainer (other specs).
- Real tablet sync, real wearables, a trained ECG classifier.
- Real astronaut wearable data. None is open; a real stream is a post-hackathon NASA request (https://lsda.jsc.nasa.gov/explore/lsdahome/datarequest).

## Further Notes

- State the limitation openly: the stream is Earth wearable data shaped to look like a crew, and the collapse is a Pulse approximation with no ischemia model.
- If H4 arrives and contracts are still moving, stop adding features and finish the seam.
