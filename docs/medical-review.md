# Medical review sign-off

Every protocol step and Safety bound in StellarForge, for a qualified clinician to check before submission (ticket 14).
The content linter proves each item is cited and free of drug names and doses. It does **not** prove the medicine is right. That is what this sheet is for.

**Scope:** weightless (spacecraft transit, station) only. Partial gravity (Moon base, Mars base, rover) is labelled "not covered by published guidance" in `content/protocols/coverage.json`.

**How to review:** for each row, tick OK or write the change needed. Check the step against its cited section, not against general practice.

## Reviewer

- Name:
- Qualification:
- Date:
- Signature or written confirmation:

If no qualified reviewer signs, the write-up must say: "Medical content not clinically reviewed."

## Protocol: CPR in microgravity (weightless only; see coverage.json for each environment)

File: `content/protocols/microgravity-cpr.json`

| Step | Text | Source | Rescuers | OK? | Change needed |
|---|---|---|---|---|---|
| `cpr-1-start` | Start CPR in a crewmember who appears to be in cardiac arrest, even if no defibrillator is available. | Hinkelbein J, et al; Defibrillation, Recommendation 14 | 1 | ☐ | |
| `cpr-2-er-compressions` | For initial Basic Life Support at the site of the emergency, apply the Evetts-Russomano (ER) method first. If you cannot give adequate chest compressions with ER, switch to the Reverse-Bear-Hug (RBH) method. | Hinkelbein J, et al; Results and recommendations, Recommendation 2 (one rescuer, no restraint, no equipment: rationale for Recommendation 1) | 1 | ☐ | |
| `cpr-3-hs-on-cmrs` | As soon as the patient is restrained on the Crew Medical Restraint System, give chest compressions with the Handstand method (HS), if the spacecraft dimensions and the rescuer's height allow it. | Hinkelbein J, et al; Results and recommendations, Recommendation 3 | 1 | ☐ | |
| `cpr-4-restrained-alternative` | If the HS method seems impossible, use restrained CPR in the standard or the straddling position. | Hinkelbein J, et al; Results and recommendations, Recommendation 4 | 1 | ☐ | |
| `cpr-5-accd` | An automated chest compression device could be used on a restrained patient, if available. Installing it should not delay high-quality chest compressions. | Hinkelbein J, et al; Results and recommendations, Recommendation 5 | 1 | ☐ | |
| `cpr-6-aed` | Use the AED only when the patient is restrained to an electrically isolated, safe surface such as the Crew Medical Restraint System. Use self-adhesive defibrillation pads. | Hinkelbein J, et al; Defibrillation, Recommendations 10 and 11 | 1 | ☐ | |
| `cpr-7-defibrillate` | Defibrillation should take place when appropriate, even if survival is likely to be reduced. | Hinkelbein J, et al; Defibrillation, Recommendation 15 | 1 | ☐ | |
| `cpr-8-airway-gate` | Manage the airway only if at least two rescuers are present and the patient has been restrained. | Hinkelbein J, et al; Abstract (Results) | 2 | ☐ | |
| `cpr-9-supraglottic` | If no rescuer with extensive training in tracheal intubation is present, use a second-generation supraglottic airway device for airway management. Keep a manual suction device ready. | Hinkelbein J, et al; Airway management, Recommendations 6 and 9 | 2 | ☐ | |
| `cpr-10-intubation` | Tracheal intubation remains the gold standard if a skilled provider performs it. Restrain patient and rescuer on the Crew Medical Restraint System during the attempt. Keep a manual suction device ready. | Hinkelbein J, et al; Airway management, Recommendations 7, 8 and 9 | 2 | ☐ | |
| `cpr-11-venous-access` | Attempt venous access only if more than two rescuers are present and high-quality CPR is being performed. Use a peripheral vein first; if that fails, use the intraosseous tibial route. | Hinkelbein J, et al; Intravenous access, Recommendations 16, 17 and 18 | 3 | ☐ | |
| `cpr-12-medication` | Medication: per flight surgeon / onboard medical checklist. | team rule (Spec 5): medication stays with the flight surgeon; protocols never name a drug or dose; Spec 5, Protocol content rules | 1 | ☐ | |
| `cpr-13-termination` | The crewmember with the highest medical qualification decides whether to stop resuscitation, after consulting telemedicine support. If telemedicine is unavailable or the time delay prevents prompt feedback, they decide alone. | Hinkelbein J, et al; Termination of CPR, Recommendation 22 | 1 | ☐ | |

