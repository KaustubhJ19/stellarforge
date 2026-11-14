import type { ReplayFile } from "../contracts";
import type { MissionState } from "../replay/state";

export function MissionBar({ replay, state }: { replay: ReplayFile; state: MissionState }) {
  const dose = state.latest.get("radiation_dose");
  return (
    <section aria-label="Mission" className="mission-bar">
      <Item label="Mission day" value={`Day ${state.missionDay}`} />
      <Item label="Profile" value={replay.profile.name} />
      <Item label="Ground delay" value={`${replay.profile.groundDelayMin} min`} />
      <Item label="Radiation dose" value={dose ? `${dose.value} ${dose.unit}` : "No reading"} />
    </section>
  );
}

function Item({ label, value }: { label: string; value: string }) {
  return (
    <div className="mission-bar__item">
      <span className="mission-bar__label">{label}</span>
      <span className="mission-bar__value">{value}</span>
    </div>
  );
}
