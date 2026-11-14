import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
function crew(sex: "male" | "female") {
  const mission = marsMission();
  mission.crew.sex = sex;
  return mission;
}

describe("body matches the Crew record", () => {
  it("draws the female body for a female crew member and says what is approximate", () => {
    const body = fakeBodyScene();
    render(<App {...crew("female")} bodyScene={body.factory} />);
    expect(body.view.model).toBe("female");
    expect(
      screen.getByText("Female organs. Muscles, skeleton and vessels are approximate (resized from the male model)."),
    ).toBeVisible();
  });

  it("draws the male body for a male crew member, with no approximate note", () => {
    const body = fakeBodyScene();
    render(<App {...crew("male")} bodyScene={body.factory} />);
    expect(body.view.model).toBe("male");
    expect(screen.queryByText(/approximate \(resized/)).not.toBeInTheDocument();
  });

  it("keeps glow, insight and zoom working on the female body", async () => {
    const body = fakeBodyScene();
    render(<App {...crew("female")} bodyScene={body.factory} />);
    expect(body.view.structures.lungs.status).toBe("green");
    await userEvent.click(screen.getByRole("button", { name: "Show stress on body" }));
    expect(body.view.model).toBe("female");
    expect(body.view.focus).toEqual({ level: "region", region: "head" });
  });
});
