import type { Status } from "./contracts";

/** Status is always shown as colour + icon + words, never colour alone. */
export const STATUS_TEXT: Record<Status, { label: string; icon: string }> = {
  green: { label: "Normal", icon: "✓" },
  amber: { label: "Watch", icon: "!" },
  red: { label: "Act now", icon: "✕" },
};

export function StatusBadge({ status }: { status: Status }) {
  const { label, icon } = STATUS_TEXT[status];
  return (
    <span className="status-badge" data-status={status}>
      <span className="status-badge__icon" data-testid="status-icon" aria-hidden="true">
        {icon}
      </span>
      <span>{label}</span>
    </span>
  );
}
