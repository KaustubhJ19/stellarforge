import type { Forecast, MissionTime } from "../contracts";
import { formatMissionTime } from "../replay/time";
import { fmt as num } from "./format";

const DAY = 86400;

/** Spec 3's forecast labels in plain words. */
const LABEL_TEXT: Record<string, string> = {
  "learning your pattern": "Learning your pattern: too few days of your data yet, so the range is the whole 0–10.",
  "re-measure": "Re-measure: the range is too wide to trust.",
};

const GAUGE_W = 300;
const GAUGE_PAD = 8;

/** The 0-10 scale as a bar: the likely range as a band, tomorrow's value as the marker. Decorative: the words say the same. */
function ForecastGauge({ forecast }: { forecast: Forecast }) {
  const x = (v: number) => GAUGE_PAD + (Math.min(10, Math.max(0, v)) / 10) * (GAUGE_W - 2 * GAUGE_PAD);
  return (
    <svg className="forecast__gauge" viewBox={`0 0 ${GAUGE_W} 36`} aria-hidden="true">
      <rect className="forecast__track" x={GAUGE_PAD} y={8} width={GAUGE_W - 2 * GAUGE_PAD} height={10} rx={5} />
      <rect className="forecast__range" x={x(forecast.low)} y={8} width={Math.max(2, x(forecast.high) - x(forecast.low))} height={10} rx={5} />
      <circle className="forecast__marker" cx={x(forecast.value)} cy={13} r={9} />
      {[0, 5, 10].map((v) => (
        <text key={v} className="forecast__tick" x={x(v)} y={34} textAnchor="middle">
          {v}
        </text>
      ))}
    </svg>
  );
}

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
          <ForecastGauge forecast={forecast} />
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
