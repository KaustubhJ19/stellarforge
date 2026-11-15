import { useState } from "react";
import { EmergencyLayout } from "./EmergencyLayout";
import { RecordDetails } from "./screens";
import { StepCard } from "./StepCard";
import { enqueue, missionNow, type Bundle } from "./offline";

export type OfflineSession = { patient: string; asRescuer: boolean };
const REFUSAL = "Not covered, ask ground.";

// Backend-down emergency mode: cached cited steps, one per screen, solo-rescuer filter.
// Opening another person's record is logged on this tablet and synced later.
export function OfflineFlow({ crew, bundle, session, onEnd }: {
  crew: string;
  bundle: Bundle;
  session: OfflineSession;
  onEnd: () => void;
}) {
  const steps = bundle.protocol.steps;
  const [pos, setPos] = useState(session.asRescuer ? -1 : 0); // -1 = record screen
  const [why, setWhy] = useState<string | null>(null);
  const name = bundle.names[session.patient] ?? session.patient;

  const go = (next: number) => {
    if (pos >= 0 && pos < steps.length && next > pos) {
      enqueue(crew, "step_completed", { step: steps[pos].id, patient: session.patient });
    }
    if (next >= 0 && next < steps.length) enqueue(crew, "step_shown", { step: steps[next].id, patient: session.patient });
    setWhy(null);
    setPos(next);
  };

  const nav = (
    <div className="nav">
      <button className="big" disabled={pos <= (session.asRescuer ? -1 : 0)} onClick={() => go(pos - 1)}>Back</button>
      <button className="big primary" onClick={() => go(pos + 1)} disabled={pos >= steps.length}>Next</button>
    </div>
  );

  if (pos === -1) {
    const rec = bundle.records[session.patient];
    return (
      <EmergencyLayout title={`Crew record — ${name}`} patient={name} offline>
        <p className="note">Opened offline in emergency mode. This access is logged on this tablet and sent when the service returns.</p>
        {rec ? (
          <div className="record">
            <RecordDetails record={rec} />
          </div>
        ) : <p className="note">No cached record.</p>}
        {nav}
      </EmergencyLayout>
    );
  }
  if (pos >= steps.length) {
    return (
      <EmergencyLayout title="End of cached steps" patient={name} offline>
        <p className="lead">No ground report while the service is down. Keep following the protocol; the report is built when the service returns.</p>
        <button className="big" onClick={() => go(pos - 1)}>Back</button>
        <button className="big primary" onClick={onEnd}>End offline session</button>
      </EmergencyLayout>
    );
  }
  const s = steps[pos];
  return (
    <EmergencyLayout title={`Step ${pos + 1} of ${steps.length} (offline)`} patient={name} offline>
      <p className="note">Urgency not assessed (offline). Crew alarm unavailable while the service is down.</p>
      {bundle.protocol.stub && <p className="stub-banner">STUB step: non-clinical test data</p>}
      <StepCard index={pos + 1} total={steps.length} step={s} />
      <button className="big secondary" onClick={() => setWhy(REFUSAL)}>Why this step?</button>
      {why && <div className="why" data-testid="why"><p>{why}</p><p className="note">Explainer unavailable offline.</p></div>}
      {nav}
    </EmergencyLayout>
  );
}

export function startOffline(crew: string, patient: string): OfflineSession {
  const asRescuer = patient !== crew;
  enqueue(crew, "trigger", {
    schema_version: "1.0.0", kind: "manual", crew: patient, t: Math.max(0, Math.round(missionNow() * 1000) / 1000), reason: asRescuer ? "Help a crewmate (offline)" : "Emergency button (offline)",
  });
  if (asRescuer) enqueue(crew, "record_access", { actor: crew, subject: patient });
  return { patient, asRescuer };
}
