# StellarForge: Implementation Plan

> NASA Space Apps Challenge 2026 · *Create Health Monitoring Software for Astronauts on Space Missions* (author: Brazilian Space Agency)
> Team StellarForge (5 members) · Melbourne Local Event
> Status: **approved plan, ready to build.** Supersedes the draft `BUILD-PLAN.md`. Terms follow `GLOSSARY.md`; decision IDs (D-###) refer to `Context1.md`.
> Deadline: **Sun 15 Nov 2026, 11:59 PM Melbourne time.** Plan clock: **H0 = start of build, H30 = deadline. Aim to submit by H28.**

---

## 1. The product in one paragraph

StellarForge is an **offline, 3D-body health tool for non-doctor astronauts**. Daily check-ins build each person's *own* normal. The app flags drift from that normal before it becomes a problem. If a crewmate collapses, the app **auto-detects** it (and a crewmate can also press an **Emergency button**). It then sounds a crew alarm, lets a crewmate take over the patient's record, suggests likely contributors from the history, and walks the rescuers through **one cited step per screen** from published microgravity CPR guidance. An offline language model explains *why* a step exists but never writes or changes a step. A ground report is built automatically and shows the Mars communication delay.

**Decision support, not diagnosis.** Rules and published guidelines decide. Models detect and forecast. The language model only explains.

### Locked decisions for this plan

| # | Decision | Why |
|---|---|---|
| L1 | Emergency trigger = **auto-detect plus manual button** | Auto-detect catches a collapsed person who cannot type; the button works with no sensors |
| L2 | After a trigger, the app reads the **history** and shows 2–3 likely contributors (rule-based, labelled "suggestion, not diagnosis") | Uses the daily check-in history, as the team intended |
| L3 | Normal-day data is **Earth wearable data (PMData)**; the **responses come from space guidelines** | No open astronaut wearable stream exists (verified, see §4.4) |
| L4 | Emergency steps come **only from published guidelines**; chest-pain phase is **non-drug only** | LLMs get resuscitation steps wrong (R-010); the tool never names a drug or dose (D-067) |
| L5 | **Replay-first architecture**: the web app can run from JSON replay files alone | One structural fallback if Pulse, Ollama or the Python service breaks |
| L6 | Free tools, models and datasets only | Students, no budget (D-045) |
| L7 | Video-first; **feature freeze at H24** | Judges may only see the video |

---

## 2. Scope tiers

| Tier | Meaning | Items |
|---|---|---|
| **P0** | Must exist for the video | Replay data + Mission clock + contracts · Home screen (3D male body, status glow, mission bar, living heart, trend charts + scrubber) · Baseline A (Acute + Drift alerts, Quarantine, daily briefing text) · Emergency flow (auto-detect + manual button → urgency verdict → confirm → 15 s crew alarm → rescuer takeover → likely contributors → cited step-per-screen protocol → "Why this step?" → ground report → ground console reply) · Measurement cards for a few indicators · Accuracy page · Credits page · "decision support" labels |
| **P1** | Only after the P0 slice works end to end (about H18) | Webcam heart rate in the morning check · Readiness forecast B + conformal range + SHAP view · ISS cabin replay + CO₂ banner · Stand test (form + Apollo reference) · Post-EVA check (form) · Profile switcher (delay, kit, safety bounds) · Check-in streaks · Female model (organs only) · Hosted replay on GitHub Pages |
| **P2** | Pitch only, not built | Camera respiratory rate and drowsiness, microphone features, voice journal, smart sensing, what-if mode, crew goals, real tablet-to-tablet sync, trained ECG classifier, body-clock coach, partial-gravity CPR |

---

## 3. Architecture (replay-first)

```
 replay/*.json  (PMData crew days · Pulse emergency · ISS cabin + dose)
        │
        ▼
 ┌──────────────────────────  WEB APP (React + Three.js, offline)  ──────────────────────────┐
 │ Home · 3D body · Physical/Mental views · Cards · Charts · Emergency screens · Accuracy     │
 │ Windows: (1) Patient tablet  (2) Rescuer tablet  (3) Ground console                        │
 └───────────────▲───────────────────────────────────────────────────────────────────────────┘
                 │ (optional live layer)
 ┌───────────────┴──────────────  LOCAL PYTHON SERVICE ("habitat network")  ─────────────────┐
 │ Mission clock · Replay player · Baseline A · Auto-detect rule · Likely-cause ranking       │
 │ Status · Quarantine · Forecast B (P1) · SHAP/conformal (P1) · Explainer (Ollama) · SQLite  │
 └────────────────────────────────────────────────────────────────────────────────────────────┘
```

If Pulse, Ollama or the service breaks, the app and the optional hosted replay still play from the files. No per-feature fallback code is needed.

### Tech stack

| Layer | Choice | Link |
|---|---|---|
| Frontend | TypeScript, React, Three.js (offline-capable web app) | https://threejs.org |
| Service + ML | Python: scikit-learn (gradient-boosted trees), `shap`, MAPIE | https://github.com/shap/shap · https://github.com/scikit-learn-contrib/MAPIE |
| Physiology simulation | Pulse Physiology Engine (Apache 2.0), Python API | https://pulse.kitware.com/ |
| Explainer | Ollama + a small free ~3–4B model, keyword retrieval (no vector DB) | https://ollama.com |
| Storage | SQLite, one file | https://www.sqlite.org/limits.html |
| 3D assets | Z-Anatomy + Human Reference Atlas, compressed GLB | see §4.5 |

The demo "tablet" is a browser on a laptop. The service plays the habitat network. Both simplifications are said honestly in the pitch.

---

## 4. Data sources (with links, licences and status)

### 4.1 Core data used in the build

| Need | Dataset | Link | Licence | How we use it | Status |
|---|---|---|---|---|---|
| **Normal days** (heart rate, steps, sleep, fatigue, mood, stress, readiness) | **PMData**: 16 people × 5 months, Fitbit Versa 2 + wellness reports | https://datasets.simula.no/pmdata/ | CC BY 4.0 | Main dataset for baseline A and forecast B. Map onto 4 synthetic crew | **Chosen.** PMData readiness scale unverified, check at download |
| **Emergency episode** (deterioration → arrest → CPR) | **Pulse Physiology Engine** | https://pulse.kitware.com/ | Apache 2.0 | Generate the collapse replay | **Chosen.** Spike A at H0 |
| **Cabin air** (temperature, CO₂, humidity) and **ISS radiation dose** | **NASA OSDR Environmental Data App** | https://visualization.osdr.nasa.gov/eda/ | Open download; terms page not read; radiation data: cite as visualization (SRAG note) | Real ISS values for the cabin banner and mission-bar dose | **Chosen** |
| **Return-to-gravity cardiovascular shift** | **NASA LSDA Apollo Flight Crew Cardiovascular Evaluations (AP005)** | https://nlsp.nasa.gov/search/data/details/e1fa5c55-ddfe-5548-91ba-864080319f44?dataType=EXPERIMENTS | Open part = 13 summarized tables from NASA SP-368; raw per-crew values restricted | Expected shift at landing and for the stand test (see §4.3) | **Chosen** (group means only) |
| **Real astronaut lab values** | **NASA OSDR Inspiration4**: OSD-569 (whole blood, includes complete blood count), OSD-570, OSD-571 (plasma), OSD-575 (serum) | I4 index: https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/ · Paper: https://pmc.ncbi.nlm.nih.gov/articles/PMC11094041 · API: https://osdr.nasa.gov/osdr/data/search?term=Inspiration4&type=cgene | Processed data public; raw requires board approval | Manual lab-entry cards (blood counts, metabolic panels) | **Chosen.** Which ID holds which panel: check at download |
| **Glucose (continuous monitor)** | **CGMacros**: 45 people (15 healthy) | https://registry.opendata.aws/cgmacros/ | CC BY-NC-SA 4.0 | Simulated glucose stream. **Keep as a separate file** (share-alike, non-commercial) | Chosen (thin) |
| **Blood pressure** | Pulse simulated normal BP | https://pulse.kitware.com/ | Apache 2.0 | No open healthy-adult BP dataset exists; labelled "simulated" | Chosen |

### 4.2 Accuracy testing and optional extras

| Need | Dataset | Link | Licence | Use |
|---|---|---|---|---|
| Webcam heart-rate accuracy | UBFC-rPPG | https://sites.google.com/view/ybenezeth/ubfcrppg | Research use only | Accuracy page only |
| Extra 24 h beat-to-beat HR/HRV, sleep, stress | MMASH (22 people) | https://physionet.org/content/mmash/ | ODbL 1.0 | Optional |
| Apple Watch heart rate + motion + sleep labels | SleepAccel (PhysioNet) | https://physionet.org/content/sleep-accel/1.0.0/ | Open; licence not checked | Optional extra sleep data |
| Wearable HRV + sleep diaries (49 people, 4 weeks) | Scientific Data 2025 | https://www.nature.com/articles/s41597-025-05801-3 | CC BY 4.0 (Figshare) | Optional extra |
| Sleep stages / wearable stress | Sleep-EDF · WESAD | https://www.physionet.org/content/sleep-edfx/1.0.0/ · https://www.eti.uni-siegen.de/ubicomp/home/datasets/icmi18/ | ODC-By · non-commercial | Not needed for the demo |
| ECG rhythm classifier (post-hackathon) | PTB-XL · MIT-BIH | https://www.physionet.org/content/ptb-xl/1.0.3/ · https://registry.opendata.aws/mitdb/ | CC BY 4.0 · ODC-By | Pitch / future |
| Blood pressure (surgical, not healthy) | VitalDB | https://physionet.org/content/vitaldb/1.0.0/ | CC BY 4.0 | Not used (surgical patients) |
| Mars surface radiation | MSL RAD (PDS id `MSL-M-RAD-3-RDR-V1.0`) | Listed in NASA catalogues; not opened | Public | Mars base profile dose; verify on download |

### 4.3 Real astronaut reference values we can cite

Source: Apollo AP005, open Table 6 (group means, 24 crew at rest, 9 standing; after landing, not in flight).

| Measure | Preflight | 1st postflight | 2nd | 3rd |
|---|---|---|---|---|
| Resting heart rate (bpm) | 61.6 | **69.7** | 67.2 | 63.5 |
| Standing heart rate (bpm) | 76.4 | **99.8** | 91.8 | 77.0 |
| Standing systolic BP (mm Hg) | 118.8 | **105.8** | 123.9 | 120.7 |

Use: expected return-to-gravity shift for the stand test and Mars arrival. The **in-flight** shift has no real source and stays labelled "team value". No fixed pass/fail line from NASA was found, so the stand test compares against the astronaut's own pre-flight test first.

### 4.4 Astronaut wearable data: what we checked (negative result)

We searched for an open astronaut heart-rate, sleep or ECG stream. **None exists publicly.**

| Source | Finding | Link |
|---|---|---|
| NASA OSDR Inspiration4 (10 studies) | Blood, microbiome, skin, stool, urine, T-cells only. **No wearable files** | https://www.nasa.gov/osdr-latest-news-i4-mission-datasets/ |
| Inspiration4 Nature paper | Crew wore Apple Watches; data went to four repositories (OSDR, SOMA portal, TRISH EXPAND). Watch data not confirmed public | https://www.nature.com/articles/s41586-024-07648-x |
| SOMA data portal | Public data confirmed is omics and blood | https://soma.weill.cornell.edu |
| Skylab Crew Health (NLSP) | Open part = radiation dose and nutrition tables only; sleep restricted | https://nlsp.nasa.gov/search/data/details/90d326d8-dd48-54d7-a2f6-ece2621b3fb1?dataType=EXPERIMENTS |
| NASA "Human Sleep, Circadian Rhythms and Performance in Space" | All datasets privacy-protected, request only | via the request page below |
| ISS Holter ECG studies (JAXA), HI-SEAS, Mars-500 | Papers exist; no open data release found | none |
| **Request path (post-hackathon)** | NASA LSDA / LSAH Data Request Form | https://lsda.jsc.nasa.gov/explore/lsdahome/datarequest |
| Attention-test data (Tu 2022, 24 ISS astronauts) | Available on request from NASA; analysis code is public | https://www.nature.com/articles/s41598-022-14456-8 · https://github.com/danni-tu/TRISH_dynamic_prediction |

**Pitch line:** "No open astronaut wearable stream exists, so the demo uses Earth wearable data shaped by space guidelines. A real stream is a post-hackathon data request."

### 4.5 3D assets

| Use | Model | Link | Licence |
|---|---|---|---|
| Inner layers, both sexes (5,000+ structures) | Z-Anatomy | https://github.com/Z-Anatomy/Models-of-human-anatomy | CC BY-SA 4.0 |
| Brain detail (141 structures) | Human Reference Atlas brain | https://humanatlas.io/3d-reference-library · https://3d.nih.gov/collections/hra | CC BY 4.0 |
| Female organs | HRA "Body, Female" | https://3d.nih.gov/collections/hra | CC BY 4.0 |
| Source of Z-Anatomy (licence) | BodyParts3D | https://dbarchive.biosciencedbc.jp/en/bodyparts3d/lic.html | CC BY 4.0 |

Pipeline: export only the structures in the indicator-to-structure map (design1.md §6.3) plus a simplified outline per layer → compressed GLB → load region detail on zoom. Female muscle, skeleton and vessel layers are resized from male and labelled "approximate". Skin is a later goal.

---

## 5. Guidelines that drive the responses

These are the sources for the emergency protocol, thresholds and "Why" lines. Every protocol step stores its citation, and the content linter fails the build if a step or threshold has none.

| Topic | Source | Link |
|---|---|---|
| CPR in microgravity (Evetts-Russomano compressions; restraint on the Crew Medical Restraint System; handstand method; airway only with 2+ rescuers) | Hinkelbein et al. 2020, DGLRM + ESAM-SMG guideline | https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/ |
| Delayed ground support, "anticipate the questions of specialists", decision support | Levin et al. 2023, EIMO (NASA HRP ExMC) | https://pmc.ncbi.nlm.nih.gov/articles/PMC10810302/ |
| Crew Medical Officer, kit, ground support | NASA, health care FAQ | https://www.nasa.gov/missions/station/faq-the-real-story-about-astronaut-health-care-in-space/ |
| Health and medical standards | NASA-STD-3001 Vol 1 §3.0 | https://www.nasa.gov/reference/3-0-health-and-medical-care/ |
| What is measured pre/in/post flight | Spaceflight Standard Measures | https://www.nasa.gov/reference/standard-measures/ |
| Five hazards | NASA HRP | https://www.nasa.gov/hrp/hazards/ |
| 17 HRP risks (each Indicator maps to one) | NASA HRP | https://www.nasa.gov/hrp/risks/ |
| Daily readiness precedent (ARCHeR) | NASA | https://www.nasa.gov/reference/archer/ |
| Radiation monitoring (CANS) | CSA | https://www.asc-csa.gc.ca/eng/news/articles/2026/2026-02-26-monitoring-radiation-astronaut-health.asp |
| Why science on the ISS | CSA | https://www.asc-csa.gc.ca/eng/iss/science/why-do-we-conduct-science-experiments-in-space.asp |
| Challenge, briefing video, FAQ | Space Apps | https://www.spaceappschallenge.org/2026/challenges/health-monitoring-software/?tab=details · https://www.youtube.com/watch?v=RERG3gEmdC8 · https://www.spaceappschallenge.org/resources/participant-faqs/ |

**Known gaps (state openly):** published space guidance exists only for CPR; **partial-gravity CPR (Moon, Mars) is open** and stays pitch only; chest-pain steps are non-drug only (stop activity, restrain, attach ECG/AED pads, prepare AED, start ground report; medication steps read "per flight surgeon / onboard medical checklist").

---

## 6. How the key parts work

### 6.1 Baseline A (detects deviation)
- **Anchor:** fixed pre-flight values per person and Indicator. Drives **Drift alerts**.
- **Adaptive baseline:** 28-day sliding window. Drives **Acute alerts**.
- Combined multi-signal deviation score, CuSum alarm, O(1) per reading (Mishra 2020: https://www.nature.com/articles/s41551-020-00640-6 · Alavi 2022: https://pmc.ncbi.nlm.nih.gov/articles/PMC8240687/).
- **Quarantine:** readings taken while an alert is open are held; released on a "false alarm" tag or after 24 h; moved to the Event store if confirmed. Abnormal data never updates the baseline.
- **Status** (green/amber/red) = the worse of A's deviation level and the safety-bound check, computed in one place. Safety bounds from Earth references are labelled "Earth reference, no space data".

### 6.2 Emergency trigger (both paths open the same flow)
- **Auto-detect rule** on the stream: abnormal rhythm state (VT, VF, PEA, asystole), or sustained extreme heart rate with low blood pressure. Thresholds are labelled "Earth reference / team value". In the demo the stream is the Pulse replay.
- **Manual button:** "Emergency" or "Help a crewmate" on any tablet.
- Auto-trigger asks the patient 1–2 questions. **No answer in 15 s** → crew alarm on every tablet. The first to accept is Rescuer 1 and answers as observer ("Does the patient respond?").
- Opening another person's record is allowed only in emergency mode, and every opening is logged.

### 6.3 Likely-cause suggestion (history-based, rule-based)
After a trigger the app shows 2–3 **likely contributors** from the person's history, for example "resting heart rate +6 bpm over 9 days", "sleep 1.5 h below normal", "glucose off baseline". Template text from A's numbers. Labelled "suggestion, not diagnosis". It does **not** choose the protocol steps; the confirmed trigger does.

### 6.4 Protocol and explainer
- Steps are fixed JSON from the guideline, one per screen, filtered by equipment on board for the Mission profile and by rescuer count.
- **"Why this step?"**: Ollama with keyword retrieval over the protocol steps and their source excerpts. It cites its answer. If nothing matches it replies "not covered, ask ground". It never edits a step.
- Urgency verdict shown on every alert: **ACT NOW / ESCALATE TO GROUND / MONITOR / ROUTINE**.

### 6.5 Ground report
Auto-packaged: vitals, history summary, timeline, actions taken, and the questions specialists are likely to ask. Shows the delay: Mars default **28.5 min one way (57 min round trip)**, a conservative team value above NASA's stated 20 min maximum. In the demo a **ground console** window lets a teammate type the flight surgeon's reply after the delay on the Mission clock (scripted fallback). The reply becomes a Label that tunes A.

### 6.6 Mission clock
One simulated clock read by every component. Demo controls: 1×, 60×, skip to next event, labelled "demo time". Needed so the 24 h quarantine, 28-day window and 57 min reply fit a short demo.

---

## 7. Contracts (data lead publishes by H2, JSON Schema in `contracts/`)

Nothing crosses a stream boundary except these files and endpoints.

| Contract | Fields |
|---|---|
| `Reading` | crew, indicator, value, unit, t (Mission clock), source (sensor / camera / mic / manual / lab / sim), confidence, state (released / quarantined / event) |
| `Alert` | id, kind (acute / drift / emergency), crew, indicator, deviation, status, urgency, likely_causes[], t |
| `CrewRecord` | id, sex, anchor{indicator: mean, sd}, missionProfile |
| `ReplayFile` | crew, profile, events[] ordered by t |
| `Protocol` | id, title, steps[{id, text, source{guideline, section}, equipment[], rescuers}] |
| `GroundReport` | id, crew, summary, history[], timeline[], actions[], sent_t, reply_t?, reply? |
| `Trigger` | kind (auto / manual), crew, t, reason, confirmed? |

---

## 8. Repo layout

```
stellarforge/
  contracts/   JSON Schemas (frozen at H2)
  replay/      crew days, emergency, ISS cabin + dose (generated at the hackathon)
  content/     protocols/  cards/  profiles/   (JSON; every item has a source)
  service/     Python: clock, replay player, baseline A, detect, likely-cause, explainer, SQLite
  web/         React + Three.js
  tools/       content linter, replay generator, golden tests
  docs/        credits, si-log.md, write-up
  LICENSE      MIT (code); derived 3D assets CC BY-SA 4.0
```

Rule: before 14 Nov only research was allowed. Downloading, generating and converting data happens now, during the hackathon.

---

## 9. Streams, owners and tasks

Owners are listed by **role**, not by name. Assign each role to a team member.

| Stream | Owner | Scope |
|---|---|---|
| 4: Data, clock, service, contracts | **Data lead** | Starts first, unblocks the rest |
| 1: 3D body, home, charts | **3D / UI lead** | |
| 2: Baseline A, detect, likely-cause, accuracy | **AI / detection lead** | |
| 3: Emergency flow, protocols, explainer, ground console | **Emergency-flow lead**, integration lead on protocol content and citations | Biggest P0 block |
| Integration, video, write-up, SI statement, submit | **Integration lead** (Team Owner) | Owns the submission checklist |

### Phase 0 (H0–2): setup and spikes

| ID | Task | Owner |
|---|---|---|
| 0.1 | Repo skeleton, MIT licence, start `docs/si-log.md` | Integration lead || 0.2 | Freeze the 7 contracts | Data lead || 0.3 | Spike A: Pulse run produces arrest + CPR CSV | Data lead || 0.4 | Spike B: Z-Anatomy GLB loads in Three.js with mapped structures | 3D / UI lead || 0.5 | Spike C: Ollama small model answers in under 5 s | Emergency-flow lead || 0.6 | Spike D: download PMData, ISS EDA, Inspiration4 blood values | AI / detection lead || 0.7 | Spike E: webcam heart rate works | AI / detection lead |
**Go/no-go at H2:**

| Spike | If it fails |
|---|---|
| A | Hand-author the emergency replay from published values, label "illustrative" |
| B | Simplified body outline plus highlighted organ meshes only |
| C | Pre-written "Why this step?" answers, labelled "recorded answer" |
| D | Use whatever downloaded; blood values can be typed in from the paper tables |
| E | Drop to P2, show a recorded heart-rate clip |

### Phase 1 (H2–10): vertical slice

**Stream 4 (data lead)**
- 4.1 Mission clock (1×, 60×, skip to next event).
- 4.2 Replay generator: 4 synthetic crew from PMData normal days, 5-month history with one planted slow drift.
- 4.3 Emergency replay from Pulse: stepwise stroke-volume drop → tachycardia → unstable VT → VF → arrest → CPR. Labelled "estimate, not validated". Chest pain is crew-reported, not simulated (Pulse has no ischemia model; its ECG is a template).
- 4.4 ISS cabin and dose replay from the EDA.
- 4.5 SQLite and a replay player pushing events to browser windows (the "habitat network").

**Stream 1 (3D / UI lead)**
- 1.1 Male body with layers and per-layer transparency.
- 1.2 Status glow from Reading state (default view only; SHAP uses a different visual).
- 1.3 Mission bar (day, profile, delay, dose).
- 1.4 Trend chart with baseline band and alert markers, plus Mission-clock scrubber.
- 1.5 Heart pulses at the real heart rate.

**Stream 2 (AI / detection lead)**
- 2.1 Baseline A with Acute and Drift alerts.
- 2.2 Quarantine manager.
- 2.3 Auto-detect rule on the stream.
- 2.4 Likely-cause ranking from history.
- 2.5 Status computed in one place.

**Stream 3 (emergency-flow lead, integration lead on content)**
- 3.1 Protocol JSON from the microgravity CPR guideline, every step cited, non-drug chest-pain phase.
- 3.2 Content linter: build fails if any step or threshold has no source, or if any drug name or dose appears.
- 3.3 Emergency screens: manual button and auto-trigger open the same flow; urgency verdict; 15 s crew alarm; rescuer takeover with access log.
- 3.4 One step per screen, large type, disclaimer on every screen.
- 3.5 Explainer (Ollama, keyword retrieval, cites, refuses off-corpus).
- 3.6 Ground report builder and ground console window.

### Phase 2 (H10–14): integration #1
- Full emergency flow on real replay, both trigger paths (integration lead leads).
- **Backup screen recording at the end of day 1.**
- First golden tests running.

### Phase 3 (H14–18): P0 polish
- Measurement cards (How / Why / If abnormal; Why names the NASA HRP risk) for a few indicators.
- "How accurate is this" page (see §10).
- Credits page and "decision support, not diagnosis" labels.
- Daily briefing text, for example "resting heart rate +6 bpm over 9 days".

### Phase 4 (H18–24): P1, in this order
1. Webcam heart rate in the morning check.
2. Readiness forecast B with conformal range and SHAP view ("Why this forecast?").
3. ISS CO₂, temperature and humidity replay with a CO₂ banner.
4. Stand test and post-EVA check (forms with the Apollo reference).
5. Profile switcher (delay, kit, safety bounds).
6. Check-in streaks.
7. Female model (organs only).
8. Hosted replay on GitHub Pages.

**Feature freeze at H24. Nothing new after that.**

### Phase 5 (H24–28): ship
- Bug fixing, two full rehearsals, record the video.
- README, write-up, SI statement from the log.
- Submit at H28 or earlier (Team Owner).

---

## 10. Tests and accuracy

| Type | What |
|---|---|
| Golden replay | Replay file → expected Status and Alert at set times: the planted drift alert; the auto-trigger on the Pulse event; the manual button giving the same flow |
| Content linter | Every protocol step and threshold has a source; no drug name or dose anywhere in protocol content |
| Unit | Baseline math, CuSum, Quarantine moves, Mission clock, likely-cause ranking, status rule |
| Safety | The explainer refuses off-corpus questions and never edits a step |
| Offline | Full emergency flow runs with the network off |
| Accessibility | Colour plus icon or text, large targets |

Coverage target: 80% on the Python service and rules. The UI is covered by the golden and offline checks.

**Accuracy page** (tested on held-out people, never trained on): baseline A = alerts raised before known events and false alerts per crew-day; forecast B (P1) = mean error and interval coverage (target about 90%); webcam heart rate (P1) = mean error in bpm on UBFC-rPPG; cardiac rule = caught every simulated Pulse event. Accuracy is measured on datasets; real-time performance with real astronauts may differ.

---

## 11. Risks

| Risk | Level | Mitigation |
|---|---|---|
| Streams invent different formats | High | Contracts frozen at H2; schema-validate every replay file |
| 3D model too heavy or misaligned | High | Spike B at H0; fallback is outline plus organ meshes |
| Medical inaccuracy | High | Published steps only, citation linter, no drugs, disclaimers |
| Pulse can't produce a clean emergency | Medium | Hand-authored replay, labelled illustrative |
| Auto-detect false alarms | Medium | Crew confirms with 1–2 questions; same flow works from the button |
| Explainer hallucination | Medium | Retrieval-only answers; "not covered, ask ground" |
| Team fatigue over 30 hours | Medium | Plan two sleep shifts; the integration lead owns the clock |
| Submission and Judging guides not found | Medium | Ask the Local Lead now; submit early |
| Real data gaps | Low | Stated openly (see §12) |

---

## 12. Known limitations (say these in the write-up)

- No hardware. All live data is simulated or replayed.
- No open astronaut wearable stream exists; normal days come from Earth wearable data (PMData).
- The collapse is a Pulse approximation with no ischemia model and a template ECG; labelled "estimate, not validated". Chest pain is crew-reported.
- Accuracy is measured on datasets, not real astronauts.
- Published space guidance exists only for CPR. Partial-gravity CPR is not covered.
- In-flight vital-sign shifts have no real source and are labelled "team value".
- Mars delay default (28.5 min one way) exceeds NASA's stated 20 min maximum, by team choice.
- Female muscle, skeleton and vessel layers are approximate.
- Demo runs on a laptop browser with one local service standing in for the habitat network.

---

## 13. Demo video script (about 3 minutes; length per the Submission Guide)

| Time | Scene | What the viewer sees |
|---|---|---|
| 0:00 | **Hook** | Mars transit, delay 28.5 min, home screen with the living 3D body |
| 0:20 | **Morning check** | Webcam heart rate (if built), then a Drift alert on the charts and the daily briefing text |
| 0:50 | **Collapse** | Auto-detect fires, urgency ACT NOW, crew alarm, a crewmate takes over the record |
| 1:20 | **Guidance** | Likely contributors from history, then one cited step per screen; "Why this step?" is answered |
| 2:00 | **Ground** | Report built with the 57 min round trip; reply arrives on the ground console and is stored as a label |
| 2:30 | **Close** | Accuracy page, credits page, one line: "same engine, a remote clinic on Earth" |

Failure table for rehearsal: service down → run from replay files; Ollama slow → recorded answer; webcam fails → recorded clip; total failure → play the backup recording.

---

## 14. Submission checklist (Team Owner)

- [ ] Ask the Local Lead for the Submission and Judging guides; confirm format and video length
- [ ] Post the three Space Apps Connect questions (attention-test data, in-flight thresholds, laptop demo)
- [ ] Keep the SI-use log from now (who, which tool, what for)
- [ ] Demo video, plus a backup recording from end of day 1
- [ ] Public repo: code MIT, derived 3D assets CC BY-SA 4.0
- [ ] Short write-up on the Project tab, including the limitations in §12
- [ ] SI-use statement written from the log (mandatory)
- [ ] Credits page: every dataset, model and asset with its source and licence
- [ ] Fill in Team Contact Information
- [ ] **Submit by Sun 15 Nov 2026, 11:59 PM Melbourne time**

### Licences and credits to list
PMData (CC BY 4.0) · Pulse (Apache 2.0) · Z-Anatomy (CC BY-SA 4.0, share-alike) · HRA models (CC BY 4.0) · CGMacros (CC BY-NC-SA 4.0, separate file) · UBFC-rPPG (research use) · NASA OSDR, Apollo and ISS data (cite source; radiation as visualization).

---

## 15. Open items

| Item | Who | When |
|---|---|---|
| Assign each role to a team member | Team | Now |
| Submission and Judging guides, submission format, video length | Team Owner → Local Lead | Now |
| PMData readiness scale and Inspiration4 ID-to-panel mapping | AI / detection lead | At download (H0–2) |
| Whether Pulse's environment action accepts cabin gas and pressure | Data lead | Day 1 |
| Exact Pulse ECG output field name and modifier sequence | Data lead | Day 1 |
| Cabin CO₂ and noise limits, stand-test warning threshold | Team | "Team value" until researched |
| Visual style (colours, typography) | 3D / UI lead | Build time |
| Post-hackathon: NASA LSDA requests for real astronaut heart, sleep and attention-test data | Team | After 15 Nov |
