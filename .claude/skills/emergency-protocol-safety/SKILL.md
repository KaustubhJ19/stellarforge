---
name: emergency-protocol-safety
description: Hard safety rules for StellarForge's emergency flow. Use before writing, changing, reviewing or testing anything that touches protocol steps or content, the content linter, the "Why this step?" explainer or Ollama prompts, emergency screens, Crew record access, the ground report or console, Labels, or offline behaviour.
---

# Emergency protocol safety

Decision support, not diagnosis. Published guidelines decide; the language model only explains. These rules beat speed, token savings and convenience. If a task conflicts with one, stop and ask the human.

## The ten rules

1. **AI drafts, humans approve, AI never overrides.** AI may draft protocol step text, but only from a cited guideline section, and every draft is marked `status: "draft"`, `drafted_by: "<tool and model>"`. A draft is never rendered in the app, used by the engine, or shown to crew. Only a named team member can set `status: "approved"` with `approved_by` and `approved_on`. AI never approves, never edits an approved step, and never bypasses review; any change to an approved step goes back to draft. Test fixtures stay visibly fake ("STUB step 1").
2. **Every step has an approved source** (`source.guideline` + `source.section`). Same for every threshold. No source → the build fails (linter) and the engine refuses to render it.
3. **AI never modifies approved instructions.** The explainer and the ground console get read-only access to steps; their output is shown beside a step, never written into it.
4. **No medication names or doses**, anywhere: content, UI strings, explainer output, ground report. Medication steps read exactly: "per flight surgeon / onboard medical checklist".
5. **Unsupported questions return exactly "Not covered, ask ground."** — when retrieval finds nothing, the question is off-corpus, the output fails a check, or the model is slow or down.
6. **Every emergency access to a Crew record is logged** (who, whose, when on the Mission clock, which emergency), enforced in the backend. If the log write fails, the record does not open. Outside emergency mode, access to another person's record is refused.
7. **Every emergency screen shows the disclaimer** "Decision support, not diagnosis", via the shared emergency layout, never per screen by hand.
8. **Offline must keep working.** No CDN or remote calls at runtime; local Ollama; the Emergency button works with the backend down.
9. **Safety-critical changes need automated tests** in the same change: linter cases, explainer cite/refuse, access log, disclaimer, filters, Label storage. Never delete or weaken one of these tests to make a build pass.
10. **Ground replies are stored as Labels**, linked to crew and emergency, and never alter protocol steps.

## Before you finish a change in this area

- [ ] Ran the content linter and the targeted safety tests for what you touched.
- [ ] No drug name, dose or invented clinical wording appears in the diff (`git diff` + linter).
- [ ] The rules above still hold on the screens or endpoints you changed.

## Load only when needed

- Detailed rules, edge cases and how each rule maps to tickets 01–16 → [references/rules-detail.md](references/rules-detail.md)
- Explainer (RAG) and prompt-injection guard rails → [references/explainer-guardrails.md](references/explainer-guardrails.md)
- Required safety tests per area → [references/safety-tests.md](references/safety-tests.md)
