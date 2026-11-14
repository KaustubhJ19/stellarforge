# 04: Mars transit mission profile

**What to build:** A Mars transit Mission profile that Spec 2 can show, with every value either sourced or honestly labelled. Starting values: gravity, radiation about 1.8 mSv/day, comm delay 28.5 min one way, no evacuation, medical and exercise kit not confirmed, crew 4, about 3 years.

**Blocked by:** 02

**Status:** ready-for-agent

- [x] Profile file has every field in the agreed Mission profile shape (Spec 5 fields plus name; Spec 2's frontend assumes {id, name, groundDelayMin} and id mars-transit: flagged to Spec 2)
- [x] Each value is marked sourced (with link) or "not confirmed: team value"
- [x] The 28.5 min delay is labelled a team value that exceeds NASA's stated 20 min maximum
- [x] Linter rule added: fails on any profile value that is neither sourced nor labelled (test d)
- [x] Linter green
- [ ] (P1) Station, Moon base, Mars base and rover profiles only if time allows. Not done
