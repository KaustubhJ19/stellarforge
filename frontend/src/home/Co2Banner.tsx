import type { IndicatorId } from "../contracts";
import type { ShownReading } from "../replay/state";
import { CO2_LIMIT } from "../teamValues";

const ppm = (n: number) => `${Math.round(n).toLocaleString("en-US")} ppm`;

/** A Watch banner while the latest cabin CO₂ Reading is over the limit, so the crew can act on the air. */
export function Co2Banner({ latest }: { latest: Map<IndicatorId, ShownReading> }) {
  const co2 = latest.get("cabin_co2");
  if (!co2 || co2.value <= CO2_LIMIT.ppm) return null;
  return (
    <section role="status" aria-label="Cabin CO₂" className="co2-banner" data-status="amber">
      <span className="status-badge" data-status="amber">
        <span className="status-badge__icon" data-testid="status-icon" aria-hidden="true">
          !
        </span>
      </span>
      <strong>Cabin CO₂ high: {ppm(co2.value)}</strong>
      <span className="co2-banner__limit">
        Limit {ppm(CO2_LIMIT.ppm)} ({CO2_LIMIT.label})
      </span>
    </section>
  );
}
