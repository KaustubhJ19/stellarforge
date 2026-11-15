import type { Step } from "./api";

/**
 * One protocol step, laid out to act on: where you are, the step exactly as published, what it needs,
 * and its source. Layout only: the step text and equipment names are shown verbatim, never reworded.
 */
export function StepCard({ index, total, step }: { index: number; total: number; step: Pick<Step, "text" | "source"> & Partial<Pick<Step, "equipment" | "rescuers">> }) {
  const equipment = step.equipment ?? [];
  const rescuers = step.rescuers ?? 0;
  return (
    <>
      <div className="stepper" role="progressbar" aria-label={`Step ${index} of ${total}`} aria-valuemin={1} aria-valuemax={total} aria-valuenow={index}>
        {Array.from({ length: total }, (_, i) => (
          <span key={i} data-state={i + 1 < index ? "done" : i + 1 === index ? "now" : "next"} aria-hidden="true" />
        ))}
      </div>
      <div className="step-card">
        <span className="step-num" aria-hidden="true">
          {index}
        </span>
        <p className="step-text" data-testid="step-text">
          {step.text}
        </p>
      </div>
      {(rescuers > 0 || equipment.length > 0) && (
        <ul className="step-meta" aria-label="Needs">
          <li className="step-meta__title">Needs</li>
          {rescuers > 0 && <li>{rescuers === 1 ? "1 rescuer" : `${rescuers} rescuers`}</li>}
          {equipment.map((e) => (
            <li key={e}>{e}</li>
          ))}
        </ul>
      )}
      <p className="source" data-testid="step-source">
        Source: {step.source.guideline}, section {step.source.section}
      </p>
    </>
  );
}
