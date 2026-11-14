import { useEffect, useRef, useState } from "react";
import type { BodyScene, BodySceneFactory, BodyView } from "./view";

type LoadState = { kind: "loading" } | { kind: "ready" } | { kind: "error"; message: string };

/** Hosts the 3D body. All drawing is delegated to the BodyScene. */
export function Body({ view, scene }: { view: BodyView; scene: BodySceneFactory }) {
  const host = useRef<HTMLDivElement>(null);
  const live = useRef<BodyScene | null>(null);
  const [load, setLoad] = useState<LoadState>({ kind: "loading" });

  useEffect(() => {
    setLoad({ kind: "loading" });
    try {
      live.current = scene(host.current!, {
        onLoaded: () => setLoad({ kind: "ready" }),
        onError: (message) => setLoad({ kind: "error", message }),
      });
    } catch (e) {
      setLoad({ kind: "error", message: (e as Error).message });
    }
    return () => {
      live.current?.dispose();
      live.current = null;
    };
  }, [scene]);

  useEffect(() => {
    live.current?.apply(view);
  }, [view, scene]);

  return (
    <div className="body-host" ref={host} aria-label="3D body" role="img">
      {load.kind === "loading" && <p className="body-host__message">Loading body…</p>}
      {load.kind === "error" && <p className="body-host__message">3D body unavailable: {load.message}</p>}
    </div>
  );
}
