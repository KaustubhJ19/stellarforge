import type { ReportView } from "./api";

const mmss = (s: number) => {
  const m = Math.floor(s / 60);
  return `${m} min ${Math.round(s - m * 60)} s`;
};

export function ReportPanel({ view }: { view: ReportView | null }) {
  if (!view) return <p className="note">Ground report not available.</p>;
  const r = view.report;
  const wait = Math.max(0, view.expected_reply_t - view.now);
  return (
    <div className="report" data-testid="report">
      <p className="lead">Sent at T+{mmss(r.sent_t)}. Expected reply at T+{mmss(view.expected_reply_t)}.</p>
      <p className="note">{view.delay_label}</p>
      {view.reply_visible && r.reply ? (
        <div className="reply" data-testid="ground-reply"><strong>Flight surgeon:</strong> {r.reply}</div>
      ) : view.reply_late ? (
        <p className="warning" data-testid="reply-late">Reply is late. Keep acting on your own with the protocol.</p>
      ) : (
        <p className="warning">No reply yet (about {mmss(wait)}). Act on your own meanwhile.</p>
      )}
      <h2>Summary</h2>
      <p>{r.summary}</p>
      <details>
        <summary>History ({r.history.length}) · Timeline ({r.timeline.length}) · Actions ({r.actions.length})</summary>
        <pre>{JSON.stringify({ history: r.history, timeline: r.timeline, actions: r.actions }, null, 1)}</pre>
      </details>
    </div>
  );
}
