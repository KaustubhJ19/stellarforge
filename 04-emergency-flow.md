# Spec 4 · Emergency Flow, Protocol Engine, Explainer and Ground Console

> **Role:** Emergency-flow lead · **Stream 3** · Anyone can pick this spec up. This is the **biggest P0 block**; if two people are free, split it (screens and alarm / explainer and ground report).
> Parent plan: [IMPLEMENTATION-PLAN.md](../IMPLEMENTATION-PLAN.md) · Vocabulary: `GLOSSARY.md` (Crew record, Protocol, Crew alarm, Ground report, Label, Alert, Quarantine, Mission clock)
> Deadline: Sun 15 Nov 2026, 11:59 PM Melbourne. Plan clock: H0 = build start, H24 = feature freeze.
> Triage: `ready-for-agent` (local file, no issue tracker).

## How to start (first 30 minutes)

1. Run **Spike C**: install Ollama, pull one small (about 3–4B) model, and time a short answer. Target: under 5 seconds.
2. Sketch the emergency screens on paper: trigger, confirm, alarm, takeover, step, "Why?", ground report.
3. Use a **stub protocol** (three fake steps with fake sources) until the integration lead delivers real, cited protocol content (about H10).

## Problem Statement

The challenge author's scenario: halfway to Mars, a crewmate has chest pain and collapses. The rescuer is not a doctor, is under stress, and ground help is up to about 57 minutes away round trip. They need to know what is happening, whether it is urgent, and exactly what to do next, from sources they can trust. A language model must not invent resuscitation steps; studies show it gets them wrong.

## Solution

One emergency flow that starts two ways, an **auto Trigger** from the stream or a manual **Emergency / Help a crewmate** button, and then works the same:

1. Show an **urgency verdict** (ACT NOW / ESCALATE TO GROUND / MONITOR / ROUTINE).
2. Ask the patient 1–2 quick questions. **No answer in 15 s** → **crew alarm** on every tablet. The first to accept is Rescuer 1 and answers as observer.
3. The rescuer's tablet opens the patient's Crew record (logged) and assigns roles.
4. Show 2–3 **likely contributors** from history (from Spec 3).
5. Show **one cited step per screen** from a fixed protocol, filtered by equipment on board and by rescuer count.
6. A **"Why this step?"** button answers using an offline language model that only searches the protocol and its source excerpts. It never writes or changes a step.
7. **Auto-build a ground report** and show the expected reply time. A **ground console** window types the flight surgeon's reply after the delay on the Mission clock. The reply becomes a Label.

Rules and published guidelines decide. The language model only explains.

## Seam

Tested by **replaying a file with an emergency and asserting the screens and events that result** (golden replay), through both the auto and manual triggers.

## Contracts (shapes, frozen at H2)

You consume `Reading`, `Alert`, `Trigger`, `CrewRecord`, `ReplayFile`. You produce `Trigger` (manual), `GroundReport` and Labels.

| Contract | Fields |
|---|---|
| `Trigger` | kind (auto / manual), crew, t, reason, confirmed? |
| `Alert` | id, kind (acute / drift / emergency), crew, indicator, deviation, status, urgency (ACT_NOW / ESCALATE_TO_GROUND / MONITOR / ROUTINE), likely_causes[], t |
| `Protocol` | id, title, steps[{id, text, source{guideline, section}, equipment[], rescuers}] |
| `GroundReport` | id, crew, summary, history[], timeline[], actions[], sent_t, reply_t?, reply? |

## User Stories

