# Cut-offs that still need a value in `content/`

From the AI / detection lead (Spec 3), 2026-11-14. For the integration lead, who owns `content/`.

The detection code takes every cut-off below as an input, so no value is written into the code. Each one needs:
- a value;
- a source, or the label "team value" / "Earth reference, no space data";
- a home in `content/`.

**Suggested start** values are proposals only. Sources were checked on 2026-11-14; each row says **checked** or **not confirmed**. The tests currently use made-up test values.

## Open question: where do they go?

None of the formats in Spec 5 fits these cut-offs: protocols, measurement cards, mission profiles and Safety bounds. Proposal: one file, `content/profiles/detection-cut-offs.json`, with one entry per cut-off:

```json
{"name": "drift_amber", "value": 5, "unit": "CuSum level", "label": "team value", "source": "..."}
```

Any other place in `content/` works too; the backend only needs to know the path.

Note: AHA published 2025 guidelines (https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/algorithms). They are newer than the 2020 paper; prefer them once read.

## 1. Baseline A: drift and acute alerts (tickets 03, 04)

Code: `Thresholds` in `backend/baseline_a.py`.

| Name | Meaning | Unit | Suggested start | Possible source / label |
|---|---|---|---|---|
| `cusum_k` | Slack per Reading before the CuSum grows | Anchor sd | 0.5 | **Checked.** NIST/SEMATECH e-Handbook 6.3.2.3 (https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc323.htm): choose k as half the shift to detect, 0.5 for a 1-sd shift. Tune on replays (ticket 13). |
| `drift_amber` | CuSum level for an amber Drift alert | CuSum level | 4 | **Checked.** Same NIST page: h "around 4 or 5". Team value after tuning. |
| `drift_red` | CuSum level for a red Drift alert | CuSum level | 8 | Team value (twice amber) |
| `acute_amber` | Distance from the 28-day baseline for an amber Acute alert | sd (z) | 3 | **Checked.** NIST/SEMATECH e-Handbook 6.3.2 (https://www.itl.nist.gov/div898/handbook/pmc/section3/pmc32.htm): 3-sigma limits are "an accepted standard in industry" (manufacturing, not medicine). Team value. |
| `acute_red` | Same, for red | sd (z) | 4 | Team value |
| `min_window` | Readings needed before the 28-day baseline is trusted | Readings | 7 | Team value |
| Expected space shift | In-flight shift added to the Anchor, per Indicator | Indicator unit | 0 until known | "team value"; Spec 3 says there is no real source |
| Return-to-gravity shift | Expected shift after landing | bpm, mmHg | Resting HR 61.6 → 69.7 bpm; standing HR 76.4 → 99.8 bpm; standing systolic BP 118.8 → 105.8 mmHg | NASA Apollo AP005, Table 6, group means (Spec 3). Averages, not limits. **Not wired into the code yet.** |

Fixed by the spec, no decision needed: 28-day Adaptive baseline window and 24 h quarantine release (Spec 3, Baseline A).

## 2. Emergency auto-detect (ticket 05)

Code: `EmergencyThresholds` in `backend/emergency.py`. Spec 3 says to label these "Earth reference / team value".

| Name | Meaning | Unit | Suggested start | Possible source / label |
|---|---|---|---|---|
| `hr_high` | Heart rate counted as extremely high | bpm | 150 | **Not confirmed.** AHA 2020 Part 3 (Panchal et al., https://www.ahajournals.org/doi/10.1161/CIR.0000000000000916) only defines tachycardia as above 100/min; 150 is not in it. Check the AHA 2025 Adult Tachyarrhythmia algorithm (cpr.heart.org, PDF) before use. |
| `hr_low` | Heart rate counted as extremely low | bpm | 50 | **Not confirmed.** AHA 2020 Part 3 only defines bradycardia as below 60/min ("can be a normal finding, especially for athletes or during sleep"); 50 is not in it. Check the AHA 2025 Adult Bradycardia algorithm before use. |
| `sbp_low` | Systolic blood pressure counted as low | mmHg | 90 | **Checked, with a caveat.** AHA 2020 Part 3, post-arrest care: definitions of hypotension vary, systolic 90 mmHg is a common cutoff. Label "Earth reference, no space data". |
| `sustain_s` | How long the heart rate must stay extreme | seconds | 30 | Team value; tune on the Pulse replay |

Fixed by the spec, no decision needed: the rhythms VT, VF, PEA and asystole trigger at once (Spec 3, Auto-detect rule).

## 3. Likely causes (ticket 08)

Code: `likely_causes()` in `backend/baseline_a.py`.

| Name | Meaning | Unit | Suggested start | Possible source / label |
|---|---|---|---|---|
| `min_sigma` | Smallest distance from the Anchor that counts as a contributor | Anchor sd | 1 | Team value |

Fixed by the spec: at most 3 causes, each labelled "suggestion, not diagnosis".

## 4. Forecast B (ticket 11, P1)

Code: `forecast()` in `backend/forecast_b.py`.

| Name | Meaning | Unit | Suggested start | Possible source / label |
|---|---|---|---|---|
| `min_days` | Days of a person's own history before leaving "learning your pattern" | days | 7 | Team value. The held-out result (mean error 1.12, coverage 89.6 %) was measured with 7. |
| `remeasure_width` | Range wider than this shows "re-measure" | readiness points (0–10) | 6 | Team value. The average range on held-out people was 5.1 points, so 6 flags only the widest ones. |

Fixed by the spec: 90 % range (Spec 3, Testing Decisions) and the 0–10 readiness scale (PMData, verified in ticket 01).

## 5. Safety bounds (ticket 06)

Code: `status()` in `backend/baseline_a.py` takes one Safety bound per Indicator, in the Spec 5 shape:
- `indicator`, `low`, `high`, `label`, `source`;
- the label is "Earth reference, no space data", or a space or personal source.

This is Spec 5 task 5.6 (integration lead). Detection needs at least heart rate, systolic blood pressure, temperature and sleep. Without a bound, Status uses the baseline level only.
