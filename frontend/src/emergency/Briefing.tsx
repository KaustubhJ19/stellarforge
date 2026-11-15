import { api, type Briefing, type CopilotChoice, type Route } from "./api";

// Collapse Copilot briefing (Spec 3). Context only: the protocol banner above it comes first.
export function BriefingPanel({ briefing }: { briefing: Briefing }) {
  return (
    <aside className="briefing" data-testid="briefing" aria-label="Briefing">
      <p className="note" data-testid="briefing-label">{briefing.context_label}</p>
      <p>{briefing.text}</p>
      <ul>
        {briefing.evidence?.map((ev, i) => (
          <li key={i}>
            {ev.text} <span className="note">({ev.label})</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}

type Protocols = { id: string; title: string }[];

// A choice is required before the steps: keep the router's pick, take the suggestion, pick another, or act alone.
export function ChoicePanel({ crew, route, protocols, suggestion, choice, act }: {
  crew: string; route: Route | null; protocols: Protocols; suggestion?: { protocol_id: string; title: string } | null;
  choice?: CopilotChoice | null; act: (fn: () => Promise<unknown>) => Promise<void>;
}) {
  const title = (id: string | null) => protocols.find((p) => p.id === id)?.title ?? id ?? "not covered";
  const pick = (kind: CopilotChoice["kind"], protocol?: string) => act(() => api.copilotChoice(crew, kind, protocol));
  return (
    <section className="choice" data-testid="choice" aria-label="Your choice">
      <p className="lead">{choice ? `Your choice: ${choice.kind === "none" ? "acting on your own" : title(choice.protocol_id)}` : "Choose before the steps"}</p>
      <button className="big" onClick={() => pick("router")}>Keep router default: {title(route?.protocol_id ?? null)}</button>
      {suggestion && <button className="big" onClick={() => pick("suggestion")}>Switch to copilot suggestion: {suggestion.title}</button>}
      <label>
        Other protocol{" "}
        <select value="" onChange={(e) => e.target.value && pick("other", e.target.value)}>
          <option value="">choose…</option>
          {protocols.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </label>
      <button className="big secondary" onClick={() => pick("none")}>None, I'll act on my own</button>
    </section>
  );
}
