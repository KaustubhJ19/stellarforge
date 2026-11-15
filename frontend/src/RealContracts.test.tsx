import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { alertFor, marsMission, missionWith } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";
import type { Reading } from "./contracts";

const HOUR = 3600;

describe("Status comes from Alerts (Spec 1 Readings carry no Status)", () => {
  it("shows an Indicator with a Reading and no Alert as Normal", () => {
    render(<App {...missionWith([{ indicator: "heart_rate", value: 131 }])} bodyScene={fakeBodyScene().factory} />);
    const hr = screen.getByRole("group", { name: "Heart rate" });
    expect(hr).toHaveAttribute("data-status", "green");
    expect(within(hr).getByText("Normal")).toBeInTheDocument();
  });

  it("takes the newest Alert's Status at the scrubbed time, so a green Alert clears it", () => {
    const mission = missionWith([
      { indicator: "heart_rate", value: 131, t: 8 * HOUR, status: "red" },
      { indicator: "heart_rate", value: 70, t: 10 * HOUR },
    ]);
    const later = mission.replay.events[2].payload as Reading;
    mission.replay.events.push({ t: later.t, type: "alert", payload: alertFor(later, "green", 9) });
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);

    const hr = () => screen.getByRole("group", { name: "Heart rate" });
    expect(hr()).toHaveAttribute("data-status", "green");
    fireEvent.change(screen.getByRole("slider", { name: "Mission clock" }), { target: { value: String(9 * HOUR) } });
    expect(hr()).toHaveAttribute("data-status", "red");
  });

  it("ignores event types the app does not show (trigger, crew_report)", () => {
    const mission = missionWith([{ indicator: "heart_rate", value: 70 }]);
    const extra = [
      { t: 9 * HOUR, type: "crew_report", payload: { crew: "A", t: 9 * HOUR, report: "chest pain", source: "crew-reported" } },
      { t: 9 * HOUR, type: "trigger", payload: { kind: "manual", crew: "A", t: 9 * HOUR, reason: "test" } },
    ];
    mission.replay.events.push(...(extra as never[]));
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Heart rate" })).toBeInTheDocument();
  });
});

describe("mission profile from its id", () => {
  it("names a known profile and gives its ground delay", () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(within(bar).getByText("Mars transit")).toBeInTheDocument();
    expect(within(bar).getByText("28.5 min")).toBeInTheDocument();
  });

  it("shows an unknown profile's id and says the delay is not known", () => {
    const mission = marsMission();
    mission.replay.profile = "lunar_gateway_test";
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(within(bar).getByText("lunar_gateway_test")).toBeInTheDocument();
    expect(within(bar).getByText("Not known")).toBeInTheDocument();
  });
});

describe("your normal band from the Crew record's anchor", () => {
  async function heartTrend(mission = marsMission()) {
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const trends = screen.getByRole("region", { name: "Trends" });
    await userEvent.click(within(trends).getByRole("button", { name: "Heart rate" }));
    return screen.getByRole("figure", { name: "Heart rate trend" });
  }

  it("shades anchor mean ± 2 SD", async () => {
    const mission = marsMission();
    mission.crew.anchor.heart_rate = { mean: 64, sd: 4 };
    expect(within(await heartTrend(mission)).getByLabelText("Your normal: 56–72 bpm")).toBeInTheDocument();
  });

  it("draws no band for an Indicator the anchor does not cover", async () => {
    const mission = marsMission();
    delete mission.crew.anchor.heart_rate;
    expect(within(await heartTrend(mission)).queryByLabelText(/Your normal/)).not.toBeInTheDocument();
  });
});

describe("body follows the Crew record", () => {
  it("uses the female body when the Crew record says female", () => {
    const body = fakeBodyScene();
    const mission = marsMission();
    mission.crew.sex = "female";
    render(<App {...mission} bodyScene={body.factory} />);
    expect(body.view.model).toBe("female");
  });
});

