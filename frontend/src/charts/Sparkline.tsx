import type { Reading } from "../contracts";
import { indicatorLabel } from "../indicators";
import { linear } from "./scale";

const W = 160;
const H = 40;
const PAD = 5;

/** A tiny trend: the line and a ringed end dot, no axes. */
export function Sparkline({ readings }: { readings: Reading[] }) {
  if (readings.length < 2) return null;
  const label = indicatorLabel(readings[0].indicator);
  const ts = readings.map((r) => r.t);
  const vs = readings.map((r) => r.value);
  const x = linear([Math.min(...ts), Math.max(...ts)], [PAD, W - PAD]);
  const y = linear([Math.min(...vs), Math.max(...vs)], [H - PAD, PAD]);
  const d = readings.map((r, i) => `${i ? "L" : "M"}${x(r.t).toFixed(1)},${y(r.value).toFixed(1)}`).join("");
  const first = readings[0];
  const last = readings[readings.length - 1];
  return (
    <svg
      className="sparkline"
      viewBox={`0 0 ${W} ${H}`}
      role="img"
      aria-label={`${label} sparkline, from ${first.value} to ${last.value} ${last.unit}`}
    >
      <path d={d} />
      <circle cx={x(last.t)} cy={y(last.value)} r={4} />
    </svg>
  );
}
