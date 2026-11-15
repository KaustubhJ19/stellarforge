import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import { unlockAudioOnGesture } from "./alarm";
import App from "./App";
import "./styles.css";

unlockAudioOnGesture();

createRoot(document.getElementById("root")!).render(
  <StrictMode>
    <App />
  </StrictMode>,
);

if ("serviceWorker" in navigator && import.meta.env.PROD) {
  navigator.serviceWorker.register("/sw.js").catch(() => undefined);
}
