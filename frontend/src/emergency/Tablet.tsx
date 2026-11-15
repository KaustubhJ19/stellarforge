import { useCallback, useEffect, useRef, useState } from "react";
import { api, ApiError, type View } from "./api";
import { Screen } from "./screens";
import { flush, loadBundle, noteMissionTime, queue, saveBundle, type Bundle } from "./offline";
import { OfflineFlow, startOffline, type OfflineSession } from "./OfflineFlow";

const POLL_MS = 500;
const BUNDLE_MS = 30_000;

export default function Tablet({ crew }: { crew: string }) {
  const [view, setView] = useState<View | null>(null);
  const [offline, setOffline] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [session, setSession] = useState<OfflineSession | null>(null);
  const [bundle, setBundle] = useState<Bundle | null>(() => loadBundle());
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
      if (alive.current && e instanceof ApiError && e.status === 0) setOffline(true);
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

  if (session && bundle) {
    return <OfflineFlow crew={crew} bundle={bundle} session={session} onEnd={() => setSession(null)} />;
  }
  if (offline && (!view || view.screen === "idle")) {
    return <OfflineHome crew={crew} bundle={bundle} start={(p) => setSession(startOffline(crew, p))} />;
  }
  return (
    <>
      <Screen crew={crew} view={view} offline={offline} error={error} act={act} />
      {offline && bundle && view && view.screen !== "idle" && (
        <main>
          <button className="big secondary" onClick={() => setSession(startOffline(crew, view.patient))}>
            Continue with offline steps
          </button>
        </main>
      )}
    </>
  );
}

// Shown when the service is unreachable and no emergency is open on this tablet.
function OfflineHome({ crew, bundle, start }: { crew: string; bundle: Bundle | null; start: (patient: string) => void }) {
  const [pick, setPick] = useState(false);
  return (
    <main className="home">
      <h1>Crew tablet: {crew}</h1>
      <p className="offline" role="status">Service unavailable — continuing offline</p>
      {!bundle ? (
        <p className="error" role="alert">No cached protocol on this tablet yet. Contact ground.</p>
      ) : (
        <>
          <button className="big emergency-button" onClick={() => start(crew)}>Emergency</button>
          <button className="big" onClick={() => setPick(!pick)}>Help a crewmate</button>
          {pick && (
            <div className="choices">
              {bundle.profile.crew.filter((c) => c !== crew).map((c) => (
                <button key={c} className="big" onClick={() => start(c)}>{bundle.names[c] ?? c}</button>
              ))}
            </div>
          )}
        </>
      )}
    </main>
  );
}
