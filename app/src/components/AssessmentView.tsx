import type { Assessment, AssessmentName, AssessmentStatus, EnvironmentDocument, Evidence } from "../data/types";
import { ToneIcon } from "./StatusBadge";
import type { Tone } from "./StatusBadge";

const STATUS: Record<AssessmentStatus, { label: string; tone: Tone }> = {
  Pass: { label: "Pass", tone: "good" },
  Fail: { label: "Fail", tone: "critical" },
  // Unknown is not a pass: it gets its own label and the warning shape.
  Unknown: { label: "Unknown", tone: "warning" },
};

export const EVIDENCE_LABELS: Record<Evidence, string> = {
  measured_maps:
    "Four map values (Sun, Earth and sky visibility, permanent shadow) come from LOLA maps. Every other input is a test assumption.",
  assumed: "Every input is an assumed value with no measured footprint.",
  apollo: "Combines Apollo mission records, models and test assumptions.",
  uploaded: "Values you supplied. They have not been checked against any measurement.",
};

export const ASSESSMENT_TITLES = { operations: "Operations", survival: "Survival" } as const;

/** True when the scorer config says this assessment has no hard gate that could fail. */
export function gatesOff(environment: Pick<EnvironmentDocument, "hard_gates">, name: AssessmentName): boolean {
  return environment.hard_gates?.[name] === false;
}

export const GATES_OFF_NOTE =
  "Hard gates are switched off in the scorer's configuration, so nothing can fail. “Pass · gates off” only means no required input was missing. It is not a verdict on the site.";

export function AssessmentBadge({ status, gatesOff = false }: { status: AssessmentStatus; gatesOff?: boolean }) {
  const { label, tone } = STATUS[status];
  // With no gate able to fail, Pass is not a verdict: no tick, and the label says why.
  if (status === "Pass" && gatesOff) return <span className="badge badge-small badge-plain">Pass · gates off</span>;
  return (
    <span className="badge badge-small">
      <ToneIcon tone={tone} />
      {label}
    </span>
  );
}

/** The final score, or why there is none. A blocked score is never shown as a number. */
export function FinalScore({ assessment }: { assessment: Assessment }) {
  if (assessment.status !== "Pass") return <span className="muted">Blocked by the {assessment.status} status</span>;
  if (assessment.score === null) return <span className="muted">Not given</span>;
  return <strong>{assessment.score.toFixed(1)}</strong>;
}

/** One assessment: status, final score, fail reasons and every domain score, as the scorer wrote them. */
export function AssessmentView(props: { title: string; assessment: Assessment; gatesOff?: boolean }) {
  const { title, assessment } = props;
  const id = `assessment-${title.toLowerCase()}`;
  return (
    <section className="card" aria-labelledby={id}>
      <h2 id={id}>{title}</h2>
      <dl className="stats">
        <div>
          <dt>Status</dt>
          <dd>
            <AssessmentBadge status={assessment.status} gatesOff={props.gatesOff} />
          </dd>
        </div>
        <div>
          <dt>Final score (0–100)</dt>
          <dd>
            <FinalScore assessment={assessment} />
          </dd>
        </div>
      </dl>
      {assessment.fail_reasons.length > 0 && (
        <>
          <h3 className="subhead">Why it did not pass</h3>
          <ul>
            {assessment.fail_reasons.map((reason) => (
              <li key={reason}>
                <code>{reason}</code>
              </li>
            ))}
          </ul>
        </>
      )}
      <table className="probabilities">
        <caption>Domain scores, 0–100. A high domain score does not override the status.</caption>
        <tbody>
          {assessment.domains.map((domain) => (
            <tr key={domain.name}>
              <th scope="row">{domain.label}</th>
              <td className="bar-cell" aria-hidden="true">
                <span className="bar-track">
                  <span className="bar-fill" style={{ width: `${Math.max(0, Math.min(100, domain.score ?? 0))}%` }} />
                </span>
              </td>
              <td className="number">{domain.score === null ? "—" : domain.score.toFixed(1)}</td>
            </tr>
          ))}
        </tbody>
      </table>
      <p className="muted">Per-check values and thresholds are not in this build. These are the scorer's domain summaries.</p>
    </section>
  );
}
