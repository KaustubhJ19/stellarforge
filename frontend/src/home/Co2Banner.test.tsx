import { fireEvent, render, screen, within } from "@testing-library/react";
import { App } from "../App";
import { missionWith, type Mission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

const HOUR = 3600;

/** A crew replay plus cabin CO₂ from the habitat: high (6,200 ppm) from 10:00 to 12:00 only. */
function withCabin(): Mission {
  const mission = missionWith([
    { indicator: "heart_rate", value: 70, t: 8 * HOUR },
    { indicator: "heart_rate", value: 71, t: 14 * HOUR },
  ]);
  for (let h = 8; h <= 14; h++) {
    const t = h * HOUR;
    const value = h >= 10 && h < 12 ? 6200 : 2600;
    mission.replay.events.push({
      t, type: "reading",
      payload: { crew: "habitat", indicator: "cabin_co2", value, unit: "ppm", t, source: "sensor", confidence: 1, state: "released" },
    });
  }
  mission.replay.events.sort((a, b) => a.t - b.t);
  return mission;
}

const scrubTo = (hour: number) =>
  fireEvent.change(screen.getByRole("slider", { name: "Mission clock" }), { target: { value: String(hour * HOUR) } });
const banner = () => screen.queryByRole("status", { name: "Cabin CO₂" });

describe("CO₂ banner", () => {
  it("shows only while cabin CO₂ is over the limit, and clears when it drops back", () => {
    render(<App {...withCabin()} bodyScene={fakeBodyScene().factory} />);
    expect(banner()).not.toBeInTheDocument(); // 14:00, back to 2,600 ppm
    scrubTo(9);
    expect(banner()).not.toBeInTheDocument();
    scrubTo(10);
    expect(banner()).toBeInTheDocument();
    scrubTo(11.5);
    expect(banner()).toBeInTheDocument();
    scrubTo(12);
    expect(banner()).not.toBeInTheDocument();
  });

  it("says it in words and an icon, not colour alone, and labels the limit a team value", () => {
    render(<App {...withCabin()} bodyScene={fakeBodyScene().factory} />);
    scrubTo(10);
    const b = banner()!;
    expect(b).toHaveAttribute("data-status", "amber");
    expect(within(b).getByTestId("status-icon")).toHaveTextContent("!");
    expect(b).toHaveTextContent("Cabin CO₂ high: 6,200 ppm");
    expect(b).toHaveTextContent("Limit 5,000 ppm (team value, not yet researched)");
  });

  it("stays away when the replay has no cabin CO₂", () => {
    render(<App {...missionWith([{ indicator: "heart_rate", value: 70 }])} bodyScene={fakeBodyScene().factory} />);
    expect(banner()).not.toBeInTheDocument();
  });
});
