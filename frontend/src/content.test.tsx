import { render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "./App";
import { CONTENT_CARDS, cardFor, normalizeCards } from "./content";
import { profileFor, profileView } from "./profiles";
import { INDICATORS } from "./indicators";
import { marsMission } from "./test/replay";
import { fakeBodyScene } from "./test/fakeBodyScene";

describe("Spec 5 content (content/ at the repo root)", () => {
  it("loads every structured measurement card, each for an Indicator the app shows", () => {
    expect(CONTENT_CARDS.map((c) => c.indicator).sort()).toEqual(
      ["body_temperature", "glucose", "heart_rate", "mood", "sleep_duration", "systolic_bp"],
    );
    for (const c of CONTENT_CARDS) {
      for (const id of [c.indicator, ...(c.related_indicators ?? [])]) expect(INDICATORS[id], id).toBeDefined();
    }
    expect(cardFor(CONTENT_CARDS, "resting_heart_rate")?.indicator).toBe("heart_rate");
  });

  it("opens the real heart-rate card by default, with its NASA risk", async () => {
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    await userEvent.click(screen.getByRole("button", { name: "Heart rate details" }));
    const card = screen.getByRole("dialog", { name: "Heart rate" });
    expect(within(card).getByRole("region", { name: "Why it matters" })).toHaveTextContent(
      "NASA HRP risk: Risk of Cardiovascular Adaptations",
    );
  });

  it("reads the Mars transit profile: name, and the one-way delay labelled a team value", () => {
    expect(profileFor("mars_transit")).toMatchObject({ name: "Mars transit", delay: "28.5 min", delayNote: "one way, team value" });
    render(<App {...marsMission()} bodyScene={fakeBodyScene().factory} />);
    const bar = screen.getByRole("region", { name: "Mission" });
    expect(within(bar).getByText("28.5 min")).toBeInTheDocument();
    expect(within(bar).getByText("one way, team value")).toBeInTheDocument();
  });
});

describe("content that is not in the structured shape", () => {
  it("drops wrong-shaped or empty fields, so the card says 'Not added yet.' instead of crashing", () => {
    const [card] = normalizeCards([
      { indicator: "heart_rate", how: "Use the cuff", why: "flat text", if_abnormal: {}, space_note: 3 } as unknown,
    ]);
    expect(card).toEqual({ indicator: "heart_rate" });
    expect(normalizeCards([{ how: ["no indicator"] }, null, "x"])).toEqual([]);
  });

  it("keeps a well-formed card as it is", () => {
    expect(normalizeCards(CONTENT_CARDS)).toEqual(CONTENT_CARDS);
  });
});

describe("profile delay units and labels", () => {
  it("shows the delay in the profile's own unit, and names any unconfirmed value", () => {
    const view = profileView({
      id: "lunar", name: "Lunar base",
      comm_delay: { value: 1.3, unit: "s one way", status: "not confirmed" },
    });
    expect(view).toMatchObject({ name: "Lunar base", delay: "1.3 s", delayNote: "one way, not confirmed" });
  });

  it("shows minutes for the Mars profile, one way, team value", () => {
    expect(profileView({ id: "m", name: "M", comm_delay: { value: 28.5, unit: "min one way (57 min round trip)", status: "not confirmed: team value" } }))
      .toMatchObject({ name: "M", delay: "28.5 min", delayNote: "one way, team value" });
  });
});
