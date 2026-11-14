import { Component, StrictMode, useEffect, useState, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import type { ReplayFile } from "./contracts";
import { App } from "./App";
import { loadReplay } from "./replay/load";
import marsDay3 from "./fixtures/mars-day3.replay.json";
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
 * The app never talks to the service: it renders a replay file. By default the
 * bundled Mars fixture; `?replay=<path>` loads another replay file served by the app itself.
 */
function Root() {
  const url = new URLSearchParams(location.search).get("replay");
  const [replay, setReplay] = useState<ReplayFile | null>(url ? null : (marsDay3 as ReplayFile));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (!url) return;
    void loadReplay(url, location.origin).then((result) => {
      if (result.ok) setReplay(result.replay);
      else setError(result.error);
    });
  }, [url]);

  if (error) return <p className="load-message">Could not load replay file: {error}</p>;
  if (!replay) return <p className="load-message">Loading replay…</p>;
  return <App replay={replay} />;
}

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Root />
    </ErrorBoundary>
  </StrictMode>,
);
