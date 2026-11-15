import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Screen } from "./screens";
import type { View } from "./api";

// Collapse Copilot ticket 04: the briefing renders beside the intake screen and the route banner.
const base = { emergency: "em-1", patient: "A", patient_name: "Crew A", disclaimer: "Decision support, not diagnosis.", t: 20 };
const resc = { ...base, role: "R1" as const, can_back: false, protocols: [{ id: "chest-pain", title: "Chest pain" }] };
const briefing = {
  assessment_id: "assess-em-1",
  text: "No rule has fired yet; waiting for the rescuer's answers. No history: no habitat service connected.",
  source: "template" as const,
  context_label: "context; the protocol above comes first",
  evidence: [{ text: "No history: no habitat service connected.", label: "no history" }],
};
const fields = { responsive: ["yes", "no"], breathing: ["normal", "abnormal", "none"], main_problem: ["other"] };

function show(view: View) {
  render(<Screen crew="B" view={view} offline={false} error={null} act={async (fn) => { await fn(); }} />);
}

describe("briefing panel", () => {
  it("shows beside the intake screen with the context label and the no-history line", () => {
    show({ ...resc, screen: "intake", fields, route: null, briefing });
    expect(screen.getByTestId("briefing-label")).toHaveTextContent("context; the protocol above comes first");
    expect(screen.getByTestId("briefing")).toHaveTextContent("no habitat service connected");
  });

  it("comes after the route banner, so the protocol is read first", () => {
    const route = { protocol_id: "chest-pain", rule_id: "chest-pain-responsive", reason: "Rescuer reports chest pain." };
    const step = { id: "cp-1", text: "STUB", source: { guideline: "G", section: "S" }, equipment: [], rescuers: 1 };
    show({ ...resc, screen: "step", step, index: 1, total: 1, stub: false, route, briefing });
    const banner = screen.getByTestId("route-banner");
    const panel = screen.getByTestId("briefing");
    expect(banner.compareDocumentPosition(panel) & Node.DOCUMENT_POSITION_FOLLOWING).toBeTruthy();
  });

  it("is absent when the service sends no briefing", () => {
    show({ ...resc, screen: "intake", fields, route: null });
    expect(screen.queryByTestId("briefing")).toBeNull();
  });
});
