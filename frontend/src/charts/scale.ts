/** [min, max] without spreading into Math.min/max (large arrays overflow the stack). */
export function extent(values: number[]): [number, number] {
  let lo = Infinity;
  let hi = -Infinity;
  for (const v of values) {
    if (v < lo) lo = v;
    if (v > hi) hi = v;
  }
  return values.length ? [lo, hi] : [0, 0];
}

export type Scale = ((v: number) => number) & { domain: [number, number] };

export function linear([d0, d1]: [number, number], [r0, r1]: [number, number]): Scale {
  const span = d1 - d0 || 1;
  const f = ((v: number) => r0 + ((v - d0) / span) * (r1 - r0)) as Scale;
  f.domain = [d0, d1];
  return f;
}

/** About `count` round tick values covering [lo, hi] (1, 2, 2.5 or 5 × 10^n steps). */
export function niceTicks(lo: number, hi: number, count = 4): number[] {
  if (hi <= lo) return [lo];
  const raw = (hi - lo) / count;
  const mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw)!;
  const ticks: number[] = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi + step * 1e-9; v += step) ticks.push(+v.toFixed(10));
  return ticks;
}
