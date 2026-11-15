import { useEffect, useState } from "react";
import { api } from "./api";
import Tablet from "./Tablet";
import Console from "./Console";

// One browser window per tablet: ?crew=<id>. The ground console is /console.
export const DEFAULT_TABLET = "A"; // the crew of Spec 2's bundled replay

// Routes: /console = ground console; /tablets = tablet picker; anything else is a crew tablet
// (?crew=<id>, default A). Spec 2's ?replay=<path> still picks the home screen's replay.
export default function Shell() {
  const params = new URLSearchParams(window.location.search);
  const path = window.location.pathname;
  if (path.startsWith("/console")) return <Console />;
  if (path.startsWith("/tablets")) return <Picker />;
  return <Tablet crew={params.get("crew") ?? DEFAULT_TABLET} />;
}

function Picker() {
  const [crew, setCrew] = useState<{ crew: string[]; names: Record<string, string>; stub: boolean } | null>(null);
  useEffect(() => {
    api.crew().then(setCrew).catch(() => setCrew(null));
  }, []);
  return (
    <main className="sf4 picker">
      <h1>StellarForge — choose a tablet</h1>
      <p className="note">Each tablet shows the crew home (Spec 2) and the emergency flow (Spec 4).</p>
      {crew?.stub && <p className="stub-banner">STUB protocol and profile: non-clinical test data</p>}
      <ul>
        {crew?.crew.map((c) => (
          <li key={c}>
            <a className="big-link" href={`/?crew=${c}`}>{crew.names[c] ?? c}</a>
          </li>
        ))}
        <li>
          <a className="big-link" href="/console">Ground console</a>
        </li>
      </ul>
    </main>
  );
}
