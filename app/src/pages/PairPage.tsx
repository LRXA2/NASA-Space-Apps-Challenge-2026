import { useEffect } from "react";
import { InBand, CheckCount } from "../components/CheckCount";
import { niceCeiling } from "../components/colorScales";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { TerrainCanvas } from "../components/TerrainCanvas";
import { candidateOf, checksWithin, loadEarthTerrain, loadMoonTerrain, loadPatchAnalogs, siteName } from "../data/analogs";
import type { PatchAnalogs } from "../data/analogs";
import { DataError } from "../data/loaders";
import type { AnalogMatch, EarthCandidate, TerrainChannel } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

const LIMITS = [
  "Both grids are 960 m squares at 30 m spacing. Features smaller than about 30 m, such as boulders and small craters, are invisible here.",
  "The Earth grid is drawn as stored in its own projection, and the Moon grid as stored in the lunar grid. Neither is rotated to north.",
  "Matching terrain shape does not make the Earth site a lunar environment: gravity is six times stronger, there is air and weather, and the surface is soil and rock, not regolith.",
  "The physical tolerances are the similarity pipeline's own comparison bands, not mission requirements.",
  "The Earth simulation-readiness score (climate, land cover, access) has not been computed.",
];

interface Pair extends PatchAnalogs {
  match: AnalogMatch;
  candidate: EarthCandidate;
}

async function loadPair(region: string, patch: string, candidateId: string): Promise<Pair> {
  const base = await loadPatchAnalogs(region, patch);
  const match = base.tile?.matches.find((entry) => candidateOf(base.earth, entry).id === candidateId);
  if (!match) throw new DataError(`Earth patch ${candidateId} is not one of this patch's matches.`);
  return { ...base, match, candidate: candidateOf(base.earth, match) };
}

function channel(channels: TerrainChannel[], name: string): TerrainChannel {
  const found = channels.find((entry) => entry.name === name);
  if (!found) throw new DataError(`The terrain file does not hold ${name}.`);
  return found;
}

function Grids({ pair }: { pair: Pair }) {
  const key = `pair-terrain:${pair.record.tile_id}:${pair.candidate.id}`;
  const terrain = useData(key, async () => {
    const [moon, earth] = await Promise.all([
      loadMoonTerrain(pair.patches, pair.record),
      loadEarthTerrain(pair.earth, pair.candidate),
    ]);
    return {
      moonSlope: channel(moon, "slope_deg"),
      moonElevation: channel(moon, "relative_elevation_m"),
      earthSlope: channel(earth, "slope_deg"),
      earthElevation: channel(earth, "relative_elevation_m"),
    };
  });
  if (terrain.status === "loading") return <p role="status">Loading terrain grids…</p>;
  if (terrain.status === "error") {
    return (
      <p className="inline-error" role="alert">
        Terrain grids are unavailable. {terrain.message} The checks below do not depend on these files.
      </p>
    );
  }
  const grids = terrain.data;
  // One scale per measurement, shared by Moon and Earth, so equal colours mean equal values.
  const slopeMax = niceCeiling(Math.max(...grids.moonSlope.values, ...grids.earthSlope.values));
  const elevationMax = niceCeiling(
    Math.max(...grids.moonElevation.values.map(Math.abs), ...grids.earthElevation.values.map(Math.abs)),
  );
  const slopeScale = { kind: "sequential" as const, min: 0, max: slopeMax };
  const elevationScale = { kind: "diverging" as const, min: -elevationMax, max: elevationMax };
  const slopeNote = () => "Moon and Earth share this slope scale.";
  const elevationNote = () => "Height above (red) or below (blue) the patch's own reference. Moon and Earth share this scale.";
  return (
    <div className="pair-grid">
      <TerrainCanvas title="Moon · slope" channel={grids.moonSlope} scale={slopeScale} scaleNote={slopeNote} />
      <TerrainCanvas title="Earth · slope" channel={grids.earthSlope} scale={slopeScale} scaleNote={slopeNote} />
      <TerrainCanvas
        title="Moon · relative elevation"
        channel={grids.moonElevation}
        scale={elevationScale}
        scaleNote={elevationNote}
      />
      <TerrainCanvas
        title="Earth · relative elevation"
        channel={grids.earthElevation}
        scale={elevationScale}
        scaleNote={elevationNote}
      />
    </div>
  );
}

