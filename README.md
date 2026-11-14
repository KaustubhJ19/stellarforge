# StellarForge

An offline, 3D-body health tool for non-doctor astronauts. Built for the **NASA Space Apps Challenge 2026**: *Create Health Monitoring Software for Astronauts on Space Missions*.

It learns each person's own normal, flags drift early, and walks the crew through an emergency (the Mars chest-pain collapse) one cited step per screen, with an automatic ground report that accounts for the Mars delay.

> **Decision support, not diagnosis.** Prototype for a hackathon. Not medical advice.

**Deadline:** Sun 15 Nov 2026, 11:59 PM Melbourne time.

## Start here

1. Read [IMPLEMENTATION-PLAN.md](IMPLEMENTATION-PLAN.md) (the whole plan, datasets, risks, video script).
2. Pick **one** spec from [specs/](specs/) and follow its "How to start" section.

| Spec | Role | Folder it mostly touches |
|---|---|---|
| [01 Data and service](specs/01-data-and-service.md) | Data lead. **Start first, others wait on the contracts** | `contracts/`, `replay/`, `backend/` |
| [02 3D body and home](specs/02-3d-body-and-home.md) | 3D / UI lead | `frontend/` |
| [03 Detection and baseline](specs/03-detection-and-baseline.md) | AI / detection lead | `backend/` |
| [04 Emergency flow](specs/04-emergency-flow.md) | Emergency-flow lead | `frontend/`, `backend/`, `tools/` |
| [05 Integration and submission](specs/05-integration-and-submission.md) | Integration lead (Team Owner) | `content/`, `docs/` |

## Repo layout

```
contracts/   Shared JSON Schemas. The only shapes that cross a stream boundary
replay/      Pre-generated crew days, emergency episode, ISS cabin data (JSON)
content/     Protocols, measurement cards, mission profiles (every item has a source)
  protocols/
  cards/
  profiles/
backend/      Local Python backend: Mission clock, detection, store, explainer
frontend/    Web app (React + Three.js)
tools/       Content linter, replay generator, golden tests
docs/        SI-use log, credits, write-up
specs/       One spec per stream
```

Folders are empty on purpose. Each spec says what to put in them.

## Tech stack (from the plan)

- **Web:** TypeScript, React, Three.js (offline-capable)
- **Backend and ML:** Python, scikit-learn, `shap`, MAPIE, Pulse Physiology Engine
- **Storage:** SQLite
- **Explainer:** Ollama with a small free model
- All free tools and data only.

## Working rules

- **Contracts first.** Add a field to a contract only by agreement in the team chat. Never remove one.
- **One test seam.** A replay file goes in; the alerts, status and screens that come out are checked.
- **Cite everything.** Every protocol step and threshold needs a source. No drug names or doses, ever.
- **Honest labels.** Use "team value", "Earth reference, no space data", "estimate, not validated" where they apply.
- **Feature freeze at H24.** After that: fix, rehearse, record, submit.
- **Log AI use.** Add every use of an AI tool to `docs/si-log.md` (who, which tool, what for). The event requires a statement.
- Commit messages: `type: description` (feat, fix, docs, test, chore, refactor).

## Known limitations

- No hardware. All live data is simulated or replayed.
- No open astronaut wearable stream exists. Normal days come from Earth wearable data (PMData).
- The collapse is a Pulse approximation, labelled "estimate, not validated".
- Published space guidance exists only for CPR. Partial-gravity CPR is not covered.
- Accuracy is measured on datasets, not real astronauts.

## Licence

Code: MIT (see [LICENSE](LICENSE)). Derived 3D assets: CC BY-SA 4.0. Every dataset, model and asset is credited in `docs/`.
