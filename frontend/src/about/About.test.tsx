import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import credits from "../../../content/credits.json";
import accuracy from "../../../content/accuracy.json";

function renderHome() {
  render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} onEmergency={vi.fn()} />);
}

describe("Accuracy page", () => {
  it("opens from the footer and shows every measured result with how to re-run it", async () => {
    renderHome();
    await userEvent.click(screen.getByRole("button", { name: "How accurate is this?" }));
    const dialog = screen.getByRole("dialog", { name: "How accurate is this?" });
    for (const row of accuracy.results) {
      expect(within(dialog).getByText(row.what)).toBeInTheDocument();
      expect(within(dialog).getByText(row.result)).toBeInTheDocument();
    }
    expect(within(dialog).getAllByText(/python .*tools\//).length).toBeGreaterThan(0);
  });

  it("states the honest limits, including that this is not measured on astronauts", async () => {
    renderHome();
    await userEvent.click(screen.getByRole("button", { name: "How accurate is this?" }));
    const dialog = screen.getByRole("dialog", { name: "How accurate is this?" });
    expect(within(dialog).getAllByText(/not on astronauts/i).length).toBeGreaterThan(0);
    expect(within(dialog).getAllByRole("listitem").length).toBe(accuracy.limits.length);
  });

  it("closes with Escape and returns focus to the button", async () => {
    renderHome();
    const open = screen.getByRole("button", { name: "How accurate is this?" });
    await userEvent.click(open);
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(open).toHaveFocus();
  });
});

describe("Credits page", () => {
  it("lists every dataset, model and asset with its licence and a link to the source", async () => {
    renderHome();
    await userEvent.click(screen.getByRole("button", { name: "Credits" }));
    const dialog = screen.getByRole("dialog", { name: "Credits" });
    const rows = within(dialog).getAllByRole("listitem");
    expect(rows).toHaveLength(credits.entries.length);
    credits.entries.forEach((entry, i) => {
      expect(within(rows[i]).getByRole("heading", { name: entry.name })).toBeInTheDocument();
      expect(rows[i]).toHaveTextContent(entry.licence);
      expect(within(rows[i]).getByRole("link", { name: `Source: ${entry.name}` })).toHaveAttribute("href", entry.link);
    });
  });

  it("shows the required PMData citation", async () => {
    renderHome();
    await userEvent.click(screen.getByRole("button", { name: "Credits" }));
    expect(screen.getByRole("dialog", { name: "Credits" })).toHaveTextContent("Thambawita V. et al., PMData");
  });
});
