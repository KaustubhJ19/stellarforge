import { act, render, screen, within } from "@testing-library/react";
import { App } from "./App";
import { marsReplay, replayWith } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";
import type { ReplayFile } from "./contracts";

describe("empty replay", () => {
  function renderEmpty() {
    const replay: ReplayFile = { ...marsReplay(), events: [] };
    render(<App replay={replay} bodyScene={fakeBodyScene().factory} />);
  }

  it("says so in each part of the home screen instead of showing blanks", () => {
    renderEmpty();
    expect(within(screen.getByRole("region", { name: "Physical health" })).getByText("No readings yet.")).toBeVisible();
    expect(within(screen.getByRole("region", { name: "Mental health" })).getByText("No readings yet.")).toBeVisible();
    expect(within(screen.getByRole("region", { name: "Today's tasks" })).getByText("Nothing due today.")).toBeVisible();
    expect(within(screen.getByRole("region", { name: "Trends" })).getByText("No trends yet.")).toBeVisible();
    expect(screen.getByText("Nothing to show on the body yet.")).toBeVisible();
    expect(within(screen.getByRole("region", { name: "Mission" })).getByText("No reading")).toBeVisible();
  });
});

describe("loading the body", () => {
  it("shows a loading message until the 3D body is ready", () => {
    const body = fakeBodyScene({ loadsImmediately: false });
    render(<App replay={marsReplay()} bodyScene={body.factory} />);
    expect(screen.getByText("Loading body…")).toBeVisible();
    act(() => body.finishLoading());
    expect(screen.queryByText("Loading body…")).not.toBeInTheDocument();
  });

  it("says when the body cannot load, and the rest still works", () => {
    const body = fakeBodyScene({ loadsImmediately: false });
    render(<App replay={marsReplay()} bodyScene={body.factory} />);
    act(() => body.failLoading("model file missing"));
    expect(screen.getByText(/3D body unavailable: model file missing/)).toBeVisible();
    expect(screen.getByRole("region", { name: "Physical health" })).toBeInTheDocument();
  });
});

describe("scale values", () => {
  it("shows a 1-5 self-report as 'of 5'", () => {
    render(<App replay={replayWith([{ indicator: "mood", value: 3, unit: "1-5", state: "amber" }])} bodyScene={fakeBodyScene().factory} />);
    expect(screen.getByRole("group", { name: "Mood" })).toHaveTextContent("3 of 5");
  });
});
