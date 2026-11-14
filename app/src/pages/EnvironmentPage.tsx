import { useEffect } from "react";
import {
  ASSESSMENT_TITLES,
  AssessmentBadge,
  AssessmentView,
  EVIDENCE_LABELS,
  FinalScore,
  GATES_OFF_NOTE,
  gatesOff,
} from "../components/AssessmentView";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { DataError, dataUrl, loadEnvironment, loadRegions } from "../data/loaders";
import type { RegionEntry, Scenario } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

// Team blocker T3: whether the app shows the six Apollo reference scenarios. Flip to true if the team agrees.
export const SHOW_APOLLO = false;

const LIMITS = [
  "These are scenario results from mostly assumed inputs, not measured site assessments. Only four map values for the first seven regions are measured.",
  "Every terrain patch in a region shares the region's environment scores. They do not vary across the region in this build.",
  "Thresholds are the team's test assumptions, not NASA requirements or certifications.",
  "Operations and Survival answer different questions and are never combined into one score.",
];

async function loadCatalogue() {
  const [environment, regions] = await Promise.all([loadEnvironment(), loadRegions()]);
  const terrain = new Map<string, RegionEntry>(regions.regions.map((entry) => [entry.source_id, entry]));
  return { environment, terrain };
}

function TerrainLink({ scenario, terrain }: { scenario: Scenario; terrain: Map<string, RegionEntry> }) {
  const entry = scenario.terrain_region ? terrain.get(scenario.terrain_region) : undefined;
  if (!entry) return <span className="muted">No terrain data</span>;
  return <a href={links.region(entry.slug)}>{entry.exported_patch_count} terrain patches</a>;
}

function SampleDownload({ file }: { file: string }) {
  return (
    <p>
      <a href={dataUrl(file)} download="sample_input.csv">
        Download the scorer's input template (sample_input.csv)
      </a>
      <span className="muted"> · the unchanged input file these results were scored from</span>
    </p>
  );
}

export function EnvironmentPage() {
  const loaded = useData("environment", loadCatalogue);
  useEffect(() => {
    document.title = "Environment · Lunar Analog Finder";
  }, []);
  if (loaded.status === "loading") return <Loading what="environment results" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="Environment results are unavailable" tone="error">
        {loaded.message}
      </PageMessage>
    );
  }
  const { environment, terrain } = loaded.data;
  const shown = environment.scenarios.filter((scenario) => scenario.kind === "artemis" || (SHOW_APOLLO && scenario.kind === "apollo"));
  const groups: { title: string; scenarios: Scenario[] }[] = [
    { title: "Artemis III candidate regions", scenarios: shown.filter((scenario) => scenario.kind === "artemis") },
    { title: "Apollo reference scenarios", scenarios: shown.filter((scenario) => scenario.kind === "apollo") },
  ].filter((group) => group.scenarios.length > 0);
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › Environment
      </nav>
      <h1>Environment assessments</h1>
      <p className="lede">
        Two separate assessments per region from the team's environment scorer: Operations (can a mission work here) and
        Survival (can a crew stay alive here).
      </p>
      {(gatesOff(environment, "operations") || gatesOff(environment, "survival")) && (
        <p className="gates-note">{GATES_OFF_NOTE}</p>
      )}
      {environment.sample_input && <SampleDownload file={environment.sample_input.file} />}
      {groups.map((group) => (
        <div className="table-scroll" key={group.title}>
          <table className="patch-table">
            <caption>
              {group.title} ({group.scenarios.length})
            </caption>
            <thead>
              <tr>
                <th scope="col">Region</th>
                <th scope="col">Operations</th>
                <th scope="col">Survival</th>
                <th scope="col">Terrain</th>
              </tr>
            </thead>
            <tbody>
              {group.scenarios.map((scenario) => (
                <tr key={scenario.id}>
                  <th scope="row">
                    <a href={links.scenario(scenario.id)}>{scenario.name}</a>
                    <span className="muted"> · {scenario.id}</span>
                  </th>
                  {(["operations", "survival"] as const).map((name) => (
                    <td key={name}>
                      <AssessmentBadge status={scenario[name].status} gatesOff={gatesOff(environment, name)} />{" "}
                      <FinalScore assessment={scenario[name]} />
                    </td>
                  ))}
                  <td>
                    <TerrainLink scenario={scenario} terrain={terrain} />
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      ))}
      <Limitations points={LIMITS} />
    </>
  );
}

export function ScenarioPage({ scenario: scenarioId }: { scenario: string }) {
  const loaded = useData(`scenario:${scenarioId}`, async () => {
    const catalogue = await loadCatalogue();
    const scenario = catalogue.environment.scenarios.find((entry) => entry.id === scenarioId);
    if (!scenario || (scenario.kind === "apollo" && !SHOW_APOLLO)) {
      throw new DataError(`No environment scenario named "${scenarioId}" is in this build.`);
    }
    return { ...catalogue, scenario };
  });
  const name = loaded.status === "ready" ? loaded.data.scenario.name : "Environment";
  useEffect(() => {
    document.title = `${name} · Environment · Lunar Analog Finder`;
  }, [name]);
  if (loaded.status === "loading") return <Loading what="environment results" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="This scenario is unavailable" tone="error">
        {loaded.message} <a href={links.environment()}>Go to all environment results.</a>
      </PageMessage>
    );
  }
  const { scenario, terrain, environment } = loaded.data;
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › <a href={links.environment()}>Environment</a> › {scenario.name}
      </nav>
      <h1>{scenario.name}</h1>
      <p className="lede">
        Environment scenario <code>{scenario.id}</code> · <TerrainLink scenario={scenario} terrain={terrain} />
      </p>
      <p className="muted source-line">
        {EVIDENCE_LABELS[scenario.evidence]} Pipeline run <code>{environment.pipeline_run}</code>.
      </p>
      <div className="cards">
        <AssessmentView
          title={ASSESSMENT_TITLES.operations}
          assessment={scenario.operations}
          gatesOff={gatesOff(environment, "operations")}
        />
        <AssessmentView
          title={ASSESSMENT_TITLES.survival}
          assessment={scenario.survival}
          gatesOff={gatesOff(environment, "survival")}
        />
      </div>
      {(gatesOff(environment, "operations") || gatesOff(environment, "survival")) && (
        <p className="muted">{GATES_OFF_NOTE}</p>
      )}
      {environment.sample_input && <SampleDownload file={environment.sample_input.file} />}
      <Limitations points={LIMITS} />
    </>
  );
}
