import type { Forecast, MissionTime } from "../contracts";
import { formatMissionTime } from "../replay/time";
import { fmt as num } from "./format";

const DAY = 86400;

/** Spec 3's forecast labels in plain words. */
const LABEL_TEXT: Record<string, string> = {
  "learning your pattern": "Learning your pattern: too few days of your data yet, so the range is the whole 0–10.",
  "re-measure": "Re-measure: the range is too wide to trust.",
};

/** Tomorrow's readiness (0-10) with its range; opens "Why this forecast?". */
export function ForecastPanel({
  forecast,
  now,
  onWhy,
}: {
  forecast: Forecast | null;
  /** The scrubbed Mission-clock time, to say when the forecast is older than today. */
  now: MissionTime;
  onWhy: () => void;
}) {
  const stale = forecast !== null && Math.floor(forecast.t / DAY) < Math.floor(now / DAY);
  return (
    <section className="forecast" aria-label="Readiness forecast">
      <h2>Readiness tomorrow</h2>
      {forecast ? (
        <>
          <p className="forecast__value">
            <strong>{num(forecast.value)}</strong> of 10
          </p>
          <p>
            Likely between {num(forecast.low)} and {num(forecast.high)}
          </p>
          <p className="forecast__note">Made {formatMissionTime(forecast.t)}, for the next day</p>
          {stale && <p className="forecast__note">Older than today: no newer forecast yet.</p>}
          {forecast.label && LABEL_TEXT[forecast.label] && <p className="forecast__note">{LABEL_TEXT[forecast.label]}</p>}
          <span className="card__label">Estimate, not validated</span>
          <button className="forecast__why" onClick={onWhy}>
            Why this forecast?
          </button>
        </>
      ) : (
        <p className="empty">No forecast yet.</p>
      )}
    </section>
  );
}
