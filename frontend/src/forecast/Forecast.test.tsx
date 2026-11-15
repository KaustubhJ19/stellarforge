import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { missionWith, type Mission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { Forecast } from "../contracts";

const HOUR = 3600;

/** Spec 3's forecast fields (their message of 2026-11-15): base + drivers = population; value adds the personal correction. */
function forecast(over: Partial<Forecast> = {}): Forecast {
  return {
    crew: "A", t: 7 * HOUR, value: 6.4, low: 4.9, high: 7.8, label: "",
    population: 6.1, personal_correction: 0.3, base: 5.6,
    drivers: { fatigue: -0.35, mood: 0.05, readiness: 0.6, sleep_duration_h: -0.4, sleep_quality: 0.2, soreness: -0.1, stress: 0.5 },
    ...over,
  };
}

function withForecasts(...forecasts: Forecast[]): Mission {
  const m = missionWith([
    { indicator: "heart_rate", value: 70, t: 6 * HOUR },
    { indicator: "heart_rate", value: 131, t: 12 * HOUR, status: "red" },
  ]);
  for (const f of forecasts) m.replay.events.push({ t: f.t, type: "forecast", payload: f });
  m.replay.events.sort((a, b) => a.t - b.t);
  return m;
}

function renderWith(mission: Mission) {
  const body = fakeBodyScene();
  render(<App {...mission} bodyScene={body.factory} />);
  return body;
}

const panel = () => screen.getByRole("region", { name: "Readiness forecast" });

describe("readiness forecast panel", () => {
  it("shows tomorrow's readiness with its range, labelled an estimate", () => {
    renderWith(withForecasts(forecast()));
    expect(panel()).toHaveTextContent("6.4 of 10");
    expect(panel()).toHaveTextContent("Likely between 4.9 and 7.8");
    expect(panel()).toHaveTextContent("Estimate, not validated");
  });

  it("explains Spec 3's labels in plain words", () => {
    renderWith(withForecasts(forecast({ label: "learning your pattern", low: 0, high: 10 })));
    expect(panel()).toHaveTextContent("Learning your pattern: too few days of your data yet, so the range is the whole 0–10.");
  });

  it("says when the range is too wide to trust", () => {
    renderWith(withForecasts(forecast({ label: "re-measure" })));
    expect(panel()).toHaveTextContent("Re-measure: the range is too wide to trust.");
  });

  it("shows the forecast known at the scrubbed time, and none before the first", () => {
    renderWith(withForecasts(forecast({ t: 7 * HOUR, value: 6.4 }), forecast({ t: 10 * HOUR, value: 5.1 })));
    expect(panel()).toHaveTextContent("5.1 of 10");
    const clock = screen.getByRole("slider", { name: "Mission clock" });
    fireEvent.change(clock, { target: { value: String(8 * HOUR) } });
    expect(panel()).toHaveTextContent("6.4 of 10");
    fireEvent.change(clock, { target: { value: String(6 * HOUR) } });
    expect(panel()).toHaveTextContent("No forecast yet.");
  });

  it("says when the forecast was made, and flags one older than the scrubbed day", () => {
    const m = withForecasts(forecast({ t: 7 * HOUR }));
    const later = 2 * 86400 + 9 * HOUR;
    m.replay.events.push({
      t: later, type: "reading",
      payload: { crew: "A", indicator: "heart_rate", value: 71, unit: "bpm", t: later, source: "sensor", confidence: 1, state: "released" },
    });
    renderWith(m);
    expect(panel()).toHaveTextContent("Made Day 1 · 07:00, for the next day");
    expect(panel()).toHaveTextContent("Older than today: no newer forecast yet.");
  });

  it("ignores another crew member's forecast", () => {
    renderWith(withForecasts(forecast({ crew: "B" })));
    expect(panel()).toHaveTextContent("No forecast yet.");
  });
});

describe('"Why this forecast?" view', () => {
  async function openWhy(f = forecast()) {
    const body = renderWith(withForecasts(f));
    await userEvent.click(within(panel()).getByRole("button", { name: "Why this forecast?" }));
    return body;
  }
  const view = () => screen.getByRole("region", { name: "Why this forecast?" });

  it("is a separate view labelled 'what drove the model'", async () => {
    await openWhy();
    expect(within(view()).getByRole("heading", { name: "What drove the model" })).toBeInTheDocument();
    expect(screen.queryByRole("group", { name: "Flagged on the body" })).not.toBeInTheDocument();
  });

  it("draws an outline heat-map on the body and never a Status colour", async () => {
    const body = await openWhy();
    const v = body.view;
    expect(v.wholeBody).toBeNull();
    expect(Object.values(v.structures).every((s) => s.status === null)).toBe(true);
    // fatigue + readiness + stress all reach the prefrontal cortex: the strongest.
    expect(v.structures["brain.prefrontal"].explain).toBe(1);
    // sleep length + sleep quality: |-0.4| + |0.2| = 0.6 of 1.45.
    expect(v.structures["brain.hypothalamus"].explain).toBeCloseTo(0.6 / 1.45, 3);
    expect(v.structures["muscle.thigh"].explain).toBeCloseTo(0.1 / 1.45, 3);
    expect(v.structures.heart.explain).toBeNull();
  });

  it("says 'no effect' for a zero driver and never shows -0", async () => {
    await openWhy(forecast({ drivers: { mood: 0, stress: 0.5 }, personal_correction: -0.001, population: 6.1, value: 6.1 }));
    expect(within(view()).getByRole("list", { name: "Drivers" })).toHaveTextContent("Mood: no effect");
    expect(view()).toHaveTextContent("adjusts it by +0, to 6.1");
  });

  it("keys the heat-map the way it is drawn: brighter means it mattered more", async () => {
    await openWhy();
    expect(view()).toHaveTextContent("brighter means it mattered more");
  });

  it("lists the drivers, biggest first, in words, with mood not placed on the body", async () => {
    await openWhy();
    const items = within(within(view()).getByRole("list", { name: "Drivers" })).getAllByRole("listitem");
    expect(items.map((li) => li.textContent)).toEqual([
      "Yesterday's readiness: raised it by 0.6",
      "Stress: raised it by 0.5",
      "Sleep length: lowered it by 0.4",
      "Fatigue: lowered it by 0.35",
      "Sleep quality: raised it by 0.2",
      "Muscle soreness: lowered it by 0.1",
      "Mood: raised it by 0.05 (not shown on the body)",
    ]);
  });

  it("says the drivers explain the general model, and the personal adjustment comes on top", async () => {
    await openWhy();
    expect(view()).toHaveTextContent(
      "These explain the general model's forecast of 6.1. Your own pattern adjusts it by +0.3, to 6.4.",
    );
  });

  it("goes back to the Status body", async () => {
    const body = await openWhy();
    await userEvent.click(within(view()).getByRole("button", { name: "Back to body" }));
    expect(screen.queryByRole("region", { name: "Why this forecast?" })).not.toBeInTheDocument();
    expect(body.view.structures.heart.status).toBe("red");
    expect(body.view.structures.heart.explain).toBeNull();
  });
});
