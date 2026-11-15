import { useEffect, useLayoutEffect } from "react";
import { PageMessage } from "./components/PageState";
import { Footer, Header } from "./components/Shell";
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
  // A hash change keeps the old scroll position, so a new page would open part-way down. Start each page at the top.
  const page = JSON.stringify(route);
  useLayoutEffect(() => {
    window.scrollTo({ top: 0, left: 0, behavior: "instant" });
  }, [page]);
  useEffect(() => {
    if (notFound) document.title = "Page not found · LEAP";
  }, [notFound]);
  return (
    <div className="shell">
      <Header route={route} />
      <main className={`page${route.name === "regions" ? " page-home" : ""}`}>
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
      <Footer />
    </div>
  );
}
