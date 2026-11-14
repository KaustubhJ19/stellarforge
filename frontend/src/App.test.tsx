import { render, screen, within } from "@testing-library/react";
import { App } from "./App";
import { marsReplay } from "./test/replay";

describe("app loaded from a replay file", () => {
  it("shows the mission bar from the replay", () => {
    render(<App replay={marsReplay()} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(within(bar).getByText("Day 3")).toBeInTheDocument();
    expect(within(bar).getByText("Mars transit")).toBeInTheDocument();
    expect(within(bar).getByText("28.5 min")).toBeInTheDocument();
    expect(within(bar).getByText("41.89 mSv")).toBeInTheDocument();
  });
});

describe("status is never shown by colour alone", () => {
  it("shows an Indicator's Status as text and icon as well as colour", () => {
    render(<App replay={marsReplay()} />);
    const hr = screen.getByRole("group", { name: "Heart rate" });
    expect(hr).toHaveAttribute("data-status", "green");
    expect(within(hr).getByText("Normal")).toBeInTheDocument();
    expect(within(hr).getByTestId("status-icon")).toHaveTextContent("✓");
  });
});

describe("safety label", () => {
  it("says decision support, not diagnosis", () => {
    render(<App replay={marsReplay()} />);
    expect(screen.getByText(/decision support, not diagnosis/i)).toBeVisible();
  });
});
