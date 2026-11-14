import { useCallback, useEffect, useMemo, useState } from "react";
import type { SyntheticEvent } from "react";
import { EarthMap } from "../components/EarthMap";
import type { EarthMarker } from "../components/EarthMap";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { CheckCount } from "../components/CheckCount";
import { candidateOf, checksWithin, loadPatchAnalogs, poolLabel, siteName } from "../data/analogs";
import { useData } from "../data/useData";
import { links } from "../router";

const LIMITS = [
  "Cosine similarity compares the shapes the model learned. It is not a percentage, an accuracy or a suitability rating.",
  "A high cosine can hide a large slope or relief mismatch. Read the physical checks before trusting a match.",
  "Matches come only from the five prepared Earth sites. A closer analog could exist somewhere else on Earth.",
  "Earth cannot reproduce lunar gravity, vacuum, radiation, lighting or regolith. A terrain analog rehearses route planning, not the whole mission.",
  "The Earth simulation-readiness score (climate, land cover, access) has not been computed.",
];

function formatCoordinate(value: number, positive: string, negative: string): string {
  return `${Math.abs(value).toFixed(3)}° ${value >= 0 ? positive : negative}`;
}

export function AnalogsPage({ region, patch }: { region: string; patch: string }) {
  const loaded = useData(`analogs:${region}/${patch}`, () => loadPatchAnalogs(region, patch));
  const [active, setActive] = useState<string | null>(null);
  const onActive = useCallback((key: string | null) => setActive(key), []);
  const title =
    loaded.status === "ready" ? `Earth analogs · Patch ${patch} · ${loaded.data.patches.region.name}` : "Earth analogs";
  useEffect(() => {
    document.title = `${title} · Lunar Analog Finder`;
  }, [title]);

  const rows = useMemo(() => {
    if (loaded.status !== "ready" || !loaded.data.tile) return [];
    const { earth, tile } = loaded.data;
    return tile.matches.map((match) => ({ match, candidate: candidateOf(earth, match) }));
  }, [loaded]);

  const markers: EarthMarker[] = useMemo(
    () =>
      rows.map(({ match, candidate }) => ({
        key: candidate.id,
        label: String(match.overall_rank),
        latitude: candidate.latitude,
        longitude: candidate.longitude,
        title: `Rank ${match.overall_rank}`,
        href: links.pair(region, patch, candidate.id),
      })),
    [rows, region, patch],
  );

  if (loaded.status === "loading") return <Loading what="Earth analogs" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="These Earth analogs are unavailable" tone="error">
        {loaded.message} <a href={links.regions()}>Go to the region list.</a>
      </PageMessage>
    );
  }
  const { patches, record, analogs, tile, earth } = loaded.data;
  const point = (event: SyntheticEvent) => setActive((event.target as HTMLElement).closest("tr")?.dataset.key ?? null);

  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › <a href={links.region(patches.region.slug)}>{patches.region.name}</a> ›{" "}
        <a href={links.patch(patches.region.slug, record.slug)}>Patch {record.slug}</a> › Earth analogs
      </nav>
      <h1>Earth terrain that resembles this patch</h1>
      <p className="lede">
        {patches.region.name}, row {record.top_row}, column {record.top_col}. Searched {poolLabel(analogs, earth)}:{" "}
        {rows.length} matches, ranked by cosine similarity.
      </p>
      <p className="muted source-line">
        Lunar tile <code>{record.tile_id}</code>, similarity query <code>{tile?.query_id ?? "none"}</code>, pipeline run{" "}
        <code>{analogs.pipeline_run}</code>
      </p>

      {!tile ? (
        <PageMessage title="No Earth matches for this patch">
          The similarity model has no prepared terrain for this patch, so no search was run. Other patches in{" "}
          {patches.region.name} may have matches.
        </PageMessage>
      ) : (
        <>
          <section className="card" aria-labelledby="map-title">
            <h2 id="map-title">Where the matches are</h2>
            <EarthMap
              markers={markers}
              active={active}
              onActive={onActive}
              label={`Map of the ${rows.length} Earth matches, numbered by rank. The table below lists the same places.`}
            />
          </section>

          <div className="table-scroll">
            <table className="patch-table">
              <caption>
                All {rows.length} matches in rank order. Every match is shown, including weak ones.
              </caption>
              <thead>
                <tr>
                  <th scope="col" className="number">
                    Rank
                  </th>
                  <th scope="col">Earth site</th>
                  <th scope="col" className="number">
                    Cosine
                  </th>
                  <th scope="col">Physical checks in band</th>
                  <th scope="col">Location</th>
                </tr>
              </thead>
              <tbody onMouseOver={point} onFocus={point} onMouseLeave={() => setActive(null)} onBlur={() => setActive(null)}>
                {rows.map(({ match, candidate }) => (
                  <tr
                    key={candidate.id}
                    data-key={candidate.id}
                    className={active === candidate.id ? "is-active" : undefined}
                  >
                    <td className="number">{match.overall_rank}</td>
                    <th scope="row">
                      <a href={links.pair(patches.region.slug, record.slug, candidate.id)}>
                        {siteName(earth, candidate.site)}
                      </a>
                      <span className="muted"> · #{match.site_rank} at this site</span>
                    </th>
                    <td className="number">{match.cosine.toFixed(3)}</td>
                    <td>
                      <CheckCount within={checksWithin(match)} total={match.within.length} />
                    </td>
                    <td>
                      {formatCoordinate(candidate.latitude, "N", "S")}, {formatCoordinate(candidate.longitude, "E", "W")}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <p className="muted source-line">
            Select a site name to compare the two terrains side by side. A physical check is in band when the Moon–Earth
            difference is within the similarity pipeline's own tolerance for that measurement.
          </p>
        </>
      )}
      <Limitations points={LIMITS} />
    </>
  );
}
