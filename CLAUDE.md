# StellarForge — Claude Code working rules

Read `README.md` once for layout and team rules. Do not re-read it each ticket.

## Emergency flow work (Spec 4)

- Work one ticket at a time from `.scratch/emergency-flow/issues/NN-*.md`. Read **only that ticket** and the files it touches. Do not load `04-emergency-flow.md` or other tickets unless the ticket is ambiguous; then read only the cited section.
- Ticket → skill map and recommended order: `.scratch/emergency-flow/SKILL-MAP.md`.
- Anything touching protocol content, linter, explainer, emergency screens, record access, ground report/console, Labels or offline → load the `emergency-protocol-safety` skill first. Its rules are not traded for speed or tokens.

## Token discipline

- Navigate with the LSP (go to definition / references) and Grep/Glob before opening files; read file ranges, not whole files.
- Don't re-investigate what this session already established; reuse the ticket's notes.
- Tests: run the targeted test file/marker first; run the full suite and all golden replays only at milestones (end of a ticket, tickets 15 and 16, before a PR).
- Subagents only for genuinely independent work (e.g. the spec's split: screens + alarm / explainer + ground report). Give each a single ticket and the files it owns.
- Library/API docs (Ollama, React, pytest, Playwright): use Context7 instead of guessing or reading `node_modules`.
- Replies: short. Report what changed, what was verified, and what wasn't.
- When a ticket is done, append a 3–5 line summary to `.scratch/emergency-flow/PROGRESS.md` (what was built, key files, open questions). Read that file instead of re-exploring finished work.

## Conventions

- Commits: `type: description` (feat, fix, docs, test, chore, refactor). Branch per ticket.
- Contracts in `contracts/` change only by team agreement; never remove a field.
- Log AI tool use in `docs/si-log.md`.
