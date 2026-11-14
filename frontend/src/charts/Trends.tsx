import { useMemo, useState } from "react";
import type { IndicatorId, MissionTime, ReplayFile } from "../contracts";
import { INDICATORS, indicatorLabel } from "../indicators";
import type { MissionState } from "../replay/state";
import { seriesOf } from "../replay/state";
import { TrendChart } from "./TrendChart";

/** Indicators with enough Readings to draw a trend, in display order. */
function chartable(replay: ReplayFile): IndicatorId[] {
  const counts = new Map<IndicatorId, number>();
  for (const e of replay.events) {
    if (e.type === "reading") counts.set(e.payload.indicator, (counts.get(e.payload.indicator) ?? 0) + 1);
  }
  const order = Object.keys(INDICATORS);
  return [...counts]
    .filter(([, n]) => n > 1)
    .map(([id]) => id)
    .sort((a, b) => order.indexOf(a) - order.indexOf(b));
}

export function Trends({
  replay,
  state,
  cursor,
}: {
  replay: ReplayFile;
  state: MissionState;
  cursor?: MissionTime;
}) {
  const options = useMemo(() => chartable(replay), [replay]);
  const [picked, setPicked] = useState<IndicatorId | null>(null);
  const indicator = picked ?? options[0];
  const readings = useMemo(() => (indicator ? seriesOf(replay, indicator) : []), [replay, indicator]);
  const alerts = useMemo(
    () =>
      replay.events.flatMap((e) => (e.type === "alert" && e.payload.indicator === indicator ? [e.payload] : [])),
    [replay, indicator],
  );

  return (
    <section className="trends" aria-label="Trends">
      <h2>Trends</h2>
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
          <TrendChart
            key={indicator}
            readings={readings}
            baseline={state.baselines.get(indicator)}
            alerts={alerts}
            cursor={cursor}
          />
        </>
      )}
    </section>
  );
}
