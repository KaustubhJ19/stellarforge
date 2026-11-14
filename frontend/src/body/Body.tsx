import { useEffect, useRef, useState } from "react";
import type { BodyScene, BodySceneFactory, BodyView } from "./view";

/** Hosts the 3D body. All drawing is delegated to the BodyScene. */
export function Body({ view, scene }: { view: BodyView; scene: BodySceneFactory }) {
  const host = useRef<HTMLDivElement>(null);
  const live = useRef<BodyScene | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    try {
      live.current = scene(host.current!);
    } catch (e) {
      setError((e as Error).message);
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
      {error && <p className="body-host__error">3D body unavailable: {error}</p>}
    </div>
  );
}
