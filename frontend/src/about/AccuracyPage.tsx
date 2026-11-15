import { FormDialog } from "../forms/FormDialog";
import accuracy from "../../../content/accuracy.json";

/** "How accurate is this?": measured results and the honest limits, from content/accuracy.json. */
export function AccuracyPage({ onClose }: { onClose: () => void }) {
  return (
    <FormDialog title={accuracy.title} onClose={onClose} wide>
      <p>{accuracy.intro}</p>
      <table className="about-table">
        <thead>
          <tr>
            <th scope="col">What</th>
            <th scope="col">Result</th>
            <th scope="col">Measured on</th>
            <th scope="col">How to re-run</th>
          </tr>
        </thead>
        <tbody>
          {accuracy.results.map((row) => (
            <tr key={row.what}>
              <th scope="row">{row.what}</th>
              <td>{row.result}</td>
              <td>{row.measured_on}</td>
              <td>
                <code>{row.rerun}</code>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
      <p>{accuracy.labels}</p>
      <h3>Honest limits</h3>
      <ul className="about-list">
        {accuracy.limits.map((limit) => (
          <li key={limit}>{limit}</li>
        ))}
      </ul>
    </FormDialog>
  );
}
