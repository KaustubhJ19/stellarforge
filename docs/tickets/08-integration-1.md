# 08: Integration #1

**What to build:** The full emergency flow runs end to end, offline, from a real replay file, with both triggers (auto-detect and manual), showing the cited protocol content. First golden tests lock it in.

**Blocked by:** 03. Also needs Spec 1 (contracts, replays) and Spec 4 (working emergency flow).

**Status:** ready-for-agent

- [x] A replay file goes in and the expected alerts, status and screens come out (backend: real crew B emergency replay -> Spec 3 emergency Alert, ACT NOW, verdict -> alarm -> record -> steps; browser screens not run)
- [x] Both triggers reach the guidance screens (auto from Spec 3 detection on the replay; manual press)
- [x] Works with the network off (only 127.0.0.1 is contacted; explainer off, "Why this step?" from recorded answers)
- [x] Golden tests cover both triggers and pass (tools/tests/test_integration_1.py, 5 passed on 3 runs)
- [x] Cross-stream contract mismatches found here are fixed or ticketed (profile fields, drug deny-list fixed; crew ids and a failing Spec 4 test noted in docs/notes-from-integration.md)
- [x] If it fails at H14: stop all P1 work and fix the P0 path first (it did not fail)

**Progress (2026-11-15):** Spec 5's side is done. Real protocols, role maps, excerpts, recorded answers, profile fields and the drug deny-list load in Spec 4's engine with 0 refused steps (tools/tests/test_spec4_handoff.py). Still needed: merge with Spec 4's branch, switch off the stubs, and run the end-to-end replay with both triggers.

**Done (2026-11-15):** merged Spec 4 (with Spec 2) and Spec 1's shared replays into this branch. Golden run on real content only: microgravity-cpr, mars_transit, replay/crew-records.json, replay/emergency-crew-B.json. Not run: the browser e2e (Playwright) tests. Spec 4's default protocol and profile are still the stubs (backend/app/runtime.py); set SF_PROTOCOL=microgravity-cpr and SF_PROFILE / DEFAULT_PROFILE=mars_transit to use the real ones.
