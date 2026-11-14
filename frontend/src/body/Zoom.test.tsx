import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsReplay } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

function renderApp() {
  const body = fakeBodyScene();
  render(<App replay={marsReplay()} bodyScene={body.factory} />);
  return body;
}

describe("zoom body → region → structure", () => {
  it("starts on the whole body", () => {
    const body = renderApp();
    expect(body.view.focus).toEqual({ level: "body" });
    expect(screen.queryByRole("button", { name: /^Back to (whole body|head|chest|abdomen|pelvis)/ })).not.toBeInTheDocument();
  });

  it("zooms into a region and offers only that region's structures", async () => {
    const body = renderApp();
    await userEvent.click(screen.getByRole("button", { name: "Chest" }));
    expect(body.view.focus).toEqual({ level: "region", region: "chest" });
    expect(screen.getByRole("button", { name: "Heart" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Lungs" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Kidneys" })).not.toBeInTheDocument();
  });

  it("zooms into one structure and steps back out one level at a time", async () => {
    const body = renderApp();
    await userEvent.click(screen.getByRole("button", { name: "Chest" }));
    await userEvent.click(screen.getByRole("button", { name: "Heart" }));
    expect(body.view.focus).toEqual({ level: "structure", structure: "heart" });

    await userEvent.click(screen.getByRole("button", { name: "Back to chest" }));
    expect(body.view.focus).toEqual({ level: "region", region: "chest" });

    await userEvent.click(screen.getByRole("button", { name: "Back to whole body" }));
    expect(body.view.focus).toEqual({ level: "body" });
  });

  it("keeps layer settings while zoomed", async () => {
    const body = renderApp();
    await userEvent.click(screen.getByRole("checkbox", { name: "Show skeleton" }));
    await userEvent.click(screen.getByRole("button", { name: "Head" }));
    expect(body.view.layers.skeleton.visible).toBe(false);
  });
});
