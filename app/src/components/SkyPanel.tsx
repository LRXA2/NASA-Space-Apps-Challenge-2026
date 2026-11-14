import { useId } from "react";
import { loadSky } from "../data/loaders";
import type { SkyDocument } from "../data/types";
import { useData } from "../data/useData";

// A 640 × 330 panorama looking toward Earth (azimuth 0 at the centre). 3.3 units per degree.
const WIDTH = 640;
const HEIGHT = 330;
const HORIZON = 282;
const PER_DEGREE = 3.3;
const MAX_MAGNITUDE = 5;
const LABELLED = ["Canopus", "Sirius"];

const x = (azimuth: number) => WIDTH / 2 + azimuth * PER_DEGREE;
const y = (altitude: number) => HORIZON - altitude * PER_DEGREE;

/** Star colour from its B−V index: blue-white, white or warm. */
function starColor(bv: number | null): string {
  if (bv === null) return "#F4F2EA";
  if (bv < 0.2) return "#CFDDFF";
  if (bv > 1.1) return "#FFE3BE";
  return "#F4F2EA";
}

function formatDate(date: string): string {
  const parsed = new Date(date.slice(0, 10));
  if (Number.isNaN(parsed.getTime())) return date;
  return parsed.toLocaleDateString("en-GB", { day: "numeric", month: "short", year: "numeric", timeZone: "UTC" });
}

function Sky({ sky, titleId }: { sky: SkyDocument; titleId: string }) {
  const stars = sky.stars.filter(([azimuth, altitude, magnitude]) => {
    const px = x(azimuth);
    const py = y(altitude);
    return magnitude <= MAX_MAGNITUDE && px >= 0 && px <= WIDTH && py >= 0 && py <= HORIZON;
  });
  return (
    <svg className="sky" viewBox={`0 0 ${WIDTH} ${HEIGHT}`} role="img" aria-labelledby={titleId}>
      <defs>
        <radialGradient id="sky-earth-glow">
          <stop offset="0" stopColor="#F4AE5B" stopOpacity=".55" />
          <stop offset="1" stopColor="#F4AE5B" stopOpacity="0" />
        </radialGradient>
        <linearGradient id="sky-fill" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0" stopColor="#05071E" />
          <stop offset="1" stopColor="#141850" />
        </linearGradient>
      </defs>
      <rect width={WIDTH} height={HEIGHT} fill="url(#sky-fill)" />
      {[30, 60].map((altitude) => (
        <g key={altitude}>
          <path d={`M0 ${y(altitude)}H${WIDTH}`} stroke="#262D63" strokeDasharray="2 6" />
          <text className="sky-label" x={8} y={y(altitude) - 6}>
            {altitude}° alt
          </text>
        </g>
      ))}
      {stars.map(([azimuth, altitude, magnitude, bv], index) => {
        const raw = 1.9 - 0.3 * magnitude;
        return (
          <circle
            key={index}
            cx={x(azimuth).toFixed(1)}
            cy={y(altitude).toFixed(1)}
            r={Math.max(0.5, raw).toFixed(2)}
            fill={starColor(bv)}
            opacity={Math.min(1, 0.17 + 0.45 * raw).toFixed(2)}
          />
        );
      })}
      {LABELLED.filter((name) => sky.named[name]).map((name) => {
        const [azimuth, altitude] = sky.named[name];
        return (
          <g key={name}>
            <circle
              cx={x(azimuth)}
              cy={y(altitude)}
              r={6}
              fill="none"
              stroke="#EAF1F7"
              strokeWidth=".9"
              opacity=".75"
            />
            <text className="sky-name" x={x(azimuth) + 11} y={y(altitude) + 4}>
              {name}
            </text>
          </g>
        );
      })}
      <rect y={HORIZON} width={WIDTH} height={HEIGHT - HORIZON} fill="#070920" />
      <path d={`M0 ${HORIZON}H${WIDTH}`} stroke="#3A4482" />
      {[
        { azimuth: -90, label: "90°W" },
        { azimuth: 0, label: "0°" },
        { azimuth: 90, label: "90°E" },
      ].map(({ azimuth, label }) => (
        <g key={label}>
          <path d={`M${x(azimuth)} ${HORIZON}v5`} stroke="#3A4482" />
          <text className="sky-label" x={x(azimuth)} y={HORIZON + 22} textAnchor="middle">
            {label}
          </text>
        </g>
      ))}
      <text className="sky-label sky-horizon" x={WIDTH - 8} y={HORIZON - 7} textAnchor="end">
        HORIZON
      </text>
      <circle cx={x(0)} cy={HORIZON} r={22} fill="url(#sky-earth-glow)" />
      <path d={`M${x(0) - 7} ${HORIZON}a7 7 0 0114 0z`} fill="#F4AE5B" />
      <text className="sky-earth" x={x(0) + 16} y={HORIZON - 10}>
        Earth, on the horizon
      </text>
    </svg>
  );
}

/** The real sky above the lunar south pole, looking toward Earth, from public/data/sky.json. */
export function SkyPanel() {
  const sky = useData("sky", loadSky);
  const titleId = useId();
  const date = sky.status === "ready" ? formatDate(sky.data.date) : null;
  return (
    <figure className="card sky-panel">
      <div className="panel-head">
        <div>
          <h2>Sky above the south pole</h2>
          <p className="panel-sub">Looking toward Earth · real star positions to magnitude {MAX_MAGNITUDE}</p>
        </div>
        {date && <span className="chip">{date}</span>}
      </div>
      <span id={titleId} className="visually-hidden">
        Sky above the lunar south pole{date ? ` on ${date}` : ""}: real star positions, Earth on the horizon at 0°
        azimuth, Sirius and Canopus high above.
      </span>
      {sky.status === "ready" && <Sky sky={sky.data} titleId={titleId} />}
      {sky.status === "loading" && (
        <div className="sky-placeholder" role="status">
          Loading the star map…
        </div>
      )}
      {sky.status === "error" && <p className="inline-error">The star map is unavailable. {sky.message}</p>}
      <figcaption className="sky-caption">
        <b>Earth never climbs far:</b> it stays within about 7° of the horizon, which is why Earth visibility is one of
        the Operations gates. The Large Magellanic Cloud is almost overhead.
      </figcaption>
    </figure>
  );
}
