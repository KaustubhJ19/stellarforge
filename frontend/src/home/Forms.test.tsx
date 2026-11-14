import { fireEvent, render, screen, within } from "@testing-library/react";
import userEvent from "@testing-library/user-event";
import { App } from "../App";
import { marsMission, type Mission } from "../test/replay";
import { fakeBodyScene } from "../test/fakeBodyScene";
import type { Reading } from "../contracts";

function renderHome(mission: Mission = marsMission(), onReadings = vi.fn()) {
  render(<App {...mission} bodyScene={fakeBodyScene().factory} onReadings={onReadings} />);
  return onReadings;
}

async function openForm(name: string) {
  const tasks = screen.getByRole("region", { name: "Today's tasks" });
  await userEvent.click(within(tasks).getByRole("button", { name }));
  return screen.getByRole("dialog");
}

async function answer(dialog: HTMLElement, question: string, choice: "Yes" | "No") {
  await userEvent.click(within(within(dialog).getByRole("radiogroup", { name: question })).getByRole("radio", { name: choice }));
}

async function fill(dialog: HTMLElement, label: string, value: string) {
  const field = within(dialog).getByLabelText(label);
  await userEvent.clear(field);
  await userEvent.type(field, value);
}

describe("stand test form", () => {
  async function logStandTest(mission?: Mission) {
    const onReadings = renderHome(mission);
    const dialog = await openForm("Log stand test");
    await fill(dialog, "Lying heart rate (bpm)", "62");
    await fill(dialog, "Standing heart rate (bpm)", "92");
    await fill(dialog, "Standing systolic blood pressure (mmHg)", "110");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    return { dialog: screen.getByRole("dialog"), onReadings };
  }

  it("is reached from today's tasks and saves Readings the home screen shows", async () => {
    const { onReadings } = await logStandTest();
    const physical = screen.getByRole("region", { name: "Physical health" });
    expect(within(physical).getByRole("group", { name: "Standing heart rate" })).toHaveTextContent("92 bpm");
    expect(within(physical).getByRole("group", { name: "Standing systolic BP" })).toHaveTextContent("110 mmHg");
    const saved = onReadings.mock.calls[0][0] as Reading[];
    expect(saved.map((r) => [r.indicator, r.value, r.unit, r.source])).toEqual([
      ["resting_heart_rate", 62, "bpm", "manual"],
      ["standing_heart_rate", 92, "bpm", "manual"],
      ["standing_systolic_bp", 110, "mmHg", "manual"],
    ]);
  });

  it("compares with the astronaut's own pre-flight test first, then the Apollo group average", async () => {
    const mission = marsMission();
    mission.crew.anchor.standing_heart_rate = { mean: 76, sd: 5 };
    const { dialog } = await logStandTest(mission);
    const row = within(dialog).getByRole("row", { name: /Standing heart rate/ });
    const cells = within(row).getAllByRole("cell").map((c) => c.textContent);
    expect(cells).toEqual(["92 bpm", "76 bpm (+16)", "+23.4 bpm"]);
    const headers = within(dialog).getAllByRole("columnheader").map((c) => c.textContent);
    expect(headers.indexOf("Your pre-flight test")).toBeLessThan(headers.indexOf("Apollo crews after landing"));
    expect(dialog).toHaveTextContent("group averages after landing, not limits");
  });

  it("takes the Apollo shift and its source from Spec 3's content file, not a copy", async () => {
    const { dialog } = await logStandTest();
    expect(dialog).toHaveTextContent("NASA Apollo AP005, Table 6, first postflight minus preflight");
  });

  it("says so when there is no pre-flight test on record", async () => {
    const { dialog } = await logStandTest();
    const row = within(dialog).getByRole("row", { name: /Standing systolic BP/ });
    expect(within(row).getAllByRole("cell")[1]).toHaveTextContent("No pre-flight test on record");
  });

  it("asks for every value before saving, and saves nothing until then", async () => {
    const onReadings = renderHome();
    const dialog = await openForm("Log stand test");
    await fill(dialog, "Lying heart rate (bpm)", "62");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent("Enter standing heart rate and standing systolic blood pressure.");
    expect(onReadings).not.toHaveBeenCalled();
  });

  it("refuses values that cannot be right, saying which and why", async () => {
    const onReadings = renderHome();
    const dialog = await openForm("Log stand test");
    await fill(dialog, "Lying heart rate (bpm)", "0x5C");
    await fill(dialog, "Standing heart rate (bpm)", "920");
    await fill(dialog, "Standing systolic blood pressure (mmHg)", "110");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent(
      "Check lying heart rate and standing heart rate: enter a number from 20 to 250 bpm.",
    );
    expect(onReadings).not.toHaveBeenCalled();
  });

  it("moves focus to Done once saved, so it stays inside the dialog", async () => {
    await logStandTest();
    expect(screen.getByRole("button", { name: "Done" })).toHaveFocus();
  });

  it("logs at the mission time now, even when the clock is scrubbed back, and returns to now", async () => {
    const onReadings = renderHome();
    const slider = screen.getByRole("slider", { name: "Mission clock" });
    const now = Number(slider.getAttribute("aria-valuemax") ?? (slider as HTMLInputElement).max);
    fireEvent.change(slider, { target: { value: String(now - 6 * 3600) } });
    const dialog = await openForm("Log stand test");
    await fill(dialog, "Lying heart rate (bpm)", "62");
    await fill(dialog, "Standing heart rate (bpm)", "92");
    await fill(dialog, "Standing systolic blood pressure (mmHg)", "110");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect((onReadings.mock.calls[0][0] as Reading[]).every((r) => r.t === now)).toBe(true);
    expect((slider as HTMLInputElement).value).toBe(String(now));
  });

  it("closes with Escape and returns focus to the task button", async () => {
    renderHome();
    await openForm("Log stand test");
    await userEvent.keyboard("{Escape}");
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    expect(screen.getByRole("button", { name: "Log stand test" })).toHaveFocus();
  });
});

