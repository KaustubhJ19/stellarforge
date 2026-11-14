import { useCallback, useEffect, useMemo, useState } from "react";
import type { CardContent, IndicatorId, ReplayFile } from "./contracts";
import { missionStateAt, replayRange, seriesOf } from "./replay/state";
import { MeasurementCard } from "./home/MeasurementCard";
import { MissionBar } from "./home/MissionBar";
import { HealthSummary } from "./home/HealthSummary";
import { TaskList } from "./home/TaskList";
import { Trends } from "./charts/Trends";
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
  cards = [],
}: {
  replay: ReplayFile;
  bodyScene?: BodySceneFactory;
  /** Hand-off to the emergency flow (Spec 4). */
  onEmergency?: (request: EmergencyRequest) => void;
  /** Measurement card content (Spec 5). */
  cards?: CardContent[];
}) {
  const range = useMemo(() => replayRange(replay), [replay]);
  const [t, setT] = useState(range[1]);
  const state = useMemo(() => missionStateAt(replay, t), [replay, t]);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [focus, setFocus] = useState<Focus>({ level: "body" });
  const [insight, setInsight] = useState<IndicatorId | null>(null);
  const [cardFor, setCardFor] = useState<IndicatorId | null>(null);
  const closeCard = useCallback(() => setCardFor(null), []);

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const model = replay.crew.sex === "female" ? "female" : "male";
  const heartRate = state.latest.get("heart_rate")?.value ?? null;
  const breathRate = state.latest.get("respiratory_rate")?.value ?? null;
  // Insight and cards need a Reading at the scrubbed time; scrubbing to before one closes them.
  const insightReading = insight ? state.latest.get(insight) : undefined;
  const cardReading = cardFor ? state.latest.get(cardFor) : undefined;
  useEffect(() => {
    if (insight && !insightReading) setInsight(null);
    if (cardFor && !cardReading) setCardFor(null);
  }, [insight, insightReading, cardFor, cardReading]);
  const examined = insightReading ? { indicator: insightReading.indicator, status: insightReading.state } : null;
  const view = useMemo(
    () => buildBodyView({ model, focus, layers, glow, heartRate, breathRate, insight: examined }),
    // `examined` is a new object each render, so depend on its parts.
    [model, focus, layers, glow, heartRate, breathRate, examined?.indicator, examined?.status],
  );

  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <main className="home">
        {/* First in tab order so Emergency is one Tab away; CSS places it on screen. */}
        <ActionButtons onEmergency={onEmergency} />
        <section className="home__body" aria-label="Body">
          {insightReading && <InsightBanner reading={insightReading} onExit={() => setInsight(null)} />}
          <Body view={view} scene={bodyScene} />
          {model === "female" && (
            <p className="body-note">
              Female organs. Muscles, skeleton and vessels are approximate (resized from the male model).
            </p>
          )}
          {!insightReading && (
            <>
              <ZoomControls focus={focus} onFocus={setFocus} />
              <FlaggedList latest={state.latest} onShow={setInsight} />
              <BodyStatusList glow={glow} />
              <LayerPanel layers={layers} onChange={(id, next) => setLayers((l) => ({ ...l, [id]: next }))} />
            </>
          )}
        </section>
        <div className="home__side">
          <div className="home__summaries">
            <HealthSummary kind="physical" latest={state.latest} onDetails={setCardFor} />
            <HealthSummary kind="mental" latest={state.latest} onDetails={setCardFor} />
          </div>
          <Trends replay={replay} state={state} range={range} onScrub={setT} />
          <TaskList tasks={state.tasks} />
        </div>
      </main>
      {cardReading && (
        <MeasurementCard
          reading={cardReading}
          history={seriesOf(replay, cardReading.indicator).filter((r) => r.t <= state.t)}
          content={cards.find((c) => c.indicator === cardReading.indicator)}
          onClose={closeCard}
        />
      )}
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
