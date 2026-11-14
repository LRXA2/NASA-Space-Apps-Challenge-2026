import { useId } from "react";
import type { TerrainChannel } from "../data/types";
import { formatValue } from "./TerrainCanvas";

// Drawn as plain SVG. Two step lines do not justify a chart library in the bundle.
const WIDTH = 360;
const HEIGHT = 230;
const PLOT = { left: 46, right: 326, top: 10, bottom: 184 };
const SHARES = [0, 0.25, 0.5, 0.75, 1];
const QUANTILES: [string, number][] = [
  ["Minimum", 0],
  ["10%", 0.1],
  ["25%", 0.25],
  ["Median", 0.5],
  ["75%", 0.75],
  ["90%", 0.9],
  ["Maximum", 1],
];

/** The smallest value that at least this share of cells are at or below. */
export function quantile(sorted: Float32Array, share: number): number {
  return sorted[Math.max(0, Math.ceil(share * sorted.length) - 1)];
}

function stepPath(sorted: Float32Array, x: (value: number) => number, y: (share: number) => number): string {
  const count = sorted.length;
  let path = `M${x(sorted[0]).toFixed(1)},${y(0).toFixed(1)}`;
  for (let index = 0; index < count; index += 1) {
    // Draw one riser per distinct value. Equal values share it.
    if (index + 1 < count && sorted[index + 1] === sorted[index]) continue;
    path += `H${x(sorted[index]).toFixed(1)}V${y((index + 1) / count).toFixed(1)}`;
  }
  return path;
}

/**
 * Cumulative distribution of one measurement for the Moon patch and the Earth patch, on one shared axis.
 * Each line reads: this share of the patch's cells are at or below this value.
 */
export function DistributionChart(props: {
  /** The measurement, such as "Slope". */
  measurement: string;
  moon: TerrainChannel;
  earth: TerrainChannel;
  /** The value axis. Pass the same domain the grids use, so the chart and the grids agree. */
  min: number;
  max: number;
}) {
  const { measurement, min, max } = props;
  const unit = props.moon.unit;
  const titleId = useId();
  const moon = Float32Array.from(props.moon.values).sort();
  const earth = Float32Array.from(props.earth.values).sort();
  const x = (value: number) => PLOT.left + ((value - min) / (max - min || 1)) * (PLOT.right - PLOT.left);
  const y = (share: number) => PLOT.bottom - share * (PLOT.bottom - PLOT.top);
  const ticks = SHARES.map((position) => min + position * (max - min));
  const unitName = unit === "deg" ? "degrees" : "metres";
  const number = (value: number) => value.toFixed(1).replace("-", "−");

  return (
    <figure className="distribution">
      <figcaption id={titleId}>{measurement} · cumulative distribution</figcaption>
      <svg viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby={titleId}>
        {SHARES.map((share) => (
          <g key={share}>
            <line className="distribution-grid" x1={PLOT.left} x2={PLOT.right} y1={y(share)} y2={y(share)} />
            <text className="distribution-tick" x={PLOT.left - 6} y={y(share) + 4} textAnchor="end">
              {share * 100}%
            </text>
          </g>
        ))}
        {ticks.map((tick) => (
          <text key={tick} className="distribution-tick" x={x(tick)} y={PLOT.bottom + 16} textAnchor="middle">
            {formatValue(tick, unit)}
          </text>
        ))}
        <line className="distribution-axis" x1={PLOT.left} x2={PLOT.right} y1={PLOT.bottom} y2={PLOT.bottom} />
        <text className="distribution-tick" x={(PLOT.left + PLOT.right) / 2} y={HEIGHT - 6} textAnchor="middle">
          {measurement} ({unitName})
        </text>
        <path className="distribution-line is-moon" d={stepPath(moon, x, y)} />
        <path className="distribution-line is-earth" d={stepPath(earth, x, y)} />
      </svg>
      <p className="distribution-key">
        <span className="distribution-swatch is-moon" /> Moon (solid) <span className="distribution-swatch is-earth" />{" "}
        Earth (dashed)
      </p>
      <p className="terrain-note">
        Share of cells at or below each value: {moon.length} Moon cells and {earth.length} Earth cells, from the grids
        above. A line further left means lower values.
      </p>
      <table className="distribution-table">
        <caption>
          {measurement} at each share of cells, in {unitName}
        </caption>
        <thead>
          <tr>
            <th scope="col">Share of cells</th>
            <th scope="col" className="number">
              Moon
            </th>
            <th scope="col" className="number">
              Earth
            </th>
          </tr>
        </thead>
        <tbody>
          {QUANTILES.map(([label, share]) => (
            <tr key={label}>
              <th scope="row">{label}</th>
              <td className="number">{number(quantile(moon, share))}</td>
              <td className="number">{number(quantile(earth, share))}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </figure>
  );
}