1. As a crewmate, I want an Emergency button that always works, so that I can start help with no sensors.
2. As a crewmate, I want the app to start the flow itself when it detects a collapse, so that no time is lost.
3. As a crewmate, I want the same flow from the button and from auto-detect, so that there is one thing to learn.
4. As a crewmate, I want an urgency verdict in plain words, so that I know how fast to act.
5. As a patient, I want to answer 1–2 quick questions, so that a false alarm can be dismissed.
6. As a crewmate, I want an alarm on every tablet when the patient does not answer in 15 seconds, so that someone comes.
7. As the first crewmate to accept, I want to be Rescuer 1 and answer as observer ("Does the patient respond?"), so that the flow continues when the patient cannot answer.
8. As a rescuer, I want my tablet to open the patient's record, so that I can help when their tablet is lost or they are the Crew Medical Officer.
9. As a patient, I want every emergency opening of my record logged, so that my privacy is respected.
10. As a rescuer, I want to see 2–3 likely contributors from the history, so that I understand what led here.
11. As a rescuer, I want exactly one step per screen, so that I never have to read a list under stress.
12. As a rescuer, I want large type and large buttons, so that I can use them in gloves.
13. As a rescuer, I want every step to show its source, so that I can trust it.
14. As a rescuer, I want only steps for equipment that is on board, so that I am never told to use something that is not there.
15. As a solo rescuer, I want airway steps hidden, so that I am not told to do what needs two people.
16. As Rescuer 2, I want my own steps (AED, airway), so that two people can work in parallel.
17. As a rescuer, I want a "Why this step?" button, so that I understand the step in one sentence.
18. As a rescuer, I want the answer to cite its source and say "not covered, ask ground" when unsure, so that I am never misled.
19. As the Crew Medical Officer, I want the tool never to name a drug or dose, so that medication stays with the flight surgeon.
20. As a rescuer, I want a disclaimer ("decision support, not diagnosis") on every emergency screen, so that no one over-trusts the app.
21. As a crewmate, I want a ground report built automatically (vitals, history, timeline, actions, likely questions), so that I do not write one under stress.
22. As a crewmate, I want the expected reply time shown (57 min round trip on Mars), so that I know to act on my own meanwhile.
23. As the flight surgeon (demo), I want a ground console where I type a reply after the delay, so that the reply flows back to the crew.
24. As the AI / detection lead, I want the ground reply stored as a Label, so that it can release or confirm quarantined readings.
25. As a presenter, I want the flow to work offline, so that a network failure does not end the demo.

## Implementation Decisions

### Tasks and hours (plan clock)

| ID | Task | Hours |
|---|---|---|
| 4.1 | **Spike C**: Ollama small model answers in under 5 s | H0–2 |
| 4.2 | Protocol format and **content linter**: the build fails if any step or threshold has no source, or if any drug name or dose appears | H2–6 |
| 4.3 | Emergency screens skeleton: trigger, urgency verdict, confirm questions, step screen | H2–10 |
| 4.4 | Crew alarm (15 s) and rescuer takeover with access log; rescuer roles; equipment and rescuer-count filter | H6–10 |
| 4.5 | Explainer: Ollama with keyword retrieval over protocol steps and source excerpts; cites; refuses off-corpus | H6–12 |
| 4.6 | Ground report builder and ground console window; delay on the Mission clock; scripted fallback reply; Label on reply | H8–14 |
| 4.7 | Integration #1 with the other specs (real protocol content arrives about H10) | H10–14 |
| 4.8 | P0 polish: large type, disclaimer on every screen, offline run, rehearsal path | H14–18 |
| 4.9 | Failure handling: service down, explainer slow, console reply late | H18–24 |
| 4.10 | Bug fixing; rehearsal support | H24–28 |

### What to build, in decisions

- **Two triggers, one flow.** The manual button posts a `Trigger` of kind `manual`; Spec 3 emits `auto`. Everything after is identical.
- **Confirm step:** 1–2 questions (symptoms, responsiveness). Chest pain is **crew-reported**, never simulated.
- **Crew alarm:** after 15 s with no answer, ring every crew tablet; the first to accept becomes Rescuer 1 and answers as observer.
- **Takeover:** only in emergency mode; every opening is logged.
- **Roles:** Rescuer 1 (compressions), Rescuer 2 (AED, airway). With one rescuer, airway steps are hidden. With a two-person rover profile, no Rescuer 2.
- **Protocol steps:** fixed JSON from the guideline. Each step stores its source (guideline, section), the equipment it needs, and how many rescuers. Equipment comes from the Mission profile.
- **Chest-pain phase is non-drug only:** stop activity, restrain, attach ECG/AED pads, prepare AED, start the ground report. Any medication step reads "per flight surgeon / onboard medical checklist". **The tool never names a drug or dose.**
- **Explainer:** keyword search over the protocol steps and their source excerpts (no vector database). The answer cites its source. If nothing matches: "not covered, ask ground". It never edits a step.
- **Ground report:** summary, history, timeline, actions taken, and the questions specialists are likely to ask. Show sent time and expected reply time.
- **Delay:** Mars default **28.5 min one way (57 min round trip)** on the Mission clock, a conservative team value above NASA's stated 20 min maximum. Adjustable per profile.
- **Ground console:** a third browser window where a teammate types the flight surgeon's reply after the delay. A scripted fallback reply exists. The reply is stored as a Label.

