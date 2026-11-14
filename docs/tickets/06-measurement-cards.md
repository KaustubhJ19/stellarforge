# 06: Measurement cards

**What to build:** An astronaut who is not a doctor opens a card for heart rate, blood pressure, sleep, glucose, temperature or mood and learns how to measure it, why it matters in space (in NASA HRP terms), and what to do if it is abnormal.

**Blocked by:** 02. Card layout agreed with Spec 2.

**Status:** ready-for-agent

- [x] One card per chosen Indicator: how[], why{text, hrp_risk, source}, if_abnormal{now, remeasure, tell_crew, tell_ground}, unit, space_note. Six cards in content/cards/ (plus labels and sources). Spec 2's frontend assumes flat strings (how, why, ifAbnormal): flagged to Spec 2
- [x] Every Why names an HRP risk, or is flagged as uncovered (glucose and body_temperature are uncovered, with a reason)
- [x] Linter rule added for the HRP risk check (test c)
- [x] No drug name or dose on any card
- [x] Linter green
- [x] Flagged for review by a qualified medical reviewer before submission (a green linter does not prove the content is medically correct). Cards added to docs/medical-review.md

**Sources ready for the sleep card** (found in ticket 05; no hard Safety bound for sleep, because 7 h would flag most ISS nights):
- NASA-STD-3001 Vol 1 Rev C, [V1 6001] rationale: recommended 8.5 hr sleep period. https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf
- Barger LK et al. Lancet Neurol 2014;13(9):904-12 (PMID 25127232): ISS crews obtained 6.09 h of sleep per night in flight (actigraphy, 21 astronauts, 3248 in-flight days). https://pubmed.ncbi.nlm.nih.gov/25127232/
- Watson NF et al. J Clin Sleep Med 2015;11(6):591-2 (AASM/SRS): adults should sleep 7 or more hours per night on a regular basis (Earth reference). https://pmc.ncbi.nlm.nih.gov/articles/PMC4442216/

**Sources ready for the glucose card** (later decision 2026-11-15: personal baseline plus ADA level 2 Safety bound 54-250 mg/dL):
- ADA Standards of Care 2025, Section 6: Level 1 hypoglycemia <70 mg/dL (diabetes care). https://pmc.ncbi.nlm.nih.gov/articles/PMC11635034/
- ADA Standards of Care 2025, Section 2: random plasma glucose >=200 mg/dL with classic symptoms meets diabetes diagnosis criteria. https://pmc.ncbi.nlm.nih.gov/articles/PMC11635041/
- NASA OSDR OSD-575 (Inspiration4 CMP): 7 of 28 astronaut values below 70 mg/dL; lab reference range 65-99 mg/dL. https://osdr.nasa.gov/bio/repo/data/studies/OSD-575
