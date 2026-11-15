import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Screen } from "./screens";
import type { View } from "./api";

const view: View = {
  emergency: "em-1", patient: "cmdr", patient_name: "STUB Commander", disclaimer: "Decision support, not diagnosis.", t: 30,
  role: "R1", can_back: false, screen: "step", index: 1, total: 2, stub: true,
  step: { id: "stub-1", text: "STUB step 1. Placeholder.", source: { guideline: "STUB-GUIDELINE (not a real source)", section: "STUB-S1" }, equipment: [], rescuers: 1 },
};

function respond(body: unknown, status = 200) {
  vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(body), { status })));
}
afterEach(() => vi.unstubAllGlobals());

describe("tickets 09 + 11: step screen and Why?", () => {
  it("shows exactly one step with its source, stub banner and disclaimer", () => {
    render(<Screen crew="eng" view={view} offline={false} error={null} act={async () => {}} />);
    expect(screen.getAllByTestId("step-text")).toHaveLength(1);
    expect(screen.getByTestId("step-source")).toHaveTextContent("STUB-GUIDELINE (not a real source), section STUB-S1");
    expect(screen.getByText(/non-clinical test data/)).toBeInTheDocument();
    expect(screen.getByTestId("disclaimer")).toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Back" })).toBeDisabled();
  });

  it("Why? shows a recorded answer with its label and source, step text unchanged", async () => {
    respond({ answer: "STUB recorded answer.", source: { guideline: "G", section: "S" }, mode: "recorded", label: "recorded answer" });
    render(<Screen crew="eng" view={view} offline={false} error={null} act={async () => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this step?" }));
    const why = await screen.findByTestId("why");
    expect(why).toHaveTextContent("STUB recorded answer.");
    expect(why).toHaveTextContent("recorded answer");
    expect(why).toHaveTextContent("Source: G, section S");
    expect(screen.getByTestId("step-text")).toHaveTextContent("STUB step 1. Placeholder.");
  });

  it("Why? with the service down says Not covered, ask ground", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("network"); }));
    render(<Screen crew="eng" view={view} offline={false} error={null} act={async () => {}} />);
    await userEvent.click(screen.getByRole("button", { name: "Why this step?" }));
    expect(await screen.findByTestId("why")).toHaveTextContent("Not covered, ask ground.");
  });
});
