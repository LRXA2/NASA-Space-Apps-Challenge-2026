// Colour ramps for terrain grids (design/exploration-theme/DESIGN.md). Moon and Earth use the same ramps.
// Slope: matplotlib magma, brighter is steeper. Relative elevation: navy to white, lighter is higher.
// The domain is fitted to the patch (or shared by a Moon–Earth pair); these stops only set the colours.

export type ScaleKind = "slope" | "elevation";
type Rgb = [number, number, number];
type Stop = { at: number; color: string };

const STOPS: Record<ScaleKind, Stop[]> = {
  slope: [
    { at: 0, color: "#000004" },
    { at: 0.2, color: "#3b0f70" },
    { at: 0.4, color: "#8c2981" },
    { at: 0.6, color: "#de4968" },
    { at: 0.8, color: "#fe9f6d" },
    { at: 1, color: "#fcfdbf" },
  ],
  // −100, −40, 0, +40, +100 m on the reference scale, as positions in a symmetric domain.
  elevation: [
    { at: 0, color: "#070a14" },
    { at: 0.3, color: "#23305a" },
    { at: 0.5, color: "#56648f" },
    { at: 0.7, color: "#a7b3d3" },
    { at: 1, color: "#f2f4fa" },
  ],
};

const PARSED: Record<ScaleKind, { at: number; rgb: Rgb }[]> = {
  slope: STOPS.slope.map(({ at, color }) => ({ at, rgb: parse(color) })),
  elevation: STOPS.elevation.map(({ at, color }) => ({ at, rgb: parse(color) })),
};

function parse(hex: string): Rgb {
  return [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16)) as Rgb;
}

/** A CSS gradient for the legend bar, with the same stop positions as the canvas. */
export function legendGradient(kind: ScaleKind): string {
  return `linear-gradient(to right, ${STOPS[kind].map(({ at, color }) => `${color} ${at * 100}%`).join(", ")})`;
}

/** Map a position from 0 (domain minimum) to 1 (domain maximum) to a colour. */
export function colorAt(kind: ScaleKind, position: number): Rgb {
  const stops = PARSED[kind];
  const t = Math.max(0, Math.min(1, Number.isFinite(position) ? position : 0));
  let upper = stops.findIndex((stop) => stop.at >= t);
  if (upper <= 0) upper = 1;
  const low = stops[upper - 1];
  const high = stops[upper];
  const mix = (t - low.at) / (high.at - low.at || 1);
  return low.rgb.map((channel, index) => Math.round(channel + (high.rgb[index] - channel) * mix)) as Rgb;
}

/** Round up to 1, 2 or 5 times a power of ten, so legend ends are easy to read. */
export function niceCeiling(value: number): number {
  if (!(value > 0)) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((multiple) => multiple * power >= value - 1e-9) ?? 10;
  return step * power;
}
