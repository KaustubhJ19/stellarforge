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

## Protocol library review sheets (Spec 1)

Each library protocol has a side-by-side review sheet (draft step next to the guideline quote it cites), generated by `tools/review_sheet.py` into [`docs/review/`](review/):

- [CPR in microgravity](review/microgravity-cpr.md)
- [Chest pain](review/chest-pain.md)
- [Sepsis / severe infection](review/sepsis.md) (Earth reference)
- [Fainting / feeling faint](review/fainting.md) (Earth reference)
- [Low blood sugar](review/low-blood-sugar.md) (Earth reference)
- [Severe bleeding](review/severe-bleeding.md) (Earth reference)
- [Head injury: concussion](review/head-injury.md) (Earth reference)
- [Overheating: heat stroke](review/overheating.md) (Earth reference)
- [Cabin air: low oxygen](review/cabin-air.md) (Earth reference)

New collapse protocols (see [`docs/protocol-library.md`](protocol-library.md)) add a sheet here when their evidence pack and drafts are ready for review. Approval of a step (`tools/approve_steps.py`) is a team member's act; this clinician sheet is a separate, later check.

## Safety bounds

File: `content/profiles/detection-cut-offs.json` (read by Spec 3 detection).

| Indicator | Low | High | Label | Source | OK? | Change needed |
|---|---|---|---|---|---|---|
| `heart_rate` | 50 | 150 | Earth reference, no space data | AHA 2025 Adult Bradycardia and Tachyarrhythmia With a Pulse Algorithms: https://cpr.heart.org/en/resuscitation-science/cpr-and-ecc-guidelines/algorithms. Not used for resting_heart_rate: AHA notes a low rate can be normal in athletes, and one crew's normal is 49 bpm. | ☐ | |
| `systolic_bp` | 90 | None | Earth reference, no space data | AHA 2020 Part 3 (Panchal et al.): systolic 90 mmHg is a common hypotension cutoff. No upper limit sourced. https://www.ahajournals.org/doi/10.1161/CIR.0000000000000916 | ☐ | |
| `glucose` | 54 | 250 | Earth reference, no space data | ADA Standards of Care in Diabetes 2025, Section 6, Table 6.2 (CGM metrics): TBR <54 mg/dL is level 2 hypoglycemia; TAR >250 mg/dL is level 2 hyperglycemia. Diabetes-care limits, used with the personal baseline. Real astronaut data: 3 of 28 Inspiration4 values (NASA OSDR OSD-575) are below 54 mg/dL, all at R+45. https://pmc.ncbi.nlm.nih.gov/articles/PMC11635034/ https://osdr.nasa.gov/bio/repo/data/studies/OSD-575 | ☐ | |
| `body_temperature` | 35.0 | 38.0 | low: NASA-STD-3001 (space standard); high: Earth reference, no space data | Low: NASA-STD-3001 Volume 1 Rev C, Definitions: hypothermia occurs as body temperature falls below 95 °F (35 °C). https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf High: CDC ill-traveler definitions (Fever): a measured temperature of 100.4 °F [38 °C] or greater. https://www.cdc.gov/quarantine/maritime/definitions-signs-symptoms-conditions-ill-travelers.html Caution: resting core temperature rose about 1 °C over 2.5 months of long-duration flight (Stahn 2017), so 38 °C may be reached by healthy crew in flight; see expected_shift. https://pmc.ncbi.nlm.nih.gov/articles/PMC5701078/ | ☐ | |

## Measurement cards

Files: `content/cards/*.json`. Check the Why, the if-abnormal steps and the space note.

| Card | HRP risk | If abnormal (now) | Space note | OK? | Change needed |
|---|---|---|---|---|---|
| card `body_temperature` | uncovered | Check the thermometer and that the crewmember is at rest. | Resting core temperature rose about 1 °C over 2.5 months of long-duration flight (Stahn 2017), so detection expects +1 °C. Safety bound 35 to 38 °C: below 35 °C is hypothermia (NASA-STD-3001); 38 °C is the CDC fever definition (Earth reference, no space data). | ☐ | |
| card `glucose` | uncovered | Check the sample and the analyser. Compare with the crewmember's own normal. | Safety bound 54 to 250 mg/dL: ADA level 2 limits (Table 6.2), an Earth reference, no space data. Inspiration4 astronauts (NASA OSDR OSD-575) had 3 of 28 values below 54 mg/dL, all 45 days after return. | ☐ | |
| card `heart_rate` | Risk of Cardiovascular Adaptations | Check the sensor is worn correctly. If the crewmember is unresponsive, start the CPR protocol. If they report chest pain, start the chest-pain protocol. | After landing, Apollo crews' average resting heart rate was 8.1 bpm higher than before flight (61.6 to 69.7), and standing heart rate 23.4 bpm higher. Safety bound 50 to 150 bpm is an Earth reference, no space data (AHA 2025). | ☐ | |
| card `mood` | Risk of Behavioral Changes and Psychiatric Disorders | Talk with the crewmember privately. | A 1 to 5 self-rating has no clinical limit, so mood has no Safety bound and is judged against the crewmember's own normal. Normal-day data come from Earth wearable users (PMData), not astronauts. | ☐ | |
| card `sleep_duration` | Risk of Inadequate Sleep and Irregular Schedules | Compare with the crewmember's own normal, not with one night. | NASA schedules an 8.5 hour sleep period (NASA-STD-3001 [V1 6001]). ISS crews actually slept about 6.1 hours a night in flight (Barger 2014). On Earth, adults need 7 or more hours (AASM). No Safety bound: judged against the personal baseline only. | ☐ | |
| card `systolic_bp` | Risk of Cardiovascular Adaptations | Check the cuff size and position. If the crewmember is unresponsive, start the CPR protocol. | After landing, Apollo crews' average standing systolic pressure was 13 mmHg lower than before flight (118.8 to 105.8). Safety bound: systolic below 90 mmHg, an Earth reference, no space data (AHA 2020); no upper limit sourced. | ☐ | |

