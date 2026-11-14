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
