/** Up to two decimals, no trailing zeros, never "-0". */
export function fmt(n: number): string {
  const r = +n.toFixed(2);
  return String(r === 0 ? 0 : r);
}

/** "+0.3", "-0.4", "+0". */
export function signed(n: number): string {
  const r = +n.toFixed(2);
  return r < 0 ? fmt(r) : `+${fmt(r)}`;
}
