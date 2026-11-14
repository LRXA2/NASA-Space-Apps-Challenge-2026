import { useId } from "react";
import type { RegionEntry } from "../data/types";
import { links } from "../router";

// The export's CRS: +proj=stere +lat_0=-90 +lat_ts=-90 +lon_0=0 +R=1737400. +y points to 0° longitude, +x to 90°E.
const MOON_RADIUS_KM = 1737.4;
// The drawing is scaled so the outermost ring has this radius in SVG units, whatever its latitude.
const OUTER = 250;
const HALF = 290;
const NODE = 14;

/** Distance from the pole, in km, of a south latitude given as a positive number of degrees. */
function ringRadius(latitudeSouth: number): number {
  return 2 * MOON_RADIUS_KM * Math.tan(((90 - latitudeSouth) * Math.PI) / 180 / 2);
}

type Placed = RegionEntry & { extent_m: NonNullable<RegionEntry["extent_m"]>; number: number };

/**
 * All exported regions on one south-polar map. Each region is a numbered node over a dashed square that shows the
 * true extent of its tiles. Numbers match the region cards on the same page.
 */
export function PolarOverview(props: {
  regions: RegionEntry[];
  /** Slug of the region to mark as selected. */
  selected?: string | null;
  /** Slugs of regions whose Operations assessment is Fail. */
  failed?: ReadonlySet<string>;
}) {
  const { regions, selected = null, failed = new Set<string>() } = props;
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
  const scale = OUTER / ringRadius(rings[rings.length - 1]);
  const r = (latitude: number) => ringRadius(latitude) * scale;
  const outerLatitude = rings[rings.length - 1];

  return (
    <figure className="polar-overview">
      <div className="polar-well">
        <svg
          viewBox={`${-HALF} ${-HALF} ${2 * HALF} ${2 * HALF}`}
          role="group"
          aria-labelledby={titleId}
          aria-describedby={noteId}
        >
          <title id={titleId}>Where the {placed.length} regions are around the lunar south pole</title>
          <g className="polar-grid" aria-hidden="true">
            {rings.slice(0, -1).map((latitude) => (
              <circle key={latitude} className="polar-ring" r={r(latitude)} />
            ))}
            <circle className="polar-outer" r={OUTER} />
            <path className="polar-spoke" d={`M0 ${-OUTER}V${OUTER}M${-OUTER} 0H${OUTER}`} />
            <path className="polar-earth-tick" d={`M0 ${-OUTER}l-5 -9h10z`} />
          </g>
          <g className="polar-labels" aria-hidden="true">
            <text className="polar-earth" x={0} y={-OUTER - 14} textAnchor="middle">
              0° · toward Earth
            </text>
            <text x={0} y={OUTER + 32} textAnchor="middle">
              180°
            </text>
            <text x={OUTER + 8} y={5}>
              90°E
            </text>
            <text x={-OUTER - 8} y={5} textAnchor="end">
              90°W
            </text>
            {rings.map((latitude) => {
              const radius = latitude === outerLatitude ? OUTER : r(latitude);
              const offset = radius * Math.SQRT1_2;
              return (
                <text key={latitude} x={offset + 4} y={offset + 4}>
                  {latitude}°S
                </text>
              );
            })}
            <circle className="polar-pole" r={3.5} />
            <text className="polar-pole-label" x={8} y={-8}>
              POLE
            </text>
          </g>
          {placed.map((region) => {
            const e = region.extent_m;
            const x = km(e.xmin) * scale;
            const y = -km(e.ymax) * scale;
            const width = km(e.xmax - e.xmin) * scale;
            const height = km(e.ymax - e.ymin) * scale;
            const cx = x + width / 2;
            const cy = y + height / 2;
            const isSelected = region.slug === selected;
            const isFail = failed.has(region.slug);
            // Starts with the visible number as its own word, so voice control can use it.
            const label = `${region.number} ${region.name}: ${region.exported_patch_count} terrain patches${isFail ? ", Operations Fail" : ""}`;
            return (
              <a
                key={region.slug}
                href={links.region(region.slug)}
                className={`polar-region${isSelected ? " is-selected" : ""}${isFail ? " is-fail" : ""}`}
                aria-current={isSelected ? "true" : undefined}
              >
                <title>{label}</title>
                <rect className="polar-extent" x={x} y={y} width={width} height={height} rx={2} />
                <circle className="polar-glow" cx={cx} cy={cy} r={NODE + 12} />
                <circle className="polar-focus" cx={cx} cy={cy} r={NODE + 6} />
                <circle className="polar-node" cx={cx} cy={cy} r={NODE} />
                <text className="polar-number" x={cx} y={cy + 5}>
                  {region.number}
                </text>
              </a>
            );
          })}
        </svg>
        <ul className="polar-legend" aria-label="Map key">
          <li>
            <i className="key-node" aria-hidden="true" />1 node = 1 region
          </li>
          <li>
            <i className="key-extent" aria-hidden="true" />
            Area covered
          </li>
          <li>
            <i className="key-fail" aria-hidden="true" />
            Operations Fail
          </li>
          {selected && (
            <li>
              <i className="key-selected" aria-hidden="true" />
              Selected
            </li>
          )}
        </ul>
      </div>
      <figcaption id={noteId}>
        South polar view with 0° longitude, toward Earth, at the top. Rings mark each degree of latitude, about 30 km
        apart. Node numbers match the region cards.
      </figcaption>
    </figure>
  );
}
