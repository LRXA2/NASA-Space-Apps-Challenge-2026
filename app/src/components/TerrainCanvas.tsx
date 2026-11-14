import { useEffect, useId, useRef, useState } from "react";
import type { KeyboardEvent, PointerEvent } from "react";
import type { TerrainChannel } from "../data/types";
import { colorAt, scaleStops } from "./colorScales";
import type { ScaleKind, Scheme } from "./colorScales";
import { useColorScheme } from "./useColorScheme";

export interface TerrainScale {
  kind: ScaleKind;
  min: number;
  max: number;
}

export interface Cell {
  row: number;
  col: number;
}

export function formatValue(value: number, unit: string): string {
  const text = value.toFixed(1).replace("-", "−");
  return unit === "deg" ? `${text}°` : `${text} ${unit}`;
}

/**
 * One terrain channel drawn cell by cell, with a legend, a hover and keyboard readout, and a table view.
 * Row 0 is drawn at the top and column 0 at the left, as stored in the source grid.
 */
export function TerrainCanvas(props: {
  title: string;
  channel: TerrainChannel;
  scale: TerrainScale;
  /** How to read the colours. The ramp direction depends on the colour scheme. */
  scaleNote: (scheme: Scheme) => string;
  /** Pass both to share the selected cell with other grids of the same shape. Otherwise the canvas keeps its own. */
  cell?: Cell | null;
  onCellChange?: (cell: Cell | null) => void;
  /** Extra help, for example that the cursor is linked to other grids. */
  linkNote?: string;
}) {
  const { channel, scale } = props;
  const { rows, cols, values, unit } = channel;
  const scheme = useColorScheme();
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const [ownCell, setOwnCell] = useState<Cell | null>(null);
  const shared = props.onCellChange !== undefined;
  const cell = shared ? (props.cell ?? null) : ownCell;
  const setCell = shared ? props.onCellChange! : setOwnCell;
  // Linked grids all move together; only the focused one announces, so a key press is read out once.
  const [focused, setFocused] = useState(false);
  const titleId = useId();
  const helpId = useId();

  useEffect(() => {
    const context = canvasRef.current?.getContext("2d");
    if (!context) return;
    const image = context.createImageData(cols, rows);
    const span = scale.max - scale.min || 1;
    for (let index = 0; index < values.length; index += 1) {
      const [red, green, blue] = colorAt(scale.kind, scheme, (values[index] - scale.min) / span);
      image.data.set([red, green, blue, 255], index * 4);
    }
    context.putImageData(image, 0, 0);
  }, [values, rows, cols, scale.kind, scale.min, scale.max, scheme]);

  function onPointerMove(event: PointerEvent<HTMLDivElement>) {
    const box = event.currentTarget.getBoundingClientRect();
    const col = Math.floor(((event.clientX - box.left) / box.width) * cols);
    const row = Math.floor(((event.clientY - box.top) / box.height) * rows);
    if (row >= 0 && row < rows && col >= 0 && col < cols) setCell({ row, col });
  }

  function onKeyDown(event: KeyboardEvent<HTMLDivElement>) {
    const moves: Record<string, [number, number]> = {
      ArrowUp: [-1, 0],
      ArrowDown: [1, 0],
      ArrowLeft: [0, -1],
      ArrowRight: [0, 1],
    };
    const move = moves[event.key];
    if (!move) return;
    event.preventDefault();
    setCell(
      cell
        ? {
            row: Math.max(0, Math.min(rows - 1, cell.row + move[0])),
            col: Math.max(0, Math.min(cols - 1, cell.col + move[1])),
          }
        : { row: 0, col: 0 },
    );
  }

  const middle = (scale.min + scale.max) / 2;
  return (
    <figure className="terrain">
      <figcaption id={titleId}>{props.title}</figcaption>
      <div
        className="terrain-plot"
        role="group"
        tabIndex={0}
        aria-labelledby={titleId}
        aria-describedby={helpId}
        onPointerMove={onPointerMove}
        onPointerLeave={() => setCell(null)}
        onKeyDown={onKeyDown}
        onFocus={() => setFocused(true)}
        onBlur={() => setFocused(false)}
      >
        <canvas ref={canvasRef} width={cols} height={rows} />
        {cell && (
          <span
            className="terrain-cursor"
            style={{
              left: `${(cell.col / cols) * 100}%`,
              top: `${(cell.row / rows) * 100}%`,
              width: `${100 / cols}%`,
              height: `${100 / rows}%`,
            }}
          />
        )}
      </div>
      <p className="terrain-readout" aria-live={!shared || focused ? "polite" : "off"}>
        {cell
          ? `Row ${cell.row}, column ${cell.col}: ${formatValue(values[cell.row * cols + cell.col], unit)}`
          : "Point at a cell to read its value."}
      </p>
      <div className="legend">
        <span
          className="legend-bar"
          style={{ background: `linear-gradient(to right, ${scaleStops(scale.kind, scheme).join(", ")})` }}
        />
        <span className="legend-ticks">
          <span>{formatValue(scale.min, unit)}</span>
          <span>{formatValue(middle, unit)}</span>
          <span>{formatValue(scale.max, unit)}</span>
        </span>
      </div>
      <p className="terrain-note" id={helpId}>
        {props.scaleNote(scheme)} Row 0 is at the top and column 0 is at the left, as stored in the source grid. Each cell is
        30 m wide. Use the arrow keys to move between cells.{props.linkNote ? ` ${props.linkNote}` : ""}
      </p>
      <details className="terrain-table">
        <summary>Show all {rows * cols} values as a table</summary>
        <div className="terrain-table-scroll">
          <table>
            <caption>
              {props.title}, in {unit === "deg" ? "degrees" : "metres"}
            </caption>
            <thead>
              <tr>
                <th scope="col">Row</th>
                {Array.from({ length: cols }, (_, col) => (
                  <th key={col} scope="col">
                    {col}
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {Array.from({ length: rows }, (_, row) => (
                <tr key={row}>
                  <th scope="row">{row}</th>
                  {Array.from({ length: cols }, (_, col) => (
                    <td key={col}>{values[row * cols + col].toFixed(1)}</td>
                  ))}
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
    </figure>
  );
}
