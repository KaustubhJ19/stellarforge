import type { NumericReading } from "../replay/state";
import { formatNumber, indicatorLabel } from "../indicators";
import { extent, linear } from "./scale";

const W = 160;
const H = 40;
const PAD = 5;

/** A tiny trend: the line and a ringed end dot, no axes. */
export function Sparkline({ readings }: { readings: NumericReading[] }) {
  if (readings.length < 2) return null;
  const label = indicatorLabel(readings[0].indicator);
  const x = linear(extent(readings.map((r) => r.t)), [PAD, W - PAD]);
  const y = linear(extent(readings.map((r) => r.value)), [H - PAD, PAD]);
  const d = readings.map((r, i) => `${i ? "L" : "M"}${x(r.t).toFixed(1)},${y(r.value).toFixed(1)}`).join("");
  const first = readings[0];
  const last = readings[readings.length - 1];
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${label} sparkline, from ${formatNumber(first.value)} to ${formatNumber(last.value)} ${last.unit}`}
    >
      <path d={d} />
      <circle cx={x(last.t)} cy={y(last.value)} r={4} />
    </svg>
  );
}
