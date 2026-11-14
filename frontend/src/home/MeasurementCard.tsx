import { useEffect, useId, useRef } from "react";
import type { CardContent, Reading } from "../contracts";
import { formatValue, indicatorLabel } from "../indicators";
import { StatusBadge } from "../status";
import { Sparkline } from "../charts/Sparkline";

const SECTIONS = [
  ["how", "How it is measured"],
  ["why", "Why it matters"],
  ["ifAbnormal", "If abnormal"],
] as const;

/** One measurement: value, source, trend, and How / Why / If abnormal from content. */
export function MeasurementCard({
  reading,
  history,
  content,
  onClose,
}: {
  reading: Reading;
  history: Reading[];
  content?: CardContent;
  onClose: () => void;
}) {
  const label = indicatorLabel(reading.indicator);
  const shown = formatValue(reading.value, reading.unit);
  const close = useRef<HTMLButtonElement>(null);
  const ids = useId();
  useEffect(() => close.current?.focus(), []);

  return (
    <div className="card-backdrop" onClick={onClose}>
      <div
        className="card"
        role="dialog"
        aria-modal="true"
        aria-label={label}
        data-status={reading.state}
        onClick={(e) => e.stopPropagation()}
        onKeyDown={(e) => e.key === "Escape" && onClose()}
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
          <StatusBadge status={reading.state} />
          <Sparkline readings={history} />
        </div>
        <p className="card__source">Source: {reading.source}</p>
        {content?.labels?.map((l) => (
          <span key={l} className="card__label">
            {l}
          </span>
        ))}
        {SECTIONS.map(([key, heading]) => (
          <section key={key} className="card__section" aria-labelledby={`${ids}-${key}`}>
            <h3 id={`${ids}-${key}`}>{heading}</h3>
            {content?.[key] ? <p>{content[key]}</p> : <p className="empty">Not added yet.</p>}
          </section>
        ))}
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
