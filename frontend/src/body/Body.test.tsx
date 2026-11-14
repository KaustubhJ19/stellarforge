import { fireEvent, render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

describe("body layers", () => {
  it("draws all five layers by default", () => {
    const body = fakeBodyScene();
    render(<App {...marsMission()} bodyScene={body.factory} />);
    for (const layer of ["muscles", "skeleton", "vessels", "organs", "brain"] as const) {
      expect(body.view.layers[layer].visible).toBe(true);
    }
  });

  it("hides a layer when its toggle is turned off", async () => {
    const body = fakeBodyScene();
    render(<App {...marsMission()} bodyScene={body.factory} />);
    await userEvent.click(screen.getByRole("checkbox", { name: "Show skeleton" }));
    expect(body.view.layers.skeleton.visible).toBe(false);
    expect(body.view.layers.muscles.visible).toBe(true);
  });

  it("sets one layer's transparency without touching the others", async () => {
    const body = fakeBodyScene();
    render(<App {...marsMission()} bodyScene={body.factory} />);
    // jsdom cannot drag a range input; set it the way a drag would.
    fireEvent.change(screen.getByRole("slider", { name: "Muscles opacity" }), { target: { value: "0" } });
    expect(body.view.layers.muscles.opacity).toBe(0);
    expect(body.view.layers.organs.opacity).toBeGreaterThan(0);
  });
});
