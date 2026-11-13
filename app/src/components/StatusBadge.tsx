import type { RoverClass, WalkingClass } from "../data/types";

type Tone = "good" | "warning" | "critical";

const CLASSES: Record<RoverClass | WalkingClass, { label: string; tone: Tone }> = {
  operable: { label: "Operable", tone: "good" },
  marginal: { label: "Marginal", tone: "warning" },
  non_operable: { label: "Non-operable", tone: "critical" },
  easy: { label: "Easy", tone: "good" },
  caution: { label: "Caution", tone: "warning" },
  unsuitable: { label: "Unsuitable", tone: "critical" },
};

export function classLabel(value: RoverClass | WalkingClass): string {
  return CLASSES[value].label;
}

// Each tone has its own shape, so the class reads without colour.
function ToneIcon({ tone }: { tone: Tone }) {
  return (
    <svg className={`tone-icon tone-${tone}`} viewBox="0 0 20 20" width="20" height="20" aria-hidden="true">
      {tone === "good" && (
        <>
          <circle cx="10" cy="10" r="9" />
          <path className="tone-mark" d="M5.5 10.5l3 3 6-6.5" />
        </>
      )}
      {tone === "warning" && (
        <>
          <path d="M10 1.5l9 16H1z" />
          <path className="tone-mark" d="M10 7.5v4.5M10 14.6v.4" />
        </>
      )}
      {tone === "critical" && (
        <>
          <path d="M6.3 1h7.4L19 6.3v7.4L13.7 19H6.3L1 13.7V6.3z" />
          <path className="tone-mark" d="M6.5 6.5l7 7M13.5 6.5l-7 7" />
        </>
      )}
    </svg>
  );
}

/** Predicted class as an icon plus a text label. Colour is never the only signal. */
export function StatusBadge({ value }: { value: RoverClass | WalkingClass }) {
  const { label, tone } = CLASSES[value];
  return (
    <span className="badge">
      <ToneIcon tone={tone} />
      {label}
    </span>
  );
}
