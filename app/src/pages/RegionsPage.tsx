import { useEffect } from "react";
import { Loading, PageMessage } from "../components/PageState";
import { PolarOverview } from "../components/PolarOverview";
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
  const hasMap = entries.some((entry) => entry.extent_m != null);
  const total = entries.reduce((sum, entry) => sum + entry.exported_patch_count, 0);
  return (
    <>
      <h1>Lunar south-pole regions</h1>
      <p className="lede">
        Terrain patches near the lunar south pole, with rover and on-foot predictions and the closest Earth terrain for
        each patch. Choose a region.
      </p>
      <p className="lede">
        This build holds {entries.length} {entries.length === 1 ? "region" : "regions"} and {total.toLocaleString("en")}{" "}
        terrain {total === 1 ? "patch" : "patches"}.
      </p>
      {entries.length === 0 ? (
        <p>No regions have been exported yet.</p>
      ) : (
        <>
          <PolarOverview regions={entries} />

        <ul className="link-list">
          {entries.map((entry, index) => (
            <li key={entry.slug}>
              <a href={links.region(entry.slug)}>
                {hasMap && <span className="region-number">{index + 1}</span>}
                {entry.name}
              </a>
              <span className="muted">
                {entry.exported_patch_count} of {entry.source_patch_count} terrain patches in this build
              </span>
            </li>
          ))}
        </ul>
        </>
      )}
      <p>
        <a href={links.environment()}>Environment assessments for all 17 Artemis candidate regions</a>, including the ten
        without terrain data.
      </p>
      <p className="muted source-line">
        Source: inference run <code>{source.run_id}</code>. {source.claim_boundary}. Pipeline run{" "}
        <code>{regions.data.pipeline.run_id}</code>: {regions.data.pipeline.caveat}
      </p>
    </>
  );
}
