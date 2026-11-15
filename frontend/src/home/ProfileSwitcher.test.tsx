import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

const bar = () => screen.getByRole("region", { name: "Mission" });
const switcher = () => within(bar()).getByRole("combobox", { name: "Mission profile" });

describe("Mission profile switcher (Spec 5's content/profiles/)", () => {
  it("lists the available profiles and starts on the replay's own", () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    const names = within(switcher()).getAllByRole("option").map((o) => o.textContent);
    expect(names).toEqual(expect.arrayContaining(["Mars transit", "Space station (ISS)"]));
    expect(switcher()).toHaveDisplayValue("Mars transit");
    expect(bar()).toHaveTextContent("28.5 min");
  });

  it("shows the chosen profile's own ground delay and how sure it is", async () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    await userEvent.selectOptions(switcher(), "Space station (ISS)");
    expect(switcher()).toHaveDisplayValue("Space station (ISS)");
    expect(bar()).toHaveTextContent("0 min");
    expect(bar()).toHaveTextContent("one way");
    expect(bar()).not.toHaveTextContent("team value");
    await userEvent.selectOptions(switcher(), "Mars transit");
    expect(bar()).toHaveTextContent("28.5 min");
    expect(bar()).toHaveTextContent("one way, team value");
  });

  it("keeps a replay's unknown profile as a choice, shown by its id", () => {
    const mission = marsMission();
    mission.replay.profile = "lunar_gateway_test";
    render(<App {...mission} bodyScene={fakeBodyScene().factory} />);
    expect(switcher()).toHaveDisplayValue("lunar_gateway_test");
    expect(bar()).toHaveTextContent("Not known");
  });
});
