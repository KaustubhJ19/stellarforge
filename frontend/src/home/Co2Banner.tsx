import type { IndicatorId, MissionTime } from "../contracts";
import type { Co2Limit } from "../profiles";
import { isNumeric, type ShownReading } from "../replay/state";

/**
 * The cabin replay gives a trailing 1-hour CO₂ average every 5 minutes; a Reading older than
 * an hour is not "now". A cabin source reporting less often than hourly would need this raised.
 */
const FRESH_S = 3600;

const mmHg = (n: number) => `${Number(n.toFixed(1))} mmHg`;

/**
 * A Watch banner while the cabin's trailing 1-hour CO₂ average (`cabin_pco2_1h`, mmHg) is recent
 * and over the Mission profile's limit (Spec 5's `co2_limit`), so the crew can act on the air.
 * Both are mmHg: no unit conversion here. With no limit in the profile, no banner can show.
 */
export function Co2Banner({
  latest,
  now,
  limit,
}: {
  latest: Map<IndicatorId, ShownReading>;
  now: MissionTime;
  limit: Co2Limit | null;
}) {
  const co2 = latest.get("cabin_pco2_1h");
  if (!limit || !isNumeric(co2) || now - co2.t > FRESH_S || co2.value <= limit.mmHg) return null;
  return (
    <section role="status" aria-label="Cabin CO₂" className="co2-banner" data-status="amber">
      <span className="status-badge" data-status="amber">
        <span className="status-badge__icon" data-testid="status-icon" aria-hidden="true">
          !
        </span>
      </span>
      <strong>Cabin CO₂ high: {mmHg(co2.value)} (1-hour average)</strong>
      <span className="co2-banner__limit">
        Limit {mmHg(limit.mmHg)}
        {limit.window && `, ${limit.window}`}
        {limit.basis && ` (${limit.basis})`}
      </span>
    </section>
  );
}
