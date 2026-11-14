import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsReplay } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { CardContent } from "../contracts";

// Placeholder text standing in for Spec 5's card content.
const heartCard: CardContent = {
  indicator: "heart_rate",
  how: "HOW placeholder",
  why: "WHY placeholder",
  ifAbnormal: "IF-ABNORMAL placeholder",
  labels: ["Earth reference, no space data"],
  sources: ["SOURCE placeholder"],
};

async function openCard(name: string, cards: CardContent[] = [heartCard]) {
  render(<App replay={marsReplay()} bodyScene={fakeBodyScene().factory} cards={cards} />);
  await userEvent.click(screen.getByRole("button", { name: `${name} details` }));
  return screen.getByRole("dialog", { name });
}

describe("measurement card", () => {
  it("shows the value, its source and a sparkline", async () => {
    const card = await openCard("Heart rate");
    expect(card).toHaveTextContent("70 bpm");
    expect(card).toHaveTextContent("Source: wearable");
    expect(within(card).getByRole("img", { name: /Heart rate sparkline/ })).toBeInTheDocument();
  });

  it("renders How, Why and If abnormal from the content", async () => {
    const card = await openCard("Heart rate");
    for (const [heading, text] of [
      ["How it is measured", "HOW placeholder"],
      ["Why it matters", "WHY placeholder"],
      ["If abnormal", "IF-ABNORMAL placeholder"],
    ]) {
      const section = within(card).getByRole("region", { name: heading });
      expect(section).toHaveTextContent(text);
    }
    expect(card).toHaveTextContent("Earth reference, no space data");
    expect(card).toHaveTextContent("SOURCE placeholder");
  });

  it("still renders when content is missing", async () => {
    const card = await openCard("SpO₂", []);
    expect(within(card).getByRole("region", { name: "If abnormal" })).toHaveTextContent("Not added yet");
    expect(card).toHaveTextContent("98 %");
  });

  it("closes", async () => {
    const card = await openCard("Heart rate");
    await userEvent.click(within(card).getByRole("button", { name: "Close" }));
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
  });
});

describe("measurement card keyboard use", () => {
  it("keeps Tab inside the card and returns focus to Details on close", async () => {
    render(<App replay={marsReplay()} bodyScene={fakeBodyScene().factory} cards={[heartCard]} />);
    const details = screen.getByRole("button", { name: "Heart rate details" });
    await userEvent.click(details);
    const card = screen.getByRole("dialog", { name: "Heart rate" });
    for (let i = 0; i < 5; i++) {
      await userEvent.tab();
      expect(card).toContainElement(document.activeElement as HTMLElement);
    }
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(details).toHaveFocus();
  });
});
