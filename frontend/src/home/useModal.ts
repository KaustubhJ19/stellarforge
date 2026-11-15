import { useEffect, type RefObject } from "react";

/**
 * Modal behaviour shared by every dialog: focus starts on `initial`, Tab stays inside,
 * Escape closes, and focus goes back to what opened it on close.
 */
export function useModal(dialog: RefObject<HTMLElement | null>, initial: RefObject<HTMLElement | null>, onClose: () => void) {
  useEffect(() => {
    const opener = document.activeElement as HTMLElement | null;
    initial.current?.focus();
    function onKey(e: KeyboardEvent) {
      if (e.key === "Escape") {
        onClose();
        return;
      }
      if (e.key !== "Tab" || !dialog.current) return;
      // A closed dropdown (<details>) hides everything but its <summary> from Tab.
      const focusable = [
        ...dialog.current.querySelectorAll<HTMLElement>(
          "button, [href], input, select, textarea, summary, [tabindex]:not([tabindex='-1'])",
        ),
      ].filter((el) => {
        const closed = el.closest("details:not([open])");
        return !closed || (el.tagName === "SUMMARY" && el.parentElement === closed);
      });
      if (focusable.length === 0) return;
      const first = focusable[0];
      const last = focusable[focusable.length - 1];
      if (e.shiftKey && document.activeElement === first) {
        e.preventDefault();
        last.focus();
      } else if (!e.shiftKey && document.activeElement === last) {
        e.preventDefault();
        first.focus();
      }
    }
    document.addEventListener("keydown", onKey);
    return () => {
      document.removeEventListener("keydown", onKey);
      opener?.focus();
    };
  }, [dialog, initial, onClose]);
}
