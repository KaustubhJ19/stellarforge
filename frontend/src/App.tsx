import { useMemo, useState } from "react";
import type { ReplayFile } from "./contracts";
import { missionStateAt, replayRange } from "./replay/state";
import { MissionBar } from "./home/MissionBar";
import { IndicatorTile } from "./home/IndicatorTile";
import { Body } from "./body/Body";
import { LayerPanel } from "./body/LayerPanel";
import { threeBodyScene } from "./body/threeBodyScene";
import { BodyStatusList } from "./body/BodyStatusList";
import { glowFrom } from "./body/glow";
import { ZoomControls } from "./body/ZoomControls";
import type { BodySceneFactory, BodyView, Focus, LayerId, LayerView } from "./body/view";

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

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const view = useMemo<BodyView>(
    () => ({
      focus,
      layers,
      structures: Object.fromEntries(
        Object.entries(glow.structures).map(([id, status]) => [id, { status, opacity: null }]),
      ),
      wholeBody: glow.wholeBody,
      heartRate: null,
    }),
    [focus, layers, glow],
  );

  const hr = state.latest.get("heart_rate");
  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <main className="home">
        <section className="home__body" aria-label="Body">
          <Body view={view} scene={bodyScene} />
          <ZoomControls focus={focus} onFocus={setFocus} />
          <BodyStatusList glow={glow} />
          <LayerPanel layers={layers} onChange={(id, next) => setLayers((l) => ({ ...l, [id]: next }))} />
        </section>
        {hr && <IndicatorTile reading={hr} />}
      </main>
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
