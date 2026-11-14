import { useEffect, useState } from "react";
import type { CrewRecord, ReplayFile } from "./contracts";
import { App } from "./App";
import { loadMission, missionFrom, withCabin, type MissionResult } from "./replay/load";
import { ActionButtons, type EmergencyRequest } from "./home/ActionButtons";
import marsDay3 from "./fixtures/mars-day3.replay.json";
import crewRecords from "./fixtures/crew-records.json";
import cabinDay3 from "./fixtures/iss-cabin-day3.json";

/**
 * Spec 2's home screen for one crew tablet (moved from Spec 2's main.tsx, same behaviour):
 * the app renders a replay file and its Crew record. `?replay=<path>` loads another replay
 * file served by the app, with its Crew record from the crew-records.json beside it, and the
 * habitat's cabin replay (CO₂, dose) merged in: `&cabin=<path>`, or the sample cabin day.
 *
 * Which replay a tablet shows: Spec 2 bundles a replay for crew A and one for crew B.
 * Crew without a replay get the Emergency / Help buttons only, and say why.
 */
const BUNDLED: MissionResult = missionFrom(marsDay3, crewRecords, "bundled crew-records.json");
/** The habitat's cabin day served beside the crew replays (Spec 2's sample). */
export const TABLET_CABIN = "/replay/iss-cabin-day3.json";
export const TABLET_REPLAYS: Record<string, string | "bundled"> = {
  A: "bundled",
  B: "/replay/mars-day3-female.json",
};

interface Mission {
  replay: ReplayFile;
  crew: CrewRecord;
}

export function CrewHome({ crew, onEmergency }: { crew: string; onEmergency: (r: EmergencyRequest) => void }) {
  const params = new URLSearchParams(location.search);
  const override = params.get("replay");
  const source = override ?? TABLET_REPLAYS[crew] ?? null;
  // A tablet's own replay comes with the sample cabin day; a ?replay= override only with &cabin=.
  const cabin = params.get("cabin") ?? (override ? undefined : TABLET_CABIN);
  const bundled =
    source === "bundled" && BUNDLED.ok
      ? { replay: withCabin(BUNDLED.replay, cabinDay3 as ReplayFile), crew: BUNDLED.crew }
      : null;
  const [mission, setMission] = useState<Mission | null>(bundled);
  const [error, setError] = useState<string | null>(source === "bundled" && !BUNDLED.ok ? BUNDLED.error : null);

  useEffect(() => {
    if (!source || source === "bundled") return;
    let alive = true;
    void loadMission(source, location.origin, fetch, cabin).then((result) => {
      if (!alive) return;
      if (result.ok) setMission({ replay: result.replay, crew: result.crew });
      else setError(result.error);
    });
    return () => {
      alive = false;
    };
  }, [source, cabin]);

  if (!source) {
    return (
      <main className="home" data-testid="home-no-replay">
        <ActionButtons onEmergency={onEmergency} />
        <p className="load-message">
          No replay data for crew {crew} yet (Spec 1 crew replays not bundled). Emergency and Help still work.
        </p>
      </main>
    );
  }
  if (error) {
    return (
      <main className="home">
        <ActionButtons onEmergency={onEmergency} />
        <p className="load-message">Could not load replay file: {error}</p>
      </main>
    );
  }
  if (!mission) return <p className="load-message">Loading replay…</p>;
  return <App replay={mission.replay} crew={mission.crew} onEmergency={onEmergency} />;
}
