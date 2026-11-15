import type { Status } from "../contracts";
import { StatusBadge } from "../status";
import { STATUS_RANK, type Glow } from "./glow";
import { STRUCTURES, type StructureId } from "./structures";

/** The body's Status in words and icons, so colour is never the only signal. */
export function BodyStatusList({ glow }: { glow: Glow }) {
  const rows: { name: string; status: Status }[] = [];
  if (glow.wholeBody) rows.push({ name: "Whole body", status: glow.wholeBody });
  for (const [id, status] of Object.entries(glow.structures) as [StructureId, Status | null][]) {
    if (status) rows.push({ name: STRUCTURES[id].label, status });
  }
  rows.sort((a, b) => STATUS_RANK[b.status] - STATUS_RANK[a.status]);
  if (rows.length === 0) return <p className="empty">Nothing to show on the body yet.</p>;
  return (
    <details className="fold">
      <summary>Body status</summary>
      <ul className="body-status" aria-label="Body status">
        {rows.map((r) => (
          <li key={r.name} aria-label={r.name} className="body-status__item" data-status={r.status}>
            <span>{r.name}</span>
            <StatusBadge status={r.status} />
          </li>
        ))}
      </ul>
    </details>
  );
}
