import type { MissionTime } from "../contracts";
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
          step={60}
          value={t}
          onChange={(e) => onChange(Number(e.target.value))}
        />
      </label>
      <button onClick={() => onChange(end)} disabled={t === end}>
        Back to now
      </button>
    </div>
  );
}
