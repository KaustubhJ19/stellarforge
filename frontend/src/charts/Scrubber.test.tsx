import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsReplay } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

const DAY3 = 2 * 86400;
const at = (hour: number) => String(DAY3 + hour * 3600);

function renderApp() {
  const body = fakeBodyScene();
  render(<App replay={marsReplay()} bodyScene={body.factory} />);
  const scrubber = screen.getByRole("slider", { name: "Mission clock" });
  return { body, scrub: (hour: number) => fireEvent.change(scrubber, { target: { value: at(hour) } }) };
}

const heartTile = () =>
  within(screen.getByRole("region", { name: "Physical health" })).getByRole("group", { name: "Heart rate" });

describe("mission-clock scrubber", () => {
  it("starts at the latest time in the replay", () => {
    renderApp();
    expect(screen.getByRole("slider", { name: "Mission clock" })).toHaveValue(at(23));
    expect(screen.getByText("Day 3 23:00")).toBeInTheDocument();
  });

  it("replays the Status at the scrubbed time on the body and in the summary", () => {
    const { body, scrub } = renderApp();

    scrub(14);
    expect(body.view.structures.heart.status).toBe("red");
    expect(body.view.heartRate).toBe(128);
    expect(heartTile()).toHaveTextContent("Act now");

    scrub(13);
    expect(body.view.structures.heart.status).toBe("green");
    expect(heartTile()).toHaveTextContent("Normal");
  });

  it("shows only what was known at the scrubbed time", () => {
    const { scrub } = renderApp();
    scrub(5); // the mood check-in is at 08:00
    expect(
      within(screen.getByRole("region", { name: "Mental health" })).queryByRole("group", { name: "Mood" }),
    ).not.toBeInTheDocument();
  });

  it("returns to now", async () => {
    const { scrub } = renderApp();
    scrub(10);
    await userEvent.click(screen.getByRole("button", { name: "Back to now" }));
    expect(screen.getByRole("slider", { name: "Mission clock" })).toHaveValue(at(23));
  });
});
