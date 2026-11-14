import type { CrossingAxis, PatchRecord } from "../data/types";

// Each axis runs between two edges of the stored grid. Row 0 is the top row.
const AXES: { key: CrossingAxis; short: string; edges: string; line: [number, number, number, number] }[] = [
  { key: "north_south", short: "N–S", edges: "top edge to bottom edge", line: [60, 8, 60, 112] },
  { key: "east_west", short: "E–W", edges: "left edge to right edge", line: [8, 60, 112, 60] },
  { key: "northwest_southeast", short: "NW–SE", edges: "top-left corner to bottom-right corner", line: [20, 20, 100, 100] },
  { key: "northeast_southwest", short: "NE–SW", edges: "top-right corner to bottom-left corner", line: [100, 20, 20, 100] },
];

/** The four undirected crossing predictions, as a diagram and as a table. */
export function CrossingAxes({ crossing }: { crossing: PatchRecord["crossing"] }) {
  return (
    <div className="crossing">
      <svg className="crossing-diagram" viewBox="0 0 120 120" width="120" height="120" aria-hidden="true">
        <rect className="crossing-frame" x="8" y="8" width="104" height="104" />
        {AXES.map((axis) => (
          <line
            key={axis.key}
            className={crossing[axis.key].predicted ? "axis-yes" : "axis-no"}
            x1={axis.line[0]}
            y1={axis.line[1]}
            x2={axis.line[2]}
            y2={axis.line[3]}
          />
        ))}
      </svg>
      <table className="crossing-table">
        <caption>Solid line: predicted crossable. Dashed line: predicted not crossable.</caption>
        <thead>
          <tr>
            <th scope="col">Axis</th>
            <th scope="col">Prediction</th>
            <th scope="col" className="number">
              Probability
            </th>
          </tr>
        </thead>
        <tbody>
          {AXES.map((axis) => (
            <tr key={axis.key}>
              <th scope="row">
                {axis.short}
                <span className="axis-edges">{axis.edges}</span>
              </th>
              <td>{crossing[axis.key].predicted ? "Crossable" : "Not crossable"}</td>
              <td className="number">{crossing[axis.key].probability.toFixed(2)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
