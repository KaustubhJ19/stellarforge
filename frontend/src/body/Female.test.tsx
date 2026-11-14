import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsReplay } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { ReplayFile } from "../contracts";

function crew(sex: "male" | "female"): ReplayFile {
  const replay = marsReplay();
  replay.crew.sex = sex;
  return replay;
}

describe("body matches the Crew record", () => {
  it("draws the female body for a female crew member and says what is approximate", () => {
    const body = fakeBodyScene();
    render(<App replay={crew("female")} bodyScene={body.factory} />);
    expect(body.view.model).toBe("female");
    expect(
      screen.getByText("Female organs. Muscles, skeleton and vessels are approximate (resized from the male model)."),
    ).toBeVisible();
  });

  it("draws the male body for a male crew member, with no approximate note", () => {
    const body = fakeBodyScene();
    render(<App replay={crew("male")} bodyScene={body.factory} />);
    expect(body.view.model).toBe("male");
    expect(screen.queryByText(/approximate \(resized/)).not.toBeInTheDocument();
  });

  it("keeps glow, insight and zoom working on the female body", async () => {
    const body = fakeBodyScene();
    render(<App replay={crew("female")} bodyScene={body.factory} />);
    expect(body.view.structures.lungs.status).toBe("green");
    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));
    expect(body.view.model).toBe("female");
    expect(body.view.focus).toEqual({ level: "region", region: "head" });
  });
});
