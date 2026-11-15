import type { NumericReading, ShownReading } from "../replay/state";
import { INDICATORS, formatValue, indicatorLabel } from "../indicators";
import { Sparkline } from "../charts/Sparkline";
import { StatusBadge } from "../status";

export function IndicatorTile({
  reading,
  history = [],
  onDetails,
}: {
  reading: ShownReading;
  /** Recent Readings up to the scrubbed time, drawn as a mini chart. */
  history?: NumericReading[];
  onDetails?: () => void;
}) {
  const label = indicatorLabel(reading.indicator);
  const shown = formatValue(reading.value, reading.unit);
  return (
    <div role="group" aria-label={label} className="indicator-tile" data-status={reading.status}>
      <span className="indicator-tile__label">{label}</span>
      <span className="indicator-tile__value">
        {shown.value} <small>{shown.unit}</small>
      </span>
      {history.length > 1 && (
        <span className="indicator-tile__spark">
          <Sparkline readings={history} />
        </span>
      )}
      <StatusBadge status={reading.status} />
      {INDICATORS[reading.indicator]?.note && <span className="card__label">{INDICATORS[reading.indicator].note}</span>}
      {onDetails && (
        <button className="indicator-tile__details" aria-label={`${label} details`} onClick={onDetails}>
          Details
        </button>
      )}
    </div>
  );
}
