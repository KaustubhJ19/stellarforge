import { useEffect, useState } from "react";
import { api, type AccessEntry, type CrewRecord, type Explanation, type Route, type View } from "./api";
import { loadBundle, type Bundle } from "./offline";
import { EmergencyLayout } from "./EmergencyLayout";
import { ReportPanel } from "./Report";
import { StepCard } from "./StepCard";
import { useAlarmSound } from "./alarm";

type Act = (fn: () => Promise<unknown>) => Promise<void>;
type Props = { crew: string; view: View | null; offline: boolean; error: string | null; act: Act };

export function Screen({ crew, view, offline, error, act }: Props) {
  const sound = useAlarmSound(view?.screen === "alarm");
  if (!view) {
    return offline ? <Home crew={crew} offline act={act} /> : <p className="loading">Connecting…</p>;
  }
  const err = error ? <p className="error" role="alert">{error}</p> : null;
  if (view.screen === "idle") return <Home crew={crew} offline={offline} act={act} error={err} t={view.t} />;
  const route = "route" in view && view.route ? view.route : null; // only when the service routes by intent
  const protocols = "protocols" in view ? view.protocols ?? [] : [];
  const L = (title: string, body: React.ReactNode) => (
    <EmergencyLayout title={title} patient={view.patient_name} offline={offline}>
      {err}
      {route && view.screen !== "intake" && <RouteBanner crew={crew} route={route} protocols={protocols} act={act} />}
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
        <div className="alarm" data-ring="true" data-sound={sound}>
          {sound === "blocked" && <p className="warning" role="alert">Sound blocked by the browser — tap anywhere to enable the alarm sound.</p>}
          {sound === "unsupported" && <p className="warning">No alarm sound on this device.</p>}
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
    case "intake":
      return L("What is happening?", <IntakeForm crew={crew} fields={view.fields} act={act} />);
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

// Question and answer labels are placeholders pending Spec 5. They route; they are not clinical guidance.
const INTAKE_QUESTIONS: { key: string; text: string; labels: Record<string, string> }[] = [
  { key: "responsive", text: "Does the patient respond?", labels: { yes: "Yes, responds", no: "No response" } },
  { key: "breathing", text: "Is the patient breathing?", labels: { normal: "Normal", abnormal: "Abnormal", none: "Not breathing" } },
  {
    key: "main_problem", text: "What is the main problem?",
    labels: {
      chest_pain: "Chest pain", breathing_trouble: "Trouble breathing", cabin_alert: "Cabin air alert",
      collapse: "Collapse", injury: "Injury", other: "Something else",
    },
  },
];

function IntakeForm({ crew, fields, act }: { crew: string; fields: Record<string, string[]>; act: Act }) {
  const [answers, setAnswers] = useState<Record<string, string>>({});
  const asked = INTAKE_QUESTIONS.filter((q) => fields[q.key]);
  const ready = asked.every((q) => answers[q.key]);
  const submit = () => act(() => api.intake(crew, Object.fromEntries(asked.map((q) => [q.key, answers[q.key]]))));
  return (
    <div data-screen="intake">
      {asked.map((q) => (
        <fieldset key={q.key} className="question">
          <legend>{q.text}</legend>
          <div className="choices">
            {fields[q.key].map((v) => (
              <button
                key={v}
                className={answers[q.key] === v ? "big selected" : "big"}
                aria-pressed={answers[q.key] === v}
                onClick={() => setAnswers((a) => ({ ...a, [q.key]: v }))}
              >
                {q.labels[v] ?? v}
              </button>
            ))}
          </div>
        </fieldset>
      ))}
      <button className="big primary" disabled={!ready} onClick={submit}>Confirm</button>
    </div>
  );
}

function RouteBanner({ crew, route, protocols, act }: {
  crew: string; route: Route; protocols: { id: string; title: string }[]; act: Act;
}) {
  const title = protocols.find((p) => p.id === route.protocol_id)?.title ?? route.protocol_id;
  return (
    <div className="route" data-testid="route-banner">
      <p className="lead">{route.protocol_id ? `Using: ${title}` : "Not covered by this tool. Contact ground."}</p>
      <p className="note">{route.reason}</p>
      <label>
        Switch protocol{" "}
        <select value={route.protocol_id ?? ""} onChange={(e) => act(() => api.switchProtocol(crew, e.target.value))}>
          {route.protocol_id === null && <option value="" disabled>none</option>}
          {protocols.map((p) => <option key={p.id} value={p.id}>{p.title}</option>)}
        </select>
      </label>
    </div>
  );
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
      <StepCard index={view.index} total={view.total} step={view.step} />
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
  // The health app's Help button opens this screen with ?start=help: show who to help straight away.
  const [pick, setPick] = useState(() => new URLSearchParams(window.location.search).get("start") === "help");
  const [others, setOthers] = useState<{ id: string; name: string }[]>([]);
  const [helping, setHelping] = useState<string | null>(null);
  useEffect(() => {
    if (!pick) return;
    // Same crew list the offline screen uses; the copy this tablet cached covers a service that just went away.
    fetch("/api/offline-bundle")
      .then((r) => (r.ok ? (r.json() as Promise<Bundle>) : null))
      .catch(() => null)
      .then((b) => b ?? loadBundle())
      .then((b) => setOthers(b ? b.profile.crew.filter((id) => id !== crew).map((id) => ({ id, name: b.names[id] ?? id })) : []));
  }, [pick, crew]);
  const help = (other: { id: string; name: string }) =>
    act(async () => {
      await api.trigger(other.id, t, "Help a crewmate");
      setHelping(other.name);
    });
  return (
    <main className="home">
      <h1>Crew tablet: {crew}</h1>
      {offline && <p className="offline" role="status">Service unavailable — continuing offline</p>}
      {error}
      <button className="big emergency-button" onClick={() => act(() => api.trigger(crew, t))}>
        Emergency
      </button>
      <button className="big" aria-expanded={pick} onClick={() => setPick(!pick)}>
        Help a crewmate
      </button>
      {pick && (
        <div className="choices">
          {others.map((o) => (
            <button key={o.id} className="big" onClick={() => help(o)}>
              {o.name}
            </button>
          ))}
        </div>
      )}
      {helping && (
        <p className="note" role="status">
          Emergency started for {helping}. When the crew alarm rings on this tablet, press Accept.
        </p>
      )}
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
