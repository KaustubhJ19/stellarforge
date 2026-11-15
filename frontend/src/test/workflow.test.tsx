import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Screen } from "../screens";
import type { View } from "../api";

const base = { emergency: "em-1", patient: "cmdr", patient_name: "STUB Commander", disclaimer: "Decision support, not diagnosis.", t: 20 };
const resc = { ...base, role: "R1" as const, can_back: true };

function setup(view: View) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(`${init?.method ?? "GET"} ${url} ${init?.body ?? ""}`);
    return new Response("{}", { status: 200 });
  }));
  const act = async (fn: () => Promise<unknown>) => { await fn(); };
  render(<Screen crew="eng" view={view} offline={false} error={null} act={act} />);
  return calls;
}
afterEach(() => vi.unstubAllGlobals());

describe("tickets 05-08 screens", () => {
  it("05: answering a question posts it", async () => {
    const calls = setup({
      ...base, screen: "verdict", urgency: "ACT_NOW", urgency_label: "ACT NOW", answers: {}, seconds_left: 9,
      questions: [{ id: "status", text: "Are you OK?", choices: [{ id: "need_help", label: "I need help" }] }],
    });
    expect(screen.getByText(/Crew alarm in 9 s/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "I need help" }));
    expect(calls[0]).toContain("POST /api/answer");
    expect(calls[0]).toContain('"choice":"need_help"');
  });

  it("06: alarm screen rings and Accept posts", async () => {
    const calls = setup({ ...base, screen: "alarm", ring: true });
    expect(screen.getByText(/CREW ALARM/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: /Accept/ }));
    expect(calls[0]).toContain("POST /api/accept");
    expect(screen.getByTestId("disclaimer")).toBeInTheDocument();
  });

  it("06: observer question", async () => {
    const calls = setup({ ...resc, screen: "observer", question: { id: "responds", text: "Does the patient respond?", choices: [{ id: "no", label: "No response" }] } });
    await userEvent.click(screen.getByRole("button", { name: "No response" }));
    expect(calls[0]).toContain("POST /api/observer");
  });

  it("07: record screen says access is logged; failure shows no record", () => {
    setup({ ...resc, screen: "record", ok: true, record: { id: "cmdr", sex: "unspecified", missionProfile: "stub-mars", anchor: { STUB_indicator: { mean: 0, sd: 1 } } } });
    expect(screen.getByText(/This access is logged/)).toBeInTheDocument();
    expect(screen.getByText("STUB_indicator: 0 ± 1")).toBeInTheDocument();
  });

  it("07: failed log shows an error and no record data", () => {
    setup({ ...resc, screen: "record", ok: false, error: "access log write failed" });
    expect(screen.getByRole("alert")).toHaveTextContent("Record not opened");
    expect(screen.queryByText("STUB_indicator: 0 ± 1")).toBeNull();
  });

  it("08: contributors list and empty message", () => {
    setup({ ...resc, screen: "contributors", causes: [], message: "No history-based contributors available." });
    expect(screen.getByText("No history-based contributors available.")).toBeInTheDocument();
  });
});
