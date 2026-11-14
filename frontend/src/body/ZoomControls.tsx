import { REGIONS, STRUCTURES, structuresIn, type RegionId } from "./structures";
import type { Focus } from "./view";

/** Big buttons to zoom body → region → structure and back out one level. */
export function ZoomControls({ focus, onFocus }: { focus: Focus; onFocus: (next: Focus) => void }) {
  const region: RegionId | null =
    focus.level === "region" ? focus.region : focus.level === "structure" ? STRUCTURES[focus.structure].region : null;

  return (
    <nav className="zoom" aria-label="Zoom">
      {focus.level === "structure" && region && (
        <button className="zoom__back" onClick={() => onFocus({ level: "region", region })}>
          <span aria-hidden="true">← </span>Back to {REGIONS[region].toLowerCase()}
        </button>
      )}
      {focus.level === "region" && (
        <button className="zoom__back" onClick={() => onFocus({ level: "body" })}>
          <span aria-hidden="true">← </span>Back to whole body
        </button>
      )}
      <div className="zoom__options">
        {focus.level === "body"
          ? (Object.keys(REGIONS) as RegionId[]).map((r) => (
              <button key={r} onClick={() => onFocus({ level: "region", region: r })}>
                {REGIONS[r]}
              </button>
            ))
          : structuresIn(region!).map((s) => (
              <button
                key={s}
                aria-pressed={focus.level === "structure" && focus.structure === s}
                onClick={() => onFocus({ level: "structure", structure: s })}
              >
                {STRUCTURES[s].label}
              </button>
            ))}
      </div>
    </nav>
  );
}
