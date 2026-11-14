import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";

function renderApp() {
  const body = fakeBodyScene();
  render(<App {...marsMission()} bodyScene={body.factory} />);
  return body;
}

describe("insight view", () => {
  it("fades everything except the structures a flagged Indicator is about", async () => {
    const body = renderApp();
    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));

    const { structures, layers } = body.view;
    expect(structures["brain.prefrontal"]).toEqual({ status: "amber", opacity: 1, explain: null });
    expect(structures["brain.amygdala"]).toEqual({ status: "amber", opacity: 1, explain: null });
    // Unrelated structures lose their glow and fade.
    expect(structures.lungs.status).toBeNull();
    expect(structures.lungs.opacity).toBeLessThan(0.2);
    // Muscles, skeleton and vessels go faint.
    for (const layer of ["muscles", "skeleton", "vessels"] as const) {
      expect(layers[layer].opacity).toBeLessThanOrEqual(0.1);
    }
    const banner = screen.getByRole("region", { name: "Insight: Stress" });
    expect(within(banner).getByText("Watch")).toBeInTheDocument();
    expect(within(banner).getByTestId("status-icon")).toHaveTextContent("!");
  });

  it("restores the astronaut's own layer settings and glow on exit", async () => {
    const body = renderApp();
    fireEvent.change(screen.getByRole("slider", { name: "Organs opacity" }), { target: { value: "40" } });
    const before = body.view;

    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));
    await userEvent.click(screen.getByRole("button", { name: "Exit insight" }));

    expect(body.view.layers).toEqual(before.layers);
    expect(body.view.structures).toEqual(before.structures);
    expect(body.view.focus).toEqual(before.focus);
  });

  it("zooms to the region when all the Indicator's structures are in one", async () => {
    const body = renderApp();
    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));
    expect(body.view.focus).toEqual({ level: "region", region: "head" });
  });

  it("offers no body view for mood", () => {
    renderApp();
    expect(screen.getByRole("button", { name: "Show stress on body" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Show mood on body" })).not.toBeInTheDocument();
  });
});
