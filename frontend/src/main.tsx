import { Component, StrictMode, type ReactNode } from "react";
import { createRoot } from "react-dom/client";
import { unlockAudioOnGesture } from "./alarm";
import Shell from "./Shell";
import "./theme.css";
import "./styles.css";

/** Last line of defence: say what broke instead of showing a blank page. (Spec 2) */
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

unlockAudioOnGesture();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <ErrorBoundary>
      <Shell />
    </ErrorBoundary>
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register("/sw.js").catch(() => undefined);
}
