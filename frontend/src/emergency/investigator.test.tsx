import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Screen } from "./screens";
import type { Investigator, View } from "./api";

// Collapse Copilot ticket 13: the AI investigator notes panel, apart from the briefing.
const base = { emergency: "em-1", patient: "A", patient_name: "Crew A", disclaimer: "Decision support, not diagnosis.", t: 20 };
const resc = { ...base, role: "R1" as const, can_back: false, protocols: [{ id: "chest-pain", title: "Chest pain" }] };
const briefing = { assessment_id: "a", text: "Briefing text.", source: "template" as const, context_label: "context", evidence: [] };
const fields = { responsive: ["yes", "no"], breathing: ["normal", "abnormal", "none"], main_problem: ["other"] };
const label = "AI investigator notes: written by a small language model.";

function show(investigator: Investigator) {
  const view: View = { ...resc, screen: "intake", fields, route: null, briefing, investigator };
  render(<Screen crew="B" view={view} offline={false} error={null} act={async (fn) => { await fn(); }} />);
}

describe("investigator panel", () => {
  it("shows a verified note with a pointer to its record, apart from the briefing", () => {
    show({
      status: "ok", label, dropped: 2,
      notes: [{ claim: "Elbow joint pain is on the post-EVA form.",
        sources: [{ tool: "forms", field: "post_eva.elbow_joint_pain", value: true, crew: "A", snapshot_t: 5, snapshot_label: "fake" }] }],
    });
    const panel = screen.getByTestId("investigator");
    expect(panel).toHaveTextContent("Elbow joint pain is on the post-EVA form.");
    expect(screen.getByTestId("investigator-source")).toHaveTextContent("forms › post_eva.elbow_joint_pain = true");
    expect(screen.getByTestId("investigator-dropped")).toHaveTextContent("2 unverified claim(s) dropped");
    expect(screen.getByTestId("briefing")).not.toContainElement(panel);
  });

  it("says investigator unavailable on failure", () => {
    show({ status: "unavailable", label, message: "investigator unavailable: no history" });
    expect(screen.getByTestId("investigator-unavailable")).toHaveTextContent("investigator unavailable");
  });

  it("shows a running state", () => {
    show({ status: "running", label });
    expect(screen.getByTestId("investigator")).toHaveTextContent("Investigator running");
  });
});
