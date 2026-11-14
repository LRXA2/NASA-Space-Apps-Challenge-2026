import { loadRegions } from "../data/loaders";
import { useData } from "../data/useData";
import { DEMO } from "../demo";
import { links } from "../router";
import type { Route } from "../router";

/** Horizon line, Earth as a gold half-disc, three stars. */
export function Logo() {
  return (
    <span className="brand-logo" aria-hidden="true">
      <svg width="28" height="28" viewBox="0 0 28 28" fill="none">
        <path d="M2 19.5h24" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
        <path d="M10.6 19.5a3.4 3.4 0 016.8 0z" fill="var(--earth)" />
        <circle cx="7" cy="7" r="1.3" fill="currentColor" />
        <circle cx="20.5" cy="5" r="0.9" fill="currentColor" />
        <circle cx="23" cy="12" r="0.7" fill="currentColor" opacity=".7" />
      </svg>
    </span>
  );
}

type Section = "regions" | "environment" | "upload" | null;

function sectionOf(route: Route): Section {
  switch (route.name) {
    case "regions":
    case "region":
    case "patch":
    case "analogs":
    case "pair":
      return "regions";
    case "environment":
    case "scenario":
      return "environment";
    case "upload":
      return "upload";
    default:
      return null;
  }
}

/** Which demo step the route is on, 0 to 3, or -1 when the page is not on the demo path. */
function demoStep(route: Route): number {
  if (!("region" in route) || route.region !== DEMO.region) return -1;
  if (route.name === "region") return 0;
  if (route.patch !== DEMO.patch) return -1;
  if (route.name === "patch") return 1;
  if (route.name === "analogs") return 2;
  if (route.name === "pair" && route.candidate === DEMO.candidate) return 3;
  return -1;
}

const STEPS = [
  { label: "Region", href: links.region(DEMO.region) },
  { label: "Patch", href: links.patch(DEMO.region, DEMO.patch) },
  { label: "Earth analogs", href: links.analogs(DEMO.region, DEMO.patch) },
  { label: "Best match", href: links.pair(DEMO.region, DEMO.patch, DEMO.candidate) },
];

function Check() {
  return (
    <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
      <path
        d="M2.5 6.3l2.2 2.2 4.8-5"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

/** The four demo steps in one pill. Steps before the current one show a check. */
export function DemoPath({ route }: { route: Route }) {
  const current = demoStep(route);
  return (
    <nav className="demo-path" aria-label="Demo path">
      <ol>
        {STEPS.map((step, index) => {
          const done = current >= 0 && index < current;
          const isCurrent = index === current;
          return (
            <li key={step.label} className={isCurrent ? "is-current" : undefined}>
              <a
                className={`demo-step${done ? " is-done" : ""}`}
                href={step.href}
                aria-current={isCurrent ? "step" : undefined}
              >
                <span className="demo-dot" aria-hidden="true">
                  {done ? <Check /> : index + 1}
                </span>
                <span className="demo-label">{step.label}</span>
                {done && <span className="visually-hidden">, done</span>}
              </a>
            </li>
          );
        })}
      </ol>
    </nav>
  );
}

export function Header({ route }: { route: Route }) {
  const section = sectionOf(route);
  const nav: { key: Section; label: string; href: string }[] = [
    { key: "regions", label: "Regions", href: links.regions() },
    { key: "environment", label: "Environment", href: links.environment() },
    { key: "upload", label: "Try your own data", href: links.upload() },
  ];
  return (
    <header className="topbar">
      <a className="brand" href={links.regions()}>
        <Logo />
        <span className="brand-text">
          Lunar Analog Finder
          <span className="brand-sub">NASA Space Apps 2026</span>
        </span>
      </a>
      <nav className="topbar-links" aria-label="Sections">
        {nav.map((item) => (
          <a key={item.label} href={item.href} aria-current={item.key === section ? "page" : undefined}>
            {item.label}
          </a>
        ))}
      </nav>
      <DemoPath route={route} />
    </header>
  );
}

export function Footer() {
  const regions = useData("regions", loadRegions);
  return (
    <footer className="footer">
      <div className="footer-inner">
        <p className="footer-name">Lunar Analog Finder · NASA Space Apps Challenge 2026</p>
        {regions.status === "ready" && (
          <p className="footer-runs">
            Inference run <code>{regions.data.source.run_id}</code> · pipeline run{" "}
            <code>{regions.data.pipeline.run_id}</code>
          </p>
        )}
        <p className="footer-note">
          Precomputed results · Earth and Moon only. Star positions from the d3-celestial catalogue (BSD licence).
        </p>
      </div>
    </footer>
  );
}
