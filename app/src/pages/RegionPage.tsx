import { useEffect } from "react";
import { Loading, PageMessage } from "../components/PageState";
import { StatusBadge } from "../components/StatusBadge";
import { DataError, loadPatches, loadRegions } from "../data/loaders";
import type { PatchesDocument } from "../data/types";
import { useData } from "../data/useData";
import { links } from "../router";

/** Load one region's patch list. An unknown region gives a readable error, not an empty page. */
export async function loadRegionPatches(region: string): Promise<PatchesDocument> {
  const entry = (await loadRegions()).regions.find((candidate) => candidate.slug === region);
  if (!entry) throw new DataError(`No region named "${region}" is in this build.`);
  return loadPatches(entry.patches_file);
}

export function RegionPage({ region }: { region: string }) {
  const patches = useData(`region:${region}`, () => loadRegionPatches(region));
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
  return (
    <>
      <nav className="crumbs" aria-label="Breadcrumb">
        <a href={links.regions()}>Regions</a> › {listing.region.name}
      </nav>
      <h1>{listing.region.name}</h1>
      <p className="lede">
        {listing.patches.length} terrain {listing.patches.length === 1 ? "patch" : "patches"} in this build. Each is{" "}
        {listing.patch_size_m} m × {listing.patch_size_m} m on a {listing.spacing_m} m grid.
      </p>
      <table className="patch-table">
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
        <tbody>
          {listing.patches.map((patch) => (
            <tr key={patch.slug}>
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
      <p className="muted source-line">
        Classes are predictions from a CNN trained on Earth terrain. They are not safety certifications.
      </p>
    </>
  );
}
