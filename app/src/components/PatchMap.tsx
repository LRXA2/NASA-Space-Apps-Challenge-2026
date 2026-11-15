import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef } from "react";
import type { PatchRecord, RoverClass, WalkingClass } from "../data/types";
import { links } from "../router";
import { classLabel, classTone } from "./StatusBadge";
import type { Tone } from "./StatusBadge";

export type ClassMode = "rover" | "walking";

const PATCH_CELLS = 32;
const CLASS_ORDER: Record<ClassMode, (RoverClass | WalkingClass)[]> = {
  rover: ["operable", "marginal", "non_operable"],
  walking: ["easy", "caution", "unsuitable"],
};

/**
 * Map units are source grid cells. x is the grid column. y is minus the grid row, because
 * Leaflet's y axis points up and grid rows grow downwards. Each patch is 32 by 32 cells.
 */
function patchBounds(patch: PatchRecord): L.LatLngBoundsLiteral {
  return [
    [-(patch.top_row + PATCH_CELLS), patch.top_col],
    [-patch.top_row, patch.top_col + PATCH_CELLS],
  ];
}

function fill(tone: Tone): string {
  return `url(#patch-fill-${tone})`;
}

interface Drawn {
  map: L.Map;
  highlight: L.Rectangle;
  squares: Map<string, { patch: PatchRecord; square: L.Rectangle }>;
}

/**
 * One square per patch on a flat grid (Leaflet CRS.Simple, no basemap). Only patches in the
 * data are drawn, so a missing patch stays an empty gap. Selecting a square opens its patch URL.
 */
export function PatchMap(props: {
  region: { slug: string; name: string };
  patches: PatchRecord[];
  mode: ClassMode;
  active: string | null;
  onActive: (patch: string | null) => void;
}) {
  const { region, patches, mode, active, onActive } = props;
  const host = useRef<HTMLDivElement>(null);
  const drawn = useRef<Drawn | null>(null);

  useEffect(() => {
    if (!host.current || patches.length === 0) return;
    const extent = L.latLngBounds(patchBounds(patches[0]));
    for (const patch of patches) extent.extend(L.latLngBounds(patchBounds(patch)));
    const map = L.map(host.current, {
      crs: L.CRS.Simple,
      attributionControl: false,
      scrollWheelZoom: false,
      zoomSnap: 0.25,
      minZoom: -3,
      maxZoom: 3,
      maxBounds: extent.pad(0.5),
    });
    map.fitBounds(extent, { padding: [8, 8] });
    const squares: Drawn["squares"] = new Map();
    for (const patch of patches) {
      const square = L.rectangle(patchBounds(patch), { className: "patch-square", weight: 1, fillOpacity: 1 });
      square.on("click", () => window.location.assign(links.patch(region.slug, patch.slug)));
      square.on("mouseover", () => onActive(patch.slug));
      square.on("mouseout", () => onActive(null));
      square.addTo(map);
      square.getElement()?.setAttribute("data-patch", patch.slug);
      squares.set(patch.slug, { patch, square });
    }
    const highlight = L.rectangle(extent, { className: "patch-highlight", interactive: false, fill: false, weight: 3 });
    drawn.current = { map, highlight, squares };
    return () => {
      drawn.current = null;
      map.remove();
    };
  }, [patches, region.slug, onActive]);

  useEffect(() => {
    drawn.current?.squares.forEach(({ patch, square }) => {
      square.setStyle({ fillColor: fill(classTone(patch[mode].class)) });
    });
  }, [patches, mode]);

  useEffect(() => {
    const current = drawn.current;
    const target = active ? current?.squares.get(active) : undefined;
    if (!current || !target) return;
    current.highlight.setBounds(patchBounds(target.patch)).addTo(current.map);
    return () => {
      current.highlight.remove();
    };
  }, [patches, active]);

  const modeName = mode === "rover" ? "rover" : "crew-on-foot";
  return (
    <>
      <svg className="patch-fills" width="0" height="0" aria-hidden="true" focusable="false">
        <defs>
          {/* The three class fills from the design: solid, 135° stripes, 45° stripes. */}
          <pattern id="patch-fill-good" width="6" height="6" patternUnits="userSpaceOnUse">
            <rect width="6" height="6" fill="#3fb8a0" />
          </pattern>
          <pattern
            id="patch-fill-warning"
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(135)"
          >
            <rect width="6" height="6" fill="#7a5f1c" />
            <rect width="3" height="6" fill="#e2bc5c" />
          </pattern>
          <pattern
            id="patch-fill-critical"
            width="6"
            height="6"
            patternUnits="userSpaceOnUse"
            patternTransform="rotate(45)"
          >
            <rect width="6" height="6" fill="#9e4636" />
            <rect width="4" height="6" fill="#e48069" />
          </pattern>
        </defs>
      </svg>
      <div
        ref={host}
        className="patch-map"
        role="group"
        aria-label={`Patch map of ${region.name}, coloured by ${modeName} class. The table below lists the same patches.`}
      />
      <ul className="map-legend" aria-label={`Map key: ${modeName} class`}>
        {CLASS_ORDER[mode].map((value) => (
          <li key={value}>
            <svg className="map-swatch" width="18" height="18" aria-hidden="true">
              <rect width="18" height="18" fill={fill(classTone(value))} />
            </svg>
            {classLabel(value)}
            <span className="muted">{patches.filter((patch) => patch[mode].class === value).length} patches</span>
          </li>
        ))}
      </ul>
    </>
  );
}
