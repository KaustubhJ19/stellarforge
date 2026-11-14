# 05: Safety bounds

**What to build:** Safety bounds for each Indicator that Spec 3 can use, each with an honest source label.

**Blocked by:** 02

**Status:** ready-for-agent

- [x] One bound per chosen Indicator: indicator, low, high, label, source. In Spec 3's detection-cut-offs.json: heart_rate, systolic_bp (Spec 3), glucose, body_temperature (added). Sleep and mood have no clinical bound
- [x] Label is either a space/personal source or "Earth reference, no space data"
- [x] In-flight shifts with no real source are labelled "team value" (expected_shift: team value, none applied)
- [x] Linter fails on any bound with no source
- [x] Linter green
- [x] Flagged for review by a qualified medical reviewer before submission (a green linter does not prove the content is medically correct). Flagged in the file's about text and the report; sign-off in ticket 14
