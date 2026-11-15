import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { marsMission, missionWith } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";
import type { Reading } from "./contracts";

const HOUR = 3600;
const DAY = 86400;

describe("values as the real replays carry them (workstream-1-data-service replay/)", () => {
  it("rounds long decimals for display", () => {
    render(<App {...missionWith([{ indicator: "resting_heart_rate", value: 64.0808973312378, unit: "bpm" }])} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Resting heart rate" })).toHaveTextContent("64.1 bpm");
  });

  it("shows °C for degC", () => {
    render(<App {...missionWith([{ indicator: "body_temperature", value: 37.1, unit: "degC" }])} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Body temperature" })).toHaveTextContent("37.1 °C");
  });

  it("knows soreness, a 1-5 self-report on the thigh muscles", () => {
    render(<App {...missionWith([{ indicator: "soreness", value: 2, unit: "score 1-5" }])} bodyScene={fakeBodyScene().factory} />);
    expect(within(screen.getByRole("region", { name: "Physical health" })).getByRole("group", { name: "Muscle soreness" })).toHaveTextContent("2 of 5");
  });

  it("shows a text value (cardiac rhythm) in words, and keeps it out of the number charts", async () => {
    const m = missionWith([
      { indicator: "heart_rate", value: 70, t: 8 * HOUR },
      { indicator: "heart_rate", value: 71, t: 9 * HOUR },
    ]);
    for (const [t, value] of [[8 * HOUR, "NormalSinus"], [9 * HOUR, "CoarseVentricularFibrillation"]] as const) {
      const r: Reading = { crew: "A", indicator: "cardiac_rhythm", value, unit: "rhythm", t, source: "sim", confidence: 1, state: "released" };
      m.replay.events.push({ t, type: "reading", payload: r });
    }
    m.replay.events.sort((a, b) => a.t - b.t);
    render(<App {...m} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Heart rhythm" })).toHaveTextContent("Coarse ventricular fibrillation");
    const trends = screen.getByRole("region", { name: "Trends" });
    expect(within(trends).queryByRole("button", { name: "Heart rhythm" })).not.toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Heart rhythm details" }));
    expect(screen.getByRole("dialog", { name: "Heart rhythm" })).toHaveTextContent("Coarse ventricular fibrillation");
  });
});

describe("cabin data that stops before the crew data (RR-1 covers 42 days)", () => {
  function staleCabin() {
    const m = missionWith([
      { indicator: "heart_rate", value: 70, t: 1 * HOUR },
      { indicator: "heart_rate", value: 71, t: 10 * DAY },
    ]);
    for (const [indicator, value, unit] of [["cabin_pco2_1h", 3.4, "mmHg"], ["radiation_dose_accumulated", 12.5, "mGy"]] as const) {
      const r: Reading = { crew: "habitat", indicator, value, unit, t: 2 * HOUR, source: "sensor", confidence: 1, state: "released" };
      m.replay.events.push({ t: 2 * HOUR, type: "reading", payload: r });
    }
    m.replay.events.sort((a, b) => a.t - b.t);
    return m;
  }

  it("does not show an old CO₂ Reading as current", () => {
    const profiles = [{ id: "mars_transit", name: "Mars transit", co2_limit: { value: 3, status: "sourced" } }];
    render(<App {...staleCabin()} bodyScene={fakeBodyScene().factory} profiles={profiles} />);
    expect(screen.queryByRole("status", { name: "Cabin CO₂" })).not.toBeInTheDocument();
    fireEvent.change(screen.getByRole("slider", { name: "Mission clock" }), { target: { value: String(3 * HOUR) } });
    expect(screen.getByRole("status", { name: "Cabin CO₂" })).toBeInTheDocument();
  });

  it("says how old the dose is when it is not from today", () => {
    render(<App {...staleCabin()} bodyScene={fakeBodyScene().factory} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(bar).toHaveTextContent("12.5 mGy");
    expect(bar).toHaveTextContent("as of Day 1 · 02:00");
  });
});

describe("sample-only data", () => {
  it("labels bone density 'sample, not real data' on its tile", () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Bone density" })).toHaveTextContent("sample, not real data");
  });
});

describe("mission bar dose from real cabin data", () => {
  function doseAt(doseT: number, value: number, nowT: number) {
    const m = missionWith([{ indicator: "heart_rate", value: 70, t: nowT }]);
    const r: Reading = { crew: "habitat", indicator: "radiation_dose_accumulated", value, unit: "mGy", t: doseT, source: "sensor", confidence: 1, state: "released" };
    m.replay.events.push({ t: doseT, type: "reading", payload: r });
    m.replay.events.sort((a, b) => a.t - b.t);
    render(<App {...m} bodyScene={fakeBodyScene().factory} />);
    return screen.getByRole("region", { name: "Mission" });
  }

  it("rounds the dose like any other value", () => {
    expect(doseAt(20 * HOUR, 7.963059999999999, 22 * HOUR)).toHaveTextContent("7.96 mGy");
  });

  it("treats a daily dose from last evening as current", () => {
    expect(doseAt(20 * HOUR, 4.16, DAY + 12 * HOUR)).not.toHaveTextContent("as of");
  });
});

describe("charts and cards read values the way tiles do", () => {
  async function openTrend(indicator: string, unit: string, values: number[], name: string) {
    render(<App {...missionWith(values.map((value, i) => ({ indicator, value, unit, t: (8 + i) * HOUR })))} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(within(screen.getByRole("region", { name: "Trends" })).getByRole("button", { name }));
    const chart = screen.getByRole("figure", { name: `${name} trend` });
    await userEvent.click(within(chart).getByRole("button", { name: "Show as table" }));
    return chart;
  }

  it("rounds long decimals in the chart's labels and table", async () => {
    const chart = await openTrend("resting_heart_rate", "bpm", [59.33289813995361, 64.0808973312378], "Resting heart rate");
    const rows = within(within(chart).getByRole("table")).getAllByRole("row");
    expect(rows[2]).toHaveTextContent("64.1");
    expect(rows[2]).not.toHaveTextContent("64.08");
  });

  it("uses °C in the chart, as on the tile", async () => {
    const chart = await openTrend("body_temperature", "degC", [37.0, 37.1], "Body temperature");
    expect(chart).toHaveTextContent("(°C)");
    expect(chart).not.toHaveTextContent("degC");
  });

  it("keeps small values readable instead of rounding them to 0", () => {
    render(<App {...missionWith([{ indicator: "radiation_dose_gcr", value: 0.004, unit: "mGy/day" }, { indicator: "bone_density", value: 0.0061, unit: "T-score" }])} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Bone density" })).toHaveTextContent("0.0061 T-score");
  });

  it("labels sample-only data on its card too", async () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(screen.getByRole("button", { name: "Bone density details" }));
    expect(screen.getByRole("dialog", { name: "Bone density" })).toHaveTextContent("sample, not real data");
  });
});

describe("time axis over a long replay (152 days of crew data)", () => {
  it("uses at most about six day labels, not one per day", async () => {
    const values = Array.from({ length: 152 }, (_, d) => 60 + (d % 5));
    const m = missionWith(values.map((value, d) => ({ indicator: "resting_heart_rate", value, unit: "bpm", t: d * DAY + 7 * HOUR })));
    render(<App {...m} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(within(screen.getByRole("region", { name: "Trends" })).getByRole("button", { name: "Resting heart rate" }));
    const ticks = screen.getByRole("figure", { name: "Resting heart rate trend" }).querySelectorAll("text.trend__xtick");
    const labels = [...ticks].map((t) => t.textContent);
    expect(labels.length).toBeGreaterThan(2);
    expect(labels.length).toBeLessThanOrEqual(7);
    expect(labels.every((l) => /^Day \d+$/.test(l ?? ""))).toBe(true);
  });
});
