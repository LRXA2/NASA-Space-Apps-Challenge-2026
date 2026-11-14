import { memo, useEffect, useState } from "react";
import type { SyntheticEvent } from "react";
import { Loading, PageMessage } from "../components/PageState";
import { PatchMap } from "../components/PatchMap";
import type { ClassMode } from "../components/PatchMap";
import { StatusBadge } from "../components/StatusBadge";
import { DataError, loadPatches, loadRegions } from "../data/loaders";
import type { PatchesDocument } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

const MODES: { value: ClassMode; label: string }[] = [
  { value: "rover", label: "Rover class" },
  { value: "walking", label: "Crew-on-foot class" },
];

// The chosen colour mode stays when the user changes region. It is not part of the URL.
let chosenMode: ClassMode = "rover";

/** Load one region's patch list. An unknown region gives a readable error, not an empty page. */
export async function loadRegionPatches(region: string): Promise<PatchesDocument> {
  const entry = (await loadRegions()).regions.find((candidate) => candidate.slug === region);
  if (!entry) throw new DataError(`No region named "${region}" is in this build.`);
  return loadPatches(entry.patches_file);
}

const PAGE_SIZE = 50;

/**
 * The patch list, 50 rows a page. It is the keyboard route to every patch, and it opens the same URLs as the map.
 * Paged because the largest region has 841 patches: one long table made the page over 12,000 px tall.
 */
const PatchTable = memo(function PatchTable(props: {
  listing: PatchesDocument;
  onActive: (patch: string | null) => void;
}) {
  const { listing, onActive } = props;
  const [page, setPage] = useState(0);
  const pages = Math.max(1, Math.ceil(listing.patches.length / PAGE_SIZE));
  const first = page * PAGE_SIZE;
  const rows = listing.patches.slice(first, first + PAGE_SIZE);
  const range = `${first + 1}–${first + rows.length} of ${listing.patches.length}`;
  const point = (event: SyntheticEvent) => onActive((event.target as HTMLElement).closest("tr")?.dataset.patch ?? null);
  const clear = () => onActive(null);
  return (
    <div className="table-scroll">
      <table className="patch-table">
        <caption aria-live="polite">
          {pages > 1 ? `Patches ${range}, in source order` : `All ${listing.patches.length} patches, in source order`}
        </caption>
        <thead>
          <tr>
            <th scope="col">Patch</th>
            <th scope="col">Rover</th>
            <th scope="col">Crew on foot</th>
            <th scope="col" className="number">
              Median slope
            </th>
          </tr>
        </thead>
        <tbody onMouseOver={point} onFocus={point} onMouseLeave={clear} onBlur={clear}>
          {rows.map((patch) => (
            <tr key={patch.slug} data-patch={patch.slug}>
              <th scope="row">
                <a href={links.patch(listing.region.slug, patch.slug)}>
                  Row {patch.top_row}, column {patch.top_col}
                </a>
              </th>
              <td>
                <StatusBadge value={patch.rover.class} />
              </td>
              <td>
                <StatusBadge value={patch.walking.class} />
              </td>
              <td className="number">{patch.physical.slope_median_deg.toFixed(1)}°</td>
            </tr>
          ))}
        </tbody>
      </table>
      {pages > 1 && (
        <nav className="pager" aria-label="Patch table pages">
          <button type="button" onClick={() => setPage(page - 1)} disabled={page === 0}>
            Previous {PAGE_SIZE}
          </button>
          <span>
            Page {page + 1} of {pages}
          </span>
          <button type="button" onClick={() => setPage(page + 1)} disabled={page === pages - 1}>
            Next {Math.min(PAGE_SIZE, listing.patches.length - first - rows.length) || PAGE_SIZE}
          </button>
        </nav>
      )}
    </div>
  );
});

export function RegionPage({ region }: { region: string }) {
  const patches = useData(`region:${region}`, () => loadRegionPatches(region));
  const catalogue = useData("regions", loadRegions);
  const [mode, setMode] = useState<ClassMode>(chosenMode);
  const [active, setActive] = useState<string | null>(null);
  const name = patches.status === "ready" ? patches.data.region.name : "Region";
  useEffect(() => {
    document.title = `${name} · Lunar Analog Finder`;
  }, [name]);

  if (patches.status === "loading") return <Loading what="region" />;
  if (patches.status === "error") {
    return (
      <PageMessage title="This region is unavailable" tone="error">
        {patches.message} <a href={links.regions()}>Go to the region list.</a>
      </PageMessage>
    );
  }
  const listing = patches.data;
  const shown = active ? listing.patches.find((patch) => patch.slug === active) : undefined;
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › {listing.region.name}
      </nav>
      {catalogue.status === "ready" && (
        <nav className="region-switch" aria-label="Change region">
          {catalogue.data.regions.map((entry) => (
            <a
              key={entry.slug}
              href={links.region(entry.slug)}
              aria-current={entry.slug === listing.region.slug ? "page" : undefined}
            >
              {entry.name}
            </a>
          ))}
        </nav>
      )}
      <h1>{listing.region.name}</h1>
      <p className="lede">
        {listing.patches.length} terrain {listing.patches.length === 1 ? "patch" : "patches"} in this build. Each is{" "}
        {listing.patch_size_m} m × {listing.patch_size_m} m on a {listing.spacing_m} m grid.
      </p>
      <section className="card" aria-labelledby="map-title">
        <div className="panel-head">
          <h2 id="map-title">{mode === "rover" ? "Rover class" : "Crew-on-foot class"} by patch</h2>
          <div className="map-mode">
            <span className="map-mode-label" id="map-mode-label">
              Colour the map by
            </span>
            <div className="segmented" role="radiogroup" aria-labelledby="map-mode-label">
              {MODES.map((option) => (
                <label key={option.value}>
                  <input
                    type="radio"
                    name="map-mode"
                    value={option.value}
                    checked={mode === option.value}
                    onChange={() => {
                      chosenMode = option.value;
                      setMode(option.value);
                    }}
                  />
                  {option.label}
                </label>
              ))}
            </div>
          </div>
        </div>
        <PatchMap region={listing.region} patches={listing.patches} mode={mode} active={active} onActive={setActive} />
        <p className="map-readout">
          {shown ? (
            <>
              <span>
                Row {shown.top_row}, column {shown.top_col}
              </span>
              <span>
                Rover: <StatusBadge value={shown.rover.class} />
              </span>
              <span>
                Crew on foot: <StatusBadge value={shown.walking.class} />
              </span>
            </>
          ) : (
            <span className="muted">
              Point at a square, or move through the table, to see a patch's classes. Select a square to open the patch.
            </span>
          )}
        </p>
        <p className="muted map-note">
          Each square is one patch, placed by its row and column in the stored grid. Row 0 is at the top. The grid is
          not a north-up map.
        </p>
      </section>
      <PatchTable key={listing.region.slug} listing={listing} onActive={setActive} />
      <p className="muted source-line">
        Classes are predictions from a CNN trained on Earth terrain. They are not safety certifications.
      </p>
    </>
  );
}
