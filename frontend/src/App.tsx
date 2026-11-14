import { useCallback, useEffect, useMemo, useState } from "react";
import type { CardContent, CrewRecord, IndicatorId, Reading, ReplayFile } from "./contracts";
import { isNumeric, missionStateAt, replayRange, seriesOf, type NumericReading } from "./replay/state";
import { MeasurementCard } from "./home/MeasurementCard";
import { CONTENT_CARDS, cardFor } from "./content";
import { MissionBar } from "./home/MissionBar";
import { Co2Banner } from "./home/Co2Banner";
import { HealthSummary } from "./home/HealthSummary";
import { TaskList, type CrewForm, type CrewNote } from "./home/TaskList";
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
import { ForecastPanel } from "./forecast/ForecastPanel";
import { WhyForecast } from "./forecast/WhyForecast";
import { explainWeights } from "./forecast/drivers";
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
  cards = CONTENT_CARDS,
  onReadings = () => {},
}: {
  replay: ReplayFile;
  /** The Crew record the replay belongs to (sex picks the body; anchor gives "your normal"). */
  crew: CrewRecord;
  bodyScene?: BodySceneFactory;
  /** Hand-off to the emergency flow (Spec 4). */
  onEmergency?: (request: EmergencyRequest) => void;
  /** Measurement card content (Spec 5); defaults to content/cards/ at the repo root. */
  cards?: CardContent[];
  /** Readings the crew logged in a form (stand test, post-EVA), for the service (POST /reading). */
  onReadings?: (readings: Reading[], note?: string) => void;
}) {
  // Readings logged on this screen join the replay, so every part of the app shows them.
  const [logged, setLogged] = useState<Reading[]>([]);
  const [notes, setNotes] = useState<CrewNote[]>([]);
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
    if (note) setNotes((n) => [...n, { t: range[1], title: "Post-EVA note", text: note }]);
    setT(range[1]);
    onReadings(readings, note);
  };

  const range = useMemo(() => replayRange(replay), [replay]);
  const [t, setT] = useState(range[1]);
  const state = useMemo(() => missionStateAt(replay, t), [replay, t]);
  const [layers, setLayers] = useState(DEFAULT_LAYERS);
  const [focus, setFocus] = useState<Focus>({ level: "body" });
  const [insight, setInsight] = useState<IndicatorId | null>(null);
  const [why, setWhy] = useState(false);
  const [openCard, setOpenCard] = useState<IndicatorId | null>(null);
  const closeCard = useCallback(() => setOpenCard(null), []);

  const glow = useMemo(() => glowFrom(state.latest), [state]);
  const model = crew.sex === "female" ? "female" : "male";
  const hr = state.latest.get("heart_rate");
  const heartRate = isNumeric(hr) ? hr.value : null;
  const br = state.latest.get("respiration_rate");
  const breathRate = isNumeric(br) ? br.value : null;
  // Insight and cards need a Reading at the scrubbed time; scrubbing to before one closes them.
  const insightReading = insight ? state.latest.get(insight) : undefined;
  const cardReading = openCard ? state.latest.get(openCard) : undefined;
  useEffect(() => {
    if (insight && !insightReading) setInsight(null);
    if (openCard && !cardReading) setOpenCard(null);
  }, [insight, insightReading, openCard, cardReading]);
  const examined = insightReading ? { indicator: insightReading.indicator, status: insightReading.status } : null;
  // "Why this forecast?" needs a forecast at the scrubbed time; scrubbing to before one closes it.
  const whyForecast = why ? state.forecast : null;
  useEffect(() => {
    if (why && !state.forecast) setWhy(false);
  }, [why, state.forecast]);
  const explain = useMemo(() => (whyForecast ? explainWeights(whyForecast.drivers) : null), [whyForecast]);
  const view = useMemo(
    () => buildBodyView({ model, focus, layers, glow, heartRate, breathRate, insight: examined, explain }),
    // `examined` is a new object each render, so depend on its parts.
    [model, focus, layers, glow, heartRate, breathRate, examined?.indicator, examined?.status, explain],
  );

  return (
    <div className="app">
      <MissionBar replay={replay} state={state} />
      <Co2Banner latest={state.latest} now={state.t} />
      <main className="home">
        {/* First in tab order so Emergency is one Tab away; CSS places it on screen. */}
        <ActionButtons onEmergency={onEmergency} />
        <section className="home__body" aria-label="Body">
          {whyForecast && <WhyForecast forecast={whyForecast} onExit={() => setWhy(false)} />}
          {!whyForecast && insightReading && <InsightBanner reading={insightReading} onExit={() => setInsight(null)} />}
          <Body view={view} scene={bodyScene} />
          {model === "female" && (
            <p className="body-note">
              Female organs. Muscles, skeleton and vessels are approximate (resized from the male model).
            </p>
          )}
          {!insightReading && !whyForecast && (
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
            <HealthSummary kind="physical" latest={state.latest} onDetails={setOpenCard} />
            <HealthSummary kind="mental" latest={state.latest} onDetails={setOpenCard} />
          </div>
          <ForecastPanel
            forecast={state.forecast}
            now={state.t}
            onWhy={() => {
              setInsight(null);
              setWhy(true);
            }}
          />
          <Trends replay={replay} crew={crew} state={state} range={range} onScrub={setT} />
          <TaskList tasks={state.tasks} notes={notes} onLog={setForm} />
        </div>
      </main>
      {cardReading && (
        <MeasurementCard
          reading={cardReading}
          history={seriesOf(replay, cardReading.indicator).filter((r) => r.t <= state.t && isNumeric(r)) as NumericReading[]}
          content={cardFor(cards, cardReading.indicator)}
          onClose={closeCard}
        />
      )}
      {form === "stand-test" && <StandTestForm crew={crew} t={range[1]} onSave={log} onClose={closeForm} />}
      {form === "post-eva" && <PostEvaForm crew={crew.id} t={range[1]} onSave={log} onClose={closeForm} />}
      <footer className="disclaimer">Decision support, not diagnosis.</footer>
    </div>
  );
}
