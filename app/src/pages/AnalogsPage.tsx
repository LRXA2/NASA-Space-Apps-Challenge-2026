import { useCallback, useEffect, useMemo, useState } from "react";
import type { SyntheticEvent } from "react";
import { EarthMap } from "../components/EarthMap";
import type { EarthMarker } from "../components/EarthMap";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { CheckCount } from "../components/CheckCount";
import { bestFit, candidateOf, checksWithin, loadPatchAnalogs, poolLabel, siteName } from "../data/analogs";
import type { AnalogMatch, EarthCandidate, EarthDocument } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

const LIMITS = [
  "Cosine similarity compares the shapes the model learned. It is not a percentage, an accuracy or a suitability rating.",
  "A high cosine can hide a large slope or relief mismatch. Read the physical checks before trusting a match.",
  "Matches come only from the five prepared Earth sites. A closer analog could exist somewhere else on Earth.",
  "Earth cannot reproduce lunar gravity, vacuum, radiation, lighting or regolith. A terrain analog rehearses route planning, not the whole mission.",
  "The Earth simulation-readiness score (climate, land cover, access) has not been computed.",
];

type Sort = "shape" | "fit";

const SORTS: { value: Sort; label: string; caption: string }[] = [
  { value: "shape", label: "Shape similarity", caption: "in rank order (cosine similarity)" },
  { value: "fit", label: "Physical fit", caption: "by physical checks in band, then by rank" },
];

// The chosen order stays while the user moves between patches. It is not part of the URL.
let chosenSort: Sort = "shape";

/** "Most similar shape" (rank 1) or "Best physical fit" (most checks in band): a link to that pair. */
function Callout(props: {
  kind: "shape" | "fit";
  match: AnalogMatch;
  candidate: EarthCandidate;
  earth: EarthDocument;
  href: string;
}) {
  const { kind, match, candidate, earth } = props;
  return (
    <a className={`callout callout-${kind}`} href={props.href}>
      <span className="callout-label">
        {kind === "shape" ? "Most similar shape" : "Best physical fit"} · rank {match.overall_rank}
      </span>
      <span className="callout-site">
        {siteName(earth, candidate.site)} <span className="data callout-cosine">{match.cosine.toFixed(3)}</span>
      </span>
      <span className="callout-checks">
        <CheckCount within={checksWithin(match)} total={match.within.length} /> physical checks in band
      </span>
    </a>
  );
}

function formatCoordinate(value: number, positive: string, negative: string): string {
  return `${Math.abs(value).toFixed(3)}° ${value >= 0 ? positive : negative}`;
}

export function AnalogsPage({ region, patch }: { region: string; patch: string }) {
  const loaded = useData(`analogs:${region}/${patch}`, () => loadPatchAnalogs(region, patch));
  const [active, setActive] = useState<string | null>(null);
  const [sort, setSort] = useState<Sort>(chosenSort);
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
  const ordered = useMemo(
    () =>
      sort === "shape"
        ? rows
        : [...rows].sort(
            (a, b) => checksWithin(b.match) - checksWithin(a.match) || a.match.overall_rank - b.match.overall_rank,
          ),
    [rows, sort],
  );

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
  const first = rows[0];
  const fitMatch = bestFit(rows.map((row) => row.match));
  const fit = rows.find((row) => row.match === fitMatch);
  const showFit = fit && first && fit !== first;
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
          {first && (
            <div className={`callouts${showFit ? " has-fit" : ""}`}>
              <Callout
                kind="shape"
                match={first.match}
                candidate={first.candidate}
                earth={earth}
                href={links.pair(patches.region.slug, record.slug, first.candidate.id)}
              />
              {showFit && (
                <Callout
                  kind="fit"
                  match={fit.match}
                  candidate={fit.candidate}
                  earth={earth}
                  href={links.pair(patches.region.slug, record.slug, fit.candidate.id)}
                />
              )}
              <p className="callout-note">
                Cosine says the model sees a similar shape; it is not a percentage. The {first.match.within.length}{" "}
                physical checks say whether slope, relief and roughness actually match. Read both.
              </p>
            </div>
          )}
          <section className="card" aria-labelledby="map-title">
            <h2 id="map-title">Where the matches are</h2>
            <EarthMap
              markers={markers}
              active={active}
              onActive={onActive}
              label={`Map of the ${rows.length} Earth matches, numbered by rank. The table below lists the same places.`}
            />
          </section>

          <div className="sort-bar">
            <span className="map-mode-label" id="sort-label">
              Sort by
            </span>
            <div className="segmented" role="radiogroup" aria-labelledby="sort-label">
              {SORTS.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    name="analog-sort"
                    value={option.value}
                    checked={sort === option.value}
                    onChange={() => {
                      chosenSort = option.value;
                      setSort(option.value);
                    }}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>
          <div className="table-scroll">
            <table className="patch-table">
              <caption aria-live="polite">
                All {rows.length} matches, {SORTS.find((option) => option.value === sort)!.caption}. Every match is
                shown, including weak ones.
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
              <tbody
                onMouseOver={point}
                onFocus={point}
                onMouseLeave={() => setActive(null)}
                onBlur={() => setActive(null)}
              >
                {ordered.map(({ match, candidate }) => (
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
                      {match === first?.match && <span className="row-tag tag-shape">Most similar shape</span>}
                      {showFit && match === fit.match && <span className="row-tag tag-fit">Best physical fit</span>}
                    </th>
                    <td className="number">{match.cosine.toFixed(3)}</td>
                    <td>
                      <CheckCount within={checksWithin(match)} total={match.within.length} />
                    </td>
                    <td>
                      {formatCoordinate(candidate.latitude, "N", "S")},{" "}
                      {formatCoordinate(candidate.longitude, "E", "W")}
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
