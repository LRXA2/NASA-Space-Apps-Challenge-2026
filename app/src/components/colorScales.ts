// Colour ramps for terrain grids.
// Sequential (magnitude): one hue. The low end recedes toward the page surface.
// Diverging (above or below a midpoint): two hues with a neutral grey midpoint.
// Placeholder palette. Replace the stops when the design tokens arrive.

export type ScaleKind = "sequential" | "diverging";
export type Scheme = "light" | "dark";
type Rgb = [number, number, number];

const SEQUENTIAL = ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"];
const STOPS: Record<ScaleKind, Record<Scheme, string[]>> = {
  sequential: { light: SEQUENTIAL, dark: [...SEQUENTIAL].reverse() },
  diverging: {
    light: ["#104281", "#2a78d6", "#f0efec", "#e34948", "#8a1f1f"],
    dark: ["#cde2fb", "#3987e5", "#383835", "#e66767", "#fbd3d3"],
  },
};

function parse(hex: string): Rgb {
  return [1, 3, 5].map((start) => parseInt(hex.slice(start, start + 2), 16)) as Rgb;
}

export function scaleStops(kind: ScaleKind, scheme: Scheme): string[] {
  return STOPS[kind][scheme];
}

/** Map a position from 0 (domain minimum) to 1 (domain maximum) to a colour. */
export function colorAt(kind: ScaleKind, scheme: Scheme, position: number): Rgb {
  const stops = STOPS[kind][scheme].map(parse);
  const scaled = Math.max(0, Math.min(1, position)) * (stops.length - 1);
  const lower = Math.min(Math.floor(scaled), stops.length - 2);
  const mix = scaled - lower;
  return stops[lower].map((channel, index) => Math.round(channel + (stops[lower + 1][index] - channel) * mix)) as Rgb;
}

/** Round up to 1, 2 or 5 times a power of ten, so legend ends are easy to read. */
export function niceCeiling(value: number): number {
  if (!(value > 0)) return 1;
  const power = 10 ** Math.floor(Math.log10(value));
  const step = [1, 2, 5, 10].find((multiple) => multiple * power >= value - 1e-9) ?? 10;
  return step * power;
}
