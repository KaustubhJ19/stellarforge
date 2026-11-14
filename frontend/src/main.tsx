import { StrictMode, useEffect, useState } from "react";
import { createRoot } from "react-dom/client";
import type { ReplayFile } from "./contracts";
import { App } from "./App";
import marsDay3 from "./fixtures/mars-day3.replay.json";
import "./theme.css";

/**
 * The app never talks to the service: it renders a replay file. By default the
 * bundled Mars fixture; `?replay=<url>` loads any static replay file instead.
 */
function Root() {
  const url = new URLSearchParams(location.search).get("replay");
  const [replay, setReplay] = useState<ReplayFile | null>(url ? null : (marsDay3 as ReplayFile));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    fetch(url)
      .then((r) => (r.ok ? r.json() : Promise.reject(new Error(`${r.status} ${r.statusText}`))))
      .then(setReplay)
      .catch((e: Error) => setError(e.message));
  }, [url]);

  if (error) return <p className="load-message">Could not load replay file: {error}</p>;
  if (!replay) return <p className="load-message">Loading replay…</p>;
  return <App replay={replay} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <Root />
  </StrictMode>,
);
