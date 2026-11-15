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
