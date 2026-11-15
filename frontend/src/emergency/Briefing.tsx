import type { Briefing } from "./api";

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
