# Rules in detail

Source of truth: `04-emergency-flow.md` (Spec 4) and tickets in `.scratch/emergency-flow/issues/`. When this file and the spec disagree, the spec wins; flag the gap.

| Rule | Where it bites | Tickets | Edge cases |
|---|---|---|---|
| 1 AI drafts, humans approve, AI never overrides | content/protocols, content/approvers.json, linter, step engine, fixtures, prompts, UI copy | 02, 09, 11, 15; Spec 1 (protocol library) | Drafts only from a quoted section in the evidence pack (`<id>.evidence.json`). Build linter and engine both drop any step not `approved` by a name on `content/approvers.json`, with `approved_on` and a matching `approved_hash` (edit = back to draft). Claude stops at "ready for review": never edits `approvers.json`, never runs `tools/approve_steps.py`, never edits an approved step. Stub protocols skip approval but every step must start with "STUB"; stubs are never routed. |
| 2 Every step/threshold sourced | protocol JSON, linter, step engine | 02, 09, 15 | Source missing `guideline` or `section` counts as missing. Engine refuses unsourced steps at runtime too. |
| 3 AI never edits steps | explainer, console | 11, 13 | Test: step text byte-identical after an explainer call or a ground reply. |
| 4 No drugs or doses | linter, explainer output filter, report | 02, 09, 11, 12 | Dose = number + unit (mg, mcg, µg, g, mL, IU, units, mg/kg). Don't flag CPR numbers like "30 compressions" — tune with real content. Drug word list is a data file, extendable. |
| 5 "Not covered, ask ground." | explainer | 11 | Also on: model > 5 s, Ollama down, output fails drug/citation check. If Spike C failed: pre-written answers labelled "recorded answer". |
| 6 Access logging | backend record endpoint, store | 07, 10, 14 | Rescuer 2 openings are logged too. Takeover while backend is down is an open team decision — do not decide it in code. |
| 7 Disclaimer everywhere | shared emergency layout | 03, 16 | Includes alarm, takeover, contributors, steps, "Why?", report and console screens. Automated screen-walk test in 16. |
| 8 Offline | build, runtime, Ollama | 01, 11, 14, 16 | Zero non-local requests in the network log. Queue Triggers/actions/Labels while backend down; deliver once with original times. |
| 9 Tests with safety changes | all | all | Tests assert screens and events through the golden replay seam, not internals. |
| 10 Replies as Labels | console, store | 13 | `Label` fields come from Spec 1/3 contracts; confirm, don't invent. |

Other fixed values (team values, label them as such):
- Mars delay 28.5 min one way / 57 min round trip, adjustable per Mission profile.
- Crew alarm after 15 s with no answer.
- Simulated (Pulse) vitals carry "estimate, not validated". Chest pain is crew-reported, never simulated.
- One rescuer → airway steps hidden. Two-person rover profile → no Rescuer 2.
