import { useCallback, useMemo } from "react";
import type { IndicatorId, MissionTime, ReplayFile } from "../contracts";
import { isNumeric, seriesOf, type NumericReading } from "../replay/state";

/** How many of the latest Readings a tile's mini chart draws. */
export const SPARK_POINTS = 48;

/**
 * The numeric Readings up to `t`, newest SPARK_POINTS, for one Indicator's tile chart.
 * A whole series is built once per replay and kept, so scrubbing only slices it.
 */
export function useSparkHistory(replay: ReplayFile, t: MissionTime): (id: IndicatorId) => NumericReading[] {
  const series = useMemo(() => new Map<IndicatorId, NumericReading[]>(), [replay]);
  return useCallback(
    (id) => {
      let all = series.get(id);
      if (!all) {
        all = seriesOf(replay, id).filter(isNumeric) as NumericReading[];
        series.set(id, all);
      }
      return all.filter((r) => r.t <= t).slice(-SPARK_POINTS);
    },
    [replay, series, t],
  );
}
