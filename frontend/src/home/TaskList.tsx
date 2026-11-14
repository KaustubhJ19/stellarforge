import type { Task } from "../contracts";

export type CrewForm = "stand-test" | "post-eva";

export function TaskList({ tasks, onLog }: { tasks: Task[]; onLog?: (form: CrewForm) => void }) {
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
      {onLog && (
        <div className="tasks__forms">
          <button onClick={() => onLog("stand-test")}>Log stand test</button>
          <button onClick={() => onLog("post-eva")}>Log post-EVA check</button>
        </div>
      )}
    </section>
  );
}
