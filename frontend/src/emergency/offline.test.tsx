import { render, screen, waitFor } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Tablet from "./Tablet";
import { flush, queue, saveBundle, type Bundle } from "./offline";

const bundle: Bundle = {
  protocol: {
    id: "stub-protocol", title: "STUB", stub: true,
    steps: [
      { id: "stub-1", text: "STUB step 1.", source: { guideline: "STUB-G", section: "S1" }, equipment: [], rescuers: 1 },
      { id: "stub-2", text: "STUB step 2.", source: { guideline: "STUB-G", section: "S2" }, equipment: [], rescuers: 1 },
    ],
  },
  profile: { id: "stub-mars", crew: ["cmdr", "eng"], delay_label: null },
  records: { cmdr: { id: "cmdr", sex: "unspecified", missionProfile: "stub-mars", anchor: { STUB_indicator: { mean: 0, sd: 1 } } } },
  names: { cmdr: "STUB Commander", eng: "STUB Engineer" },
  questions: [],
  disclaimer: "Decision support, not diagnosis.",
};

beforeEach(() => {
  localStorage.clear();
  saveBundle(bundle);
  vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("backend down"); }));
});
afterEach(() => vi.unstubAllGlobals());

describe("ticket 14: backend down", () => {
  it("Help a crewmate offline: record logged locally, cited steps one per screen, disclaimer", async () => {
    render(<Tablet crew="eng" />);
    expect(await screen.findByText(/Service unavailable/)).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Help a crewmate" }));
    await userEvent.click(screen.getByRole("button", { name: "STUB Commander" }));
    expect(screen.getByText(/logged on this tablet/)).toBeInTheDocument();
    expect(screen.getByText("STUB_indicator: 0 ± 1")).toBeInTheDocument();
    expect(screen.getByTestId("disclaimer")).toBeInTheDocument();
    await userEvent.click(screen.getByRole("button", { name: "Next" }));
    expect(screen.getAllByTestId("step-text")).toHaveLength(1);
    expect(screen.getByTestId("step-source")).toHaveTextContent("STUB-G, section S1");
    await userEvent.click(screen.getByRole("button", { name: "Why this step?" }));
    expect(screen.getByTestId("why")).toHaveTextContent("Not covered, ask ground.");
    const types = queue().map((q) => q.type);
    expect(types).toEqual(["trigger", "record_access", "step_shown"]);
    expect(queue()[1].data).toEqual({ actor: "eng", subject: "cmdr" });
  });

  it("own Emergency offline goes straight to steps without opening any record", async () => {
    render(<Tablet crew="cmdr" />);
    await userEvent.click(await screen.findByRole("button", { name: "Emergency" }));
    expect(screen.getByTestId("step-text")).toHaveTextContent("STUB step 1.");
    expect(queue().some((q) => q.type === "record_access")).toBe(false);
  });

  it("flush sends the queue once and clears it only after success", async () => {
    render(<Tablet crew="cmdr" />);
    await userEvent.click(await screen.findByRole("button", { name: "Emergency" }));
    const n = queue().length;
    await expect(flush("cmdr")).rejects.toThrow();
    expect(queue()).toHaveLength(n);
    const sync = vi.fn(async () => new Response(JSON.stringify({ accepted: n, duplicates: 0 })));
    vi.stubGlobal("fetch", sync);
    expect(await flush("cmdr")).toBe(n);
    expect(queue()).toHaveLength(0);
    expect(await flush("cmdr")).toBe(0);
    expect(sync).toHaveBeenCalledTimes(1);
  });

  it("no cached protocol shows a clear message", async () => {
    localStorage.clear();
    render(<Tablet crew="cmdr" />);
    await waitFor(() => expect(screen.getByRole("alert")).toHaveTextContent("No cached protocol"));
  });
});
