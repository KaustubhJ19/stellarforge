import { render, screen } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Screen } from "./screens";
import type { View } from "./api";

// Intent-first routing (docs/spec-intent-routing.md): intake screen, "Using X, because Y" banner, override, not covered.
const base = { emergency: "em-1", patient: "A", patient_name: "Crew A", disclaimer: "Decision support, not diagnosis.", t: 20 };
const protocols = [{ id: "microgravity-cpr", title: "CPR" }, { id: "chest-pain", title: "Chest pain" }];
const resc = { ...base, role: "R1" as const, can_back: true, protocols };
const fields = {
  responsive: ["yes", "no"],
  breathing: ["normal", "abnormal", "none"],
  main_problem: ["chest_pain", "breathing_trouble", "cabin_alert", "collapse", "injury", "other"],
};
const route = { protocol_id: "chest-pain", rule_id: "chest-pain-responsive", reason: "Rescuer reports chest pain." };
const step = { id: "cp-1", text: "STUB", source: { guideline: "G", section: "S" }, equipment: [], rescuers: 1 };

function setup(view: View) {
  const calls: string[] = [];
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: RequestInit) => {
    calls.push(`${init?.method ?? "GET"} ${url} ${init?.body ?? ""}`);
    return new Response("{}", { status: 200 });
  }));
  render(<Screen crew="B" view={view} offline={false} error={null} act={async (fn) => { await fn(); }} />);
  return calls;
}
afterEach(() => vi.unstubAllGlobals());

describe("intake screen", () => {
  const intake: View = { ...resc, screen: "intake", fields, route: null };

  it("labels every main problem the service offers, including the team-agreed library values", () => {
    const all = ["chest_pain", "breathing_trouble", "cabin_alert", "collapse", "bleeding", "head_injury", "injury",
      "low_blood_sugar", "seizure", "overheating", "infection", "after_eva", "other"];
    setup({ ...intake, fields: { ...fields, main_problem: all } });
    for (const name of ["Severe bleeding", "Head injury", "Low blood sugar", "Seizure", "Overheating or fever",
      "Severe infection", "Problem after a spacewalk (EVA)"]) {
      expect(screen.getByRole("button", { name })).toBeInTheDocument();
    }
    for (const raw of all) expect(screen.queryByRole("button", { name: raw })).toBeNull();
  });

  it("confirm stays disabled until every question is answered", async () => {
    setup(intake);
    const confirm = screen.getByRole("button", { name: /Confirm/ });
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Yes, responds" }));
    await userEvent.click(screen.getByRole("button", { name: "Normal" }));
    expect(confirm).toBeDisabled();
    await userEvent.click(screen.getByRole("button", { name: "Chest pain" }));
    expect(confirm).toBeEnabled();
  });

  it("confirm posts the structured answers, tap source", async () => {
    const calls = setup(intake);
    await userEvent.click(screen.getByRole("button", { name: "Yes, responds" }));
    await userEvent.click(screen.getByRole("button", { name: "Normal" }));
    await userEvent.click(screen.getByRole("button", { name: "Chest pain" }));
    await userEvent.click(screen.getByRole("button", { name: /Confirm/ }));
    expect(calls[0]).toContain("POST /api/intake");
    expect(calls[0]).toContain('"intake":{"responsive":"yes","breathing":"normal","main_problem":"chest_pain"}');
  });
});

describe("route banner and override", () => {
  it("a step screen says which protocol is used and why", () => {
    setup({ ...resc, screen: "step", step, index: 1, total: 2, stub: false, route });
    expect(screen.getByTestId("route-banner")).toHaveTextContent("Using: Chest pain");
    expect(screen.getByTestId("route-banner")).toHaveTextContent("Rescuer reports chest pain.");
  });

  it("switching protocol posts the override", async () => {
    const calls = setup({ ...resc, screen: "step", step, index: 1, total: 2, stub: false, route });
    await userEvent.selectOptions(screen.getByLabelText(/Switch protocol/), "microgravity-cpr");
    expect(calls[0]).toContain("POST /api/switch-protocol");
    expect(calls[0]).toContain('"protocol":"microgravity-cpr"');
  });

  it("not covered says so, shows no steps, and still offers the override", () => {
    const notCovered = { protocol_id: null, rule_id: "no-match", reason: "This situation is not covered by the tool. Contact ground." };
    setup({ ...resc, screen: "contributors", causes: ["a"], message: null, route: notCovered });
    expect(screen.getByTestId("route-banner")).toHaveTextContent("Not covered by this tool. Contact ground.");
    expect(screen.getByLabelText(/Switch protocol/)).toBeInTheDocument();
  });

  it("no banner when the service does not route", () => {
    setup({ ...resc, screen: "step", step, index: 1, total: 1, stub: false });
    expect(screen.queryByTestId("route-banner")).toBeNull();
  });
});
