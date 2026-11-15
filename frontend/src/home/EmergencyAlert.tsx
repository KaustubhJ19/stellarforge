import { useEffect, useRef, useState } from "react";
import { useModal } from "./useModal";

const POLL_MS = 2000;

/** The tablet screens that mean "someone else needs you", and what to say for each. */
const WORDS = { join: "needs help", alarm: "needs help", join_r2: "needs a second rescuer" } as const;

type Seen = { screen: keyof typeof WORDS; emergency: string; patient: string; patient_name: string };

const isAsking = (v: unknown): v is Seen =>
  typeof v === "object" && v !== null && "screen" in v && typeof v.screen === "string" && v.screen in WORDS;

/**
 * Pops up on this person's dashboard when another crew member needs help. It asks the emergency
 * service for this person's tablet state; with no service it stays silent, so replay mode is unaffected.
 */
export function EmergencyAlert({ crew, everyMs = POLL_MS }: { crew: string; everyMs?: number }) {
  const [asking, setAsking] = useState<Seen | null>(null);
  const [dismissed, setDismissed] = useState<string | null>(null);

  useEffect(() => {
    let alive = true;
    async function poll() {
      try {
        const r = await fetch(`/api/view?crew=${encodeURIComponent(crew)}`);
        const v: unknown = r.ok ? await r.json() : null;
        if (alive) setAsking(isAsking(v) ? v : null);
      } catch {
        if (alive) setAsking(null); // no service (or not JSON): nothing to show
      }
    }
    poll();
    const id = setInterval(poll, everyMs);
    return () => {
      alive = false;
      clearInterval(id);
    };
  }, [crew, everyMs]);

  const key = asking ? `${asking.emergency}:${asking.screen}` : null;
  if (!asking || key === dismissed) return null;
  return <Popup crew={crew} asking={asking} onDismiss={() => setDismissed(key)} />;
}

function Popup({ crew, asking, onDismiss }: { crew: string; asking: Seen; onDismiss: () => void }) {
  const dialog = useRef<HTMLDivElement>(null);
  const respond = useRef<HTMLAnchorElement>(null);
  useModal(dialog, respond, onDismiss);
  const title = `${asking.patient_name} ${WORDS[asking.screen]}`;
  return (
    <div className="card-backdrop">
      <div className="card alert-pop" ref={dialog} role="alertdialog" aria-modal="true" aria-label={title}>
        <h2>{title}</h2>
        <p>Open your emergency tablet to respond.</p>
        <a className="alert-pop__respond" ref={respond} href={`/emergency.html?crew=${encodeURIComponent(crew)}`}>
          Respond
        </a>
        <button onClick={onDismiss}>Dismiss</button>
      </div>
    </div>
  );
}
