import { act, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { afterEach, describe, expect, it, vi } from "vitest";
import { EmergencyAlert } from "./EmergencyAlert";

const serve = (view: unknown) => vi.stubGlobal("fetch", vi.fn(async () => new Response(JSON.stringify(view), { status: 200 })));
const settle = (ms = 80) => act(() => new Promise((r) => setTimeout(r, ms)));
afterEach(() => vi.unstubAllGlobals());

describe("pop-up when another crew member needs help", () => {
  it("shows who needs help, with a Respond link to this person's own tablet", async () => {
    serve({ screen: "join", emergency: "em-1", patient: "B", patient_name: "Crew B" });
    render(<EmergencyAlert crew="A" everyMs={20} />);
    const dialog = await screen.findByRole("alertdialog", { name: "Crew B needs help" });
    expect(within(dialog).getByRole("link", { name: "Respond" })).toHaveAttribute("href", "/emergency.html?crew=A");
  });

  it("also pops up when the crew alarm rings (the patient did not answer)", async () => {
    serve({ screen: "alarm", emergency: "em-1", patient: "B", patient_name: "Crew B" });
    render(<EmergencyAlert crew="C" everyMs={20} />);
    expect(await screen.findByRole("alertdialog", { name: "Crew B needs help" })).toBeInTheDocument();
  });

  it("asks for a second rescuer once the first has accepted", async () => {
    serve({ screen: "join_r2", emergency: "em-1", patient: "B", patient_name: "Crew B" });
    render(<EmergencyAlert crew="C" everyMs={20} />);
    expect(await screen.findByRole("alertdialog", { name: "Crew B needs a second rescuer" })).toBeInTheDocument();
  });

  it("shows nothing while nobody needs help, and not to the patient", async () => {
    serve({ screen: "help_requested", emergency: "em-1", patient: "B", patient_name: "Crew B" });
    render(<EmergencyAlert crew="B" everyMs={20} />);
    await settle();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("Dismiss hides it and it stays hidden for that emergency", async () => {
    serve({ screen: "join", emergency: "em-1", patient: "B", patient_name: "Crew B" });
    render(<EmergencyAlert crew="A" everyMs={20} />);
    await userEvent.click(await screen.findByRole("button", { name: "Dismiss" }));
    await settle();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });

  it("stays silent when there is no service", async () => {
    vi.stubGlobal("fetch", vi.fn(async () => { throw new TypeError("Failed to fetch"); }));
    render(<EmergencyAlert crew="A" everyMs={20} />);
    await settle();
    expect(screen.queryByRole("alertdialog")).toBeNull();
  });
});
