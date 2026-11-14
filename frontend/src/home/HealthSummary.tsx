import type { IndicatorId, Reading } from "../contracts";
import { INDICATORS, byIndicatorOrder, type HealthKind } from "../indicators";
import { IndicatorTile } from "./IndicatorTile";

const TITLE: Record<HealthKind, string> = { physical: "Physical health", mental: "Mental health" };
/** Shown in the mission bar instead. */
const IN_MISSION_BAR: IndicatorId[] = ["radiation_dose"];

/** One summary per kind of health; the two are never mixed. */
export function HealthSummary({
  kind,
  latest,
  onDetails,
}: {
  kind: HealthKind;
  latest: Map<IndicatorId, Reading>;
  onDetails?: (indicator: IndicatorId) => void;
}) {
  const readings = [...latest.values()]
    .filter((r) => (INDICATORS[r.indicator]?.kind ?? "physical") === kind && !IN_MISSION_BAR.includes(r.indicator))
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
