import { Component, StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import type { CrewRecord, ReplayFile } from "./contracts";
import { App } from "./App";
import { loadMission, missionFrom, type MissionResult } from "./replay/load";
import marsDay3 from "./fixtures/mars-day3.replay.json";
import crewRecords from "./fixtures/crew-records.json";
import "./theme.css";

/** Last line of defence: say what broke instead of showing a blank page. */
class ErrorBoundary extends Component<{ children: ReactNode }, { error: Error | null }> {
  state = { error: null as Error | null };
  static getDerivedStateFromError(error: Error) {
    return { error };
  }
  render() {
    if (this.state.error) {
      return <p className="load-message">Something went wrong showing this replay: {this.state.error.message}</p>;
    }
    return this.props.children;
  }
}

/**
 * The app never talks to the service: it renders a replay file and its Crew record.
 * By default the bundled Mars fixture; `?replay=<path>` loads another replay file served by
 * the app itself, with its Crew record from the crew-records.json beside it.
 */
interface Mission {
  replay: ReplayFile;
  crew: CrewRecord;
}
const BUNDLED: MissionResult = missionFrom(marsDay3, crewRecords, "bundled crew-records.json");
const bundledMission = BUNDLED.ok ? { replay: BUNDLED.replay, crew: BUNDLED.crew } : null;

function Root() {
  const url = new URLSearchParams(location.search).get("replay");
  const [mission, setMission] = useState<Mission | null>(url ? null : bundledMission);
  const [error, setError] = useState<string | null>(!url && !BUNDLED.ok ? BUNDLED.error : null);

  useEffect(() => {
    if (!url) return;
    void loadMission(url, location.origin).then((result) => {
      if (result.ok) setMission({ replay: result.replay, crew: result.crew });
      else setError(result.error);
    });
  }, [url]);

  if (error) return <p className="load-message">Could not load replay file: {error}</p>;
  if (!mission) return <p className="load-message">Loading replay…</p>;
  return <App replay={mission.replay} crew={mission.crew} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Root />
    </ErrorBoundary>
  </StrictMode>,
);
