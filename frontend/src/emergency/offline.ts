// Backend-down support (ticket 14): cached offline bundle + local queue synced later.
// Storage can be unavailable (private mode, quota): every access is wrapped.
import type { Question, Step, CrewRecord } from "./api";

export type Bundle = {
  protocol: { id: string; title: string; stub: boolean; steps: Step[] };
  profile: { id: string; crew: string[]; delay_label: string | null };
  records: Record<string, CrewRecord>;
  names: Record<string, string>;
  questions: Question[];
  disclaimer: string;
};

export type QueueItem = {
  id: string;
  type: "trigger" | "step_shown" | "step_completed" | "record_access";
  t: number;
  data: Record<string, unknown>;
};

const BUNDLE = "sf-offline-bundle";
const QUEUE = "sf-offline-queue";
const CLOCK = "sf-mission-clock"; // last known mission time + wall time it was seen

function get<T>(key: string): T | null {
  try {
    const v = localStorage.getItem(key);
    return v ? (JSON.parse(v) as T) : null;
  } catch {
    return null;
  }
}

function put(key: string, value: unknown): boolean {
  try {
    localStorage.setItem(key, JSON.stringify(value));
    return true;
  } catch {
    return false;
  }
}

export const saveBundle = (b: Bundle) => put(BUNDLE, b);
export const loadBundle = () => get<Bundle>(BUNDLE);

export function noteMissionTime(t: number) {
  put(CLOCK, { t, wall: Date.now() });
}

// Offline estimate of mission time: last server time + elapsed wall time (1x clock assumed).
export function missionNow(): number {
  const c = get<{ t: number; wall: number }>(CLOCK);
  return c ? c.t + (Date.now() - c.wall) / 1000 : 0;
}

export function queue(): QueueItem[] {
  return get<QueueItem[]>(QUEUE) ?? [];
}

let seq = 0;
export function enqueue(tablet: string, type: QueueItem["type"], data: Record<string, unknown>): QueueItem {
  const item: QueueItem = { id: `${tablet}-${Date.now()}-${seq++}`, type, t: Math.round(missionNow() * 1000) / 1000, data };
  put(QUEUE, [...queue(), item]);
  return item;
}

// Send queued items once; remove them only after the backend confirms.
export async function flush(tablet: string): Promise<number> {
  const items = queue();
  if (!items.length) return 0;
  const res = await fetch("/api/sync", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ tablet, items }),
  });
  if (!res.ok) throw new Error(`sync failed: ${res.status}`);
  const sent = new Set(items.map((i) => i.id));
  put(QUEUE, queue().filter((i) => !sent.has(i.id)));
  return items.length;
}