describe("post-EVA check form", () => {
  it("logs vitals and symptoms as self-reported Readings", async () => {
    const onReadings = renderHome();
    const dialog = await openForm("Log post-EVA check");
    await fill(dialog, "Heart rate (bpm)", "88");
    await userEvent.click(within(dialog).getByRole("radio", { name: "4" }));
    await answer(dialog, "Hand or finger pain", "Yes");
    for (const symptom of ["Joint pain", "Skin itch or rash", "Tingling or numbness"]) await answer(dialog, symptom, "No");
    await userEvent.type(within(dialog).getByLabelText("Note (optional)"), "Left index finger sore");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));

    const saved = onReadings.mock.calls[0][0] as Reading[];
    expect(saved.map((r) => [r.indicator, r.value, r.unit])).toEqual([
      ["post_eva_heart_rate", 88, "bpm"],
      ["fatigue", 4, "score 1-5"],
      ["hand_pain", 1, "yes/no"],
      ["joint_pain", 0, "yes/no"],
      ["skin_irritation", 0, "yes/no"],
      ["tingling", 0, "yes/no"],
    ]);
    expect(saved.every((r) => r.source === "manual")).toBe(true);
    expect(screen.queryByRole("dialog")).not.toBeInTheDocument();
    const physical = screen.getByRole("region", { name: "Physical health" });
    expect(within(physical).getByRole("group", { name: "Hand or finger pain" })).toHaveTextContent("Yes");
    expect(within(screen.getByRole("region", { name: "Mental health" })).getByRole("group", { name: "Fatigue" })).toHaveTextContent(
      "4 of 5",
    );
    const tasks = screen.getByRole("region", { name: "Today's tasks" });
    expect(within(tasks).getByRole("listitem", { name: /Post-EVA note/ })).toHaveTextContent("Left index finger sore");
  });

  it("asks for fatigue and every symptom before saving: a skipped question is not a 'No'", async () => {
    const onReadings = renderHome();
    const dialog = await openForm("Log post-EVA check");
    await fill(dialog, "Heart rate (bpm)", "88");
    await answer(dialog, "Hand or finger pain", "No");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(within(dialog).getByRole("alert")).toHaveTextContent(
      "Enter fatigue, joint pain, skin itch or rash and tingling or numbness.",
    );
    expect(onReadings).not.toHaveBeenCalled();
  });

  it("keeps the post-EVA heart rate apart from the wearable's, so the heart keeps its own beat", async () => {
    const body = fakeBodyScene();
    render(<App {...marsMission()} bodyScene={body.factory} />);
    const before = body.view.heartRate;
    const dialog = await openForm("Log post-EVA check");
    await fill(dialog, "Heart rate (bpm)", "130");
    await userEvent.click(within(dialog).getByRole("radio", { name: "2" }));
    for (const symptom of ["Hand or finger pain", "Joint pain", "Skin itch or rash", "Tingling or numbness"]) await answer(dialog, symptom, "No");
    await userEvent.click(within(dialog).getByRole("button", { name: "Save" }));
    expect(body.view.heartRate).toBe(before);
    expect(screen.getByRole("group", { name: "Heart rate after EVA" })).toHaveTextContent("130 bpm");
  });
});
