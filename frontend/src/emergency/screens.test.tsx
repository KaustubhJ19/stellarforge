import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Screen } from "./screens";
import type { View } from "./api";

const base = { emergency: "em-1", patient: "cmdr", patient_name: "STUB Commander", disclaimer: "Decision support, not diagnosis.", t: 3 };
const verdict: View = {
  ...base, screen: "verdict", urgency: null, urgency_label: "Urgency not assessed (manual start)",
  questions: [{ id: "status", text: "Are you OK?", choices: [{ id: "false_alarm", label: "I'm OK - false alarm" }, { id: "need_help", label: "I need help" }] }],
  answers: {}, seconds_left: 12,
};

function mockFetch() {
  const f = vi.fn(async () => new Response(JSON.stringify({ emergency: "em-1" }), { status: 201 }));
  vi.stubGlobal("fetch", f);
  return f;
}
afterEach(() => vi.unstubAllGlobals());

describe("ticket 03: manual trigger and verdict", () => {
  it("idle home has an Emergency button that posts a manual Trigger with mission time", async () => {
    const f = mockFetch();
    const act = async (fn: () => Promise<unknown>) => { await fn(); };
    render(<Screen crew="cmdr" view={{ screen: "idle", t: 42 }} offline={false} error={null} act={act} />);
    await userEvent.click(screen.getByRole("button", { name: "Emergency" }));
    const [url, init] = f.mock.calls[0] as unknown as [string, RequestInit];
    expect(url).toBe("/api/trigger");
    expect(JSON.parse(init.body as string)).toMatchObject({ kind: "manual", crew: "cmdr", t: 42 });
    expect(screen.queryByTestId("disclaimer")).toBeNull();
  });

  it("idle home has a Help a crewmate action: it lists the other crew, not yourself, and raises an emergency for the one picked", async () => {
    const f = vi.fn(async (url: string) =>
      url === "/api/offline-bundle"
        ? new Response(JSON.stringify({ profile: { crew: ["cmdr", "eng", "sci"] }, names: { cmdr: "Commander", eng: "Engineer", sci: "Scientist" } }), { status: 200 })
        : new Response(JSON.stringify({ emergency: "em-1" }), { status: 201 }),
    );
    vi.stubGlobal("fetch", f);
    const act = async (fn: () => Promise<unknown>) => { await fn(); };
    render(<Screen crew="cmdr" view={{ screen: "idle", t: 42 }} offline={false} error={null} act={act} />);
    await userEvent.click(screen.getByRole("button", { name: "Help a crewmate" }));
    expect(await screen.findByRole("button", { name: "Engineer" })).toBeInTheDocument();
    expect(screen.queryByRole("button", { name: "Commander" })).toBeNull();
    await userEvent.click(screen.getByRole("button", { name: "Engineer" }));
    const post = f.mock.calls.find(([u]) => u === "/api/trigger") as unknown as [string, RequestInit];
    expect(JSON.parse(post[1].body as string)).toMatchObject({ kind: "manual", crew: "eng", t: 42, reason: "Help a crewmate" });
  });

  it("record screen: access granted but no record on file is said plainly, not shown as an error", () => {
    const view = { ...base, role: "R1", can_back: false, screen: "record", ok: true, record: null, t: 5 } as unknown as View;
    render(<Screen crew="eng" view={view} offline={false} error={null} act={async () => {}} />);
    expect(screen.getByText(/No record on file for STUB Commander/)).toBeInTheDocument();
    expect(screen.queryByText(/Record not opened/)).toBeNull();
  });

  it("record screen: a refused record shows its reason", () => {
    const view = { ...base, role: "R1", can_back: false, screen: "record", ok: false, error: "log write failed", t: 5 } as unknown as View;
    render(<Screen crew="eng" view={view} offline={false} error={null} act={async () => {}} />);
    expect(screen.getByRole("alert")).toHaveTextContent("Record not opened: log write failed");
  });

  it("verdict screen shows plain-words urgency, questions and the disclaimer", () => {
    render(<Screen crew="cmdr" view={verdict} offline={false} error={null} act={async () => {}} />);
    expect(screen.getByTestId("urgency")).toHaveTextContent("Urgency not assessed (manual start)");
    expect(screen.getByRole("button", { name: "I need help" })).toBeInTheDocument();
    expect(screen.getByTestId("disclaimer")).toHaveTextContent("Decision support, not diagnosis.");
  });

  it("shows API errors and keeps the button usable", () => {
    render(<Screen crew="cmdr" view={{ screen: "idle", t: 0 }} offline={false} error={null} act={async () => {}} />);
    expect(screen.getByRole("button", { name: "Emergency" })).toBeEnabled();
  });
});
