import { useEffect } from "react";
import { niceCeiling } from "../components/colorScales";
import { CrossingAxes } from "../components/CrossingAxes";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { ProbabilityBars } from "../components/ProbabilityBars";
import { StatusBadge, classLabel } from "../components/StatusBadge";
import { TerrainCanvas } from "../components/TerrainCanvas";
import { CheckCount } from "../components/CheckCount";
import { AssessmentBadge, FinalScore } from "../components/AssessmentView";
import { candidateOf, checksWithin, loadPatchAnalogs, poolLabel, siteName } from "../data/analogs";
import { DataError, decodePatch, loadEnvironment, loadGridFile } from "../data/loaders";
import type { PatchRecord, PatchesDocument, RoverClass, TerrainChannel, WalkingClass } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";
import { loadRegionPatches } from "./RegionPage";

const ROVER_ORDER: RoverClass[] = ["operable", "marginal", "non_operable"];
const WALKING_ORDER: WalkingClass[] = ["easy", "caution", "unsuitable"];

const LIMITS = [
  "Rover and on-foot classes are predictions from a CNN trained on Earth terrain. No lunar ground truth exists for them, and they are not safety certifications.",
  "A probability is the model's confidence in its own class. A high probability does not establish that the terrain is safe.",
  "On-foot walkability reads slope and roughness only. It ignores spacesuit limits, lighting, regolith and fatigue.",
  "A 30 m grid cannot show boulders or craters smaller than about 30 m.",
  "Crossing directions are four straight axes across one patch, named for the stored grid. They are not true lunar compass directions and not a route plan.",
];

async function loadPatch(region: string, patch: string): Promise<{ document: PatchesDocument; record: PatchRecord }> {
  const document = await loadRegionPatches(region);
  const record = document.patches.find((candidate) => candidate.slug === patch);
  if (!record) throw new DataError(`No patch named "${patch}" is in this build of ${document.region.name}.`);
  return { document, record };
}

async function loadTerrain(document: PatchesDocument, record: PatchRecord): Promise<TerrainChannel[]> {
  return decodePatch(await loadGridFile(document.grid), document.grid, record.grid_offset);
}

/** The best Earth match and a link to all of them. Similarity is a separate question from the classes above. */
function AnalogSummary({ region, patch }: { region: string; patch: string }) {
  const loaded = useData(`analogs:${region}/${patch}`, () => loadPatchAnalogs(region, patch));
  if (loaded.status === "loading") return <p role="status">Loading Earth analogs…</p>;
  if (loaded.status === "error") return <p className="inline-error" role="alert">{loaded.message}</p>;
  const { tile, earth, analogs } = loaded.data;
  if (!tile) return <p className="muted">No Earth search was run for this patch.</p>;
  const best = tile.matches[0];
  const candidate = candidateOf(earth, best);
  return (
    <>
      <p>
        Closest match: <strong>{siteName(earth, candidate.site)}</strong>, cosine {best.cosine.toFixed(3)},{" "}
        <CheckCount within={checksWithin(best)} total={best.within.length} /> physical checks in band.
      </p>
      <p className="muted">
        Searched {poolLabel(analogs, earth)}. Cosine is a similarity measure, not a percentage.
      </p>
      <p>
        <a href={links.analogs(region, patch)}>See all {tile.matches.length} Earth matches and the map</a>
      </p>
    </>
  );
}

/** The region's environment scenario. Every patch in the region shares it. */
function EnvironmentSummary({ regionSourceId }: { regionSourceId: string }) {
  const loaded = useData("environment-doc", loadEnvironment);
  if (loaded.status !== "ready") return null;
  const scenario = loaded.data.scenarios.find((entry) => entry.terrain_region === regionSourceId);
  if (!scenario) return <p className="muted">No environment scenario covers this region.</p>;
  return (
    <>
      <dl className="stats">
        {(["operations", "survival"] as const).map((name) => (
          <div key={name}>
            <dt>{name === "operations" ? "Operations" : "Survival"}</dt>
            <dd>
              <AssessmentBadge status={scenario[name].status} /> <FinalScore assessment={scenario[name]} />
            </dd>
          </div>
        ))}
      </dl>
      <p className="muted">
        Region-wide scenario <code>{scenario.id}</code> from mostly assumed inputs. It is the same for every patch in
        this region. <a href={links.scenario(scenario.id)}>See the domain scores</a>
      </p>
    </>
  );
}

