import type { Investigator } from "./api";

// Collapse Copilot L3 notes (Spec 3). Separate from the ranking and the protocol; each note points at its record.
export function InvestigatorPanel({ panel }: { panel: Investigator }) {
  const notes = panel.notes ?? [];
  return (
    <aside className="briefing" data-testid="investigator" aria-label="AI investigator notes">
      <h3>AI investigator notes</h3>
      <p className="note" data-testid="investigator-label">{panel.label}</p>
      {panel.status === "running" && <p>Investigator running…</p>}
      {panel.status === "unavailable" && <p data-testid="investigator-unavailable">{panel.message ?? "investigator unavailable"}</p>}
      {panel.status === "ok" && notes.length === 0 && <p>No verified notes.</p>}
      <ul>
        {notes.map((n, i) => (
          <li key={i}>
            {n.claim}{" "}
            {n.sources.map((s, j) => (
              <span className="note" key={j} data-testid="investigator-source">
                (source: {s.tool} › {s.field} = {String(s.value)}, {s.crew} record at t={s.snapshot_t}; {s.snapshot_label})
              </span>
            ))}
          </li>
        ))}
      </ul>
      {panel.status === "ok" && !!panel.dropped && (
        <p className="note" data-testid="investigator-dropped">{panel.dropped} unverified claim(s) dropped.</p>
      )}
    </aside>
  );
}
