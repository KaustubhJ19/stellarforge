import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { CardContent } from "../contracts";

// Placeholder text in Spec 5's structured card shape (content/cards/*.json).
const heartCard: CardContent = {
  indicator: "heart_rate",
  related_indicators: ["resting_heart_rate"],
  unit: "bpm",
  how: ["HOW step one", "HOW step two"],
  why: { text: "WHY placeholder", hrp_risk: "Risk of Placeholder", source: "https://example.org/hrp" },
  if_abnormal: { now: "NOW placeholder", remeasure: "REMEASURE placeholder", tell_crew: "CREW placeholder", tell_ground: "GROUND placeholder" },
  space_note: "SPACE placeholder",
  labels: ["Earth reference, no space data"],
  sources: ["SOURCE placeholder"],
};

async function openCard(name: string, cards: CardContent[] = [heartCard]) {
  render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} cards={cards} />);
  await userEvent.click(screen.getByRole("button", { name: `${name} details` }));
  return screen.getByRole("dialog", { name });
}

describe("measurement card", () => {
  it("shows the value, its source and a sparkline", async () => {
    const card = await openCard("Heart rate");
    expect(card).toHaveTextContent("70 bpm");
    expect(card).toHaveTextContent("Source: Sensor");
    expect(within(card).getByRole("img", { name: /Heart rate sparkline/ })).toBeInTheDocument();
  });

  it("says plainly when a value is simulated", async () => {
    const { replay, crew } = marsMission();
    for (const e of replay.events) if (e.type === "reading" && e.payload.indicator === "heart_rate") e.payload.source = "sim";
    render(<App replay={replay} crew={crew} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(screen.getByRole("button", { name: "Heart rate details" }));
    expect(screen.getByRole("dialog")).toHaveTextContent("Source: Simulated");
  });

  it("shows How as steps, Why with its NASA risk and space note, and If abnormal in four parts", async () => {
    const card = await openCard("Heart rate");
    const how = within(card).getByRole("region", { name: "How it is measured" });
    expect(within(how).getAllByRole("listitem").map((li) => li.textContent)).toEqual(["HOW step one", "HOW step two"]);
    const why = within(card).getByRole("region", { name: "Why it matters" });
    expect(why).toHaveTextContent("WHY placeholder");
    expect(why).toHaveTextContent("NASA HRP risk: Risk of Placeholder");
    expect(why).toHaveTextContent("In space: SPACE placeholder");
    expect(within(why).getByRole("link", { name: "https://example.org/hrp" })).toHaveAttribute("href", "https://example.org/hrp");
    const abnormal = within(card).getByRole("region", { name: "If abnormal" });
    const terms = within(abnormal).getAllByRole("term").map((t) => t.textContent);
    const defs = within(abnormal).getAllByRole("definition").map((d) => d.textContent);
    expect(terms).toEqual(["Now", "Measure again", "Tell the crew", "Tell the ground"]);
    expect(defs).toEqual(["NOW placeholder", "REMEASURE placeholder", "CREW placeholder", "GROUND placeholder"]);
    expect(card).toHaveTextContent("Earth reference, no space data");
    expect(card).toHaveTextContent("SOURCE placeholder");
  });

  it("says when no NASA HRP risk covers the Indicator, and why", async () => {
    const uncovered: CardContent = {
      ...heartCard,
      why: { text: "WHY", hrp_risk: "uncovered", uncovered_reason: "No HRP risk names this.", source: "x" },
    };
    const why = within(await openCard("Heart rate", [uncovered])).getByRole("region", { name: "Why it matters" });
    expect(why).toHaveTextContent("NASA HRP risk: not covered. No HRP risk names this.");
  });

  it("uses a card for its related Indicators too (heart rate's card for resting heart rate)", async () => {
    const card = await openCard("Resting heart rate");
    expect(within(card).getByRole("region", { name: "Why it matters" })).toHaveTextContent("WHY placeholder");
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
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} cards={[heartCard]} />);
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
