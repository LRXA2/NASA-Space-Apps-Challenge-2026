import { useId } from "react";
import type { RegionEntry } from "../data/types";
import { links } from "../router";

// The export's CRS: +proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400. +y points to 0° longitude, +x to 90°E.
const MOON_RADIUS_KM = 1737.4;

/** Distance from the pole, in km, of a south latitude given as a positive number of degrees. */
function ringRadius(latitudeSouth: number): number {
  return 2 * MOON_RADIUS_KM * Math.tan(((90 - latitudeSouth) * Math.PI) / 180 / 2);
}

const SPOKES = [
  { lon: 0, label: "0°" },
  { lon: 90, label: "90°E" },
  { lon: 180, label: "180°" },
  { lon: 270, label: "90°W" },
];

type Placed = RegionEntry & { extent_m: NonNullable<RegionEntry["extent_m"]>; number: number };

/**
 * All exported regions on one south-polar map, each drawn at the true extent of its tiles.
 * Numbers match the region list on the same page.
 */
export function PolarOverview({ regions }: { regions: RegionEntry[] }) {
  const titleId = useId();
  const noteId = useId();
  // Numbered by position in the full list, so the numbers still match it if a region has no extent.
  const placed = regions
    .map((region, index) => ({ ...region, number: index + 1 }))
    .filter((region): region is Placed => region.extent_m != null);
  if (placed.length === 0) return null;

  const km = (metres: number) => metres / 1000;
  const farthest = Math.max(
    ...placed.flatMap(({ extent_m: e }) =>
      [e.xmin, e.xmax].flatMap((x) => [e.ymin, e.ymax].map((y) => Math.hypot(km(x), km(y)))),
    ),
  );
  // Rings every degree from 89°S outwards, up to the first one that encloses every region.
  const rings: number[] = [];
  for (let latitude = 89; latitude >= 80; latitude -= 1) {
    rings.push(latitude);
    if (ringRadius(latitude) >= farthest) break;
  }
  const outer = ringRadius(rings[rings.length - 1]);
  const half = outer + 32; // Room for the longitude labels at phone-size text.
  const labelAngle = (135 * Math.PI) / 180; // Ring labels run down and to the right, where no region sits.

  return (
    <figure className="polar-overview">
      <svg
        viewBox={`${-half} ${-half} ${2 * half} ${2 * half}`}
        role="group"
        aria-labelledby={titleId}
        aria-describedby={noteId}
      >
        <title id={titleId}>Where the {placed.length} regions are around the lunar south pole</title>
        <g className="polar-grid" aria-hidden="true">
          {rings.map((latitude) => (
            <circle key={latitude} cx={0} cy={0} r={ringRadius(latitude)} />
          ))}
          {SPOKES.map(({ lon }) => {
            const angle = (lon * Math.PI) / 180;
            return <line key={lon} x1={0} y1={0} x2={outer * Math.sin(angle)} y2={-outer * Math.cos(angle)} />;
          })}
        </g>
        <g className="polar-labels" aria-hidden="true">
          {rings.map((latitude) => {
            const r = ringRadius(latitude);
            return (
              <text key={latitude} x={r * Math.sin(labelAngle) + 2} y={-r * Math.cos(labelAngle) - 2}>
                {latitude}°S
              </text>
            );
          })}
          {SPOKES.map(({ lon, label }) => {
            const angle = (lon * Math.PI) / 180;
            const r = outer + 11;
            return (
              <text
                key={lon}
                x={r * Math.sin(angle)}
                y={-r * Math.cos(angle)}
                textAnchor="middle"
                dominantBaseline="middle"
              >
                {label}
              </text>
            );
          })}
          <circle className="polar-pole" cx={0} cy={0} r={1.8} />
          <text x={4} y={-4}>
            Pole
          </text>
        </g>
        {placed.map((region) => {
          const e = region.extent_m;
          const x = km(e.xmin);
          const y = -km(e.ymax);
          const width = km(e.xmax - e.xmin);
          const height = km(e.ymax - e.ymin);
          return (
            <a key={region.slug} href={links.region(region.slug)} className="polar-region">
              <title>
                {region.number}. {region.name}: {region.exported_patch_count} terrain patches
              </title>
              <rect x={x} y={y} width={width} height={height} />
              <text x={x + width / 2} y={y + height / 2} textAnchor="middle" dominantBaseline="central">
                {region.number}
              </text>
            </a>
          );
        })}
      </svg>
      <figcaption id={noteId}>
        South polar stereographic view centred on the pole, with 0° longitude at the top. Rings mark each degree of
        latitude (about 30 km apart). Each numbered box is the area covered by one region's terrain patches, and the
        numbers match the list.
      </figcaption>
    </figure>
  );
}
