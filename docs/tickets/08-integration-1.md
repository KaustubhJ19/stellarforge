# 08: Integration #1

**What to build:** The full emergency flow runs end to end, offline, from a real replay file, with both triggers (auto-detect and manual), showing the cited protocol content. First golden tests lock it in.

**Blocked by:** 03. Also needs Spec 1 (contracts, replays) and Spec 4 (working emergency flow).

**Status:** ready-for-agent

- [ ] A replay file goes in and the expected alerts, status and screens come out
- [ ] Both triggers reach the guidance screens
- [ ] Works with the network off
- [ ] Golden tests cover both triggers and pass
- [ ] Cross-stream contract mismatches found here are fixed or ticketed
- [ ] If it fails at H14: stop all P1 work and fix the P0 path first
