import type { IndicatorId, Reading } from "../contracts";
import { indicatorLabel } from "../indicators";
import { StatusBadge } from "../status";
import { insightStructures } from "./buildView";

/** Flagged Indicators (amber or red) that can be shown on the body. */
export function FlaggedList({
  latest,
  onShow,
}: {
  latest: Map<IndicatorId, Reading>;
  onShow: (indicator: IndicatorId) => void;
}) {
  const flagged = [...latest.values()].filter(
    (r) => r.state !== "green" && insightStructures(r.indicator).length > 0,
  );
  if (flagged.length === 0) return null;
  return (
    <div className="flagged" role="group" aria-label="Flagged on the body">
      {flagged.map((r) => {
        const label = indicatorLabel(r.indicator);
        return (
          <button
            key={r.indicator}
            className="flagged__item"
            data-status={r.state}
            aria-label={`Show ${label.toLowerCase()} on body`}
            onClick={() => onShow(r.indicator)}
          >
            <span>{label}</span>
            <StatusBadge status={r.state} />
          </button>
        );
      })}
    </div>
  );
}

export function InsightBanner({ reading, onExit }: { reading: Reading; onExit: () => void }) {
  const title = `Insight: ${indicatorLabel(reading.indicator)}`;
  return (
    <section className="insight-banner" aria-label={title}>
      <h2>{title}</h2>
      <StatusBadge status={reading.state} />
      <button onClick={onExit}>Exit insight</button>
    </section>
  );
}
