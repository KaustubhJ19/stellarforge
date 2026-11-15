import { render, screen } from "@testing-library/react";
import { describe, expect, it } from "vitest";
import { Screen } from "../screens";
import { OfflineFlow } from "../OfflineFlow";
import type { View } from "../api";
import type { Bundle } from "../offline";

// Ticket 16: every emergency screen type shows the disclaimer (story 20).
const base = { emergency: "em-1", patient: "cmdr", patient_name: "Crew cmdr", disclaimer: "Decision support, not diagnosis.", t: 1 };
const resc = { ...base, role: "R1" as const, can_back: true };
const q = { id: "status", text: "Are you OK?", choices: [{ id: "need_help", label: "I need help" }] };
const step = { id: "s", text: "STUB", source: { guideline: "G", section: "S" }, equipment: [], rescuers: 1 };
const record = { id: "cmdr", sex: "unspecified", missionProfile: "stub-mars", anchor: {} };

const views: View[] = [
  { ...base, screen: "verdict", urgency: null, urgency_label: "x", questions: [q], answers: {}, seconds_left: 3 },
  { ...base, screen: "help_requested", rescuers: [] },
  { ...base, screen: "patient_alarm", rescuers: [] },
  { ...base, screen: "patient_waiting", rescuers: ["eng"] },
  { ...base, screen: "alarm", ring: true },
  { ...base, screen: "join", ring: false },
  { ...base, screen: "join_r2", ring: false, rescuer1: "eng" },
  { ...resc, screen: "observer", question: q },
  { ...resc, screen: "record", ok: true, record },
  { ...resc, screen: "record", ok: false, error: "x" },
  { ...resc, screen: "contributors", causes: ["a"], message: null },
  { ...resc, screen: "step", step, index: 1, total: 1, stub: true },
  { ...resc, screen: "report", report: null },
];

describe("disclaimer on every emergency screen", () => {
  it.each(views.map((v) => [v.screen, v] as const))("%s", (_name, v) => {
    render(<Screen crew="eng" view={v} offline={false} error={null} act={async () => {}} />);
    expect(screen.getByTestId("disclaimer")).toHaveTextContent("Decision support, not diagnosis.");
  });

  it("covers every non-idle screen type the API defines", () => {
    const covered = new Set(views.map((v) => v.screen));
    const all: View["screen"][] = ["verdict", "help_requested", "patient_alarm", "patient_waiting", "alarm", "join", "join_r2",
      "observer", "record", "contributors", "step", "report"];
    expect(all.filter((s) => !covered.has(s))).toEqual([]);
  });

  const bundle: Bundle = {
    protocol: { id: "p", title: "t", stub: true, steps: [step] }, profile: { id: "x", crew: ["cmdr", "eng"], delay_label: null },
    records: { cmdr: record }, names: {}, questions: [], disclaimer: "Decision support, not diagnosis.",
  };
  it.each([["offline record", true], ["offline step", false]])("%s", (_n, asRescuer) => {
    render(<OfflineFlow crew="eng" bundle={bundle} session={{ patient: "cmdr", asRescuer }} onEnd={() => {}} />);
    expect(screen.getByTestId("disclaimer")).toHaveTextContent("Decision support, not diagnosis.");
  });
});
