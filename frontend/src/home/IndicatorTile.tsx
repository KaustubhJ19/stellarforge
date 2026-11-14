import type { Reading } from "../contracts";
import { indicatorLabel } from "../indicators";
import { StatusBadge } from "../status";

export function IndicatorTile({ reading, onDetails }: { reading: Reading; onDetails?: () => void }) {
  const label = indicatorLabel(reading.indicator);
  return (
    <div role="group" aria-label={label} className="indicator-tile" data-status={reading.state}>
      <span className="indicator-tile__label">{label}</span>
      <span className="indicator-tile__value">
        {reading.value} <small>{reading.unit}</small>
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
