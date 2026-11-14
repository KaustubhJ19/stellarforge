# 02: Content linter and first cited CPR step

**What to build:** One real protocol step from Hinkelbein et al. 2020 (microgravity CPR guideline) lives in the content folder in the `Protocol` shape, and a content linter checks it. This is the tracer bullet the later content tickets extend.

**Blocked by:** None (can start immediately). Needs the `Protocol` contract from Spec 1, frozen at H2.

**Status:** ready-for-agent

- [x] One CPR step (e.g. "no response → start compressions") stored with `source{guideline, section}`, equipment and rescuers
- [x] The linter passes on that file
- [x] The linter fails on a protocol step or threshold with no source (test a). Protocol steps only for now; thresholds get this rule in ticket 05, when their content exists
- [x] The linter fails on any drug name or dose in protocol content (test b)
- [x] Linter runs with one command and exits non-zero on failure
