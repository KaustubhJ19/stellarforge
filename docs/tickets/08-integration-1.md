# 08: Integration #1

**What to build:** The full emergency flow runs end to end, offline, from a real replay file, with both triggers (auto-detect and manual), showing the cited protocol content. First golden tests lock it in.

**Blocked by:** 03. Also needs Spec 1 (contracts, replays) and Spec 4 (working emergency flow).

**Status:** ready-for-agent

- [ ] A replay file goes in and the expected alerts, status and screens come out
- [ ] Both triggers reach the guidance screens
- [ ] Works with the network off
- [ ] Golden tests cover both triggers and pass
- [x] Cross-stream contract mismatches found here are fixed or ticketed (profile fields, drug deny-list fixed; crew ids and a failing Spec 4 test noted in docs/notes-from-integration.md)
- [ ] If it fails at H14: stop all P1 work and fix the P0 path first

**Progress (2026-11-15):** Spec 5's side is done. Real protocols, role maps, excerpts, recorded answers, profile fields and the drug deny-list load in Spec 4's engine with 0 refused steps (tools/tests/test_spec4_handoff.py). Still needed: merge with Spec 4's branch, switch off the stubs, and run the end-to-end replay with both triggers.