### Protocol content (written in Spec 5, not here)

The integration lead writes and cites the protocol content. This spec builds the engine, screens and linter. **Do not invent clinical steps.** The published source for the CPR sequence is Hinkelbein et al. 2020: https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/ . Outline from the plan: no response → start compressions (Evetts-Russomano method) → restrain on the Crew Medical Restraint System → handstand method → Rescuer 2: AED → airway only with two or more rescuers. Exact wording and parameters come from the guideline.

## Sources (links)

| Topic | Source | Link |
|---|---|---|
| CPR in microgravity | Hinkelbein et al. 2020 | https://pmc.ncbi.nlm.nih.gov/articles/PMC7607644/ |
| Delayed ground support; anticipate specialists' questions | Levin et al. 2023 (EIMO) | https://pmc.ncbi.nlm.nih.gov/articles/PMC10810302/ |
| Crew Medical Officer, kit | NASA health care FAQ | https://www.nasa.gov/missions/station/faq-the-real-story-about-astronaut-health-care-in-space/ |
| Local language model | Ollama | https://ollama.com |

## Spike go/no-go (decide by H2)

| Spike | If it fails |
|---|---|
| C: Ollama answers in under 5 s | Ship pre-written "Why this step?" answers labelled "recorded answer" |
| Retrieval returns wrong excerpts | Restrict to exact step-text lookup and refuse everything else |
| Ground console reply feels too slow | Use the scripted fallback reply and say so |

## Dependencies

- **Needs from Spec 1:** contracts (H2), the emergency replay (H6), a service to post Triggers and Labels (H10).
- **Needs from Spec 3:** the auto `Trigger`, likely causes and the urgency value (H8–11); Label hooks for quarantine.
- **Needs from Spec 5:** cited protocol content, Mission profile equipment and delay (H10).
- **Needs from Spec 2:** the Emergency and Help buttons on the home screen (H10).

## Testing Decisions

- A good test replays a file and asserts **which screens and events result**, not component internals.
- Tests: (a) the auto Trigger and the manual button reach the same first screen; (b) no answer in 15 s raises an alarm on every other tablet and the first to accept is Rescuer 1; (c) opening another person's record is logged; (d) with one rescuer, airway steps are hidden; (e) steps needing equipment not in the Mission profile are not shown; (f) the content linter fails on a step with no source and on any drug name or dose; (g) the explainer cites a source, and answers "not covered, ask ground" on an off-corpus question; (h) the ground report contains vitals, history, timeline and actions, with the correct expected reply time; (i) the ground reply is stored as a Label; (j) the whole flow runs with the network off.
- Prior art: none (no code yet).

## Acceptance Criteria

- [ ] Both triggers open the same flow.
- [ ] Urgency verdict, confirm questions, 15 s crew alarm and rescuer takeover work, with an access log.
- [ ] One cited step per screen, filtered by equipment and rescuer count.
- [ ] Linter blocks uncited steps and any drug name or dose.
- [ ] "Why this step?" cites or refuses; never edits a step.
- [ ] Ground report auto-built; console reply arrives after the delay and is stored as a Label.
- [ ] Disclaimer on every emergency screen; full flow runs offline.

## Out of Scope

- Writing protocol content (Spec 5). Detecting the collapse (Spec 3). The 3D body (Spec 2). Data (Spec 1).
- Partial-gravity CPR (Moon, Mars). Published space guidance exists only for CPR, and partial gravity is open. Pitch only.
- Real tablet-to-tablet sync (the service stands in for the habitat network).

## Further Notes

- The collapse in the demo is a Pulse approximation labelled "estimate, not validated". Pulse has no ischemia model, so chest pain is crew-reported.
- Be explicit in the write-up: the language model only explains; published steps decide.
