import { render, screen, waitFor, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Tablet from "../Tablet";
import type { BodySceneFactory } from "../body/view";

// The 3D scene needs WebGL; Spec 2's tests swap it for a fake. The tablet renders Spec 2's App
// with its default scene, so stub the module the same way.
vi.mock("../body/threeBodyScene", async () => {
  const fake = await import("./fakeBodyScene");
  return { threeBodyScene: fake.fakeBodyScene().factory as BodySceneFactory };
});

type Call = { method: string; url: string; body: unknown };
let calls: Call[] = [];
let screenFor: Record<string, unknown> = {};

const bundle = {
  protocol: { id: "p", title: "t", stub: true, steps: [] },
  profile: { id: "stub-mars_transit", crew: ["A", "B", "C", "D"], delay_label: null },
  records: {}, names: { A: "Crew A", B: "Crew B", C: "Crew C", D: "Crew D" }, questions: [], disclaimer: "x",
};

beforeEach(() => {
  calls = [];
  screenFor = {};
  localStorage.clear();
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    const body = init?.body ? JSON.parse(init.body as string) : undefined;
    calls.push({ method: init?.method ?? "GET", url, body });
    if (url.startsWith("/api/view")) {
      const crew = new URL(url, "http://x").searchParams.get("crew")!;
      return new Response(JSON.stringify(screenFor[crew] ?? { screen: "idle", t: 42 }));
    }
    if (url === "/api/offline-bundle") return new Response(JSON.stringify(bundle));
    if (url.startsWith("/api/access-log")) return new Response("[]");
    if (url === "/api/trigger") return new Response(JSON.stringify({ emergency: "em-1" }), { status: 201 });
    return new Response("{}");
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("Spec 2 home wired to the Spec 4 flow", () => {
  it("idle tablet A shows Spec 2's home; its Emergency button posts a manual Trigger for A", async () => {
    render(<Tablet crew="A" />);
    const emergency = await screen.findByRole("button", { name: "Emergency" });
    expect(document.querySelector(".app")).not.toBeNull(); // Spec 2's App root
    await userEvent.click(emergency);
    await waitFor(() => expect(calls.some((c) => c.url === "/api/trigger")).toBe(true));
    const trig = calls.find((c) => c.url === "/api/trigger")!.body as Record<string, unknown>;
    expect(trig).toMatchObject({ schema_version: "1.0.0", kind: "manual", crew: "A", t: 42, reason: "Emergency button" });
  });

  it("Help a crewmate: pick a crewmate, which posts a manual Trigger for THAT crewmate (same flow)", async () => {
    render(<Tablet crew="A" />);
    await waitFor(() => expect(calls.some((c) => c.url === "/api/offline-bundle")).toBe(true));
    await userEvent.click(await screen.findByRole("button", { name: "Help a crewmate" }));
    const dialog = await screen.findByRole("dialog", { name: "Help a crewmate" });
    expect(within(dialog).queryByRole("button", { name: "Crew A" })).toBeNull(); // not yourself
    await userEvent.click(within(dialog).getByRole("button", { name: "Crew C" }));
    await waitFor(() => expect(calls.some((c) => c.url === "/api/trigger")).toBe(true));
    expect(calls.find((c) => c.url === "/api/trigger")!.body).toMatchObject({
      kind: "manual", crew: "C", reason: "Help a crewmate (requested by A)",
    });
  });

  it("an emergency screen from the backend takes over the tablet", async () => {
    screenFor.A = { screen: "alarm", ring: true, emergency: "em-1", patient: "B", patient_name: "Crew B", disclaimer: "Decision support, not diagnosis.", t: 50 };
    render(<Tablet crew="A" />);
    expect(await screen.findByText(/CREW ALARM/)).toBeInTheDocument();
    expect(document.querySelector(".app")).toBeNull();
    expect(screen.getByTestId("disclaimer")).toBeInTheDocument();
  });

  it("crew without a bundled replay still get Emergency and Help", async () => {
    render(<Tablet crew="C" />);
    expect(await screen.findByTestId("home-no-replay")).toHaveTextContent("No replay data for crew C");
    expect(screen.getByRole("button", { name: "Emergency" })).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Help a crewmate" })).toBeInTheDocument();
  });
});
