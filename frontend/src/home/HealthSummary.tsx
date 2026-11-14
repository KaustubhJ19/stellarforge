import type { IndicatorId } from "../contracts";
import { HABITAT_INDICATORS, INDICATORS, byIndicatorOrder, type HealthKind } from "../indicators";
import type { ShownReading } from "../replay/state";
import { IndicatorTile } from "./IndicatorTile";

const TITLE: Record<HealthKind, string> = { physical: "Physical health", mental: "Mental health" };

/** One summary per kind of health; the two are never mixed. */
export function HealthSummary({
  kind,
  latest,
  onDetails,
}: {
  kind: HealthKind;
  latest: Map<IndicatorId, ShownReading>;
  onDetails?: (indicator: IndicatorId) => void;
}) {
  const readings = [...latest.values()]
    .filter((r) => (INDICATORS[r.indicator]?.kind ?? "physical") === kind && !HABITAT_INDICATORS.includes(r.indicator))
    .sort((a, b) => byIndicatorOrder(a.indicator, b.indicator));
  return (
    <section className="summary" aria-label={TITLE[kind]}>
      <h2>{TITLE[kind]}</h2>
      {readings.length === 0 ? (
        <p className="empty">No readings yet.</p>
      ) : (
        <div className="summary__tiles">
          {readings.map((r) => (
            <IndicatorTile
              key={r.indicator}
              reading={r}
              onDetails={onDetails && (() => onDetails(r.indicator))}
            />
          ))}
        </div>
      )}
    </section>
  );
}
