import { useMemo, useState } from "react";
import type { ReplayFile } from "./contracts";
import { missionStateAt, replayRange } from "./replay/state";
import { MissionBar } from "./home/MissionBar";
import { IndicatorTile } from "./home/IndicatorTile";
import { Body } from "./body/Body";
import { LayerPanel } from "./body/LayerPanel";
import { threeBodyScene } from "./body/threeBodyScene";
import type { BodySceneFactory, BodyView, LayerId, LayerView } from "./body/view";

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
  const [, end] = replayRange(replay);
  const state = missionStateAt(replay, end);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);

  const view = useMemo<BodyView>(() => ({ layers, structures: {}, heartRate: null }), [layers]);

  const hr = state.latest.get("heart_rate");
  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <main className="home">
        <section className="home__body" aria-label="Body">
          <Body view={view} scene={bodyScene} />
          <LayerPanel layers={layers} onChange={(id, next) => setLayers((l) => ({ ...l, [id]: next }))} />
        </section>
        {hr && <IndicatorTile reading={hr} />}
      </main>
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
