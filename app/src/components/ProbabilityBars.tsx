/** Model probabilities as labelled bars. The predicted class is marked in text, not only by weight. */
export function ProbabilityBars(props: {
  caption: string;
  rows: { key: string; label: string; probability: number }[];
  predicted: string;
}) {
  return (
    <table className="probabilities">
      <caption>{props.caption}</caption>
      <tbody>
        {props.rows.map((row) => {
          const isPredicted = row.key === props.predicted;
          return (
            <tr key={row.key} className={isPredicted ? "is-predicted" : undefined}>
              <th scope="row">
                {row.label}
                {isPredicted && <span className="predicted-tag"> (predicted)</span>}
              </th>
              <td className="bar-cell" aria-hidden="true">
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${Math.max(0, Math.min(1, row.probability)) * 100}%` }} />
                </span>
              </td>
              <td className="number">{row.probability.toFixed(2)}</td>
            </tr>
          );
        })}
      </tbody>
    </table>
  );
}
