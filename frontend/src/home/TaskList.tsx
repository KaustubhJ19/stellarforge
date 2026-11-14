import type { Task } from "../contracts";

export function TaskList({ tasks }: { tasks: Task[] }) {
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
    </section>
  );
}