function format(value: number): string {
  return Math.abs(value) >= 100 ? value.toFixed(0) : Math.abs(value) >= 1 ? value.toFixed(2) : value.toFixed(3);
}

export function PairPage({ region, patch, candidate }: { region: string; patch: string; candidate: string }) {
  const loaded = useData(`pair:${region}/${patch}/${candidate}`, () => loadPair(region, patch, candidate));
  const title = loaded.status === "ready" ? `Moon–Earth pair · Patch ${patch}` : "Moon–Earth pair";
  useEffect(() => {
    document.title = `${title} · Lunar Analog Finder`;
  }, [title]);

  if (loaded.status === "loading") return <Loading what="comparison" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="This comparison is unavailable" tone="error">
        {loaded.message} <a href={links.analogs(region, patch)}>Go back to the Earth analogs.</a>
      </PageMessage>
    );
  }
  const pair = loaded.data;
  const { patches, record, match, earth, tile } = pair;
  const site = siteName(earth, pair.candidate.site);
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › <a href={links.region(patches.region.slug)}>{patches.region.name}</a> ›{" "}
        <a href={links.patch(patches.region.slug, record.slug)}>Patch {record.slug}</a> ›{" "}
        <a href={links.analogs(patches.region.slug, record.slug)}>Earth analogs</a> › Rank {match.overall_rank}
      </nav>
      <h1>
        {patches.region.name} and {site}
      </h1>
      <p className="lede">
        Rank {match.overall_rank} of {tile?.matches.length}. Cosine similarity {match.cosine.toFixed(3)}.{" "}
        <CheckCount within={checksWithin(match)} total={match.within.length} /> physical checks in band.
      </p>
      <p className="muted source-line">
        Moon tile <code>{record.tile_id}</code> · Earth patch <code>{pair.candidate.id}</code> at{" "}
        {pair.candidate.latitude.toFixed(4)}, {pair.candidate.longitude.toFixed(4)}
      </p>

      <section className="card" aria-labelledby="checks-title">
        <h2 id="checks-title">Physical checks</h2>
        <div className="table-scroll">
          <table className="patch-table">
            <caption>Values from the similarity pipeline. Difference is Earth minus Moon.</caption>
            <thead>
              <tr>
                <th scope="col">Measurement</th>
                <th scope="col" className="number">
                  Moon
                </th>
                <th scope="col" className="number">
                  Earth
                </th>
                <th scope="col" className="number">
                  Difference
                </th>
                <th scope="col" className="number">
                  Tolerance
                </th>
                <th scope="col">Result</th>
              </tr>
            </thead>
            <tbody>
              {earth.checks.map((check, index) => {
                const moonValue = tile?.moon_checks[index] ?? Number.NaN;
                const earthValue = pair.candidate.checks[index];
                return (
                  <tr key={check.name}>
                    <th scope="row">{check.label}</th>
                    <td className="number">{format(moonValue)}</td>
                    <td className="number">{format(earthValue)}</td>
                    <td className="number">{format(earthValue - moonValue).replace("-", "−")}</td>
                    <td className="number">±{format(match.bands[index])}</td>
                    <td>
                      <InBand within={match.within[index]} />
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </section>

      <section className="card" aria-labelledby="pair-terrain-title">
        <h2 id="pair-terrain-title">Terrain side by side</h2>
        <Grids pair={pair} />
      </section>

      <section className="card" aria-labelledby="readiness-title">
        <h2 id="readiness-title">Earth simulation readiness</h2>
        <p className="muted">
          Not computed. Climate, land cover and access for {site} were explored in the team's notebooks, but no score
          has been built from them.
        </p>
      </section>

      <Limitations points={LIMITS} />
    </>
  );
}
