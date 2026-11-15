import { useId } from "react";
import type {
  Assessment,
  AssessmentName,
  AssessmentStatus,
  EnvironmentDocument,
  Evidence,
  GateCheck,
} from "../data/types";
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
    "Four map values (Sun, Earth and sky visibility, permanent shadow) come from LOLA maps. Every other input is a best-effort estimate, not a measurement.",
  assumed: "Every input is a best-effort estimate with no measured footprint.",
  apollo: "A historical equatorial landing site, shown for comparison. Combines Apollo mission records, models and best-effort estimates. No terrain data.",
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
    <span className={`badge badge-small badge-${tone}`}>
      <ToneIcon tone={tone} />
      {label}
    </span>
  );
}

/** The final score, or why there is none. A blocked score is never shown as a number. */
export function FinalScore({ assessment, explain = false }: { assessment: Assessment; explain?: boolean }) {
  if (assessment.status !== "Pass") {
    // The reason is always read out; on the scenario page it is also shown.
    return (
      <span className="no-score">
        No score
        <span className={explain ? "no-score-reason" : "visually-hidden"}>
          {explain ? "" : ": "}Blocked by the {assessment.status} status
        </span>
      </span>
    );
  }
  if (assessment.score === null) return <span className="no-score">Not given</span>;
  return <strong className="score">{assessment.score.toFixed(1)}</strong>;
}

/** One assessment: status, final score, fail reasons and every domain score, as the scorer wrote them. */
export function AssessmentView(props: {
  title: string;
  assessment: Assessment;
  gatesOff?: boolean;
  /** Names the scenario when several are on one page, so each section has a unique name. */
  context?: string;
}) {
  const { title, assessment } = props;
  const id = useId();
  return (
    <section
      className="card"
      aria-labelledby={props.context ? undefined : id}
      aria-label={props.context ? `${title}, ${props.context}` : undefined}
    >
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
            <FinalScore assessment={assessment} explain />
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
      {assessment.gates == null ? (
        <p className="muted">
          Per-check values and thresholds are not in this build. These are the scorer's domain summaries.
        </p>
      ) : (
        <GateTable title={title} gates={assessment.gates} coverage={assessment.coverage ?? null} />
      )}
    </section>
  );
}

const number = new Intl.NumberFormat("en", { maximumFractionDigits: 3 });

function quantity(value: number, unit: string): string {
  const text = number.format(value).replace("-", "−");
  return unit ? `${text} ${unit}` : text;
}

/** The rule a gate checks, in words a reader can compare with the value. */
function gateRule(check: GateCheck): string {
  if (check.operator === "between" && check.lower !== null && check.upper !== null) {
    return `between ${quantity(check.lower, "")} and ${quantity(check.upper, check.unit)}`;
  }
  if (check.threshold === null) return "no threshold";
  const rule = `${check.operator === "above" ? "≥" : "≤"} ${quantity(check.threshold, check.unit)}`;
  // The scorer shortens a duration threshold that cannot fit in the time window.
  if (check.configured_threshold !== null && check.window_hours !== null) {
    return `${rule} (${quantity(check.configured_threshold, check.unit)}, capped to the ${number.format(check.window_hours)} h window)`;
  }
  return rule;
}

/** Every hard gate behind the status: value, rule, verdict and, for Fail or Unknown, the scorer's reason. */
function GateTable({ title, gates, coverage }: { title: string; gates: GateCheck[]; coverage: string | null }) {
  if (gates.length === 0) {
    return <p className="muted">No hard gate applies to {title}, so its status only reflects missing inputs.</p>;
  }
  const rationales = [...new Set(gates.map((check) => check.rationale).filter(Boolean))];
  return (
    <>
      <h3 className="subhead">Gate checks</h3>
      <div className="table-scroll">
        <table className="patch-table gate-table">
          <caption>
            The {gates.length} hard gates behind the {title} status, as the scorer reported them.
            {coverage ? ` Evidence coverage ${coverage}.` : ""}
          </caption>
          <thead>
            <tr>
              <th scope="col">Check</th>
              <th scope="col" className="number">
                Value
              </th>
              <th scope="col">Rule</th>
              <th scope="col">Result</th>
            </tr>
          </thead>
          <tbody>
            {gates.map((check) => (
              <tr key={check.column}>
                <th scope="row">
                  {check.label}
                  <span className="muted gate-domain">{check.domain_label}</span>
                </th>
                <td className="number">
                  {check.value === null ? <span className="muted">Missing</span> : quantity(check.value, check.unit)}
                </td>
                <td>{gateRule(check)}</td>
                <td>
                  <AssessmentBadge status={check.status} />
                  {/* The scorer repeats the rationale as the reason when a value is present; show only real reasons. */}
                  {check.status !== "Pass" && check.reason && check.reason !== check.rationale && (
                    <span className="gate-reason">{check.reason}</span>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {rationales.map((text) => (
        <p key={text} className="muted gate-rationale">
          {text}
        </p>
      ))}
    </>
  );
}