describe("real replay file details", () => {
  it("shows quarantined Readings: Spec 3 holds them while an Alert is open, they are the abnormal values", () => {
    const mission = missionWith([
      { indicator: "heart_rate", value: 70, t: 8 * HOUR },
      { indicator: "heart_rate", value: 131, t: 9 * HOUR, state: "quarantined", status: "red" },
    ]);
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const hr = screen.getByRole("group", { name: "Heart rate" });
    expect(hr).toHaveTextContent("131");
    expect(hr).toHaveAttribute("data-status", "red");
  });

  it("ignores another crew member's Alerts", () => {
    const mission = missionWith([{ indicator: "heart_rate", value: 70 }]);
    const reading = mission.replay.events[0].payload as Reading;
    mission.replay.events.push({ t: reading.t, type: "alert", payload: { ...alertFor(reading, "red"), crew: "B" } });
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Heart rate" })).toHaveAttribute("data-status", "green");
  });

  it("charts a 0-1 fraction as a percentage, as the tile shows it", async () => {
    const mission = missionWith([
      { indicator: "spo2", value: 0.97, unit: "fraction", t: 8 * HOUR },
      { indicator: "spo2", value: 0.98, unit: "fraction", t: 9 * HOUR },
    ]);
    mission.crew.anchor.spo2 = { mean: 0.975, sd: 0.01 };
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const chart = screen.getByRole("figure", { name: "SpO₂ trend" });
    expect(chart).toHaveTextContent("(%)");
    expect(within(chart).getByLabelText("Your normal: 95.5–99.5 %")).toBeInTheDocument();
  });

  it("draws no band from an anchor entry that is not a number pair", async () => {
    const mission = marsMission();
    mission.crew.anchor.heart_rate = { mean: 64 } as never;
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const trends = screen.getByRole("region", { name: "Trends" });
    await userEvent.click(within(trends).getByRole("button", { name: "Heart rate" }));
    expect(within(screen.getByRole("figure", { name: "Heart rate trend" })).queryByLabelText(/Your normal/)).not.toBeInTheDocument();
  });
});

describe("habitat Readings in the trends", () => {
  it("offers the accumulated dose but not cabin air or dose-rate breakdowns", () => {
    const mission = missionWith([
      { indicator: "heart_rate", value: 70, t: 8 * HOUR },
      { indicator: "heart_rate", value: 72, t: 9 * HOUR },
    ]);
    for (const indicator of ["radiation_dose_accumulated", "cabin_co2", "cabin_temperature", "radiation_dose_gcr"]) {
      for (const t of [8 * HOUR, 9 * HOUR]) {
        mission.replay.events.push({
          t, type: "reading",
          payload: { crew: "habitat", indicator, value: 1, unit: "x", t, source: "sensor", confidence: 1, state: "released" },
        });
      }
    }
    mission.replay.events.sort((a, b) => a.t - b.t);
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const picker = within(screen.getByRole("region", { name: "Trends" }));
    expect(picker.getAllByRole("button", { pressed: undefined }).map((b) => b.textContent)).toEqual(
      expect.arrayContaining(["Heart rate", "Radiation dose"]),
    );
    for (const raw of ["cabin_co2", "cabin_temperature", "radiation_dose_gcr"]) {
      expect(picker.queryByRole("button", { name: raw })).not.toBeInTheDocument();
    }
  });
});

describe("green Alerts clear one kind of Alert (Spec 3, db44200)", () => {
  function mission(extra: { kind: "acute" | "drift"; status: "green" | "amber" | "red"; t: number; safety?: boolean }[]) {
    const m = missionWith([
      { indicator: "heart_rate", value: 70, t: 8 * HOUR },
      { indicator: "heart_rate", value: 72, t: 12 * HOUR },
    ]);
    const reading = m.replay.events[0].payload as Reading;
    extra.forEach(({ kind, status, t, safety }, i) => {
      const a = { ...alertFor({ ...reading, t }, status, 100 + i, kind) };
      if (safety) a.deviation = { value: 160, bound: { low: 50, high: 150 } };
      m.replay.events.push({ t, type: "alert", payload: a });
    });
    m.replay.events.sort((a, b) => a.t - b.t);
    return m;
  }
  const hr = () => screen.getByRole("group", { name: "Heart rate" });

  it("keeps a drift Watch when only the acute Alert clears", () => {
    render(<App {...mission([
      { kind: "drift", status: "amber", t: 9 * HOUR },
      { kind: "acute", status: "red", t: 10 * HOUR },
      { kind: "acute", status: "green", t: 11 * HOUR },
    ])} bodyScene={fakeBodyScene().factory} />);
    expect(hr()).toHaveAttribute("data-status", "amber");
  });

  it("keeps a Safety-bound Alert when the acute (sigma) Alert clears", () => {
    render(<App {...mission([
      { kind: "acute", status: "red", t: 9 * HOUR, safety: true },
      { kind: "acute", status: "amber", t: 10 * HOUR },
      { kind: "acute", status: "green", t: 11 * HOUR },
    ])} bodyScene={fakeBodyScene().factory} />);
    expect(hr()).toHaveAttribute("data-status", "red");
  });

  it("shows Normal once every kind has cleared", () => {
    render(<App {...mission([
      { kind: "drift", status: "amber", t: 9 * HOUR },
      { kind: "acute", status: "red", t: 10 * HOUR },
      { kind: "acute", status: "green", t: 10.5 * HOUR },
      { kind: "drift", status: "green", t: 11 * HOUR },
    ])} bodyScene={fakeBodyScene().factory} />);
    expect(hr()).toHaveAttribute("data-status", "green");
  });

  it("calls red 'Alert', Spec 3's word", () => {
    render(<App {...mission([{ kind: "acute", status: "red", t: 11 * HOUR }])} bodyScene={fakeBodyScene().factory} />);
    expect(within(hr()).getByText("Alert")).toBeInTheDocument();
  });
});

