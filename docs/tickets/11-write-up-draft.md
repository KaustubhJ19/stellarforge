# 11: Write-up draft with limitations

**What to build:** A short write-up for the Project tab that explains the product, shows the accuracy and Credits pages, and states every limitation openly.

**Blocked by:** 07, 10. Also needs Spec 3's accuracy numbers.

**Status:** ready-for-agent

- [x] Explains the problem, the product and the Mars chest-pain story in plain words
- [x] Includes the accuracy page (measured on datasets, not astronauts) and the Credits
- [x] Lists all nine limitations from the spec (no hardware, no astronaut wearable stream, Pulse estimate not validated, CPR-only guidance, team-value shifts, Mars delay above 20 min, approximate female layers, laptop demo)
- [x] Links the HRP risk map
- [x] "Decision support, not diagnosis" stated

**Done (2026-11-15):** docs/write-up.md. tools/tests/test_write_up.py checks the nine limitations, the links, the disclaimer, accuracy numbers against docs/accuracy.md, HRP coverage against the risk map, the medical-review status and no drug or dose. Limitation 6 updated: body temperature now has a sourced in-flight shift (Stahn 2017). Still a draft: for the Project tab, paste and trim to the submission's length limit.
