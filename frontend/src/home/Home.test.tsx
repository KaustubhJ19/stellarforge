import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsReplay } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

function renderHome(onEmergency = vi.fn()) {
  render(<App replay={marsReplay()} bodyScene={fakeBodyScene().factory} onEmergency={onEmergency} />);
  return onEmergency;
}

const namesIn = (region: HTMLElement) =>
  within(region).getAllByRole("group").map((g) => g.getAttribute("aria-label"));

describe("home screen", () => {
  it("shows physical and mental health in separate summaries", () => {
    renderHome();
    const physical = namesIn(screen.getByRole("region", { name: "Physical health" }));
    const mental = namesIn(screen.getByRole("region", { name: "Mental health" }));
    expect(physical).toEqual(expect.arrayContaining(["Heart rate", "SpO₂", "Respiration", "Bone density"]));
    expect(mental).toEqual(expect.arrayContaining(["Stress", "Alertness", "Mood"]));
    expect(physical).not.toContain("Mood");
    expect(physical).not.toContain("Stress");
  });

  it("lists today's tasks and which are done", () => {
    renderHome();
    const tasks = within(screen.getByRole("region", { name: "Today's tasks" })).getAllByRole("listitem");
    expect(tasks.map((t) => t.textContent)).toEqual([
      expect.stringContaining("Morning check-in"),
      expect.stringContaining("Blood pressure"),
      expect.stringContaining("Attention test"),
    ]);
    expect(tasks[0]).toHaveTextContent("Done");
    expect(tasks[1]).toHaveTextContent("Due");
  });

  it("opens the emergency flow from a large Emergency button", async () => {
    const onEmergency = renderHome();
    await userEvent.click(screen.getByRole("button", { name: "Emergency" }));
    expect(onEmergency).toHaveBeenCalledWith("emergency");
  });

  it("opens the help-a-crewmate flow", async () => {
    const onEmergency = renderHome();
    await userEvent.click(screen.getByRole("button", { name: "Help a crewmate" }));
    expect(onEmergency).toHaveBeenCalledWith("help-crewmate");
  });
});
