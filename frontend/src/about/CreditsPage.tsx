import { FormDialog } from "../forms/FormDialog";
import credits from "../../../content/credits.json";

/** Every dataset, model and asset with its licence and source, from content/credits.json. */
export function CreditsPage({ onClose }: { onClose: () => void }) {
  return (
    <FormDialog title="Credits" onClose={onClose}>
      <p>Every dataset, model and asset StellarForge uses, with its source and licence (checked {credits.checked}).</p>
      <ul className="about-list about-list--credits">
        {credits.entries.map((entry) => (
          <li key={entry.name}>
            <h3>{entry.name}</h3>
            <p>
              {entry.kind}, licence{" "}
              {entry.licence_url ? (
                <a href={entry.licence_url} target="_blank" rel="noreferrer">
                  {entry.licence}
                </a>
              ) : (
                entry.licence
              )}
            </p>
            <p>{entry.used_for}</p>
            {"citation" in entry && entry.citation && <p>{entry.citation}</p>}
            <p>
              <a href={entry.link} target="_blank" rel="noreferrer">
                Source: {entry.name}
              </a>
            </p>
          </li>
        ))}
      </ul>
    </FormDialog>
  );
}