describe("your normal band stays inside the scale", () => {
  function chartFor(indicator: string, unit: string, values: number[], anchor: { mean: number; sd: number }) {
    const mission = missionWith(values.map((value, i) => ({ indicator, value, unit, t: (8 + i) * HOUR })));
    mission.crew.anchor[indicator] = anchor;
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    return screen.getByRole("figure", { name: /trend$/ });
  }

  it("trims a self-report band at the bottom of its 1-5 scale", () => {
    const chart = chartFor("stress", "score 1-5", [2, 3], { mean: 2, sd: 0.6 });
    expect(within(chart).getByLabelText("Your normal: 1–3.2 score 1-5")).toBeInTheDocument();
  });

  it("trims an SpO₂ band at 100%", () => {
    const chart = chartFor("spo2", "fraction", [0.99, 0.98], { mean: 0.99, sd: 0.01 });
    expect(within(chart).getByLabelText("Your normal: 97–100 %")).toBeInTheDocument();
  });

  it("leaves a band on an open-ended unit as mean ± 2 SD", () => {
    const chart = chartFor("heart_rate", "bpm", [60, 62], { mean: 64, sd: 4 });
    expect(within(chart).getByLabelText("Your normal: 56–72 bpm")).toBeInTheDocument();
  });
});

describe("recorded replays from Spec 3's proposed script", () => {
  it("loads reading_state events without doubling Readings, and shows the forecast", async () => {
    const mission = missionWith([
      { indicator: "heart_rate", value: 70, t: 8 * HOUR },
      { indicator: "heart_rate", value: 131, t: 9 * HOUR, status: "red" },
    ]);
    const held = mission.replay.events.find((e) => e.type === "reading" && e.payload.value === 131)!.payload as Reading;
    const extra = [
      { t: 9 * HOUR, type: "reading_state", payload: { ...held, state: "quarantined" } },
      { t: 10 * HOUR, type: "reading_state", payload: { ...held, state: "released" } },
      {
        t: 10 * HOUR, type: "forecast",
        payload: { crew: "A", t: 10 * HOUR, value: 6.2, low: 4.5, high: 7.9, label: "", population: 6.0,
          personal_correction: 0.2, base: 5.5, drivers: { fatigue: -0.4, sleep_duration_h: 0.9 } },
      },
    ];
    mission.replay.events.push(...(extra as never[]));
    mission.replay.events.sort((a, b) => a.t - b.t);
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Heart rate" })).toHaveTextContent("131");
    await userEvent.click(within(screen.getByRole("region", { name: "Trends" })).getByRole("button", { name: "Heart rate" }));
    await userEvent.click(screen.getByRole("button", { name: "Show as table" }));
    expect(within(screen.getByRole("table")).getAllByRole("row")).toHaveLength(3); // header + 2 Readings, not 4
    expect(screen.getByRole("region", { name: "Readiness forecast" })).toHaveTextContent("6.2 of 10");
  });
});

describe("units as the crew reads them", () => {
  it("shows Pulse's 1/min as /min", () => {
    render(<App {...missionWith([{ indicator: "respiration_rate", value: 15, unit: "1/min" }])} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Respiration" })).toHaveTextContent("15 /min");
  });
});

describe("emergency Alerts (Spec 3, recorded emergency replay)", () => {
  it("leaves an emergency Alert with no Indicator to Spec 4's flow: no tile or body change, nothing breaks", () => {
    const m = missionWith([{ indicator: "heart_rate", value: 70, t: 8 * HOUR }]);
    m.replay.events.push({
      t: 9 * HOUR, type: "alert",
      payload: { id: "B-emergency", kind: "emergency", crew: "A", indicator: null, deviation: null, status: "red", urgency: "ACT_NOW", likely_causes: [], t: 9 * HOUR },
    });
    const body = fakeBodyScene();
    render(<App {...m} bodyScene={body.factory} />);
    expect(screen.getByRole("group", { name: "Heart rate" })).toHaveAttribute("data-status", "green");
    expect(body.view.wholeBody).toBeNull();
  });
});
