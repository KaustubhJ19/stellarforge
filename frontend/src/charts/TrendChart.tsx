import { useId, useState, type PointerEvent } from "react";
import type { Alert, Baseline, MissionTime, Reading } from "../contracts";
import { indicatorLabel } from "../indicators";
import { formatClock, formatMissionTime } from "../replay/time";
import { STATUS_TEXT, StatusBadge } from "../status";
import { linear, niceTicks } from "./scale";

const W = 640;
const H = 260;
const M = { top: 16, right: 64, bottom: 32, left: 48 };
const ALERT_SHAPE = { acute: "triangle", drift: "diamond", emergency: "square" } as const;
const ALERT_WORD = { acute: "Acute", drift: "Drift", emergency: "Emergency" } as const;

export interface TrendChartProps {
  readings: Reading[];
  baseline?: Baseline;
  alerts: Alert[];
  /** Mission-clock cursor (scrubber); the chart greys out what comes after it. */
  cursor?: MissionTime;
}

/** Value over the Mission clock, with the person's own normal band and alert markers. */
export function TrendChart({ readings, baseline, alerts, cursor }: TrendChartProps) {
  const [hover, setHover] = useState<number | null>(null);
  const [asTable, setAsTable] = useState(false);
  const clipId = useId();
  if (readings.length === 0) return null;

  const indicator = readings[0].indicator;
  const label = indicatorLabel(indicator);
  const unit = readings[0].unit;

  const ts = readings.map((r) => r.t);
  const x = linear([Math.min(...ts), Math.max(...ts)], [M.left, W - M.right]);
  const values = readings.map((r) => r.value).concat(baseline ? [baseline.low, baseline.high] : []);
  const [lo, hi] = [Math.min(...values), Math.max(...values)];
  const pad = (hi - lo || 1) * 0.12;
  const y = linear([lo - pad, hi + pad], [H - M.bottom, M.top]);
  const yTicks = niceTicks(lo - pad, hi + pad, 4);
  const xTicks = hourTicks(x.domain[0], x.domain[1]);

  const path = readings.map((r, i) => `${i ? "L" : "M"}${x(r.t).toFixed(1)},${y(r.value).toFixed(1)}`).join("");
  const last = readings[readings.length - 1];
  const shown = hover !== null ? readings[hover] : null;

  function onMove(e: PointerEvent<SVGSVGElement>) {
    const box = e.currentTarget.getBoundingClientRect();
    const px = ((e.clientX - box.left) / box.width) * W;
    let best = 0;
    readings.forEach((r, i) => {
      if (Math.abs(x(r.t) - px) < Math.abs(x(readings[best].t) - px)) best = i;
    });
    setHover(best);
  }

  return (
    <figure className="trend" aria-label={`${label} trend`}>
      <figcaption className="trend__title">
        {label} <span className="trend__unit">({unit})</span>
      </figcaption>
      <div className="trend__plot">
        <svg
          viewBox={`0 0 ${W} ${H}`}
          role="presentation"
          onPointerMove={onMove}
          onPointerLeave={() => setHover(null)}
        >
          <clipPath id={clipId}>
            <rect x={M.left} y={0} width={W - M.left - M.right} height={H} />
          </clipPath>
          {yTicks.map((v) => (
            <g key={v} className="trend__grid">
              <line x1={M.left} x2={W - M.right} y1={y(v)} y2={y(v)} />
              <text x={M.left - 8} y={y(v)} dy="0.32em" textAnchor="end">
                {v}
              </text>
            </g>
          ))}
          {xTicks.map((t) => (
            <text key={t} className="trend__xtick" x={x(t)} y={H - 8} textAnchor="middle">
              {formatClock(t)}
            </text>
          ))}
          {baseline && (
            <g aria-label={`Your normal: ${baseline.low}–${baseline.high} ${unit}`} role="img">
              <rect
                className="trend__band"
                x={M.left}
                width={W - M.left - M.right}
                y={y(baseline.high)}
                height={y(baseline.low) - y(baseline.high)}
              />
              <text className="trend__band-label" x={M.left + 6} y={y(baseline.high) + 14}>
                Your normal
              </text>
            </g>
          )}
          <path className="trend__line" d={path} clipPath={`url(#${clipId})`} />
          {cursor !== undefined && cursor < x.domain[1] && (
            <rect
              className="trend__future"
              x={Math.max(x(cursor), M.left)}
              width={W - M.right - Math.max(x(cursor), M.left)}
              y={M.top}
              height={H - M.top - M.bottom}
            />
          )}
          {alerts.map((a) => {
            const ax = x(a.t);
            const word = ALERT_WORD[a.kind];
            return (
              <g
                key={a.id}
                className="trend__alert"
                data-status={a.status}
                data-shape={ALERT_SHAPE[a.kind]}
                data-x={ax.toFixed(1)}
                aria-label={`${word} alert, ${formatMissionTime(a.t)}`}
                role="img"
              >
                <line x1={ax} x2={ax} y1={M.top + 18} y2={H - M.bottom} />
                <AlertMark shape={ALERT_SHAPE[a.kind]} cx={ax} cy={M.top + 8} />
                <text x={ax + 9} y={M.top + 12}>
                  {word}
                </text>
              </g>
            );
          })}
          <circle className="trend__end" cx={x(last.t)} cy={y(last.value)} r={4} />
          <text className="trend__end-label" x={x(last.t) + 10} y={y(last.value)} dy="0.32em">
            {last.value}
          </text>
          {shown && (
            <g className="trend__crosshair">
              <line x1={x(shown.t)} x2={x(shown.t)} y1={M.top} y2={H - M.bottom} />
              <circle cx={x(shown.t)} cy={y(shown.value)} r={5} />
            </g>
          )}
        </svg>
        {shown && (
          <div
            className="trend__tooltip"
            style={{ left: `${(x(shown.t) / W) * 100}%`, top: `${(y(shown.value) / H) * 100}%` }}
          >
            <div>{formatMissionTime(shown.t)}</div>
            <strong>
              {shown.value} {unit}
            </strong>
            <StatusBadge status={shown.state} />
          </div>
        )}
      </div>
      <button className="trend__table-toggle" onClick={() => setAsTable((v) => !v)}>
        {asTable ? "Hide table" : "Show as table"}
      </button>
      {asTable && (
        <table className="trend__table">
          <thead>
            <tr>
              <th>Time</th>
              <th>Value ({unit})</th>
              <th>Status</th>
            </tr>
          </thead>
          <tbody>
            {readings.map((r) => (
              <tr key={r.t}>
                <td>{formatMissionTime(r.t)}</td>
                <td>{r.value}</td>
                <td>{STATUS_TEXT[r.state].label}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </figure>
  );
}

/** Ticks on whole hours of the Mission clock, at a step that gives at most six. */
function hourTicks(t0: number, t1: number): number[] {
  const hours = (t1 - t0) / 3600;
  const step = ([1, 2, 3, 6, 12, 24].find((h) => hours / h <= 6) ?? 24) * 3600;
  const ticks: number[] = [];
  for (let t = Math.ceil(t0 / step) * step; t <= t1; t += step) ticks.push(t);
  return ticks;
}

function AlertMark({ shape, cx, cy }: { shape: (typeof ALERT_SHAPE)[keyof typeof ALERT_SHAPE]; cx: number; cy: number }) {
  const r = 6;
  if (shape === "triangle") return <path d={`M${cx},${cy - r}L${cx + r},${cy + r}L${cx - r},${cy + r}Z`} />;
  if (shape === "diamond") return <path d={`M${cx},${cy - r}L${cx + r},${cy}L${cx},${cy + r}L${cx - r},${cy}Z`} />;
  return <rect x={cx - r} y={cy - r} width={2 * r} height={2 * r} />;
}
