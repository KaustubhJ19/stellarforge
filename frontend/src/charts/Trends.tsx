import { useMemo, useState } from "react";
import type { CrewRecord, IndicatorId, MissionTime, ReplayFile } from "../contracts";
import { HABITAT_INDICATORS, byIndicatorOrder, displayScale, indicatorLabel, scaleRange } from "../indicators";
import type { MissionState } from "../replay/state";
import { baselineFor, isNumeric, seriesOf } from "../replay/state";
import { TrendChart } from "./TrendChart";
import { Scrubber } from "./Scrubber";

/** Habitat Readings stay out of the health trends, except the dose the mission bar shows. */
const NOT_CHARTED = HABITAT_INDICATORS.filter((id) => id !== "radiation_dose_accumulated");

/** Indicators with enough Readings to draw a trend, in display order. */
function chartable(replay: ReplayFile): IndicatorId[] {
  const counts = new Map<IndicatorId, number>();
  for (const e of replay.events) {
    if (e.type === "reading" && isNumeric(e.payload) && !NOT_CHARTED.includes(e.payload.indicator)) counts.set(e.payload.indicator, (counts.get(e.payload.indicator) ?? 0) + 1);
  }
  return [...counts]
    .filter(([, n]) => n > 1)
    .map(([id]) => id)
    .sort(byIndicatorOrder);
}

export function Trends({
  replay,
  crew,
  state,
  range,
  onScrub,
}: {
  replay: ReplayFile;
  crew: CrewRecord;
  state: MissionState;
  range: [MissionTime, MissionTime];
  onScrub: (t: MissionTime) => void;
}) {
  const options = useMemo(() => chartable(replay), [replay]);
  const [picked, setPicked] = useState<IndicatorId | null>(null);
  const indicator = picked ?? options[0];
  const series = useMemo(() => (indicator ? seriesOf(replay, indicator).filter(isNumeric) : []), [replay, indicator]);
  // Only what was known at the scrubbed time; the axis still spans the whole replay.
  // Shown in display units (a 0-1 fraction as %), as the tiles show it.
  const scale = displayScale(series[0]?.unit ?? "");
  const shown = (n: number) => +(n * scale.factor).toFixed(3);
  const readings = series
    .filter((r) => r.t <= state.t)
    .map((r) => ({ ...r, value: shown(r.value), unit: scale.unit }));
  // Mean ± 2 SD, drawn only inside the scale's possible range (e.g. 1-5, SpO₂ up to 100%).
  const band = indicator ? baselineFor(crew, indicator) : undefined;
  const [min, max] = scaleRange(series[0]?.unit ?? "") ?? [-Infinity, Infinity];
  const baseline = band && { low: shown(Math.max(band.low, min)), high: shown(Math.min(band.high, max)) };
  const alerts = state.alerts.filter((a) => a.indicator === indicator);

  return (
    <section className="trends" aria-label="Trends">
      <h2>Trends</h2>
      <Scrubber range={range} t={state.t} onChange={onScrub} />
      {options.length === 0 ? (
        <p className="empty">No trends yet.</p>
      ) : (
        <>
          <div className="trends__picker">
            {options.map((id) => (
              <button key={id} aria-pressed={id === indicator} onClick={() => setPicked(id)}>
                {indicatorLabel(id)}
              </button>
            ))}
          </div>
          {readings.length === 0 ? (
            <p className="empty">No {indicatorLabel(indicator).toLowerCase()} readings yet at this time.</p>
          ) : (
            <TrendChart
              key={indicator}
              readings={readings}
              baseline={baseline}
              alerts={alerts}
              domain={range}
              cursor={state.t}
            />
          )}
        </>
      )}
    </section>
  );
}
