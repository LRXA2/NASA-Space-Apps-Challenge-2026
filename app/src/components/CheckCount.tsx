import { ToneIcon } from "./StatusBadge";
import type { Tone } from "./StatusBadge";

/** "3 of 5", with a shape and colour by how many physical checks are in band. Text is always present. */
export function CheckCount({ within, total }: { within: number; total: number }) {
  const tone: Tone = within === total ? "good" : within >= Math.ceil(total / 2) ? "warning" : "critical";
  return (
    <span className={`badge badge-small badge-${tone}`}>
      <ToneIcon tone={tone} />
      {within} of {total}
    </span>
  );
}

/** One check: in band or not, as an icon plus a word. */
export function InBand({ within }: { within: boolean }) {
  return (
    <span className={`badge badge-small badge-${within ? "good" : "critical"}`}>
      <ToneIcon tone={within ? "good" : "critical"} />
      {within ? "In band" : "Out of band"}
    </span>
  );
}
