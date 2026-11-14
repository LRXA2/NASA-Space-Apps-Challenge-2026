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

/** The patch list. It is the keyboard route to every patch, and it opens the same URLs as the map. */
const PatchTable = memo(function PatchTable(props: {
  listing: PatchesDocument;
  onActive: (patch: string | null) => void;
}) {
  const { listing, onActive } = props;
  const point = (event: SyntheticEvent) => onActive((event.target as HTMLElement).closest("tr")?.dataset.patch ?? null);
  const clear = () => onActive(null);
  return (
    <div className="table-scroll">
      <table className="patch-table">
        <caption>All {listing.patches.length} patches, in source order</caption>
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
          {listing.patches.map((patch) => (
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
      <div className="map-mode" role="radiogroup" aria-label="Colour the map by">
        <span className="map-mode-label">Colour the map by</span>
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
        Each square is one patch, placed by its row and column in the stored grid. Row 0 is at the top. The grid is not
        a north-up map.
      </p>
      <PatchTable listing={listing} onActive={setActive} />
      <p className="muted source-line">
        Classes are predictions from a CNN trained on Earth terrain. They are not safety certifications.
      </p>
    </>
  );
}
