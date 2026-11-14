import type { Reading } from "../contracts";
import { indicatorLabel } from "../indicators";
import { StatusBadge } from "../status";

export function IndicatorTile({ reading }: { reading: Reading }) {
  const label = indicatorLabel(reading.indicator);
  return (
    <div role="group" aria-label={label} className="indicator-tile" data-status={reading.state}>
      <span className="indicator-tile__label">{label}</span>
      <span className="indicator-tile__value">
        {reading.value} <small>{reading.unit}</small>
      </span>
      <StatusBadge status={reading.state} />
    </div>
  );
}
