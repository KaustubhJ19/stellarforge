import { useId, useRef, type ReactNode } from "react";
import { useModal } from "./useModal";
import type { CardContent } from "../contracts";
import type { NumericReading, ShownReading } from "../replay/state";
import { INDICATORS, formatValue, indicatorLabel, sourceLabel } from "../indicators";
import { StatusBadge } from "../status";
import { Sparkline } from "../charts/Sparkline";

const STEPS = [
  ["now", "Now"],
  ["remeasure", "Measure again"],
  ["tell_crew", "Tell the crew"],
  ["tell_ground", "Tell the ground"],
] as const;

/** One card section as a dropdown; "Not added yet." until Spec 5 writes it. */
function Section({ id, heading, open = false, children }: { id: string; heading: string; open?: boolean; children?: ReactNode }) {
  return (
    <section className="card__section" aria-labelledby={id}>
      <details className="fold" open={open}>
        <summary id={id}>{heading}</summary>
        <div className="fold__body">{children ?? <p className="empty">Not added yet.</p>}</div>
      </details>
    </section>
  );
}

/** One measurement: value, source, trend, and How / Why / If abnormal from content. */
export function MeasurementCard({
  reading,
  history,
  content,
  onClose,
}: {
  reading: ShownReading;
  history: NumericReading[];
  content?: CardContent;
  onClose: () => void;
}) {
  const label = indicatorLabel(reading.indicator);
  const shown = formatValue(reading.value, reading.unit);
  const close = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const ids = useId();

  useModal(dialog, close, onClose);

  return (
    <div className="card-backdrop" onClick={onClose}>
      <div
        className="card"
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label={label}
        data-status={reading.status}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="card__head">
          <h2>{label}</h2>
          <button ref={close} onClick={onClose}>
            Close
          </button>
        </header>
        <div className="card__value">
          <span className="card__number">
            {shown.value} {shown.unit}
          </span>
          <StatusBadge status={reading.status} />
          <Sparkline readings={history} />
        </div>
        <p className="card__source">Source: {sourceLabel(reading.source)}</p>
        {INDICATORS[reading.indicator]?.note && <span className="card__label">{INDICATORS[reading.indicator].note}</span>}
        {content?.labels?.map((l) => (
          <span key={l} className="card__label">
            {l}
          </span>
        ))}
        <Section id={`${ids}-how`} heading="How it is measured">
          {content?.how?.length ? (
            <ol className="card__steps">
              {content.how.map((step, i) => (
                <li key={i}>{step}</li>
              ))}
            </ol>
          ) : undefined}
        </Section>
        <Section id={`${ids}-why`} heading="Why it matters">
          {content?.why ? (
            <>
              <p>{content.why.text}</p>
              {content.why.hrp_risk && (
                <p>
                  <strong>NASA HRP risk:</strong>{" "}
                  {content.why.hrp_risk === "uncovered"
                    ? `not covered. ${content.why.uncovered_reason ?? ""}`.trim()
                    : content.why.hrp_risk}
                </p>
              )}
              {content.why.source && (
                <p className="card__source">
                  Source: <a href={content.why.source}>{content.why.source}</a>
                </p>
              )}
              {content.space_note && (
                <p>
                  <strong>In space:</strong> {content.space_note}
                </p>
              )}
            </>
          ) : undefined}
        </Section>
        <Section id={`${ids}-abnormal`} heading="If abnormal" open={reading.status !== "green"}>
          {content?.if_abnormal ? (
            <dl className="card__abnormal">
              {STEPS.filter(([key]) => content.if_abnormal?.[key]).map(([key, label]) => (
                <div key={key}>
                  <dt>{label}</dt>
                  <dd>{content.if_abnormal![key]}</dd>
                </div>
              ))}
            </dl>
          ) : undefined}
        </Section>
        {content?.sources?.length ? (
          <footer className="card__sources">
            <h3>Sources</h3>
            <ul>
              {content.sources.map((s) => (
                <li key={s}>{s}</li>
              ))}
            </ul>
          </footer>
        ) : null}
      </div>
    </div>
  );
}
