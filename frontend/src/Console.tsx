import { useEffect, useState } from "react";
import { api, type ConsoleView } from "./api";

// Ground console (demo): a teammate plays the flight surgeon.
export default function Console() {
  const [data, setData] = useState<ConsoleView | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [text, setText] = useState<Record<string, string>>({});

  useEffect(() => {
    const load = () => api.console().then((d) => { setData(d); setError(null); }).catch((e) => setError(String(e.message ?? e)));
    load();
    const id = setInterval(load, 1000);
    return () => clearInterval(id);
  }, []);

  const send = async (id: string, scripted: boolean) => {
    try {
      await api.reply(id, scripted ? "" : text[id] ?? "", scripted);
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    }
  };

  return (
    <main className="sf4 console">
      <h1>Ground console — flight surgeon (demo)</h1>
      <p className="note">Mission clock T+{Math.round(data?.now ?? 0)} s · Reports arrive after the one-way delay.</p>
      {error && <p className="error" role="alert">{error}</p>}
      {!data?.reports.length && <p>No reports yet.</p>}
      {data?.reports.map((r) => (
        <article key={r.id} className="console-report">
          <h2>{r.id} — {r.crew}</h2>
          {!r.arrived ? (
            <p>In transit. Arrives at T+{Math.round(r.arrives_t)} s.</p>
          ) : (
            <>
              <p>{r.report.summary}</p>
              <details><summary>Full report</summary><pre>{JSON.stringify(r.report, null, 1)}</pre></details>
              {r.replied ? (
                <p className="note">Reply sent.</p>
              ) : (
                <>
                  <textarea
                    aria-label="Reply"
                    value={text[r.id] ?? ""}
                    onChange={(e) => setText({ ...text, [r.id]: e.target.value })}
                  />
                  <button className="big primary" onClick={() => send(r.id, false)}>Send reply</button>
                  <button className="big" onClick={() => send(r.id, true)}>Send scripted fallback reply</button>
                </>
              )}
            </>
          )}
        </article>
      ))}
    </main>
  );
}
