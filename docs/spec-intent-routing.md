# Spec: intent-first protocol routing

Status: built on branch `feat/intent-routing` except `cabin-air` content (needs a cited source), the optional free-text intake, and offline routing in the tablet frontend (the bundle already carries the protocols, route table and intake fields). Not yet clinically reviewed.

## Problem

The emergency service loads one protocol at startup (`SF_PROTOCOL`, default `microgravity-cpr`; `backend/app/main.py`). Every confirmed Trigger gets CPR steps, whatever is actually wrong. A crewmate with chest pain who is awake, or a cabin-air problem, gets the wrong flow.

## Goal

Work out what is happening first, then pick one pre-written, cited protocol. If nothing fits, say so and hand over to ground.

## Principles (from the README working rules, not negotiable)

1. **Rules decide, the model only explains.** The router is a fixed table. A language model may only turn free text into structured answers, and a person confirms them before the router uses them.
2. **Every step is cited; AI drafts, humans approve, AI never overrides.** A model may draft step text only from a cited guideline section, marked `status: "draft"` with `drafted_by`. Drafts are never rendered, routed or shown to crew; only a named team member approves (`approved_by`, `approved_on`), and any change to an approved step returns it to draft (Spec 1, Rule 1). No drug names or doses.
3. **Honest labels.** New protocols are "Earth reference, no space data" and "not clinically reviewed" until someone reviews them.
4. **Contracts do not change** without team agreement. This spec adds none (see Contracts).

## Non-goals

- Diagnosis. The screen says "what the rescuer reports", never "the patient has X".
- Covering all 17 HRP risks. The demo covers 3 situations plus "not covered".
- Partial-gravity (Moon, Mars surface) guidance. Still not covered.
- Replacing the Trigger or Alert shapes.

## Flow

```
Trigger (auto or manual)
  → Intake screen: "What's happening?"
       tap questions (always)        free text (optional, needs Ollama)
              └──────── structured Intake ◄── rescuer confirms ┘
  → Router (rules) → protocol_id | "not_covered"
  → Existing flow: record → likely contributors → cited steps → ground report
```

An auto Trigger from the arrest rule skips the questions and routes straight to `microgravity-cpr`. A person can still change it (see Override).

## Intake

Structured form, held on the `Emergency` and never sent to a model as a decision.

| Field | Values |
|---|---|
| `responsive` | `yes`, `no` |
| `breathing` | `normal`, `abnormal`, `none` |
| `main_problem` | `chest_pain`, `breathing_trouble`, `cabin_alert`, `collapse`, `injury`, `other` |
| `source` | `tap`, `text_confirmed` |

Tap questions come from `content/flow/confirm-questions.json` (currently a stub; wording is to be replaced).

**Free-text path (optional).** Ollama maps the sentence to the form above using a fixed list of allowed values. Output that is not valid is discarded and the tap questions are shown. The rescuer sees the filled form and presses Confirm or edits it. With Ollama off, only the tap path exists. Free text is stored in the ground report only as the rescuer's own words.

## Router

A pure function: `route(intake, live) -> {protocol_id, rule_id, reason}`. `live` is the patient's latest rhythm and cabin alert, if any. First matching row wins.

| # | Condition | Result |
|---|---|---|
| 1 | `responsive = no` and `breathing` in (`none`, `abnormal`) | `microgravity-cpr` |
| 2 | live rhythm is an arrest rhythm | `microgravity-cpr` |
| 3 | `main_problem = chest_pain` and `responsive = yes` | `chest-pain` |
| 4 | `main_problem = cabin_alert`, or an active cabin Alert | `cabin-air` |
| 5 | anything else | `not_covered` |

Rows live in `content/triage/routes.json`, not in code. Each row has an id, a condition and a source note. The linter checks that every `protocol_id` exists.

**`not_covered`** shows "Not covered by this tool. Contact ground." with no steps, still shows the likely contributors, and pre-fills the ground report.

**Override.** The rescuer can switch to any other covered protocol from the step screen. The switch is logged in the emergency timeline with who did it. This is required because the router can be wrong.

## Protocols

| id | Status | Source |
|---|---|---|
| `microgravity-cpr` | exists | Hinkelbein et al. 2020 |
| `chest-pain` | exists | ESC 2023 ACS guideline (Earth reference) |
| `cabin-air` | **new** | to be chosen and cited by the content owner |

Each protocol needs the same four files as today: `<id>.json`, `.excerpts.json`, `.roles.json`, `.recorded.json`, plus an entry in `coverage.json`. The `cabin-air` source is not yet picked. It must be a published guideline. If none can be cited, drop the scenario and keep "not covered".

## Changes

| Area | File | Change |
|---|---|---|
| Router | `backend/app/triage.py` (new) | `route()`, loads `routes.json` |
| Content | `content/triage/routes.json` (new) | Router table |
| Content | `content/protocols/cabin-air.*` (new) | Protocol files |
| Flow | `backend/app/flow.py` | Replace single `self.protocol` with a dict. Store `protocol_id` and `intake` on `Emergency`. Add `intake` and `switch_protocol` actions |
| Service | `backend/app/main.py` | Load all protocols. Keep `SF_PROTOCOL` as the forced override for tests. Add `/api/intake` and `/api/switch-protocol` |
| Explainer | `backend/app/explainer.py` | Look up excerpts for the emergency's protocol |
| Ground | `backend/app/ground.py` | Put intake answers, protocol and rule id into `summary` and `actions` |
| UI | `frontend/src/emergency/screens.tsx` | "What's happening?" screen; "Using: X, because Y" banner; switch control; not-covered screen |
| Offline | `backend/app/offline.py` | Bundle all protocols and `routes.json` |

## Contracts

No change. `Trigger`, `Alert` and `Protocol` keep their fields. Intake and routing details travel in the ground report's existing `summary`, `timeline` and `actions` fields. If the team wants them as their own fields, that needs agreement first.

## Acceptance criteria

1. Each router row has a unit test, and a table-driven test checks that nothing outside the table is reachable.
2. Collapse replay (crew B): auto Trigger → `microgravity-cpr`, same steps as today.
3. Manual start with `chest_pain` + `responsive = yes` → `chest-pain` steps.
4. Cabin Alert replay → `cabin-air`.
5. `main_problem = injury` → "Not covered", no steps, report pre-filled.
6. Invalid or missing model output → tap questions shown; nothing is routed from unconfirmed text.
7. Ollama stopped: scenarios 2 to 5 still work.
8. Override switches protocol, is logged with the actor, and appears in the ground report.
9. `tools/content_lint.py` and the drug denylist pass on all protocols, and `routes.json` is checked.
10. Existing tests still pass (`pytest backend contracts tools`, `npm test`).
11. Offline mode shows the same routing.

## Risks and open questions

- **Wrong route.** A rescuer under stress may answer wrongly. Mitigation: override, the visible "because" line, and conservative row order (row 1 first).
- **`cabin-air` content.** No citable source chosen. Owner and source needed.
- **Question wording** is still a placeholder (Spec 5).
- **Model scope.** Decide whether the free-text path ships or stays a stretch goal. The tap path is enough for the demo.
- **Clinical review** is not done for any protocol except the cited text itself. Keep the banner.

## Tickets (one per branch)

1. Router, `routes.json`, unit tests, `protocol_id` on `Emergency`.
2. Intake API and tap screen; ground report fields.
3. `cabin-air` protocol and its replay scenario.
4. Not-covered screen, override, offline bundle.
5. Optional: free-text intake via Ollama.

Load the `emergency-protocol-safety` skill before tickets 2 to 4.
