import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { missionWith, type Mission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { ProfileContent } from "../content";

const HOUR = 3600;

/** Spec 5's co2_limit as both profiles carry it (NASA-STD-3001 Vol 2 [V2 6004]). */
const CO2_LIMIT = {
  value: 3,
  unit: "mmHg CO2 partial pressure, 1-hour average",
  averaging_window_min: 60,
  status: "sourced",
  source: "NASA-STD-3001 Vol 2 [V2 6004], via OCHMO-TB-004 Rev D",
};
const MARS: ProfileContent = { id: "mars_transit", name: "Mars transit", co2_limit: CO2_LIMIT };
const STATION: ProfileContent = { id: "station", name: "Space station (ISS)", co2_limit: { ...CO2_LIMIT, value: 4 } };

/** A crew replay plus the cabin's trailing 1-hour CO₂ average: 3.4 mmHg from 10:00 to 12:00 only. */
function withCabin(): Mission {
  const mission = missionWith([
    { indicator: "heart_rate", value: 70, t: 8 * HOUR },
    { indicator: "heart_rate", value: 71, t: 14 * HOUR },
  ]);
  for (let h = 8; h <= 14; h++) {
    const t = h * HOUR;
    const value = h >= 10 && h < 12 ? 3.4 : 2.1;
    mission.replay.events.push({
      t, type: "reading",
      payload: { crew: "habitat", indicator: "cabin_pco2_1h", value, unit: "mmHg", t, source: "sensor", confidence: 1, state: "released" },
    });
  }
  mission.replay.events.sort((a, b) => a.t - b.t);
  return mission;
}

function renderWith(profiles: ProfileContent[] = [MARS, STATION], mission = withCabin()) {
  render(<App {...mission} bodyScene={fakeBodyScene().factory} profiles={profiles} />);
}

const scrubTo = (hour: number) =>
  fireEvent.change(screen.getByRole("slider", { name: "Mission clock" }), { target: { value: String(hour * HOUR) } });
const banner = () => screen.queryByRole("status", { name: "Cabin CO₂" });

describe("CO₂ banner", () => {
  it("shows only while the cabin's 1-hour CO₂ average is over the profile's limit", () => {
    renderWith();
    expect(banner()).not.toBeInTheDocument(); // 14:00, back to 2.1 mmHg
    scrubTo(9);
    expect(banner()).not.toBeInTheDocument();
    scrubTo(10);
    expect(banner()).toBeInTheDocument();
    scrubTo(11.5);
    expect(banner()).toBeInTheDocument();
    scrubTo(12);
    expect(banner()).not.toBeInTheDocument();
  });

  it("says it in words and an icon, in mmHg, with the limit's source", () => {
    renderWith();
    scrubTo(10);
    const b = banner()!;
    expect(b).toHaveAttribute("data-status", "amber");
    expect(within(b).getByTestId("status-icon")).toHaveTextContent("!");
    expect(b).toHaveTextContent("Cabin CO₂ high: 3.4 mmHg (1-hour average)");
    expect(b).toHaveTextContent("Limit 3 mmHg, 1-hour average (NASA-STD-3001 Vol 2 [V2 6004], via OCHMO-TB-004 Rev D)");
    expect(b).not.toHaveTextContent("ppm");
  });

  it("uses the limit of the profile chosen in the mission bar", async () => {
    renderWith();
    scrubTo(10);
    expect(banner()).toBeInTheDocument();
    const mission = screen.getByRole("region", { name: "Mission" });
    await userEvent.selectOptions(within(mission).getByRole("combobox", { name: "Mission profile" }), "Space station (ISS)");
    expect(banner()).not.toBeInTheDocument(); // 3.4 is under the station's 4
  });

  it("labels a limit that is not sourced", () => {
    renderWith([{ ...MARS, co2_limit: { ...CO2_LIMIT, status: "not confirmed: team value" } }]);
    scrubTo(10);
    expect(banner()).toHaveTextContent("Limit 3 mmHg, 1-hour average (not confirmed: team value)");
  });

  it("stays away when the profile gives no CO₂ limit", () => {
    renderWith([{ id: "mars_transit", name: "Mars transit" }]);
    scrubTo(10);
    expect(banner()).not.toBeInTheDocument();
  });

  it("stays away when the replay has no cabin CO₂", () => {
    renderWith(undefined, missionWith([{ indicator: "heart_rate", value: 70 }]));
    expect(banner()).not.toBeInTheDocument();
  });
});
