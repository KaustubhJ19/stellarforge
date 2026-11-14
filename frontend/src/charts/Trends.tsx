import { useMemo, useState } from "react";
import type { IndicatorId, MissionTime, ReplayFile } from "../contracts";
import { byIndicatorOrder, indicatorLabel } from "../indicators";
import type { MissionState } from "../replay/state";
import { seriesOf } from "../replay/state";
import { TrendChart } from "./TrendChart";
import { Scrubber } from "./Scrubber";

/** Indicators with enough Readings to draw a trend, in display order. */
function chartable(replay: ReplayFile): IndicatorId[] {
  const counts = new Map<IndicatorId, number>();
  for (const e of replay.events) {
    if (e.type === "reading") counts.set(e.payload.indicator, (counts.get(e.payload.indicator) ?? 0) + 1);
  }
  return [...counts]
    .filter(([, n]) => n > 1)
    .map(([id]) => id)
    .sort(byIndicatorOrder);
}

export function Trends({
  replay,
  state,
  range,
  onScrub,
}: {
  replay: ReplayFile;
  state: MissionState;
  range: [MissionTime, MissionTime];
  onScrub: (t: MissionTime) => void;
}) {
  const options = useMemo(() => chartable(replay), [replay]);
  const [picked, setPicked] = useState<IndicatorId | null>(null);
  const indicator = picked ?? options[0];
  const series = useMemo(() => (indicator ? seriesOf(replay, indicator) : []), [replay, indicator]);
  // Only what was known at the scrubbed time; the axis still spans the whole replay.
  const readings = series.filter((r) => r.t <= state.t);
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
              baseline={state.baselines.get(indicator)}
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
