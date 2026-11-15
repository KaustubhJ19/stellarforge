import type { MissionTime, Task } from "../contracts";
import { formatMissionTime } from "../replay/time";

/** A note the crew typed in a form, shown until the service stores it. */
export interface CrewNote {
  t: MissionTime;
  title: string;
  text: string;
}

export type CrewForm = "stand-test" | "post-eva";

export function TaskList({
  tasks,
  notes = [],
  onLog,
}: {
  tasks: Task[];
  notes?: CrewNote[];
  onLog?: (form: CrewForm) => void;
}) {
  return (
    <section className="tasks" aria-label="Today's tasks">
      <h2>Today's tasks</h2>
      {tasks.length === 0 ? (
        <p className="empty">Nothing due today.</p>
      ) : (
        <ul>
          {tasks.map((t) => (
            <li key={t.id} data-done={t.done}>
              <span className="tasks__mark" aria-hidden="true">
                {t.done ? "✓" : "○"}
              </span>
              <span className="tasks__title">{t.title}</span>
              <span className="tasks__state">{t.done ? "Done" : "Due"}</span>
            </li>
          ))}
        </ul>
      )}
      {notes.length > 0 && (
        <ul className="tasks__notes" aria-label="Notes">
          {notes.map((n, i) => {
            const heading = `${n.title}, ${formatMissionTime(n.t)}`;
            return (
              <li key={i} aria-label={heading}>
                <strong>{heading}:</strong> {n.text}
              </li>
            );
          })}
        </ul>
      )}
      {onLog && (
        <div className="tasks__forms">
          <button onClick={() => onLog("stand-test")}>Log stand test</button>
          <button onClick={() => onLog("post-eva")}>Log post-EVA check</button>
        </div>
      )}
    </section>
  );
}