## Protocol: Chest pain, before any collapse (crew-reported symptom)

File: `content/protocols/chest-pain.json`

| Step | Text | Source | Rescuers | OK? | Change needed |
|---|---|---|---|---|---|
| `cp-1-ecg` | Record an ECG immediately. | Byrne RA, Rossello X, et al. 2023 ESC Guidelines for the management of acute coronary syndromes. Eur Heart J. 2023;44(38):3720-3826. doi:10.1093/eurheartj/ehad191 (Earth reference, no space data); 3.2 Diagnostic tools, Electrocardiogram | 1 | ☐ | |
| `cp-2-defibrillator-ready` | Have defibrillation equipment ready: everyone caring for a patient with suspected acute coronary syndrome should have access to it. | Byrne RA, Rossello X, et al. 2023 ESC Guidelines for the management of acute coronary syndromes. Eur Heart J. 2023;44(38):3720-3826. doi:10.1093/eurheartj/ehad191 (Earth reference, no space data); 4.1 Pre-hospital logistics of care | 1 | ☐ | |
| `cp-3-restrain` | A defibrillator should only be used on a patient restrained to an electrically isolated, safe surface, such as the Crew Medical Restraint System. | Hinkelbein J, et al; Defibrillation, Recommendation 10 and its rationale | 1 | ☐ | |
| `cp-4-mission-control` | Inform Mission Control of the ongoing medical emergency. | Hinkelbein J, et al; Telemedicine, rationale for Recommendation 21 | 1 | ☐ | |
| `cp-5-medication` | Medication: per flight surgeon / onboard medical checklist. | team rule (Spec 5): medication stays with the flight surgeon; protocols never name a drug or dose; Spec 5, Protocol content rules | 1 | ☐ | |

## Safety bounds

File: `content/profiles/detection-cut-offs.json` (read by Spec 3 detection).

| Indicator | Low | High | Label | Source | OK? | Change needed |
|---|---|---|---|---|---|---|
| `heart_rate` | 50 | 150 | Earth reference, no space data | AHA 2025 Adult Bradycardia and Tachyarrhythmia With a Pulse Algorithms: https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/algorithms. Not used for resting_heart_rate: AHA notes a low rate can be normal in athletes, and one crew's normal is 49 bpm. | ☐ | |
| `systolic_bp` | 90 | None | Earth reference, no space data | AHA 2020 Part 3 (Panchal et al.): systolic 90 mmHg is a common hypotension cutoff. No upper limit sourced. https://www.ahajournals.org/doi/10.1161/CIR.0000000000000916 | ☐ | |
| `body_temperature` | 35.0 | 38.0 | low: NASA-STD-3001 (space standard); high: Earth reference, no space data | Low: NASA-STD-3001 Volume 1 Rev C, Definitions: hypothermia occurs as body temperature falls below 95 °F (35 °C). https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf High: CDC ill-traveler definitions (Fever): a measured temperature of 100.4 °F [38 °C] or greater. https://www.cdc.gov/quarantine/maritime/definitions-signs-symptoms-conditions-ill-travelers.html Caution: resting core temperature rose about 1 °C over 2.5 months of long-duration flight (Stahn 2017), so 38 °C may be reached by healthy crew in flight; see expected_shift. https://pmc.ncbi.nlm.nih.gov/articles/PMC5701078/ | ☐ | |

## Points to check first

- Rescuer counts of 1: the guideline names a single "rescuer" or gives no number for those steps.
- Chest-pain ECG and defibrillator steps come from an Earth guideline (ESC 2023), labelled "Earth reference, no space data".
- Glucose has no Safety bound (decision 2026-11-15): 7 of 28 Inspiration4 astronaut values (NASA OSDR OSD-575) fall below ADA's 70 mg/dL, minimum 36. Glucose uses the personal baseline only.
- Body temperature: in-flight resting core temperature rises about 1 °C (Stahn 2017), so the 38 °C Earth fever bound may fire on healthy crew. Detection applies a +1 °C expected shift.
- "Stop activity" was dropped from the chest-pain phase: no source found.
