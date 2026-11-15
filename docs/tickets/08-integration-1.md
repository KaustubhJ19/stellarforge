# 08: Integration #1

**What to build:** The full emergency flow runs end to end, offline, from a real replay file, with both triggers (auto-detect and manual), showing the cited protocol content. First golden tests lock it in.

**Blocked by:** 03. Also needs Spec 1 (contracts, replays) and Spec 4 (working emergency flow).

**Status:** ready-for-agent

- [x] A replay file goes in and the expected alerts, status and screens come out (backend: real crew B emergency replay -> Spec 3 emergency Alert, ACT NOW, verdict -> alarm -> record -> steps; browser: real steps and citations render, see below)
- [x] Both triggers reach the guidance screens (auto from Spec 3 detection on the replay; manual press)
- [x] Works with the network off (only 127.0.0.1 is contacted; explainer off, "Why this step?" from recorded answers)
- [x] Golden tests cover both triggers and pass (tools/tests/test_integration_1.py, 5 passed on 3 runs)
- [x] Cross-stream contract mismatches found here are fixed or ticketed (profile fields, drug deny-list fixed; crew ids and a failing Spec 4 test noted in docs/notes-from-integration.md)
- [x] If it fails at H14: stop all P1 work and fix the P0 path first (it did not fail)

**Progress (2026-11-15):** Spec 5's side is done. Real protocols, role maps, excerpts, recorded answers, profile fields and the drug deny-list load in Spec 4's engine with 0 refused steps (tools/tests/test_spec4_handoff.py). Still needed: merge with Spec 4's branch, switch off the stubs, and run the end-to-end replay with both triggers.

**Done (2026-11-15):** merged Spec 4 (with Spec 2) and Spec 1's shared replays into this branch. Golden run on real content only: microgravity-cpr, mars_transit, replay/crew-records.json, replay/emergency-crew-B.json. Browser e2e (Playwright) run on 2026-11-15, see the note below. Spec 4's default protocol and profile are still the stubs (backend/app/runtime.py); set SF_PROTOCOL=microgravity-cpr and SF_PROFILE / DEFAULT_PROFILE=mars_transit to use the real ones.

**Browser run (2026-11-15, macOS, Chromium):**
- **As committed (stub content):** `tsc` clean; vitest 201 passed; Playwright 37 passed (home 33, emergency 4).
- **With the real protocol, profile and crew** (`SF_PROTOCOL=microgravity-cpr`, `SF_PROFILE=mars_transit`, `replay/crew-records.json`), on a scratch copy of the e2e specs with the crew ids mapped (cmdr→B, eng→A, sci→C):
  - The auto Trigger reaches the first screen: passed.
  - The golden UI run shows the real first step and its Hinkelbein citation. It then fails on the stub's own texts ("STUB step 1", "STUB-S2").
  - Offline, the tablet walks the real protocol ("Step 3 of 9 (offline)", with citation and "Why this step?"). The test then waits for the stub's "End offline session" after 3 steps and times out.
  - The glove check fails on real UI: a home "Head" zoom button is 56 px, below the 64 px team value.
- **For Spec 4:** the e2e specs are written for the stub (crew `cmdr`/`eng`/`sci`, "STUB" texts, 3 steps). Point them at the real content before the demo.
