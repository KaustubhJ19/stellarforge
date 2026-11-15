import type { ReplayFile } from "../contracts";
import { profileFor } from "../profiles";
import type { MissionState } from "../replay/state";

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
      <Item label="Radiation dose" value={dose ? `${dose.value} ${dose.unit}` : "No reading"} />
    </section>
  );
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
