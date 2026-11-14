import { useState } from "react";
import type { ReplayFile } from "../contracts";
import { formatValue } from "../indicators";
import { profileChoices, profileFor } from "../profiles";
import type { MissionState } from "../replay/state";
import { formatMissionTime } from "../replay/time";

/** Dose is logged once a day; older than this, the mission bar says how old it is. */
const DOSE_FRESH_S = 36 * 3600;

export function MissionBar({ replay, state }: { replay: ReplayFile; state: MissionState }) {
  const dose = state.latest.get("radiation_dose_accumulated");
  // Starts on the replay's own profile; the crew can switch to compare (ticket 17).
  const [chosen, setChosen] = useState({ replay: replay.profile, id: replay.profile });
  const profileId = chosen.replay === replay.profile ? chosen.id : replay.profile;
  const profile = profileFor(profileId);
  return (
    <section aria-label="Mission" className="mission-bar">
      <Item label="Mission day" value={`Day ${state.missionDay}`} />
      <div className="mission-bar__item">
        <label className="mission-bar__label" htmlFor="mission-profile">
          Mission profile
        </label>
        <select
          id="mission-profile"
          className="mission-bar__select"
          value={profileId}
          onChange={(e) => setChosen({ replay: replay.profile, id: e.target.value })}
        >
          {profileChoices(replay.profile).map((p) => (
            <option key={p.id} value={p.id}>
              {p.name}
            </option>
          ))}
        </select>
      </div>
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
