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
import type { AssessmentName, AssessmentStatus, EnvironmentDocument, RegionEntry, Scenario } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

const LIMITS = [
  "The inputs are best-effort estimates, not measurements of the sites. Only four map values for the first seven regions are measured.",
  "A Pass marks a potential site worth a closer look, not a confirmed or safe one.",
  "Every terrain patch in a region shares the region's environment scores. They do not vary across the region in this build.",
  "Thresholds are the team's test assumptions, not NASA requirements or certifications.",
  "Operations and Survival answer different questions and are never combined into one score.",
];

async function loadCatalogue() {
  const [environment, regions] = await Promise.all([loadEnvironment(), loadRegions()]);
  const terrain = new Map<string, RegionEntry>(regions.regions.map((entry) => [entry.source_id, entry]));
  // Region numbers match the home page's cards and polar map.
  const numbers = new Map<string, number>(regions.regions.map((entry, index) => [entry.source_id, index + 1]));
  return { environment, terrain, numbers };
}

function TerrainLink({ scenario, terrain }: { scenario: Scenario; terrain: Map<string, RegionEntry> }) {
  const entry = scenario.terrain_region ? terrain.get(scenario.terrain_region) : undefined;
  if (!entry) return <span className="muted">No terrain data</span>;
  return <a href={links.region(entry.slug)}>{entry.exported_patch_count} terrain patches</a>;
}

const STATUSES: AssessmentStatus[] = ["Pass", "Fail", "Unknown"];

/**
 * Pass, Fail and Unknown counts for each assessment, side by side and never combined, plus what the Fails share.
 */
function Summary({ scenarios, environment }: { scenarios: Scenario[]; environment: EnvironmentDocument }) {
  const anyGates = environment.hard_gates?.operations || environment.hard_gates?.survival;
  // Which gates the Fails come from, by check label, when the per-check evidence is in this build.
  const failGates = (name: AssessmentName) => {
    const failed = scenarios.filter((scenario) => scenario[name].status === "Fail");
    if (failed.length === 0 || failed.some((scenario) => scenario[name].gates == null)) return null;
    const labels = new Set(
      failed.flatMap((scenario) =>
        (scenario[name].gates ?? []).filter((check) => check.status === "Fail").map((check) => check.label),
      ),
    );
    return { count: failed.length, labels: [...labels] };
  };
  const notes = (["operations", "survival"] as const).flatMap((name) => {
    const fails = failGates(name);
    if (!fails) return [];
    const which =
      fails.labels.length === 1
        ? `one gate, ${fails.labels[0].toLowerCase()}`
        : `${fails.labels.length} gates: ${fails.labels.join(", ").toLowerCase()}`;
    const all = fails.count === 1 ? "The" : fails.count === 2 ? "Both" : `All ${fails.count}`;
    return [`${all} ${ASSESSMENT_TITLES[name]} ${fails.count === 1 ? "Fail comes" : "Fails come"} from ${which}.`];
  });
  return (
    <section className="card env-summary" aria-label="Summary">
      <dl className="env-counts">
        {(["operations", "survival"] as const).map((name) => (
          <div key={name}>
            <dt>{ASSESSMENT_TITLES[name]}</dt>
            <dd>
              {STATUSES.map((status) => {
                const count = scenarios.filter((scenario) => scenario[name].status === status).length;
                return count === 0 ? null : (
                  <span key={status} className="env-count">
                    <AssessmentBadge status={status} gatesOff={gatesOff(environment, name)} />
                    <span className="data">{count}</span>
                  </span>
                );
              })}
            </dd>
          </div>
        ))}
      </dl>
      <p className="env-summary-note">
        {anyGates
          ? "Hard gates are on. A region must pass every gate before it gets a score; a Fail or Unknown shows no score. "
          : ""}
        {notes.join(" ")} <strong>Gate thresholds are project test values, not NASA limits.</strong>
      </p>
    </section>
  );
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
  const { environment, terrain, numbers } = loaded.data;
  const artemis = environment.scenarios.filter((scenario) => scenario.kind === "artemis");
  const hasTerrain = (scenario: Scenario) => scenario.terrain_region != null && terrain.has(scenario.terrain_region);
  const withTerrain = artemis.filter(hasTerrain);
  const environmentOnly = artemis.filter((scenario) => !hasTerrain(scenario));
  const groups: { title: string; scenarios: Scenario[]; terrainColumn: boolean }[] = [
    { title: `${withTerrain.length} with terrain patches`, scenarios: withTerrain, terrainColumn: true },
    { title: `${environmentOnly.length} with environment data only`, scenarios: environmentOnly, terrainColumn: false },
    // T3: the Apollo references are shown, apart from the south-pole regions.
    {
      title:
        "Apollo landing sites, for comparison. Equatorial, not south-pole candidates, scored from mission records, models and best-effort estimates",
      scenarios: environment.scenarios.filter((scenario) => scenario.kind === "apollo"),
      terrainColumn: false,
    },
  ].filter((group) => group.scenarios.length > 0);
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › Environment
      </nav>
      <h1>Environment checks for {artemis.length} potential landing regions</h1>
      <p className="lede">
        Two separate assessments per region from the team's environment scorer, each 0–100: Operations (can a mission
        work here) and Survival (can a crew stay alive here). They are never combined.
      </p>
      <p className="estimates-note">
        <strong>The inputs are best-effort estimates.</strong> Few of these conditions have been measured at the sites
        themselves, so a Pass marks a potential site, not a confirmed one. An uncrewed rover could map a potential
        site's terrain and measure its conditions; scoring those measurements would give a much clearer picture.
      </p>
      <Summary scenarios={artemis} environment={environment} />
      {(gatesOff(environment, "operations") || gatesOff(environment, "survival")) && (
        <p className="gates-note">{GATES_OFF_NOTE}</p>
      )}
      {environment.sample_input && <SampleDownload file={environment.sample_input.file} />}
      {groups.map((group) => (
        <div className="table-scroll" key={group.title}>
          <table className="patch-table">
            <caption>{group.title}</caption>
            <thead>
              <tr>
                <th scope="col">Region</th>
                <th scope="col">Operations</th>
                <th scope="col">Survival</th>
                {group.terrainColumn && <th scope="col">Terrain</th>}
              </tr>
            </thead>
            <tbody>
              {group.scenarios.map((scenario) => (
                <tr key={scenario.id}>
                  <th scope="row">
                    {group.terrainColumn && scenario.terrain_region && numbers.has(scenario.terrain_region) && (
                      <span className="region-number" aria-hidden="true">
                        {numbers.get(scenario.terrain_region)}
                      </span>
                    )}
                    <a href={links.scenario(scenario.id)}>{scenario.name}</a>
                    <span className="muted"> · {scenario.id}</span>
                  </th>
                  {(["operations", "survival"] as const).map((name) => (
                    <td key={name}>
                      <AssessmentBadge status={scenario[name].status} gatesOff={gatesOff(environment, name)} />{" "}
                      <FinalScore assessment={scenario[name]} />
                    </td>
                  ))}
                  {group.terrainColumn && (
                    <td>
                      <TerrainLink scenario={scenario} terrain={terrain} />
                    </td>
                  )}
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
    if (!scenario) {
      throw new DataError(`No environment scenario named "${scenarioId}" is in this build.`);
    }
    return { ...catalogue, scenario };
  });
  const title = loaded.status === "ready" ? `${loaded.data.scenario.name} · Environment` : "Environment";
  useEffect(() => {
    document.title = `${title} · Lunar Analog Finder`;
  }, [title]);
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
