import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type View } from "./api";
import { AccessLog, Screen } from "./screens";
import { CrewHome } from "./CrewHome";
import type { EmergencyRequest } from "./home/ActionButtons";
import { flush, loadBundle, missionNow, noteMissionTime, queue, saveBundle, type Bundle } from "./offline";
import { OfflineFlow, startOffline, type OfflineSession } from "./OfflineFlow";

const POLL_MS = 500;
const BUNDLE_MS = 30_000;

/**
 * One crew tablet. Idle: Spec 2's home (3D body, trends, tasks) with its Emergency and Help
 * buttons wired to the Spec 4 flow. Any emergency screen from the Spec 4 backend takes over.
 * Backend down: the same home stays; Emergency / Help start the offline emergency mode.
 */
export default function Tablet({ crew }: { crew: string }) {
  const [view, setView] = useState<View | null>(null);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<OfflineSession | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(() => loadBundle());
  const [picking, setPicking] = useState(false);
  const alive = useRef(true);
  const lastBundle = useRef(0);

  const refresh = useCallback(async () => {
    try {
      const v = await api.view(crew);
      if (!alive.current) return;
      setView(v);
      setOffline(false);
      noteMissionTime(v.t);
      if (Date.now() - lastBundle.current > BUNDLE_MS) {
        lastBundle.current = Date.now();
        const b = await fetch("/api/offline-bundle").then((r) => (r.ok ? r.json() : null)).catch(() => null);
        if (b) {
          saveBundle(b);
          setBundle(b);
        }
      }
      if (queue().length) await flush(crew).catch(() => undefined);
    } catch (e) {
      // 0 = unreachable; 404 = the app is served without the Spec 4 backend (static preview).
      if (alive.current && e instanceof ApiError && (e.status === 0 || e.status === 404)) setOffline(true);
    }
  }, [crew]);

  useEffect(() => {
    alive.current = true;
    refresh();
    const id = setInterval(refresh, POLL_MS);
    return () => {
      alive.current = false;
      clearInterval(id);
    };
  }, [refresh]);

  const act = useCallback(
    async (fn: () => Promise<unknown>) => {
      setError(null);
      try {
        await fn();
      } catch (e) {
        if (e instanceof ApiError && e.status === 0) setOffline(true);
        else setError(e instanceof Error ? e.message : String(e));
      }
      await refresh();
    },
    [refresh],
  );

  // Emergency or Help a crewmate for `patient`: the same shared flow (one manual Trigger).
  const startFor = useCallback(
    (patient: string, reason: string) => {
      setPicking(false);
      if (!offline) return act(() => api.trigger(patient, view?.t ?? missionNow(), reason));
      if (!bundle) {
        setError("No cached protocol on this tablet yet. Contact ground.");
        return;
      }
      setSession(startOffline(crew, patient));
    },
    [act, bundle, crew, offline, view],
  );

  const onEmergency = useCallback(
    (request: EmergencyRequest) => {
      if (request === "emergency") void startFor(crew, "Emergency button");
      else setPicking(true);
    },
    [crew, startFor],
  );

  if (session && bundle) {
    return <OfflineFlow crew={crew} bundle={bundle} session={session} onEnd={() => setSession(null)} />;
  }
  if (view && view.screen !== "idle") {
    return (
      <>
        <Screen crew={crew} view={view} offline={offline} error={error} act={act} />
        {offline && bundle && (
          <div className="sf4 sf4-strip">
            <button className="big secondary" onClick={() => setSession(startOffline(crew, view.patient))}>
              Continue with offline steps
            </button>
          </div>
        )}
      </>
    );
  }
  const crewmates = (bundle?.profile.crew ?? []).filter((c) => c !== crew);
  return (
    <>
      <CrewHome crew={crew} onEmergency={onEmergency} />
      <div className="sf4 sf4-strip" data-testid="tablet-strip">
        <p className="note">Tablet: crew {crew}</p>
        {offline && <p className="offline" role="status">Service unavailable — continuing offline</p>}
        {error && <p className="error" role="alert">{error}</p>}
        {!offline && <AccessLog crew={crew} />}
      </div>
      {picking && (
        <div className="sf4-dialog" role="dialog" aria-modal="true" aria-label="Help a crewmate">
          <div className="sf4">
            <h1>Help a crewmate</h1>
            {crewmates.length === 0 ? (
              <p className="note">Crew list not available yet.</p>
            ) : (
              <div className="choices">
                {crewmates.map((c) => (
                  <button key={c} className="big" onClick={() => void startFor(c, `Help a crewmate (requested by ${crew})`)}>
                    {bundle?.names[c] ?? c}
                  </button>
                ))}
              </div>
            )}
            <div className="nav">
              <button className="big" onClick={() => setPicking(false)}>Cancel</button>
            </div>
          </div>
        </div>
      )}
    </>
  );
}
