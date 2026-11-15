import { render, screen, within } from "@testing-library/react";
import { App } from "./App";
import { marsMission } from "./test/replay";

describe("app loaded from a replay file", () => {
  it("shows the mission bar from the replay", () => {
    render(<App {...marsMission()} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(within(bar).getByText("Day 3")).toBeInTheDocument();
    expect(within(bar).getByText("Mars transit")).toBeInTheDocument();
    expect(within(bar).getByText("28.5 min")).toBeInTheDocument();
    expect(within(bar).getByText("41.89 mGy")).toBeInTheDocument();
  });
});

describe("status is never shown by colour alone", () => {
  it("shows an Indicator's Status as text and icon as well as colour", () => {
    render(<App {...marsMission()} />);
    const hr = screen.getByRole("group", { name: "Heart rate" });
    expect(hr).toHaveAttribute("data-status", "green");
    expect(within(hr).getByText("Normal")).toBeInTheDocument();
    expect(within(hr).getByTestId("status-icon")).toHaveTextContent("✓");
  });
});

describe("safety label", () => {
  it("says decision support, not diagnosis", () => {
    render(<App {...marsMission()} />);
    expect(screen.getByText(/decision support, not diagnosis/i)).toBeVisible();
  });
});
