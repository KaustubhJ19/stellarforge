import { useState } from "react";
import { api, type AccessEntry, type CrewRecord, type Explanation, type View } from "./api";
import { EmergencyLayout } from "./EmergencyLayout";
import { ReportPanel } from "./Report";

type Act = (fn: () => Promise<unknown>) => Promise<void>;
type Props = { crew: string; view: View | null; offline: boolean; error: string | null; act: Act };

export function Screen({ crew, view, offline, error, act }: Props) {
  if (!view) {
    return offline ? <Home crew={crew} offline act={act} /> : <p className="loading">Connecting…</p>;
  }
  const err = error ? <p className="error" role="alert">{error}</p> : null;
  if (view.screen === "idle") return <Home crew={crew} offline={offline} act={act} error={err} t={view.t} />;
  const L = (title: string, body: React.ReactNode) => (
    <EmergencyLayout title={title} patient={view.patient_name} offline={offline}>
      {err}
      {body}
    </EmergencyLayout>
  );

  switch (view.screen) {
    case "verdict":
      return L(
        view.urgency_label,
        <div data-screen="verdict">
          <p className={`urgency urgency-${(view.urgency ?? "none").toLowerCase()}`} data-testid="urgency">
            {view.urgency_label}
          </p>
          {view.questions.map((q) => (
            <fieldset key={q.id} className="question">
              <legend>{q.text}</legend>
              <div className="choices">
                {q.choices.map((c) => (
                  <button
                    key={c.id}
                    className={view.answers[q.id] === c.id ? "big selected" : "big"}
                    onClick={() => act(() => api.answer(crew, q.id, c.id))}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </fieldset>
          ))}
          {view.seconds_left !== null && (
            <p className="countdown">Crew alarm in {Math.ceil(view.seconds_left)} s if no answer</p>
          )}
        </div>,
      );
    case "help_requested":
      return L("Help requested", <p className="lead">Waiting for a crewmate to join.</p>);
    case "patient_alarm":
      return L("Crew alarm raised", <p className="lead">The crew has been alerted. Help is coming.</p>);
    case "patient_waiting":
      return L("Help is here", <p className="lead">Rescuer: {view.rescuers.join(", ")}</p>);
    case "alarm":
      return L(
        `CREW ALARM — ${view.patient_name}`,
        <div className="alarm" data-ring="true">
          <p className="lead">{view.patient_name} did not answer. Go now.</p>
          <button className="big primary" onClick={() => act(() => api.accept(crew))}>Accept — I'm going</button>
        </div>,
      );
    case "join":
      return L(
        `${view.patient_name} needs help`,
        <button className="big primary" onClick={() => act(() => api.accept(crew))}>Join as Rescuer 1</button>,
      );
    case "join_r2":
      return L(
        `${view.patient_name}: rescue in progress`,
        <button className="big primary" onClick={() => act(() => api.joinR2(crew))}>Join as Rescuer 2</button>,
      );
    case "observer":
      return L(
        view.question.text,
        <div className="choices">
          {view.question.choices.map((c) => (
            <button key={c.id} className="big" onClick={() => act(() => api.observer(crew, c.id))}>{c.label}</button>
          ))}
        </div>,
      );
    case "record":
      return L(
        `Crew record — ${view.patient_name}`,
        <>
          {view.ok && view.record ? (
            <div className="record">
              <p className="note">Opened in emergency mode. This access is logged.</p>
              <RecordDetails record={view.record} />
            </div>
          ) : (
            <p className="error" role="alert">Record not opened: {view.error}</p>
          )}
          <Nav crew={crew} act={act} canBack={view.can_back} />
        </>,
      );
    case "contributors":
      return L(
        "Likely contributors",
        <>
          {view.causes.length > 0 && <ol className="causes">{view.causes.map((c, i) => <li key={i}>{c}</li>)}</ol>}
          {view.message && <p className="note">{view.message}</p>}
          <Nav crew={crew} act={act} canBack={view.can_back} />
        </>,
      );
    case "step":
      return L(
        `Step ${view.index} of ${view.total}${view.role === "R2" ? " — Rescuer 2" : ""}`,
        <StepScreen crew={crew} view={view} act={act} />,
      );
    case "report":
      return L("Ground report", <ReportPanel view={view.report} />);
  }
}

function StepScreen({ crew, view, act }: { crew: string; view: Extract<View, { screen: "step" }>; act: Act }) {
  const [why, setWhy] = useState<{ step: string; data: Explanation | null; busy: boolean } | null>(null);
  const shown = why && why.step === view.step.id ? why : null;
  const ask = async () => {
    setWhy({ step: view.step.id, data: null, busy: true });
    try {
      setWhy({ step: view.step.id, data: await api.explain(crew), busy: false });
    } catch {
      setWhy({ step: view.step.id, data: { answer: "Not covered, ask ground.", source: null, mode: "refused", label: null }, busy: false });
    }
  };
  return (
    <div data-screen="step">
      {view.stub && <p className="stub-banner">STUB step: non-clinical test data</p>}
      <p className="step-text" data-testid="step-text">{view.step.text}</p>
      <p className="source" data-testid="step-source">
        Source: {view.step.source.guideline}, section {view.step.source.section}
      </p>
      <button className="big secondary" onClick={ask} disabled={shown?.busy}>Why this step?</button>
      {shown && (
        <div className="why" data-testid="why" aria-live="polite">
          {shown.busy ? "…" : (
            <>
              <p>{shown.data?.answer}</p>
              {shown.data?.source && <p className="source">Source: {shown.data.source.guideline}, section {shown.data.source.section}</p>}
              {shown.data?.label && <p className="note">{shown.data.label}</p>}
            </>
          )}
        </div>
      )}
      <Nav crew={crew} act={act} canBack={view.can_back} />
    </div>
  );
}

function Nav({ crew, act, canBack }: { crew: string; act: Act; canBack: boolean }) {
  return (
    <div className="nav">
      <button className="big" disabled={!canBack} onClick={() => act(() => api.back(crew))}>Back</button>
      <button className="big primary" onClick={() => act(() => api.next(crew))}>Next</button>
    </div>
  );
}

// Temporary home screen. Spec 2 owns the real home screen and its Emergency / Help buttons.
function Home({ crew, offline, act, error, t = 0 }: { crew: string; offline: boolean; act: Act; error?: React.ReactNode; t?: number }) {
  return (
    <main className="home">
      <h1>Crew tablet: {crew}</h1>
      {offline && <p className="offline" role="status">Service unavailable — continuing offline</p>}
      {error}
      <button className="big emergency-button" onClick={() => act(() => api.trigger(crew, t))}>
        Emergency
      </button>
      <AccessLog crew={crew} />
    </main>
  );
}

// Story 9: the patient sees every emergency opening of their record.
function AccessLog({ crew }: { crew: string }) {
  const [log, setLog] = useState<AccessEntry[] | null>(null);
  const load = () => api.accessLog(crew).then(setLog).catch(() => setLog(null));
  return (
    <details className="access-log" onToggle={(e) => (e.currentTarget.open ? load() : undefined)}>
      <summary>Who opened my record</summary>
      {log === null ? <p className="note">Not available.</p> : log.length === 0 ? <p className="note">No openings.</p> : (
        <ul>
          {log.map((x) => (
            <li key={x.id}>T+{Math.round(x.t)} s — {x.actor} — {x.allowed ? "opened" : "refused"} ({x.reason})</li>
          ))}
        </ul>
      )}
    </details>
  );
}

export function RecordDetails({ record }: { record: CrewRecord }) {
  return (
    <>
      <p><strong>Crew {record.id}</strong> · {record.sex} · {record.missionProfile}</p>
      <h2>Personal normal (Anchor)</h2>
      <ul>
        {Object.entries(record.anchor ?? {}).map(([k, a]) => (
          <li key={k}>{k}: {a.mean} ± {a.sd}</li>
        ))}
      </ul>
    </>
  );
}
