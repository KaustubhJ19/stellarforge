import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { marsMission } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";

const END = 2 * 86400 + 23 * 3600;

describe("keyboard use", () => {
  it("puts Emergency first in the tab order", async () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Emergency" })).toHaveFocus();
    await userEvent.tab();
    expect(screen.getByRole("button", { name: "Help a crewmate" })).toHaveFocus();
  });

  it("moves the Mission clock 5 minutes per arrow key and 1 hour per Page key", () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    const slider = screen.getByRole("slider", { name: "Mission clock" });
    fireEvent.keyDown(slider, { key: "ArrowLeft" });
    expect(slider).toHaveValue(String(END - 300));
    fireEvent.keyDown(slider, { key: "PageDown" });
    expect(slider).toHaveValue(String(END - 300 - 3600));
    fireEvent.keyDown(slider, { key: "End" });
    expect(slider).toHaveValue(String(END));
    fireEvent.keyDown(slider, { key: "ArrowRight" }); // never past the newest event
    expect(slider).toHaveValue(String(END));
  });
});
