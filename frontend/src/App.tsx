import { useMemo, useState } from "react";
import type { IndicatorId, ReplayFile } from "./contracts";
import { missionStateAt, replayRange } from "./replay/state";
import { MissionBar } from "./home/MissionBar";
import { HealthSummary } from "./home/HealthSummary";
import { TaskList } from "./home/TaskList";
import { ActionButtons, type EmergencyRequest } from "./home/ActionButtons";
import { Body } from "./body/Body";
import { LayerPanel } from "./body/LayerPanel";
import { threeBodyScene } from "./body/threeBodyScene";
import { BodyStatusList } from "./body/BodyStatusList";
import { glowFrom } from "./body/glow";
import { ZoomControls } from "./body/ZoomControls";
import { buildBodyView } from "./body/buildView";
import { FlaggedList, InsightBanner } from "./body/InsightControls";
import type { BodySceneFactory, Focus, LayerId, LayerView } from "./body/view";

/** See-through by default: outer layers faint, organs and brain nearly solid. */
const DEFAULT_LAYERS: Record<LayerId, LayerView> = {
  muscles: { visible: true, opacity: 0.2 },
  skeleton: { visible: true, opacity: 0.35 },
  vessels: { visible: true, opacity: 0.5 },
  organs: { visible: true, opacity: 0.9 },
  brain: { visible: true, opacity: 0.9 },
};

/** Until Spec 4's emergency flow is wired in, say so rather than do nothing. */
function emergencyNotWired(request: EmergencyRequest) {
  alert(`The ${request === "emergency" ? "emergency" : "help a crewmate"} flow opens here (Spec 4).`);
}

export function App({
  replay,
  bodyScene = threeBodyScene,
  onEmergency = emergencyNotWired,
}: {
  replay: ReplayFile;
  bodyScene?: BodySceneFactory;
  /** Hand-off to the emergency flow (Spec 4). */
  onEmergency?: (request: EmergencyRequest) => void;
}) {
  const state = useMemo(() => missionStateAt(replay, replayRange(replay)[1]), [replay]);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [focus, setFocus] = useState<Focus>({ level: "body" });
  const [insight, setInsight] = useState<IndicatorId | null>(null);

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const heartRate = state.latest.get("heart_rate")?.value ?? null;
  const breathRate = state.latest.get("respiratory_rate")?.value ?? null;
  const view = useMemo(
    () => buildBodyView({ focus, layers, glow, heartRate, breathRate, insight }),
    [focus, layers, glow, heartRate, breathRate, insight],
  );

  const insightReading = insight ? state.latest.get(insight) : undefined;
  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <main className="home">
        <section className="home__body" aria-label="Body">
          {insightReading && <InsightBanner reading={insightReading} onExit={() => setInsight(null)} />}
          <Body view={view} scene={bodyScene} />
          {!insight && (
            <>
              <ZoomControls focus={focus} onFocus={setFocus} />
              <FlaggedList latest={state.latest} onShow={setInsight} />
              <BodyStatusList glow={glow} />
              <LayerPanel layers={layers} onChange={(id, next) => setLayers((l) => ({ ...l, [id]: next }))} />
            </>
          )}
        </section>
        <div className="home__side">
          <ActionButtons onEmergency={onEmergency} />
          <div className="home__summaries">
            <HealthSummary kind="physical" latest={state.latest} />
            <HealthSummary kind="mental" latest={state.latest} />
          </div>
          <TaskList tasks={state.tasks} />
        </div>
      </main>
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
