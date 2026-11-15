import { render, waitFor } from "@testing-library/react";
import { afterEach, beforeEach, describe, expect, it, vi } from "vitest";
import Tablet from "./Tablet";

const calls: string[] = [];

beforeEach(() => {
  calls.length = 0;
  vi.stubGlobal("fetch", vi.fn(async (url: string, init?: { method?: string }) => {
    calls.push(`${init?.method ?? "GET"} ${url}`);
    const body = url.startsWith("/api/view") ? { screen: "idle", t: 5 } : { emergency: "em-1" };
    return { ok: true, status: 200, statusText: "OK", json: async () => body };
  }));
});
afterEach(() => vi.unstubAllGlobals());

describe("hand-off from the health app", () => {
  it("opens the emergency flow once when started with autoStart", async () => {
    render(<Tablet crew="A" autoStart />);
    await waitFor(() => expect(calls).toContain("POST /api/trigger"));
    await new Promise((r) => setTimeout(r, 1200));
    expect(calls.filter((c) => c === "POST /api/trigger")).toHaveLength(1);
  });

  it("does not trigger anything by itself without autoStart", async () => {
    render(<Tablet crew="A" />);
    await waitFor(() => expect(calls.some((c) => c.startsWith("GET /api/view"))).toBe(true));
    expect(calls).not.toContain("POST /api/trigger");
  });
});
