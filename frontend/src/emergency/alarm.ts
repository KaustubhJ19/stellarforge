// Audible crew alarm (ticket 06: "audible and visual").
// Generated with Web Audio, so it needs no sound file and works offline.
// Browsers block audio until the page has had a user gesture; any tap on the tablet
// unlocks it, and the alarm screen shows when sound is still blocked.
import { useEffect, useState } from "react";

export type AlarmSound = "off" | "playing" | "blocked" | "unsupported";

const BEEP_MS = 400;
const GAP_MS = 250;
const FREQ_HZ = 880;

let ctx: AudioContext | null = null;

function audio(): AudioContext | null {
  if (ctx) return ctx;
  const AC = window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext;
  if (!AC) return null;
  ctx = new AC();
  return ctx;
}

// Any user gesture on the tablet unlocks audio for later alarms.
export function unlockAudioOnGesture() {
  const unlock = () => {
    const c = audio();
    if (c && c.state === "suspended") c.resume().catch(() => undefined);
  };
  window.addEventListener("pointerdown", unlock, { capture: true });
  window.addEventListener("keydown", unlock, { capture: true });
}

export function useAlarmSound(active: boolean): AlarmSound {
  const [state, setState] = useState<AlarmSound>("off");

  useEffect(() => {
    if (!active) {
      setState("off");
      return;
    }
    const c = audio();
    if (!c) {
      setState("unsupported");
      return;
    }
    let stopped = false;
    let timer: ReturnType<typeof setTimeout> | undefined;

    const beep = () => {
      if (stopped) return;
      if (c.state !== "running") {
        setState("blocked");
        c.resume().catch(() => undefined);
      } else {
        setState("playing");
        const osc = c.createOscillator();
        const gain = c.createGain();
        osc.type = "square";
        osc.frequency.value = FREQ_HZ;
        gain.gain.value = 0.2;
        osc.connect(gain).connect(c.destination);
        osc.start();
        osc.stop(c.currentTime + BEEP_MS / 1000);
      }
      navigator.vibrate?.(BEEP_MS);
      timer = setTimeout(beep, BEEP_MS + GAP_MS);
    };
    beep();
    return () => {
      stopped = true;
      if (timer) clearTimeout(timer);
      navigator.vibrate?.(0);
    };
  }, [active]);

  return state;
}
