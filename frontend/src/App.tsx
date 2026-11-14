import { useMemo, useState } from "react";
import type { IndicatorId, ReplayFile } from "./contracts";
import { missionStateAt, replayRange } from "./replay/state";
import { MissionBar } from "./home/MissionBar";
import { IndicatorTile } from "./home/IndicatorTile";
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

export function App({
  replay,
  bodyScene = threeBodyScene,
}: {
  replay: ReplayFile;
  bodyScene?: BodySceneFactory;
}) {
  const state = useMemo(() => missionStateAt(replay, replayRange(replay)[1]), [replay]);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [focus, setFocus] = useState<Focus>({ level: "body" });
  const [insight, setInsight] = useState<IndicatorId | null>(null);

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const view = useMemo(
    () => buildBodyView({ focus, layers, glow, heartRate: null, insight }),
    [focus, layers, glow, insight],
  );

  const insightReading = insight ? state.latest.get(insight) : undefined;
  const hr = state.latest.get("heart_rate");
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
        {hr && <IndicatorTile reading={hr} />}
      </main>
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
