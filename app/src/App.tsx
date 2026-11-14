import { useEffect } from "react";
import { PageMessage } from "./components/PageState";
import { AnalogsPage } from "./pages/AnalogsPage";
import { EnvironmentPage, ScenarioPage } from "./pages/EnvironmentPage";
import { PairPage } from "./pages/PairPage";
import { PatchPage } from "./pages/PatchPage";
import { RegionPage } from "./pages/RegionPage";
import { RegionsPage } from "./pages/RegionsPage";
import { UploadPage } from "./pages/UploadPage";
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
        <nav className="topbar-links" aria-label="Sections">
          <a href={links.regions()}>Regions</a>
          <a href={links.environment()}>Environment</a>
          <a href={links.upload()}>Try your own data</a>
        </nav>
        <span className="topbar-note">Precomputed results · Earth and Moon only</span>
      </header>
      <main className="page">
        {route.name === "regions" && <RegionsPage />}
        {route.name === "region" && <RegionPage key={route.region} region={route.region} />}
        {route.name === "patch" && (
          <PatchPage key={`${route.region}/${route.patch}`} region={route.region} patch={route.patch} />
        )}
        {route.name === "analogs" && (
          <AnalogsPage key={`${route.region}/${route.patch}`} region={route.region} patch={route.patch} />
        )}
        {route.name === "pair" && (
          <PairPage
            key={`${route.region}/${route.patch}/${route.candidate}`}
            region={route.region}
            patch={route.patch}
            candidate={route.candidate}
          />
        )}
        {route.name === "environment" && <EnvironmentPage />}
        {route.name === "scenario" && <ScenarioPage key={route.scenario} scenario={route.scenario} />}
        {route.name === "upload" && <UploadPage />}
        {route.name === "not-found" && (
          <PageMessage title="Page not found" tone="error">
            No page exists at <code>{route.path}</code>. <a href={links.regions()}>Go to the region list.</a>
          </PageMessage>
        )}
      </main>
    </div>
  );
}
