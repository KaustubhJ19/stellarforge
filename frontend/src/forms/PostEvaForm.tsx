import { useId, useState, type FormEvent } from "react";
import type { MissionTime, Reading } from "../contracts";
import { FormDialog, problemsWith, readNumber, type NumberField } from "./FormDialog";
import { manualReading } from "./manualReading";

type Question = readonly [id: string, label: string];

/** Common complaints after a spacewalk (Type I decompression sickness), asked as yes/no. */
const SYMPTOMS: Question[] = [
  ["hand_pain", "Hand or finger pain"],
  ["joint_pain", "Joint pain"],
  ["skin_irritation", "Skin itch or rash"],
  ["tingling", "Tingling"],
];

/**
 * NASA's Type II decompression sickness warning signs (OCHMO-TB-037 Rev D, p. 3), which need
 * immediate action: a Yes to any opens the emergency flow. Wording awaits the medical reviewer.
 */
const WARNING_SIGNS: Question[] = [
  ["numbness", "Numbness"],
  ["weakness", "Weakness"],
  ["confusion", "Confusion"],
  ["dizziness", "Dizziness or ear problems"],
  ["chest_or_breathing", "Chest pain or trouble breathing"],
];

const HEART_RATE: NumberField = { name: "heart rate", unit: "bpm", range: [20, 250] };

/**
 * Post-EVA check: heart rate, fatigue (1-5) and yes/no symptoms, logged as self-reports.
 * Every question needs an answer: a skipped symptom is not a "No". The heart rate is its own
 * Indicator, so a typed value never replaces the wearable's heart rate. A Yes to a warning sign
 * saves the check, then calls `onWarningSign` (the app opens Spec 4's emergency flow).
 */
export function PostEvaForm({
  crew,
  t,
  onSave,
  onClose,
  onWarningSign,
}: {
  crew: string;
  t: MissionTime;
  onSave: (readings: Reading[], note?: string) => void;
  onClose: () => void;
  onWarningSign: () => void;
}) {
  const ids = useId();
  const [heartRate, setHeartRate] = useState("");
  const [fatigue, setFatigue] = useState<number | null>(null);
  const [symptoms, setSymptoms] = useState<Record<string, boolean | undefined>>({});
  const [note, setNote] = useState("");
  const [error, setError] = useState<string | null>(null);

  function submit(e: FormEvent) {
    e.preventDefault();
    const hr = readNumber(heartRate, HEART_RATE);
    const missing = [
      hr === "missing" ? HEART_RATE.name : null,
      fatigue === null ? "fatigue" : null,
      ...[...SYMPTOMS, ...WARNING_SIGNS].filter(([id]) => symptoms[id] === undefined).map(([, label]) => label.toLowerCase()),
    ].filter((m): m is string => m !== null);
    const problem = problemsWith(missing, hr === "wrong" ? [HEART_RATE] : []);
    if (problem) return setError(problem);
    onSave(
      [
        manualReading(crew, "post_eva_heart_rate", hr as number, "bpm", t),
        manualReading(crew, "fatigue", fatigue!, "score 1-5", t),
        ...[...SYMPTOMS, ...WARNING_SIGNS].map(([id]) => manualReading(crew, id, symptoms[id] ? 1 : 0, "yes/no", t)),
      ],
      note.trim() || undefined,
    );
    onClose();
    if (WARNING_SIGNS.some(([id]) => symptoms[id])) onWarningSign();
  }

  const yesNo = ([id, label]: Question) => (
    <div className="form-field" key={id}>
      <span id={`${ids}-${id}`}>{label}</span>
      <div className="form-choices" role="radiogroup" aria-labelledby={`${ids}-${id}`}>
        {(["No", "Yes"] as const).map((answer) => (
          <label key={answer} className="form-choice">
            <input
              type="radio"
              name={`${ids}-${id}`}
              checked={symptoms[id] !== undefined && symptoms[id] === (answer === "Yes")}
              onChange={() => setSymptoms((s) => ({ ...s, [id]: answer === "Yes" }))}
            />
            {answer}
          </label>
        ))}
      </div>
    </div>
  );

  return (
    <FormDialog title="Post-EVA check" onClose={onClose}>
      <form onSubmit={submit} noValidate>
        <div className="form-field">
          <label htmlFor={`${ids}-hr`}>Heart rate (bpm)</label>
          <input id={`${ids}-hr`} inputMode="decimal" value={heartRate} onChange={(e) => setHeartRate(e.target.value)} />
        </div>
        <div className="form-field">
          <span id={`${ids}-fatigue`}>Fatigue (1 = fresh, 5 = exhausted)</span>
          <div className="form-choices" role="radiogroup" aria-labelledby={`${ids}-fatigue`}>
            {[1, 2, 3, 4, 5].map((n) => (
              <label key={n} className="form-choice">
                <input type="radio" name={`${ids}-fatigue`} checked={fatigue === n} onChange={() => setFatigue(n)} />
                {n}
              </label>
            ))}
          </div>
        </div>
        {SYMPTOMS.map(yesNo)}
        <fieldset className="form-warning">
          <legend>Warning signs</legend>
          <p className="form-warning__note">A Yes to any of these opens the emergency flow when you save.</p>
          {WARNING_SIGNS.map(yesNo)}
        </fieldset>
        <div className="form-field">
          <label htmlFor={`${ids}-note`}>Note (optional)</label>
          <textarea id={`${ids}-note`} rows={2} value={note} onChange={(e) => setNote(e.target.value)} />
        </div>
        {error && (
          <p role="alert" className="form-error">
            {error}
          </p>
        )}
        <button type="submit" className="form-submit">
          Save
        </button>
      </form>
    </FormDialog>
  );
}
