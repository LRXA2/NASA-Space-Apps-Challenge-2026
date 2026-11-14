import L from "leaflet";
import "leaflet/dist/leaflet.css";
import { useEffect, useRef, useState } from "react";

export interface EarthMarker {
  key: string;
  label: string;
  latitude: number;
  longitude: number;
  title: string;
  href: string;
}

const TILES = "https://tile.openstreetmap.org/{z}/{x}/{y}.png";
const ATTRIBUTION = '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors';

/**
 * Earth match locations on a normal lat/lon basemap. Markers are numbered divs (no image assets).
 * If the basemap fails, the markers still work and the page says so. The result table is the list fallback.
 */
export function EarthMap(props: {
  markers: EarthMarker[];
  active: string | null;
  onActive: (key: string | null) => void;
  label: string;
}) {
  const { markers, active, onActive, label } = props;
  const host = useRef<HTMLDivElement>(null);
  const placed = useRef<Map<string, L.Marker>>(new Map());
  const [tilesFailed, setTilesFailed] = useState(false);

  useEffect(() => {
    if (!host.current || markers.length === 0) return;
    const map = L.map(host.current, { scrollWheelZoom: false, worldCopyJump: true });
    const tiles = L.tileLayer(TILES, { attribution: ATTRIBUTION, maxZoom: 17 });
    let failures = 0;
    tiles.on("tileerror", () => {
      failures += 1;
      if (failures >= 4) setTilesFailed(true);
    });
    tiles.addTo(map);
    const bounds = L.latLngBounds(markers.map((marker) => [marker.latitude, marker.longitude]));
    map.fitBounds(bounds.pad(0.2), { maxZoom: 9 });
    const added = new Map<string, L.Marker>();
    for (const marker of markers) {
      const icon = L.divIcon({ className: "earth-marker", html: `<span>${marker.label}</span>`, iconSize: [28, 28] });
      const pin = L.marker([marker.latitude, marker.longitude], { icon, title: marker.title, keyboard: true });
      pin.on("click", () => window.location.assign(marker.href));
      pin.on("mouseover", () => onActive(marker.key));
      pin.on("mouseout", () => onActive(null));
      pin.addTo(map);
      const element = pin.getElement();
      element?.addEventListener("focus", () => onActive(marker.key));
      element?.addEventListener("blur", () => onActive(null));
      added.set(marker.key, pin);
    }
    placed.current = added;
    return () => {
      placed.current = new Map();
      map.remove();
    };
  }, [markers, onActive]);

  useEffect(() => {
    placed.current.forEach((pin, key) => {
      pin.getElement()?.classList.toggle("is-active", key === active);
      pin.setZIndexOffset(key === active ? 1000 : 0);
    });
  }, [active, markers]);

  return (
    <>
      <div ref={host} className="earth-map" role="group" aria-label={label} />
      {tilesFailed && (
        <p className="inline-error" role="status">
          The basemap could not load. The numbered markers still show each match, and the table lists the same places.
        </p>
      )}
    </>
  );
}
