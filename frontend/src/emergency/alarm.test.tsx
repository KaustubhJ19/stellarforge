import { render } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";
import { Screen } from "./screens";
import type { View } from "./api";

const base = { emergency: "em-1", patient: "cmdr", patient_name: "Crew cmdr", disclaimer: "Decision support, not diagnosis.", t: 16 };
const alarm: View = { ...base, screen: "alarm", ring: true };
const idle: View = { screen: "idle", t: 16 };

function fakeAudio(state: "running" | "suspended") {
  const started: number[] = [];
  class FakeCtx {
    state = state;
    currentTime = 0;
    destination = {};
    resume = vi.fn(async () => undefined);
    createGain() { return { gain: { value: 0 }, connect: (d: unknown) => d }; }
    createOscillator() {
      return { type: "", frequency: { value: 0 }, connect: (g: unknown) => g, start: () => started.push(1), stop: () => undefined };
    }
  }
  vi.stubGlobal("AudioContext", FakeCtx);
  return started;
}
afterEach(() => vi.unstubAllGlobals());

describe("ticket 06: audible crew alarm", () => {
  it("beeps while the alarm screen is shown and stops after it", async () => {
    vi.resetModules();
    const started = fakeAudio("running");
    const { Screen: S } = await import("../screens");
    const { container, rerender } = render(<S crew="eng" view={alarm} offline={false} error={null} act={async () => {}} />);
    expect(started.length).toBe(1);
    expect(container.querySelector("[data-sound]")?.getAttribute("data-sound")).toBe("playing");
    rerender(<S crew="eng" view={idle} offline={false} error={null} act={async () => {}} />);
    const n = started.length;
    await new Promise((r) => setTimeout(r, 800));
    expect(started.length).toBe(n); // no more beeps once the alarm is gone
  });

  it("tells the crew when the browser blocks sound", async () => {
    vi.resetModules();
    fakeAudio("suspended");
    const { Screen: S } = await import("../screens");
    const { getByRole } = render(<S crew="eng" view={alarm} offline={false} error={null} act={async () => {}} />);
    expect(getByRole("alert")).toHaveTextContent("tap anywhere to enable the alarm sound");
  });

  it("no sound outside the alarm screen", () => {
    const started = fakeAudio("running");
    render(<Screen crew="eng" view={idle} offline={false} error={null} act={async () => {}} />);
    expect(started.length).toBe(0);
  });
});
