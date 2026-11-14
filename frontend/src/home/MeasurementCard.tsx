import { useEffect, useId, useRef } from "react";
import type { CardContent } from "../contracts";
import type { ShownReading } from "../replay/state";
import { formatValue, indicatorLabel, sourceLabel } from "../indicators";
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
  reading: ShownReading;
  history: ShownReading[];
  content?: CardContent;
  onClose: () => void;
}) {
  const label = indicatorLabel(reading.indicator);
  const shown = formatValue(reading.value, reading.unit);
  const close = useRef<HTMLButtonElement>(null);
  const dialog = useRef<HTMLDivElement>(null);
  const ids = useId();

  // Modal: focus starts on Close, Tab stays inside, Escape closes, focus goes back on close.
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    close.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !dialog.current) return;
      const focusable = dialog.current.querySelectorAll<HTMLElement>(
        "button, [href], input, select, textarea, [tabindex]:not([tabindex='-1'])",
      );
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      opener?.focus();
    };
  }, [onClose]);

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
