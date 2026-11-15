import type { ChainStatus, CopilotEvent, CopilotSection } from "./api";

const kindOf = (ev: CopilotEvent) => ev.type.replace(/^copilot_/, "");

function describe(ev: CopilotEvent): string {
  switch (kindOf(ev)) {
    case "assessment": {
      const l0 = ev.l0 as { rule_id?: string } | undefined;
      const b = ev.briefing as { text?: string } | undefined;
      return `Assessed: ${l0?.rule_id ? `rule ${l0.rule_id}. ` : ""}${b?.text ?? ""}`;
    }
    case "choice":
      return `Rescuer ${String(ev.by)} chose "${String(ev.kind)}" (protocol ${String(ev.protocol_id ?? "none")}).`;
    case "investigator": {
      const notes = (ev.notes as { claim: string }[] | undefined) ?? [];
      return `Investigator ${String(ev.status)}: ${notes.length} verified note(s), ${String(ev.dropped ?? 0)} dropped.`;
    }
    case "ground_reply":
      return "Ground reply delivered.";
    case "outcome_label":
      return `Outcome labelled: ${String(ev.text)}`;
    default:
      return kindOf(ev);
  }
}

/** The tamper check is the headline: ground re-checks the copy it received, the crew sees the check made at send. */
export function ChainBadge({ status }: { status: ChainStatus }) {
  return status.ok ? (
    <p className="note" data-testid="chain-status">Record verified: {status.length} events, chain intact.</p>
  ) : (
    <p className="warning" role="alert" data-testid="chain-status">
      Record check FAILED: {status.reason || "chain broken"}. Do not rely on this record.
    </p>
  );
}

export function CopilotRecord({ section, status }: { section: CopilotSection | undefined; status?: ChainStatus | null }) {
  if (!section) return null;
  const t = section.timings ?? {};
  return (
    <section className="copilot-record" data-testid="copilot-record" aria-label="Copilot record">
      <h2>Copilot record</h2>
      <ChainBadge status={status ?? section.chain} />
      <ol>
        {section.events.map((ev, i) => (
          <li key={i}>T+{Math.round(ev.t)} s · {describe(ev)}</li>
        ))}
      </ol>
      <p className="note" data-testid="copilot-versions">
        Build: {String(section.versions?.model ?? "unknown")} · schema {String(section.versions?.schema_version ?? "?")}
        {t.choice_after_s !== undefined && ` · choice after ${t.choice_after_s} s`}
        {t.investigator_elapsed_s !== undefined && ` · investigator ${t.investigator_elapsed_s} s`}
      </p>
    </section>
  );
}
