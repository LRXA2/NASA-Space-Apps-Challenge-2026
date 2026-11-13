import { useEffect } from "react";
import { PageMessage } from "./components/PageState";
import { PatchPage } from "./pages/PatchPage";
import { RegionPage } from "./pages/RegionPage";
import { RegionsPage } from "./pages/RegionsPage";
import { links, useRoute } from "./router";

export function App() {
  const route = useRoute();
  const notFound = route.name === "not-found";
  useEffect(() => {
    if (notFound) document.title = "Page not found · Lunar Analog Finder";
  }, [notFound]);
  return (
    <div className="shell">
      <header className="topbar">
        <a className="brand" href={links.regions()}>
          Lunar Analog Finder
        </a>
        <span className="topbar-note">Precomputed results · Earth and Moon only</span>
      </header>
      <main className="page">
        {route.name === "regions" && <RegionsPage />}
        {route.name === "region" && <RegionPage key={route.region} region={route.region} />}
        {route.name === "patch" && (
          <PatchPage key={`${route.region}/${route.patch}`} region={route.region} patch={route.patch} />
        )}
        {route.name === "not-found" && (
          <PageMessage title="Page not found" tone="error">
            No page exists at <code>{route.path}</code>. <a href={links.regions()}>Go to the region list.</a>
          </PageMessage>
        )}
      </main>
    </div>
  );
}
