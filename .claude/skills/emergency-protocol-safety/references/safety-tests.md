# Required safety tests

Run the targeted ones for the area you touched; run the whole set at integration milestones (tickets 15, 16) and before any PR.

| Area | Must-have tests | Spec test |
|---|---|---|
| Linter | no source; partial source; uncited threshold; drug name (case variants); dose formats (`300mg`, `0.5 mg`, `1 mg/kg`, `10 mL`); non-dose numbers pass; medication placeholder passes | (f) |
| Step engine | unsourced step not rendered; equipment not on board hidden; one rescuer hides airway; rover has no Rescuer 2; medication step shows placeholder only | (d) (e) |
| Explainer | cites a retrieved source; off-corpus → "Not covered, ask ground."; drug/dose output filtered; Ollama down / > 5 s → fallback; step text unchanged after call | (g) |
| Record access | opening another's record logged; refused outside emergency mode; log-write failure blocks access | (c) |
| Disclaimer | screen-walk finds it on every emergency screen | AC |
| Ground | report has vitals, history, timeline, actions; reply time = sent + profile delay; reply stored as Label; step text unchanged after reply | (h) (i) |
| Offline | golden replay passes with network off; zero non-local requests; backend-down queue flushes once | (j) |
| Triggers | auto and manual reach the same first screen | (a) |
| Alarm | 15 s no answer → alarm on every other tablet; first accept = Rescuer 1; race gives one Rescuer 1 | (b) |
