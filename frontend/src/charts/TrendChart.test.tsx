import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { Mission } from "../test/replay";

const DAY3 = 2 * 86400;

/** The Mars day plus a Drift alert on heart rate at 09:00 (an Acute one is already at 14:00). */
function missionWithHeartAlerts(): Mission {
  const mission = marsMission();
  const t = DAY3 + 9 * 3600;
  const events = mission.replay.events;
  events.push({
    t,
    type: "alert",
    payload: {
      id: "a-drift-hr", kind: "drift", crew: mission.crew.id, indicator: "heart_rate",
      deviation: { sigma: 1.6, cusum: 4.8, combined: 1 }, status: "amber", urgency: "MONITOR", likely_causes: [], t,
    },
  });
  events.sort((a, b) => a.t - b.t);
  return mission;
}

async function openTrend(name: string) {
  render(<App {...missionWithHeartAlerts()} bodyScene={fakeBodyScene().factory} />);
  const trends = screen.getByRole("region", { name: "Trends" });
  await userEvent.click(within(trends).getByRole("button", { name }));
  return screen.getByRole("figure", { name: `${name} trend` });
}

describe("trend chart", () => {
  it("shades the astronaut's own baseline band", async () => {
    const chart = await openTrend("Heart rate");
    expect(within(chart).getByLabelText("Your normal: 55–75 bpm")).toBeInTheDocument();
  });

  it("marks Acute and Drift alerts at the times they happened, by shape and words", async () => {
    const chart = await openTrend("Heart rate");
    // 14:00 and 15:00 sit close together, so the word shows on the later one.
    expect(within(chart).getByLabelText("Acute alert, Day 3 14:00")).toBeInTheDocument();
    const acute = within(chart).getByLabelText("Acute alert, Day 3 15:00");
    const drift = within(chart).getByLabelText("Drift alert, Day 3 09:00");
    expect(acute).toHaveTextContent("Acute");
    expect(drift).toHaveTextContent("Drift");
    expect(acute.dataset.shape).not.toBe(drift.dataset.shape);
    // The Acute marker sits right of the Drift marker on the Mission-clock axis.
    expect(Number(acute.dataset.x)).toBeGreaterThan(Number(drift.dataset.x));
  });

  it("names every kind in a group of close markers, so a Drift beside an Acute keeps its word", async () => {
    const mission = marsMission();
    const t = DAY3 + 13.7 * 3600;
    mission.replay.events.push({
      t, type: "alert",
      payload: {
        id: "near-drift", kind: "drift", crew: mission.crew.id, indicator: "heart_rate",
        deviation: { sigma: 1.2, cusum: 4.1, combined: 1 }, status: "amber", urgency: "MONITOR", likely_causes: [], t,
      },
    });
    mission.replay.events.sort((a, b) => a.t - b.t);
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    const chart = screen.getByRole("figure", { name: "Heart rate trend" });
    expect(within(chart).getByLabelText("Acute alert, Day 3 15:00")).toHaveTextContent("Drift, Acute");
  });

  it("does not mark a green Alert, which only clears a Status", async () => {
    const chart = await openTrend("Heart rate");
    expect(within(chart).queryByLabelText("Acute alert, Day 3 16:00")).not.toBeInTheDocument();
    expect(within(chart).getByLabelText("Acute alert, Day 3 15:00")).toBeInTheDocument();
  });

  it("only marks alerts for the Indicator on show", async () => {
    const chart = await openTrend("Stress");
    expect(within(chart).getByLabelText("Drift alert, Day 3 11:00")).toBeInTheDocument();
    expect(within(chart).queryByLabelText(/Acute alert/)).not.toBeInTheDocument();
  });

  it("offers the values as a table", async () => {
    const chart = await openTrend("Heart rate");
    await userEvent.click(within(chart).getByRole("button", { name: "Show as table" }));
    const rows = within(within(chart).getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(25); // header + 24 hourly Readings
    expect(rows[15]).toHaveTextContent("Day 3 14:00");
    expect(rows[15]).toHaveTextContent("128");
    expect(rows[15]).toHaveTextContent("Act now");
  });
});
