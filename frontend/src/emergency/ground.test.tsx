import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { ReportPanel } from "./Report";
import Console from "./Console";
import type { ReportView } from "./api";

const report: ReportView["report"] = {
  id: "gr-em-1", crew: "cmdr", summary: "STUB summary", history: [{ type: "vitals" }], timeline: [], actions: [],
  sent_t: 16, reply_t: null, reply: null,
};
const rv = (over: Partial<ReportView>): ReportView => ({
  report, expected_reply_t: 16 + 3420, delay_label: "team value: 28.5 min one way / 57 min round trip",
  reply_visible: false, reply_late: false, now: 100, ...over,
});
afterEach(() => vi.unstubAllGlobals());

describe("ticket 12: report panel", () => {
  it("shows sent time, expected reply time (57 min round trip) and act-on-your-own", () => {
    render(<ReportPanel view={rv({})} />);
    expect(screen.getByText(/Sent at T\+0 min 16 s\. Expected reply at T\+57 min 16 s/)).toBeInTheDocument();
    expect(screen.getByText(/team value: 28.5 min one way/)).toBeInTheDocument();
    expect(screen.getByText(/Act on your own meanwhile/)).toBeInTheDocument();
  });

  it("shows the late state and then the delivered reply", () => {
    const { rerender } = render(<ReportPanel view={rv({ reply_late: true })} />);
    expect(screen.getByTestId("reply-late")).toBeInTheDocument();
    rerender(<ReportPanel view={rv({ reply_visible: true, report: { ...report, reply: "Reply text." } })} />);
    expect(screen.getByTestId("ground-reply")).toHaveTextContent("Reply text.");
  });
});

describe("ticket 13: ground console", () => {
  it("lists an arrived report and sends a typed reply", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url} ${init?.body ?? ""}`);
      const body = url === "/api/console"
        ? { now: 2000, scripted_reply: "STUB", reports: [{ id: "gr-em-1", crew: "cmdr", arrived: true, arrives_t: 1726, report, replied: false }] }
        : {};
      return new Response(JSON.stringify(body), { status: 200 });
    }));
    render(<Console />);
    expect(await screen.findByText("STUB summary")).toBeInTheDocument();
    await userEvent.type(screen.getByLabelText("Reply"), "Hello crew");
    await userEvent.click(screen.getByRole("button", { name: "Send reply" }));
    expect(calls.some((c) => c.startsWith("POST /api/console/reply") && c.includes('"text":"Hello crew"'))).toBe(true);
  });

  it("shows in-transit reports without their content", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify({
      now: 20, scripted_reply: "STUB", reports: [{ id: "gr-em-1", crew: "cmdr", arrived: false, arrives_t: 1726, report: null, replied: false }],
    }))));
    render(<Console />);
    expect(await screen.findByText(/In transit/)).toBeInTheDocument();
    expect(screen.queryByText("STUB summary")).toBeNull();
  });
});

describe("ticket 06: copilot record in the report and console", () => {
  const H = "a".repeat(64);
  const copilot = {
    chain: { ok: true, reason: "", length: 2, head: H },
    events: [
      { t: 1, type: "copilot_assessment", prev: "0".repeat(64), l0: { rule_id: "R1" }, briefing: { text: "STUB briefing" } },
      { t: 9, type: "copilot_choice", prev: H, kind: "router", by: "B", protocol_id: "stub" },
    ],
    versions: { model: "none (L0 rules only)", schema_version: "1.0.0" },
    timings: { choice_after_s: 8 },
  };
  const withCopilot = { ...report, copilot };
  const consoleBody = (over: object) => ({
    now: 2000, scripted_reply: "STUB",
    reports: [{ id: "gr-em-1", crew: "cmdr", arrived: true, arrives_t: 1726, report: withCopilot, replied: false,
      copilot_chain: { ok: true, length: 2 }, outcomes: [], ...over }],
  });

  it("shows the copilot section and the verified status in the crew report", () => {
    render(<ReportPanel view={rv({ report: withCopilot })} />);
    expect(screen.getByTestId("chain-status")).toHaveTextContent("Record verified: 2 events, chain intact");
    expect(screen.getByText(/Rescuer B chose "router"/)).toBeInTheDocument();
    expect(screen.getByTestId("copilot-versions")).toHaveTextContent("none (L0 rules only)");
  });

  it("shows a failed ground-side re-check as an alert", async () => {
    const bad = { ok: false, reason: "event 1 (copilot_choice) does not match the one before it", length: 2 };
    vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(consoleBody({ copilot_chain: bad })))));
    render(<Console />);
    expect(await screen.findByRole("alert")).toHaveTextContent(/Record check FAILED: event 1/);
  });

  it("saves an outcome label and lists the ones already stored", async () => {
    const calls: string[] = [];
    vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? "GET"} ${url} ${init?.body ?? ""}`);
      const body = url === "/api/console" ? consoleBody({ replied: true, outcomes: [{ id: "lb-1", t: 1900, text: "Back on duty." }] }) : {};
      return new Response(JSON.stringify(body), { status: 200 });
    }));
    render(<Console />);
    expect(await screen.findByTestId("outcome")).toHaveTextContent("Back on duty.");
    await userEvent.type(screen.getByLabelText("Outcome"), "Recovered");
    await userEvent.click(screen.getByRole("button", { name: "Save outcome label" }));
    expect(calls.some((c) => c.startsWith("POST /api/console/outcome") && c.includes('"text":"Recovered"'))).toBe(true);
  });
});
