import { render, screen, within } from "@testing-library/react";
import { App } from "../App";
import { replayWith } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

function renderBody(replay: Parameters<typeof replayWith>[0]) {
  const body = fakeBodyScene();
  render(<App replay={replayWith(replay)} bodyScene={body.factory} />);
  return body;
}

describe("status glow", () => {
  it("colours the structure of a red Indicator and labels it with text and icon", () => {
    const body = renderBody([{ indicator: "heart_rate", value: 131, state: "red" }]);
    expect(body.view.structures.heart.status).toBe("red");
    expect(body.view.structures["vessels.carotids"].status).toBe("red");

    const heart = within(screen.getByRole("list", { name: "Body status" })).getByRole("listitem", { name: "Heart" });
    expect(heart).toHaveTextContent("Act now");
    expect(within(heart).getByTestId("status-icon")).toHaveTextContent("✕");
  });

  it("never lights a structure for mood", () => {
    const body = renderBody([{ indicator: "mood", value: 1, state: "red" }]);
    const glowing = Object.values(body.view.structures).filter((s) => s.status !== null);
    expect(glowing).toEqual([]);
    expect(screen.queryByRole("list", { name: "Body status" })).not.toBeInTheDocument();
    expect(screen.getByText("Nothing to show on the body yet.")).toBeVisible();
  });

  it("shows the worse Status when two Indicators share a structure", () => {
    const body = renderBody([
      { indicator: "stress", value: 30, state: "green" },
      { indicator: "alertness", value: 60, state: "amber" },
    ]);
    expect(body.view.structures["brain.prefrontal"].status).toBe("amber");
    expect(body.view.structures["brain.amygdala"].status).toBe("green");
  });

  it("glows the whole body for radiation dose only when it needs attention", () => {
    expect(renderBody([{ indicator: "radiation_dose", value: 41, state: "green" }]).view.wholeBody).toBeNull();
  });

  it("glows the whole body amber for a raised radiation dose", () => {
    const body = renderBody([{ indicator: "radiation_dose", value: 140, state: "amber" }]);
    expect(body.view.wholeBody).toBe("amber");
    const item = within(screen.getByRole("list", { name: "Body status" })).getByRole("listitem", { name: "Whole body" });
    expect(item).toHaveTextContent("Watch");
  });
});
