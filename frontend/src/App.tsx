import type { ReplayFile } from "./contracts";
import { missionStateAt, replayRange } from "./replay/state";
import { MissionBar } from "./home/MissionBar";
import { IndicatorTile } from "./home/IndicatorTile";

export function App({ replay }: { replay: ReplayFile }) {
  const [, end] = replayRange(replay);
  const state = missionStateAt(replay, end);
  const hr = state.latest.get("heart_rate");
  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <main>{hr && <IndicatorTile reading={hr} />}</main>
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
