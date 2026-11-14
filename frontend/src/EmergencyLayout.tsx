import type { ReactNode } from "react";

export const DISCLAIMER = "Decision support, not diagnosis.";

// Every emergency screen renders through this layout, so the disclaimer is never forgotten.
export function EmergencyLayout({ title, patient, offline, children }: {
  title: string;
  patient?: string;
  offline?: boolean;
  children: ReactNode;
}) {
  return (
    <main className="emergency" data-testid="emergency-screen">
      <header>
        <span className="tag">EMERGENCY</span>
        {patient && <span className="patient">Patient: {patient}</span>}
      </header>
      {offline && <p className="offline" role="status">Service unavailable — continuing offline</p>}
      <h1>{title}</h1>
      <section className="body">{children}</section>
      <footer className="disclaimer" data-testid="disclaimer">{DISCLAIMER}</footer>
    </main>
  );
}
