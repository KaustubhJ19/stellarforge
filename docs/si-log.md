# AI-use log

Every use of an AI tool on this project: who, which tool, what for.

| Date | Who (stream) | Tool | What for |
|---|---|---|---|
| 2026-11-14 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | Broke Spec 2 into tickets; wrote the Z-Anatomy body export script (Spike B) and the Spec 2 web app (3D body, home screen, charts) test-first, with human review |
| 2026-11-14 | 3D / UI lead (Stream 1) | Claude Code (Claude Opus 5.5) | Tested the Spec 2 web app (coverage, Playwright browser tests, large-replay and slow-device runs, keyboard / high-contrast / reduced-motion checks, colour-blind palette validation, security review) and fixed the issues found, with human review and decisions |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Broke Spec 5 (integration and submission) into 14 tickets with blocking edges, with human review and approval of the breakdown |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Created the Spec 5 branch, inspected the repo and the other streams' branches for dependencies, and started this log, with human review |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Merged the Stream 1 log rows into this log and matched the shared .gitignore so the Spec 5 branch merges cleanly with the 3D branch, with human review |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Wrote the content linter test-first (source and no-drug/no-dose rules) and the first cited microgravity CPR step from Hinkelbein et al. 2020; a web-fetch subagent read the guideline, with human review; step flagged for medical review |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Verified the CPR step against the guideline's full text (Recommendation 2), added environment coverage per mission environment (Recommendations 20 and 21; partial gravity labelled not covered) and a flight-surgeon handoff rule to the linter, test-first; web-fetch subagents read the guideline and NASA medication abstracts, with human review |
| 2026-11-15 | Integration lead (Stream 5) | Claude Code (Claude Opus 5.5) | Expanded the linter's drug blocklist to 64 names in a sourced data file: ISS crew-kit drugs from Wotring 2016 (Table I) and Du 2011 (PMC full text), plus a team-value emergency group; test-first, with human review |
