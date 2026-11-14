import type { ReplayFile } from "../contracts";
import { formatValue } from "../indicators";
import { profileFor } from "../profiles";
import type { MissionState } from "../replay/state";
import { formatMissionTime } from "../replay/time";

/** Dose is logged once a day; older than this, the mission bar says how old it is. */
const DOSE_FRESH_S = 36 * 3600;

export function MissionBar({ replay, state }: { replay: ReplayFile; state: MissionState }) {
  const dose = state.latest.get("radiation_dose_accumulated");
  const profile = profileFor(replay.profile);
  return (
    <section aria-label="Mission" className="mission-bar">
      <Item label="Mission day" value={`Day ${state.missionDay}`} />
      <Item label="Profile" value={profile.name} />
      <Item
        label="Ground delay"
        value={profile.delay ?? "Not known"}
        note={profile.delayNote ?? undefined}
      />
      <Item
        label="Radiation dose"
        value={dose ? doseText(dose.value, dose.unit) : "No reading"}
        // Cabin data can stop before the crew data (RR-1 covers 42 days): say how old the dose is.
        note={dose && state.t - dose.t > DOSE_FRESH_S ? `as of ${formatMissionTime(dose.t)}` : undefined}
      />
    </section>
  );
}

function doseText(value: number | string, unit: string): string {
  const shown = formatValue(value, unit);
  return shown.unit ? `${shown.value} ${shown.unit}` : shown.value;
}

function Item({ label, value, note }: { label: string; value: string; note?: string }) {
  return (
    <div className="mission-bar__item">
      <span className="mission-bar__label">{label}</span>
      <span className="mission-bar__value">{value}</span>
      {note && <span className="mission-bar__note">{note}</span>}
    </div>
  );
}
