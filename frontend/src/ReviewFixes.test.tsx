import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { marsReplay, replayWith } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";

const DAY3 = 2 * 86400;
const scrubTo = (hour: number) =>
  fireEvent.change(screen.getByRole("slider", { name: "Mission clock" }), { target: { value: String(DAY3 + hour * 3600) } });

describe("scrubbed-back views show only what was known then", () => {
  it("hides alerts and readings from after the scrubbed time on the trend chart", () => {
    render(<App replay={marsReplay()} bodyScene={fakeBodyScene().factory} />);
    scrubTo(10);
    const chart = screen.getByRole("figure", { name: "Heart rate trend" });
    expect(within(chart).queryByLabelText(/Acute alert/)).not.toBeInTheDocument();
    fireEvent.click(within(chart).getByRole("button", { name: "Show as table" }));
    const rows = within(within(chart).getByRole("table")).getAllByRole("row");
    expect(rows).toHaveLength(12); // header + 00:00 … 10:00
  });

  it("does not reopen a card that scrubbing closed", async () => {
    render(<App replay={marsReplay()} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(screen.getByRole("button", { name: "Mood details" }));
    scrubTo(5); // before the 08:00 mood check-in
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    scrubTo(9);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("insight shows the examined Indicator's own Status", () => {
  it("glows a shared structure with the chosen Indicator's Status, not the worst one", async () => {
    const body = fakeBodyScene();
    render(
      <App
        replay={replayWith([
          { indicator: "stress", value: 50, state: "amber" },
          { indicator: "alertness", value: 40, state: "red" },
        ])}
        bodyScene={body.factory}
      />,
    );
    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));
    expect(body.view.structures["brain.prefrontal"].status).toBe("amber");
  });
});
