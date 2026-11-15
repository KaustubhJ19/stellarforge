import { useEffect, useState } from "react";
import { api } from "./api";
import Tablet from "./Tablet";
import Console from "./Console";

// One browser window per tablet: ?crew=<id>. The ground console is ?view=console.
export default function App() {
  const params = new URLSearchParams(window.location.search);
  const crew = params.get("crew");
  if (params.get("view") === "console") return <Console />;
  if (crew) return <Tablet crew={crew} />;
  return <Picker />;
}

function Picker() {
  const [crew, setCrew] = useState<{ crew: string[]; names: Record<string, string>; stub: boolean } | null>(null);
  useEffect(() => {
    api.crew().then(setCrew).catch(() => setCrew(null));
  }, []);
  return (
    <main className="picker">
      <h1>StellarForge — choose a tablet</h1>
      {crew?.stub && <p className="stub-banner">STUB protocol and profile: non-clinical test data</p>}
      <ul>
        {crew?.crew.map((c) => (
          <li key={c}>
            <a className="big-link" href={`/emergency.html?crew=${c}`}>{crew.names[c] ?? c}</a>
          </li>
        ))}
        <li>
          <a className="big-link" href="/emergency.html?view=console">Ground console</a>
        </li>
      </ul>
    </main>
  );
}