## Recorded "Why this step?" answers

Files: `content/protocols/<id>.recorded.json`. Written by the team from the cited excerpts (`<id>.excerpts.json`); shown when the explainer is off.

| Step | Recorded answer | OK? | Change needed |
|---|---|---|---|
| recorded `cpr-1-start` | The guideline says to start CPR in anyone who appears to be in cardiac arrest, even when no defibrillator is on board. Survival is unlikely without defibrillation, but starting CPR is still recommended. | ☐ | |
| recorded `cpr-2-er-compressions` | The Evetts-Russomano method needs no restraint and no equipment, so one rescuer can start at once, wherever the crewmember is. It also lets a third person move patient and rescuer while compressions continue. If you cannot give adequate compressions with it, switch to the Reverse-Bear-Hug method. | ☐ | |
| recorded `cpr-3-hs-on-cmrs` | Once the patient is restrained on the Crew Medical Restraint System, the Handstand method gives the best compressions in weightlessness, if the spacecraft and your height allow it. | ☐ | |
| recorded `cpr-4-restrained-alternative` | If the Handstand method is not possible, the guideline recommends restrained CPR in the standard or straddling position instead. | ☐ | |
| recorded `cpr-5-accd` | An automated compression device may help on a restrained patient, but only if one is available, and setting it up must not delay good compressions. | ☐ | |
| recorded `cpr-6-aed` | A defibrillator should only be used on a patient restrained to an electrically isolated, safe surface, such as the restraint system. Self-adhesive pads keep your hands free. | ☐ | |
| recorded `cpr-7-defibrillate` | The guideline says to defibrillate when appropriate, even though survival is likely to be lower in space. | ☐ | |
| recorded `cpr-8-airway-gate` | Airway management needs at least two rescuers and a restrained patient, so compressions can continue while the airway is handled. | ☐ | |
| recorded `cpr-9-supraglottic` | Without a rescuer trained in tracheal intubation, a second-generation supraglottic airway device is recommended. Keep the manual suction device ready during airway management. | ☐ | |
| recorded `cpr-10-intubation` | Tracheal intubation is the gold standard when a skilled provider does it, with patient and rescuer restrained on the restraint system. | ☐ | |
| recorded `cpr-11-venous-access` | Venous access is only attempted when more than two rescuers are present and good CPR is under way. If a vein cannot be used, the intraosseous route at the shin is next. | ☐ | |
| recorded `cpr-12-medication` | This tool never names a drug or a dose. Any medication is decided by the flight surgeon or the onboard medical checklist. | ☐ | |
| recorded `cpr-13-termination` | The crewmember with the highest medical qualification decides whether to stop, after talking with the ground if possible. If the delay is too long, they decide alone. | ☐ | |
| recorded `cp-1-ecg` | An Earth guideline for suspected heart attack recommends recording an ECG straight away. There is no space-specific guidance for this step. | ☐ | |
| recorded `cp-2-defibrillator-ready` | The same Earth guideline says everyone caring for a suspected heart attack should have a defibrillator to hand. | ☐ | |
| recorded `cp-3-restrain` | If a shock is needed, the defibrillator may only be used on a patient restrained to an electrically isolated, safe surface, so restrain early. | ☐ | |
| recorded `cp-4-mission-control` | The crew must tell Mission Control about an ongoing medical emergency. On a Mars mission the reply is delayed, so the crew does not wait for it. | ☐ | |
| recorded `cp-5-medication` | This tool never names a drug or a dose. Any medication is decided by the flight surgeon or the onboard medical checklist. | ☐ | |

## Points to check first

- Rescuer counts of 1: the guideline names a single "rescuer" or gives no number for those steps.
- Chest-pain ECG and defibrillator steps come from an Earth guideline (ESC 2023), labelled "Earth reference, no space data".
- Glucose: personal baseline plus an ADA level 2 Safety bound (54-250 mg/dL), decision 2026-11-15. Level 1 (70) would fire on 7 of 28 Inspiration4 values (OSD-575); level 2 fires on 3, all at R+45 (36, 43, 44 mg/dL).
- Body temperature: in-flight resting core temperature rises about 1 °C (Stahn 2017), so the 38 °C Earth fever bound may fire on healthy crew. Detection applies a +1 °C expected shift.
- "Stop activity" was dropped from the chest-pain phase: no source found.
- Card Why texts summarise NASA's HRP risk descriptions in plain words; only part of each is quoted verbatim.
- Rescuer 1 / Rescuer 2 role split (`<id>.roles.json`) is a team value; the guideline does not assign roles.