function Terrain({ document, record }: { document: PatchesDocument; record: PatchRecord }) {
  const terrain = useData(`terrain:${document.grid.file}:${record.grid_offset}`, () => loadTerrain(document, record));
  if (terrain.status === "loading") return <p role="status">Loading terrain grids…</p>;
  if (terrain.status === "error") {
    return (
      <p className="inline-error" role="alert">
        Terrain grids are unavailable. {terrain.message} The predictions above do not depend on this file.
      </p>
    );
  }
  const slope = terrain.data.find((channel) => channel.name === "slope_deg");
  const elevation = terrain.data.find((channel) => channel.name === "relative_elevation_m");
  if (!slope || !elevation) {
    return (
      <p className="inline-error" role="alert">
        Terrain grids are unavailable. The terrain file does not hold slope and relative elevation.
      </p>
    );
  }
  const slopeMax = niceCeiling(Math.max(...slope.values));
  const elevationMax = niceCeiling(Math.max(...elevation.values.map(Math.abs)));
  return (
    <div className="terrain-pair">
      <TerrainCanvas
        title="Slope"
        channel={slope}
        scale={{ kind: "sequential", min: 0, max: slopeMax }}
        scaleNote={(scheme) => `${scheme === "dark" ? "Lighter" : "Darker"} blue is steeper. The scale is fitted to this patch.`}
      />
      <TerrainCanvas
        title="Relative elevation"
        channel={elevation}
        scale={{ kind: "diverging", min: -elevationMax, max: elevationMax }}
        scaleNote={() => "Height above (red) or below (blue) this patch's mean height. The scale is fitted to this patch."}
      />
    </div>
  );
}

export function PatchPage({ region, patch }: { region: string; patch: string }) {
  const loaded = useData(`patch:${region}/${patch}`, () => loadPatch(region, patch));
  const title = loaded.status === "ready" ? `Patch ${loaded.data.record.slug} · ${loaded.data.document.region.name}` : "Patch";
  useEffect(() => {
    document.title = `${title} · Lunar Analog Finder`;
  }, [title]);

  if (loaded.status === "loading") return <Loading what="patch" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="This patch is unavailable" tone="error">
        {loaded.message} <a href={links.regions()}>Go to the region list.</a>
      </PageMessage>
    );
  }
  const { document: patches, record } = loaded.data;
  const size = patches.patch_size_m;
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › <a href={links.region(patches.region.slug)}>{patches.region.name}</a> ›
        Patch {record.slug}
      </nav>
      <h1>
        Patch at row {record.top_row}, column {record.top_col}
      </h1>
      <p className="lede">
        {patches.region.name} · {size} m × {size} m · {patches.grid.shape[0]} × {patches.grid.shape[1]} grid at{" "}
        {patches.spacing_m} m
      </p>
      <p className="muted source-line">
        Source patch <code>{record.source_id}</code>, inference run <code>{patches.run_id}</code>
      </p>

      <div className="cards">
        <section className="card" aria-labelledby="rover-title">
          <h2 id="rover-title">Rover</h2>
          <StatusBadge value={record.rover.class} />
          <ProbabilityBars
            caption="Model probability for each rover class"
            predicted={record.rover.class}
            rows={ROVER_ORDER.map((key) => ({ key, label: classLabel(key), probability: record.rover.probabilities[key] }))}
          />
        </section>
        <section className="card" aria-labelledby="walking-title">
          <h2 id="walking-title">Crew on foot</h2>
          <StatusBadge value={record.walking.class} />
          <ProbabilityBars
            caption="Model probability for each on-foot class"
            predicted={record.walking.class}
            rows={WALKING_ORDER.map((key) => ({
              key,
              label: classLabel(key),
              probability: record.walking.probabilities[key],
            }))}
          />
          <p className="muted">
            A simple slope rule gives {classLabel(record.direct_rule.walking_class).toLowerCase()}. The CNN{" "}
            {record.direct_rule.cnn_agrees ? "agrees" : "disagrees"} with it.
          </p>
        </section>
        <section className="card" aria-labelledby="crossing-title">
          <h2 id="crossing-title">Rover crossing directions</h2>
          <CrossingAxes crossing={record.crossing} />
        </section>
      </div>

      <div className="cards">
        <section className="card" aria-labelledby="analogs-title">
          <h2 id="analogs-title">Earth analogs</h2>
          <AnalogSummary region={patches.region.slug} patch={record.slug} />
        </section>
        <section className="card" aria-labelledby="environment-title">
          <h2 id="environment-title">Environment</h2>
          <EnvironmentSummary regionSourceId={patches.region.source_id} />
        </section>
      </div>

      <section className="card" aria-labelledby="measured-title">
        <h2 id="measured-title">Measured from the terrain grid</h2>
        <dl className="stats">
          <div>
            <dt>Median slope</dt>
            <dd>{record.physical.slope_median_deg.toFixed(1)}°</dd>
          </div>
          <div>
            <dt>90th percentile slope</dt>
            <dd>{record.physical.slope_p90_deg.toFixed(1)}°</dd>
          </div>
          <div>
            <dt>Relief (highest minus lowest)</dt>
            <dd>{record.physical.relative_relief_m.toFixed(1)} m</dd>
          </div>
        </dl>
      </section>

      <section className="card" aria-labelledby="terrain-title">
        <h2 id="terrain-title">Terrain</h2>
        <Terrain document={patches} record={record} />
      </section>

      <Limitations points={LIMITS} />
    </>
  );
}
