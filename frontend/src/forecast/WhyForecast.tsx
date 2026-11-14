import type { Forecast } from "../contracts";
import { DRIVERS, driverLabel } from "./drivers";
import { fmt, signed } from "./format";

/** "raised it by 0.6", "lowered it by 0.4", or "no effect". */
function effect(shap: number): string {
  const size = fmt(Math.abs(shap));
  if (size === "0") return "no effect";
  return `${shap > 0 ? "raised" : "lowered"} it by ${size}`;
}

/**
 * "Why this forecast?": what drove the general model, as words and as a heat-map on the body
 * (drawn by the body view in one neutral hue, never a Status colour).
 */
export function WhyForecast({ forecast, onExit }: { forecast: Forecast; onExit: () => void }) {
  const drivers = Object.entries(forecast.drivers).sort(([, a], [, b]) => Math.abs(b) - Math.abs(a));
  return (
    <section className="why-forecast" aria-label="Why this forecast?">
      <h2>What drove the model</h2>
      <p className="why-forecast__key">
        <span className="why-forecast__swatch" aria-hidden="true" /> Heat-map on the body: brighter means it mattered more.
        Not a health Status.
      </p>
      <ul aria-label="Drivers" className="why-forecast__drivers">
        {drivers.map(([key, shap]) => (
          <li key={key}>
            {driverLabel(key)}: {effect(shap)}
            {(DRIVERS[key]?.place.length ?? 0) === 0 ? " (not shown on the body)" : ""}
          </li>
        ))}
      </ul>
      <p className="form-note">
        These explain the general model's forecast of {fmt(forecast.population)}. Your own pattern adjusts it by{" "}
        {signed(forecast.personal_correction)}, to {fmt(forecast.value)}.
      </p>
      <button onClick={onExit}>Back to body</button>
    </section>
  );
}
