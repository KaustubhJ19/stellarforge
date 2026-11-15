// Thin client for the local backend. Same origin in production (served by FastAPI),
// proxied to :8000 in dev.

export type Choice = { id: string; label: string };
export type Question = { id: string; text: string; choices: Choice[] };
export type Step = {
  id: string;
  text: string;
  source: { guideline: string; section: string };
  equipment: string[];
  rescuers: number;
};

type Base = { emergency: string; patient: string; patient_name: string; disclaimer: string };
// Present only when the service routes by intent (docs/spec-intent-routing.md).
export type Route = { protocol_id: string | null; rule_id: string; reason: string };
type Rescuer = Base & {
  role: "R1" | "R2";
  can_back: boolean;
  route?: Route | null;
  protocols?: { id: string; title: string }[];
};

export type View = (
  | { screen: "idle" }
  | (Base & {
      screen: "verdict";
      urgency: string | null;
      urgency_label: string;
      questions: Question[];
      answers: Record<string, string>;
      seconds_left: number | null;
    })
  | (Base & { screen: "help_requested" | "patient_alarm" | "patient_waiting"; rescuers: string[] })
  | (Base & { screen: "alarm" | "join"; ring: boolean })
  | (Base & { screen: "join_r2"; ring: boolean; rescuer1: string })
  | (Rescuer & { screen: "observer"; question: Question })
  | (Rescuer & { screen: "intake"; fields: Record<string, string[]> })
  | (Rescuer & { screen: "record"; ok: boolean; record?: CrewRecord; error?: string })
  | (Rescuer & { screen: "contributors"; causes: string[]; message: string | null })
  | (Rescuer & { screen: "step"; step: Step; index: number; total: number; stub: boolean })
  | (Rescuer & { screen: "report"; report: ReportView | null })
) & { t: number };

export type AccessEntry = { id: number; t: number; actor: string; subject: string; allowed: boolean; reason: string };

// Spec 1 CrewRecord.
export type CrewRecord = {
  id: string;
  sex: string;
  missionProfile: string;
  anchor: Record<string, { mean: number; sd: number }>;
};

export type ReportView = {
  report: {
    id: string;
    crew: string;
    summary: string;
    history: Record<string, unknown>[];
    timeline: Record<string, unknown>[];
    actions: Record<string, unknown>[];
    sent_t: number;
    reply_t?: number | null;
    reply?: string | null;
  };
  expected_reply_t: number;
  delay_label: string;
  reply_visible: boolean;
  reply_late: boolean;
  now: number;
};

export type Explanation = {
  answer: string;
  source: { guideline: string; section: string } | null;
  mode: "live" | "recorded" | "refused";
  label: string | null;
};

export class ApiError extends Error {
  constructor(public status: number, message: string) {
    super(message);
  }
}

async function call<T>(method: string, path: string, body?: unknown): Promise<T> {
  let res: Response;
  try {
    res = await fetch(path, {
      method,
      headers: body ? { "Content-Type": "application/json" } : undefined,
      body: body ? JSON.stringify(body) : undefined,
    });
  } catch {
    throw new ApiError(0, "service unavailable");
  }
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new ApiError(res.status, (data as { error?: string }).error ?? res.statusText);
  return data as T;
}

export const api = {
  view: (crew: string) => call<View>("GET", `/api/view?crew=${encodeURIComponent(crew)}`),
  trigger: (crew: string, t: number, reason = "Emergency button") =>
    call<{ emergency: string }>("POST", "/api/trigger", { schema_version: "1.0.0", kind: "manual", crew, t, reason }),
  answer: (crew: string, question: string, choice: string) => call<View>("POST", "/api/answer", { crew, question, choice }),
  accept: (crew: string) => call<{ role: string }>("POST", "/api/accept", { crew }),
  joinR2: (crew: string) => call<{ role: string }>("POST", "/api/join-r2", { crew }),
  observer: (crew: string, choice: string) => call<View>("POST", "/api/observer", { crew, choice }),
  intake: (crew: string, intake: Record<string, string>) => call<View>("POST", "/api/intake", { crew, intake }),
  switchProtocol: (crew: string, protocol: string) => call<View>("POST", "/api/switch-protocol", { crew, protocol }),
  next: (crew: string) => call<View>("POST", "/api/next", { crew }),
  back: (crew: string) => call<View>("POST", "/api/back", { crew }),
  explain: (crew: string) => call<Explanation>("POST", "/api/explain", { crew }),
  accessLog: (crew: string) =>
    call<AccessEntry[]>("GET", `/api/access-log?crew=${encodeURIComponent(crew)}&viewer=${encodeURIComponent(crew)}`),
  crew: () => call<{ crew: string[]; names: Record<string, string>; t: number; stub: boolean; profile: string }>("GET", "/api/sim/crew"),
  console: () => call<ConsoleView>("GET", "/api/console"),
  reply: (report: string, text: string, scripted = false) =>
    call<unknown>("POST", "/api/console/reply", { report, text, scripted }),
};

export type ConsoleView = {
  now: number;
  scripted_reply: string;
  reports: {
    id: string;
    crew: string;
    arrived: boolean;
    arrives_t: number;
    report: ReportView["report"];
    replied: boolean;
  }[];
};
