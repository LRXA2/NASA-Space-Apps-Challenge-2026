import { useEffect, useRef, useState } from "react";
import type { ChangeEvent } from "react";
import {
  ASSESSMENT_TITLES,
  AssessmentBadge,
  AssessmentView,
  EVIDENCE_LABELS,
  FinalScore,
  GATES_OFF_NOTE,
  gatesOff,
} from "../components/AssessmentView";
import { InputGuide } from "../components/InputGuide";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { dataUrl, loadEnvironment } from "../data/loaders";
import type { EnvironmentDocument, Scenario } from "../data/types";
import { useData } from "../data/useData";
import type { ScoreReply, ScorerFile } from "../workers/environmentWorker";

const LIMITS = [
  "These are scores for the values you typed in, not measurements of a real site. Nothing is checked against data.",
  "The scorer, its weights and its thresholds are the team's test configuration, not NASA requirements.",
  "Results stay in this browser tab. They are not saved or sent anywhere, and they disappear when you reload.",
  "Terrain uploads (rover and on-foot classes, Earth analogs) are not available in this build.",
];

// One worker per visit, so Pyodide downloads only once.
let worker: Worker | null = null;
let nextId = 0;

function scorer(): Worker {
  worker ??= new Worker(new URL("../workers/environmentWorker.ts", import.meta.url), { type: "module" });
  return worker;
}

type State =
  | { stage: "idle" }
  | { stage: "loading" | "scoring"; file: string }
  | { stage: "error"; file: string; message: string }
  | { stage: "done"; file: string; scenarios: Scenario[] };

function score(files: ScorerFile[], csv: string, onReply: (reply: ScoreReply) => void): () => void {
  const id = (nextId += 1);
  const current = scorer();
  const listener = (event: MessageEvent<ScoreReply>) => {
    if (event.data.id !== id) return;
    onReply(event.data);
    if (event.data.stage !== "loading") current.removeEventListener("message", listener);
  };
  current.addEventListener("message", listener);
  current.postMessage({ id, files, csv });
  return () => current.removeEventListener("message", listener);
}

function Results({ scenarios, gates }: { scenarios: Scenario[]; gates: Pick<EnvironmentDocument, "hard_gates"> }) {
  const anyOff = gatesOff(gates, "operations") || gatesOff(gates, "survival");
  return (
    <>
      {anyOff && <p className="gates-note">{GATES_OFF_NOTE}</p>}
      <div className="table-scroll">
        <table className="patch-table">
          <caption>Your {scenarios.length} rows, scored in this browser. User-supplied, not NASA candidate sites.</caption>
          <thead>
            <tr>
              <th scope="col">Row ID</th>
              <th scope="col">{ASSESSMENT_TITLES.operations}</th>
              <th scope="col">{ASSESSMENT_TITLES.survival}</th>
            </tr>
          </thead>
          <tbody>
            {scenarios.map((scenario) => (
              <tr key={scenario.id}>
                <th scope="row">
                  <button
                    type="button"
                    aria-controls={`upload-${scenario.id}`}
                    onClick={() => {
                      const detail = document.getElementById(`upload-${scenario.id}`);
                      if (detail instanceof HTMLDetailsElement) {
                        detail.open = true;
                        detail.querySelector("summary")?.focus();
                      }
                    }}
                  >
                    {scenario.id}
                  </button>
                </th>
                {(["operations", "survival"] as const).map((name) => (
                  <td key={name}>
                    <AssessmentBadge status={scenario[name].status} gatesOff={gatesOff(gates, name)} />{" "}
                    <FinalScore assessment={scenario[name]} />
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {scenarios.map((scenario) => (
        <details key={scenario.id} id={`upload-${scenario.id}`} className="card">
          <summary>
            <strong>{scenario.id}</strong>: domain scores and reasons
          </summary>
          <p className="muted">{EVIDENCE_LABELS.uploaded}</p>
          <div className="cards">
            <AssessmentView
              title={ASSESSMENT_TITLES.operations}
              assessment={scenario.operations}
              gatesOff={gatesOff(gates, "operations")}
              context={scenario.id}
            />
            <AssessmentView
              title={ASSESSMENT_TITLES.survival}
              assessment={scenario.survival}
              gatesOff={gatesOff(gates, "survival")}
              context={scenario.id}
            />
          </div>
        </details>
      ))}
    </>
  );
}

export function UploadPage() {
  const environment = useData("environment-doc", loadEnvironment);
  const [state, setState] = useState<State>({ stage: "idle" });
  const cancel = useRef<(() => void) | null>(null);
  useEffect(() => {
    document.title = "Try your own data · Lunar Analog Finder";
    return () => cancel.current?.();
  }, []);

  if (environment.status === "loading") return <Loading what="the scorer" />;
  if (environment.status === "error") {
    return (
      <PageMessage title="The upload is unavailable" tone="error">
        {environment.message}
      </PageMessage>
    );
  }
  const { sample_input: sample, upload_files: published } = environment.data;
  const files: ScorerFile[] | null = published
    ? published.map((file) => ({ name: file.name, url: new URL(dataUrl(file.file), window.location.href).href, sha256: file.sha256 }))
    : null;

  async function onFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0];
    event.target.value = "";
    if (!file || !files) return;
    cancel.current?.();
    setState({ stage: "scoring", file: file.name });
    const text = await file.text();
    cancel.current = score(files, text, (reply) => {
      if (reply.stage === "loading") setState({ stage: "loading", file: file.name });
      else if (reply.stage === "failed") setState({ stage: "error", file: file.name, message: reply.message });
      else if (!reply.result.ok) setState({ stage: "error", file: file.name, message: reply.result.error });
      else setState({ stage: "done", file: file.name, scenarios: reply.result.scenarios as Scenario[] });
    });
  }

  const busy = state.stage === "loading" || state.stage === "scoring";
  return (
    <>
      <h1>Score your own environment scenario</h1>
      <p className="lede">
        Fill in the environment scorer's input template with your own values, upload it, and see Operations and Survival
        results. The team's scorer runs inside your browser. Your file is not uploaded to any server.
      </p>
      <ol className="steps">
        <li>
          {sample ? (
            <a href={dataUrl(sample.file)} download="sample_input.csv">
              Download the input template (sample_input.csv)
            </a>
          ) : (
            "The input template is missing from this build."
          )}
          . Each row is one scenario. Keep the column names. Change the values, and give each row a new unique{" "}
          <code>id</code>.
        </li>
        <li>
          <label>
            Upload your filled-in CSV:{" "}
            <input type="file" accept=".csv,text/csv" onChange={onFile} disabled={!files || busy} />
          </label>
        </li>
      </ol>
      <InputGuide />
      {!files && <p className="inline-error">The scorer files are missing from this build, so uploads are switched off.</p>}
      <div aria-live="polite">
        {state.stage === "loading" && (
          <p role="status">Loading the scorer for the first time (about 10 MB). Later uploads in this visit are instant.</p>
        )}
        {state.stage === "scoring" && <p role="status">Scoring {state.file}…</p>}
        {state.stage === "error" && (
          <p className="inline-error" role="alert">
            {state.file} could not be scored. {state.message.replace(/\.?\s*$/, ".")} No results are shown.
          </p>
        )}
      </div>
      {state.stage === "done" && <Results scenarios={state.scenarios} gates={environment.data} />}
      <Limitations points={LIMITS} />
    </>
  );
}
