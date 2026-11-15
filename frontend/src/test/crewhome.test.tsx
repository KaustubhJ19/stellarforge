import { render, screen, within } from "@testing-library/react";
import { describe, expect, it, vi } from "vitest";
import { CrewHome } from "../CrewHome";
import type { BodySceneFactory } from "../body/view";
import cabin from "../fixtures/iss-cabin-day3.json";
import female from "../../public/replay/mars-day3-female.json";
import crewRecords from "../../public/replay/crew-records.json";

vi.mock("../body/threeBodyScene", async () => {
  const fake = await import("./fakeBodyScene");
  return { threeBodyScene: fake.fakeBodyScene().factory as BodySceneFactory };
});

const mission = () => screen.getByRole("region", { name: "Mission" });

describe("crew tablet home (Spec 2 inside Spec 4's tablet)", () => {
  it("crew A: the bundled replay with the bundled cabin day, so the dose and CO₂ banner are there", () => {
    render(<CrewHome crew="A" onEmergency={() => {}} />);
    expect(mission()).toHaveTextContent("41.89 mGy");
    expect(within(mission()).getByText("Mars transit")).toBeInTheDocument();
  });

  it("crew B: loads the female replay and the cabin replay", async () => {
    const asked: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string) => {
      asked.push(new URL(url).pathname);
      const body = url.endsWith("crew-records.json") ? crewRecords : url.endsWith("iss-cabin-day3.json") ? cabin : female;
      return new Response(JSON.stringify(body), { headers: { "content-type": "application/json" } });
    }));
    render(<CrewHome crew="B" onEmergency={() => {}} />);
    expect(await screen.findByText("41.89 mGy")).toBeInTheDocument();
    expect(asked).toEqual(["/replay/mars-day3-female.json", "/replay/crew-records.json", "/replay/iss-cabin-day3.json"]);
    vi.unstubAllGlobals();
  });
});
