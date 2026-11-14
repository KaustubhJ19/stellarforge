import type { IndicatorId, MissionTime } from "../contracts";
import { isNumeric, type ShownReading } from "../replay/state";
import { CO2_LIMIT } from "../teamValues";

const ppm = (n: number) => `${Math.round(n).toLocaleString("en-US")} ppm`;

/**
 * The real cabin replay (RR-1) samples CO₂ every 5 minutes; a Reading older than an hour is
 * not "now". A cabin source sampling less often than hourly would need this raised.
 */
const FRESH_S = 3600;

/** A Watch banner while the latest cabin CO₂ Reading is recent and over the limit, so the crew can act on the air. */
export function Co2Banner({ latest, now }: { latest: Map<IndicatorId, ShownReading>; now: MissionTime }) {
  const co2 = latest.get("cabin_co2");
  if (!isNumeric(co2) || now - co2.t > FRESH_S || co2.value <= CO2_LIMIT.ppm) return null;
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
