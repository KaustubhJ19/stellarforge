import { useEffect, useId, useRef, useState, type FormEvent } from "react";
import type { CrewRecord, MissionTime, Reading } from "../contracts";
import { APOLLO_RETURN_SHIFT } from "../references";
import { FormDialog, problemsWith, readNumber, type NumberField } from "./FormDialog";
import { manualReading } from "./manualReading";
import { isNumeric } from "../replay/state";

/** The stand test's three measures, as Apollo AP005 reported them. */
const HEART: [number, number] = [20, 250];
const SYSTOLIC: [number, number] = [50, 250];
const MEASURES: (NumberField & { indicator: string; field: string; row: string })[] = [
  { indicator: "resting_heart_rate", field: "Lying heart rate (bpm)", row: "Lying heart rate", name: "lying heart rate", unit: "bpm", range: HEART },
  { indicator: "standing_heart_rate", field: "Standing heart rate (bpm)", row: "Standing heart rate", name: "standing heart rate", unit: "bpm", range: HEART },
  {
    indicator: "standing_systolic_bp",
    field: "Standing systolic blood pressure (mmHg)",
    row: "Standing systolic BP",
    name: "standing systolic blood pressure",
    unit: "mmHg",
    range: SYSTOLIC,
  },
];

const signed = (n: number) => `${n > 0 ? "+" : ""}${+n.toFixed(1)}`;

/**
 * Lying, then standing heart rate and standing systolic BP. Once saved, each value is set
 * against the astronaut's own pre-flight test first, then the Apollo group average shift.
 */
export function StandTestForm({
  crew,
  t,
  onSave,
  onClose,
}: {
  crew: CrewRecord;
  t: MissionTime;
  onSave: (readings: Reading[]) => void;
  onClose: () => void;
}) {
  const ids = useId();
  const [values, setValues] = useState<Record<string, string>>({});
  const [error, setError] = useState<string | null>(null);
  const [saved, setSaved] = useState<Reading[] | null>(null);
  const done = useRef<HTMLButtonElement>(null);
  // The Save button goes away on save; keep focus inside the dialog.
  useEffect(() => {
    if (saved) done.current?.focus();
  }, [saved]);

  function submit(e: FormEvent) {
    e.preventDefault();
    const read = MEASURES.map((m) => readNumber(values[m.indicator] ?? "", m));
    const problem = problemsWith(
      MEASURES.filter((_, i) => read[i] === "missing").map((m) => m.name),
      MEASURES.filter((_, i) => read[i] === "wrong"),
    );
    if (problem) return setError(problem);
    const readings = MEASURES.map((m, i) => manualReading(crew.id, m.indicator, read[i] as number, m.unit, t));
    setSaved(readings);
    onSave(readings);
  }

  return (
    <FormDialog title="Stand test" onClose={onClose}>
      {saved ? (
        <>
          <table className="form-results">
            <caption>Saved. How today compares</caption>
            <thead>
              <tr>
                <th scope="col">Measure</th>
                <th scope="col">Today</th>
                <th scope="col">Your pre-flight test</th>
                <th scope="col">Apollo crews after landing</th>
              </tr>
            </thead>
            <tbody>
              {MEASURES.map((m, i) => {
                const r = saved[i];
                if (!isNumeric(r)) return null;
                const value = r.value;
                const own = Object.hasOwn(crew.anchor, m.indicator) ? crew.anchor[m.indicator].mean : null;
                const apollo = APOLLO_RETURN_SHIFT.shift[m.indicator];
                return (
                  <tr key={m.indicator}>
                    <th scope="row">{m.row}</th>
                    <td>
                      {value} {m.unit}
                    </td>
                    <td>{own === null ? "No pre-flight test on record" : `${own} ${m.unit} (${signed(value - own)})`}</td>
                    <td>
                      {signed(apollo)} {m.unit}
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
          <p className="form-note">
            Apollo: change from before flight, {APOLLO_RETURN_SHIFT.label}. Source: {APOLLO_RETURN_SHIFT.source}
          </p>
          <button ref={done} className="form-submit" onClick={onClose}>
            Done
          </button>
        </>
      ) : (
        <form onSubmit={submit} noValidate>
          <p className="form-note">Lie still for 5 minutes, then stand for 3 minutes.</p>
          {MEASURES.map((m) => (
            <div className="form-field" key={m.indicator}>
              <label htmlFor={`${ids}-${m.indicator}`}>{m.field}</label>
              <input
                id={`${ids}-${m.indicator}`}
                inputMode="decimal"
                value={values[m.indicator] ?? ""}
                onChange={(e) => setValues((v) => ({ ...v, [m.indicator]: e.target.value }))}
              />
            </div>
          ))}
          {error && (
            <p role="alert" className="form-error">
              {error}
            </p>
          )}
          <button type="submit" className="form-submit">
            Save
          </button>
        </form>
      )}
    </FormDialog>
  );
}
