import { useRef, type ReactNode } from "react";
import { useModal } from "../home/useModal";

/** A modal form sized for gloved hands: large type, large fields and buttons. */
export function FormDialog({ title, onClose, wide = false, children }: { title: string; onClose: () => void; wide?: boolean; children: ReactNode }) {
  const dialog = useRef<HTMLDivElement>(null);
  const close = useRef<HTMLButtonElement>(null);
  useModal(dialog, close, onClose);
  return (
    <div className="card-backdrop" onClick={onClose}>
      <div
        className={wide ? "card form-dialog form-dialog--wide" : "card form-dialog"}
        ref={dialog}
        role="dialog"
        aria-modal="true"
        aria-label={title}
        onClick={(e) => e.stopPropagation()}
      >
        <header className="card__head">
          <h2>{title}</h2>
          <button ref={close} onClick={onClose}>
            Close
          </button>
        </header>
        {children}
      </div>
    </div>
  );
}

/** "a", "a and b", "a, b and c". */
export function listed(items: string[]): string {
  return items.length < 2 ? items.join("") : `${items.slice(0, -1).join(", ")} and ${items[items.length - 1]}`;
}

export interface NumberField {
  /** Lower-case name used in messages, e.g. "standing heart rate". */
  name: string;
  unit: string;
  range: [number, number];
}

/** A plain decimal number inside the field's range; "missing" if blank, "wrong" otherwise. */
export function readNumber(text: string, field: NumberField): number | "missing" | "wrong" {
  const s = text.trim();
  if (s === "") return "missing";
  if (!/^\d+(\.\d+)?$/.test(s)) return "wrong";
  const n = Number(s);
  return n >= field.range[0] && n <= field.range[1] ? n : "wrong";
}

/**
 * One message for every problem: "Enter a and b." for blanks, and "Check c: enter a number
 * from 20 to 250 bpm." for values that cannot be right (grouped by range).
 */
export function problemsWith(missing: string[], wrong: NumberField[]): string | null {
  const parts: string[] = [];
  if (missing.length) parts.push(`Enter ${listed(missing)}.`);
  const byRange = new Map<string, string[]>();
  for (const f of wrong) {
    const key = `${f.range[0]} to ${f.range[1]} ${f.unit}`;
    byRange.set(key, [...(byRange.get(key) ?? []), f.name]);
  }
  for (const [range, names] of byRange) parts.push(`Check ${listed(names)}: enter a number from ${range}.`);
  return parts.length ? parts.join(" ") : null;
}
