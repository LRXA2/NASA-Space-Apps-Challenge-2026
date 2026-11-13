import { useEffect } from "react";
import { Loading, PageMessage } from "../components/PageState";
import { loadRegions } from "../data/loaders";
import { useData } from "../data/useData";
import { links } from "../router";

export function RegionsPage() {
  const regions = useData("regions", loadRegions);
  useEffect(() => {
    document.title = "Regions · Lunar Analog Finder";
  }, []);

  if (regions.status === "loading") return <Loading what="regions" />;
  if (regions.status === "error") {
    return (
      <PageMessage title="Region data is unavailable" tone="error">
        {regions.message}
      </PageMessage>
    );
  }
  const { source, regions: entries } = regions.data;
  const total = entries.reduce((sum, entry) => sum + entry.exported_patch_count, 0);
  return (
    <>
      <h1>Lunar south-pole regions</h1>
      <p className="lede">
        Terrain patches near the lunar south pole, with rover and on-foot predictions for each patch. Choose a region.
      </p>
      <p className="lede">
        This build holds {entries.length} {entries.length === 1 ? "region" : "regions"} and {total.toLocaleString("en")}{" "}
        terrain {total === 1 ? "patch" : "patches"}.
      </p>
      {entries.length === 0 ? (
        <p>No regions have been exported yet.</p>
      ) : (
        <ul className="link-list">
          {entries.map((entry) => (
            <li key={entry.slug}>
              <a href={links.region(entry.slug)}>{entry.name}</a>
              <span className="muted">
                {entry.exported_patch_count} of {entry.source_patch_count} terrain patches in this build
              </span>
            </li>
          ))}
        </ul>
      )}
      <p className="muted source-line">
        Source: inference run <code>{source.run_id}</code>. {source.claim_boundary}.
      </p>
    </>
  );
}
