import type { KeyboardEvent } from "react";
import type { MissionTime } from "../contracts";

const ARROW_STEP = 5 * 60;
const PAGE_STEP = 60 * 60;
import { formatMissionTime } from "../replay/time";

/** Replays how status evolved: drag back along the Mission clock. */
export function Scrubber({
  range: [start, end],
  t,
  onChange,
}: {
  range: [MissionTime, MissionTime];
  t: MissionTime;
  onChange: (t: MissionTime) => void;
}) {
  // The input steps by the second so it can reach the newest event exactly;
  // keys move in steps a person can use.
  function onKeyDown(e: KeyboardEvent<HTMLInputElement>) {
    const delta: Record<string, number> = {
      ArrowLeft: -ARROW_STEP,
      ArrowDown: -ARROW_STEP,
      ArrowRight: ARROW_STEP,
      ArrowUp: ARROW_STEP,
      PageDown: -PAGE_STEP,
      PageUp: PAGE_STEP,
    };
    let next: number | null = null;
    if (e.key in delta) next = t + delta[e.key];
    else if (e.key === "Home") next = start;
    else if (e.key === "End") next = end;
    if (next === null) return;
    e.preventDefault();
    onChange(Math.min(end, Math.max(start, next)));
  }

  return (
    <div className="scrubber">
      <label className="scrubber__label">
        <span>Mission clock</span>
        <output className="scrubber__time">{formatMissionTime(t)}</output>
        <input
          type="range"
          aria-label="Mission clock"
          min={start}
          max={end}
          step={1}
          value={t}
          onChange={(e) => onChange(Number(e.target.value))}
          onKeyDown={onKeyDown}
        />
      </label>
      <button onClick={() => onChange(end)} disabled={t === end}>
        Back to now
      </button>
    </div>
  );
}
