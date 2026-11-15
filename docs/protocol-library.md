# Protocol library

Spec 1: grow the collapse-protocol library through "AI drafts, humans approve, AI never overrides" (safety Rule 1).

> Decision support, not diagnosis. Hackathon prototype; not medical advice.

## Condition selection rule

This is Claude's call and is open to correction. From NASA's IMPACT/IMM condition list, keep a condition only if it:

1. can cause sudden collapse or loss of responsiveness,
2. has published guidance that a non-doctor can follow, and
3. has a credible prior incidence.

## Workflow (per condition)

| Step | Who | Output |
|---|---|---|
| 1. Evidence pack | Claude | `content/protocols/<id>.evidence.json`. Contains: why the condition is in the library, guideline citation and licence, verbatim recommendations with section numbers, what applies in microgravity, and whether Pulse can simulate it. |
| 2. Draft steps | Claude | `content/protocols/<id>.json`. Each step cites one section from the pack and carries `status: "draft"` and `drafted_by: "<tool and model>"`. |
| 3. Review sheet | Claude | `python tools/review_sheet.py <id>` writes `docs/review/<id>.md`, with each draft next to its quote. |
| 4. Accept, edit or reject each step | **Team member** | To edit, change the JSON (the hash goes stale, so the step stays a draft). To reject, delete the step or leave it as a draft. |
| 5. Approve | **Team member** | `python tools/approve_steps.py <id>` in an interactive terminal. It records `approved_by`, `approved_on` and `approved_hash`. |
| 6. Check | Claude | `python tools/content_lint.py` and the safety tests; report any mismatch. |

Claude stops at "ready for review". Claude never edits `content/approvers.json`, never runs `approve_steps.py`, and never edits an approved step.

## Guards

- **Build linter** (`tools/content_lint.py`). Every step must be `approved` by a name on `content/approvers.json`, with a real `approved_on` date and an `approved_hash` that matches the current step. Every approved step must cite a section that is in its evidence pack. The drug and dose checks are unchanged. Stub protocols skip approval, but every one of their steps must start with "STUB".
- **Engine** (`backend/app/content.py`, `runtime.py`). The loader drops any step that fails the same rule. A protocol with no approved steps, or a stub, is not loadable, so its router row resolves to "not covered", both online and in the offline bundle.

## Library

| Condition | Protocol | Guidance candidate (to verify in the pack) | Pulse | State | Router |
|---|---|---|---|---|---|
| Cardiac arrest / arrhythmia | `microgravity-cpr` | Hinkelbein 2020 | yes | exists, awaiting approval | rows on main |
| Chest pain | `chest-pain` | ESC 2023 (Earth reference) | check | exists, awaiting approval | `chest-pain-responsive` |
| Fainting / orthostatic intolerance | `fainting` | ESC 2018 syncope; ERC first aid | check | pending | `collapse-responsive` |
| Low blood sugar | `low-blood-sugar` | ERC/AHA first aid | check | pending | `*-reported` (team-agreed intake value) |
| Cabin air: low O₂ / CO₂ build-up (merged) | `cabin-air` | ERC first aid; NASA-STD-3001 | yes | pending | `cabin-alert-*` |
| Severe bleeding | `severe-bleeding` | ERC first aid | yes | pending | `*-reported` (team-agreed intake value) |
| Sepsis / severe infection | `sepsis` | Surviving Sepsis Campaign 2021 (verified, PMC8486643) | yes | approved by Kaustubh 2026-11-15 (Earth reference) | `*-reported` (team-agreed intake value) |
| Overheating / fever | `overheating` | ERC first aid | check | pending | `*-reported` (team-agreed intake value) |
| Decompression sickness after EVA | `decompression-sickness` | NASA EVA DCS references | no | pending | `*-reported` (team-agreed intake value) |
| Seizure | `seizure` | ERC first aid | no | pending | `*-reported` (team-agreed intake value) |
| Head injury | `head-injury` | ERC first aid | no | pending | `*-reported` (team-agreed intake value) |

Condition records are in `content/conditions/<id>.json`. Not done yet for the 9 new conditions: evidence pack, draft steps, review sheet (workflow steps 1–3), signs with likelihood ratios (`signs: []`) and Pulse scenario ids (`null`). These need the guideline full texts; Claude does not quote from memory. Every prior incidence is currently `pending`, a third state beside the spec's "sourced" and "team value" that the linter allows only with no value. Fill one in only from a public IMM/IMPACT paper that prints the value, or label it `team value`.

## Team decisions

Agreed by the team on 2026-11-15 (reported by Kaustubh):

- **Contract change.** Add-only fields `status`, `drafted_by`, `approved_by`, `approved_on`, `approved_hash` and `condition_ids` in `contracts/protocol.schema.json`.
- **`collapse-responsive` router row.** A collapse where the patient responds **and breathes normally** routes to `fainting`. It resolves to "not covered" until `fainting` is approved.
- **New intake `main_problem` values.** `bleeding`, `head_injury`, `low_blood_sugar`, `seizure`, `overheating`, `infection` and `after_eva`, each with its own router row. `injury` stays for any other injury and routes to "not covered". An unresponsive patient who is not breathing still goes to CPR first, whatever the main problem.
- **Stub exemption.** Stub protocols skip approval (they are the engine's test doubles) but may only carry "STUB" text or the exact medication hand-off, and are never routed.

Still open:

- **Evidence-pack licences.** Every pack source has `licence_checked: false` until a person confirms the licence.
- **Approvers list.** It holds Kaustubh only; other approvers are added by the team.
