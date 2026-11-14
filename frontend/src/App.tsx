import { useCallback, useEffect, useMemo, useState } from "react";
import type { CardContent, CrewRecord, IndicatorId, Reading, ReplayFile } from "./contracts";
import { missionStateAt, replayRange, seriesOf } from "./replay/state";
import { MeasurementCard } from "./home/MeasurementCard";
import { MissionBar } from "./home/MissionBar";
import { Co2Banner } from "./home/Co2Banner";
import { HealthSummary } from "./home/HealthSummary";
import { TaskList, type CrewForm } from "./home/TaskList";
import { StandTestForm } from "./forms/StandTestForm";
import { PostEvaForm } from "./forms/PostEvaForm";
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
  replay: givenReplay,
  crew,
  bodyScene = threeBodyScene,
  onEmergency = emergencyNotWired,
  cards = [],
  onReadings = () => {},
}: {
  replay: ReplayFile;
  /** The Crew record the replay belongs to (sex picks the body; anchor gives "your normal"). */
  crew: CrewRecord;
  bodyScene?: BodySceneFactory;
  /** Hand-off to the emergency flow (Spec 4). */
  onEmergency?: (request: EmergencyRequest) => void;
  /** Measurement card content (Spec 5). */
  cards?: CardContent[];
  /** Readings the crew logged in a form (stand test, post-EVA), for the service (POST /reading). */
  onReadings?: (readings: Reading[], note?: string) => void;
}) {
  // Readings logged on this screen join the replay, so every part of the app shows them.
  const [logged, setLogged] = useState<Reading[]>([]);
  const replay = useMemo<ReplayFile>(
    () =>
      logged.length === 0
        ? givenReplay
        : {
            ...givenReplay,
            events: [...givenReplay.events, ...logged.map((r) => ({ t: r.t, type: "reading" as const, payload: r }))].sort(
              (a, b) => a.t - b.t,
            ),
          },
    [givenReplay, logged],
  );
  const [form, setForm] = useState<CrewForm | null>(null);
  const closeForm = useCallback(() => setForm(null), []);
  // Logged at the mission time now (the end of the replay), and the screen returns to now.
  const log = (readings: Reading[], note?: string) => {
    setLogged((l) => [...l, ...readings]);
    setT(range[1]);
    onReadings(readings, note);
  };

  const range = useMemo(() => replayRange(replay), [replay]);
  const [t, setT] = useState(range[1]);
  const state = useMemo(() => missionStateAt(replay, t), [replay, t]);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [focus, setFocus] = useState<Focus>({ level: "body" });
  const [insight, setInsight] = useState<IndicatorId | null>(null);
  const [cardFor, setCardFor] = useState<IndicatorId | null>(null);
  const closeCard = useCallback(() => setCardFor(null), []);

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const model = crew.sex === "female" ? "female" : "male";
  const heartRate = state.latest.get("heart_rate")?.value ?? null;
  const breathRate = state.latest.get("respiration_rate")?.value ?? null;
  // Insight and cards need a Reading at the scrubbed time; scrubbing to before one closes them.
  const insightReading = insight ? state.latest.get(insight) : undefined;
  const cardReading = cardFor ? state.latest.get(cardFor) : undefined;
  useEffect(() => {
    if (insight && !insightReading) setInsight(null);
    if (cardFor && !cardReading) setCardFor(null);
  }, [insight, insightReading, cardFor, cardReading]);
  const examined = insightReading ? { indicator: insightReading.indicator, status: insightReading.status } : null;
  const view = useMemo(
    () => buildBodyView({ model, focus, layers, glow, heartRate, breathRate, insight: examined }),
    // `examined` is a new object each render, so depend on its parts.
    [model, focus, layers, glow, heartRate, breathRate, examined?.indicator, examined?.status],
  );

  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <Co2Banner latest={state.latest} />
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
          <Trends replay={replay} crew={crew} state={state} range={range} onScrub={setT} />
          <TaskList tasks={state.tasks} onLog={setForm} />
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
      {form === "stand-test" && <StandTestForm crew={crew} t={range[1]} onSave={log} onClose={closeForm} />}
      {form === "post-eva" && <PostEvaForm crew={crew.id} t={range[1]} onSave={log} onClose={closeForm} />}
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
