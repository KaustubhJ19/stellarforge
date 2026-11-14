import type { Reading } from "../contracts";
import { formatValue, indicatorLabel } from "../indicators";
import { StatusBadge } from "../status";

export function IndicatorTile({ reading, onDetails }: { reading: Reading; onDetails?: () => void }) {
  const label = indicatorLabel(reading.indicator);
  const shown = formatValue(reading.value, reading.unit);
  return (
    <div role="group" aria-label={label} className="indicator-tile" data-status={reading.state}>
      <span className="indicator-tile__label">{label}</span>
      <span className="indicator-tile__value">
        {shown.value} <small>{shown.unit}</small>
      </span>
      <StatusBadge status={reading.state} />
      {onDetails && (
        <button className="indicator-tile__details" aria-label={`${label} details`} onClick={onDetails}>
          Details
        </button>
      )}
    </div>
  );
}
