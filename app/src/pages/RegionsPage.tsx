import { useEffect, useRef } from "react";
import { AssessmentBadge, gatesOff } from "../components/AssessmentView";
import { CheckCount } from "../components/CheckCount";
import { colorAt, legendGradient, niceCeiling } from "../components/colorScales";
import { Limitations } from "../components/Limitations";
import { Loading, PageMessage } from "../components/PageState";
import { PolarOverview } from "../components/PolarOverview";
import { SkyPanel } from "../components/SkyPanel";
import { ToneIcon } from "../components/StatusBadge";
import {
  bestFit,
  candidateOf,
  checksWithin,
  loadEarthTerrain,
  loadMoonTerrain,
  loadPatchAnalogs,
  siteName,
} from "../data/analogs";
import type { PatchAnalogs } from "../data/analogs";
import { DataError, loadEnvironment, loadRegions } from "../data/loaders";
import type {
  AnalogMatch,
  Assessment,
  EnvironmentDocument,
  RegionEntry,
  Scenario,
  TerrainChannel,
} from "../data/types";
import { useData } from "../data/useData";
import { DEMO } from "../demo";
import { links } from "../router";

const LIMITS = [
  "Rover and on-foot classes are predictions from a CNN trained on Earth terrain, not measured EVA performance or safety.",
  "Environment checks are region-wide scenarios built mostly from assumed inputs. Gate thresholds are project test values, not NASA limits.",
  "Cosine compares shapes the model learned. It is not a percentage or a suitability rating.",
];

const WORDS = ["no", "one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten"];
const word = (count: number) => WORDS[count] ?? count.toLocaleString("en");
const capital = (text: string) => text.charAt(0).toUpperCase() + text.slice(1);

function Arrow() {
  return (
    <svg width="18" height="18" viewBox="0 0 18 18" fill="none" aria-hidden="true" style={{ flex: "none" }}>
      <path
        d="M3 9h11M10 4.6L14.4 9 10 13.4"
        stroke="currentColor"
        strokeWidth="1.8"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
    </svg>
  );
}

async function loadHome() {
  const [regions, environment] = await Promise.all([loadRegions(), loadEnvironment().catch(() => null)]);
  return { regions, environment };
}

// ───────── Hero ─────────

function Hero(props: {
  entries: RegionEntry[];
  artemis: number | null;
  sites: number;
  perPatch: number;
  start: RegionEntry;
}) {
  const { entries, artemis, sites, perPatch, start } = props;
  const total = entries.reduce((sum, entry) => sum + entry.exported_patch_count, 0);
  const size = entries[0]?.patch_size_m;
  const spacing = entries[0]?.spacing_m;
  return (
    <section className="home-hero" aria-labelledby="home-title">
      <div className="hero-copy">
        <h1 id="home-title" className="display">
          Which <span className="text-earth">Earth terrain</span> stands in for a{" "}
          <span className="text-moon">lunar landing site</span>?
        </h1>
        <p className="lede">
          Pick a south-pole region. See whether a rover and a crew on foot can work each{" "}
          {size ? <b className="data">{size} m</b> : "terrain"} patch, which of {word(sites)} Earth field sites
          resembles it, and where the analogy breaks.
        </p>
        <div className="cta">
          <a className="button" href={links.region(start.slug)}>
            Start at {start.name} <Arrow />
          </a>
          {artemis !== null && (
            <a className="button-secondary" href={links.environment()}>
              Environment checks for all {artemis} regions
            </a>
          )}
        </div>
      </div>
      <ul className="hero-stats" aria-label="This build at a glance">
        <li>
          <span className="hero-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="8.5" stroke="currentColor" strokeWidth="1.5" />
              <circle cx="11" cy="11" r="4.5" stroke="currentColor" strokeWidth="1.5" strokeDasharray="2 2" />
              <circle cx="11" cy="11" r="1.6" fill="currentColor" />
            </svg>
          </span>
          <span className="hero-value">
            {entries.length}
            {artemis !== null && <small>of {artemis}</small>}
          </span>
          <span className="hero-note">Artemis III candidate regions with terrain</span>
        </li>
        {size && (
          <li>
            <span className="hero-icon" aria-hidden="true">
              <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
                <rect x="3" y="3" width="16" height="16" rx="2" stroke="currentColor" strokeWidth="1.5" />
                <path d="M8.3 3v16M13.7 3v16M3 8.3h16M3 13.7h16" stroke="currentColor" strokeWidth="1.2" />
              </svg>
            </span>
            <span className="hero-value">{size} m</span>
            <span className="hero-note">
              Patch: {spacing ? `${size / spacing} × ${size / spacing} cells at ${spacing} m · ` : ""}
              {total.toLocaleString("en")} patches
            </span>
          </li>
        )}
        <li className="is-earth">
          <span className="hero-icon" aria-hidden="true">
            <svg width="22" height="22" viewBox="0 0 22 22" fill="none">
              <circle cx="11" cy="11" r="8.5" stroke="currentColor" strokeWidth="1.5" />
              <path
                d="M2.5 11h17M11 2.5c2.6 2.4 3.8 5.3 3.8 8.5s-1.2 6.1-3.8 8.5c-2.6-2.4-3.8-5.3-3.8-8.5S8.4 4.9 11 2.5z"
                stroke="currentColor"
                strokeWidth="1.3"
              />
            </svg>
          </span>
          <span className="hero-value">
            {sites}
            <small>sites</small>
          </span>
          <span className="hero-note">Earth field sites · {perPatch} matches per patch</span>
        </li>
      </ul>
    </section>
  );
}

// ───────── Region cards ─────────

/** One assessment on a card: a score with a small Pass label, or the status with "no score". Never combined. */
function CardAssessment(props: { title: string; assessment: Assessment | undefined; gatesOff: boolean }) {
  const { title, assessment } = props;
  return (
    <span className="card-assessment">
      <span className="card-assessment-title">{title}</span>
      {!assessment ? (
        <span className="no-score">No environment data</span>
      ) : assessment.status === "Pass" && assessment.score !== null ? (
        <>
          <span className="card-score">{assessment.score.toFixed(1)}</span>
          {props.gatesOff ? (
            <AssessmentBadge status="Pass" gatesOff />
          ) : (
            <span className="card-pass">
              <ToneIcon tone="good" />
              Pass
            </span>
          )}
        </>
      ) : (
        <>
          <AssessmentBadge status={assessment.status} gatesOff={props.gatesOff} />
          {assessment.status !== "Pass" && <span className="no-score">No score</span>}
        </>
      )}
    </span>
  );
}

function MixBar({ counts }: { counts: NonNullable<RegionEntry["rover_class_counts"]> }) {
  const total = counts.operable + counts.marginal + counts.non_operable || 1;
  const share = (value: number) => `${((value / total) * 100).toFixed(1)}%`;
  return (
    <>
      <span className="mix-key">
        <span>Rover terrain</span>
        <span className="data">{Math.round((counts.operable / total) * 100)}% operable</span>
      </span>
      <span className="mix-bar" aria-hidden="true">
        <span className="class-good" style={{ width: share(counts.operable) }} />
        <span className="class-warning" style={{ width: share(counts.marginal) }} />
        <span className="class-critical" style={{ width: share(counts.non_operable) }} />
      </span>
      <span className="visually-hidden">
        {counts.operable} operable, {counts.marginal} marginal, {counts.non_operable} non-operable patches.
      </span>
    </>
  );
}

function RegionCard(props: {
  entry: RegionEntry;
  number: number;
  scenario: Scenario | undefined;
  environment: EnvironmentDocument | null;
}) {
  const { entry, number, scenario, environment } = props;
  const isDemo = entry.slug === DEMO.region;
  return (
    <li>
      <a className={`region-card${isDemo ? " is-selected" : ""}`} href={links.region(entry.slug)}>
        <span className="region-card-top">
          <span className="region-number">{number}</span>
          {isDemo && <span className="chip">Demo path</span>}
          <span className="region-card-count data">{entry.exported_patch_count} patches</span>
        </span>
        <span className="region-card-name">{entry.name}</span>
        {entry.rover_class_counts && <MixBar counts={entry.rover_class_counts} />}
        <span className="card-assessments">
          <CardAssessment
            title="Operations"
            assessment={scenario?.operations}
            gatesOff={environment ? gatesOff(environment, "operations") : false}
          />
          <CardAssessment
            title="Survival"
            assessment={scenario?.survival}
            gatesOff={environment ? gatesOff(environment, "survival") : false}
          />
        </span>
        <span className="region-card-go" aria-hidden="true">
          Open region <Arrow />
        </span>
      </a>
    </li>
  );
}

function ClassLegend() {
  return (
    <ul className="class-legend" aria-label="Rover class key">
      <li>
        <span className="class-swatch class-good" aria-hidden="true" />
        Operable
      </li>
      <li>
        <span className="class-swatch class-warning" aria-hidden="true" />
        Marginal
      </li>
      <li>
        <span className="class-swatch class-critical" aria-hidden="true" />
        Non-operable
      </li>
    </ul>
  );
}

// ───────── Looks alike, measures different ─────────

/** One slope grid as a small static tile on a shared domain. */
function SlopeTile({ channel, max, label }: { channel: TerrainChannel; max: number; label: string }) {
  const canvas = useRef<HTMLCanvasElement>(null);
  useEffect(() => {
    const context = canvas.current?.getContext("2d");
    if (!context) return;
    const image = context.createImageData(channel.cols, channel.rows);
    channel.values.forEach((value, index) => {
      image.data.set([...colorAt("slope", value / max), 255], index * 4);
    });
    context.putImageData(image, 0, 0);
  }, [channel, max]);
  return (
    <canvas
      ref={canvas}
      className="slope-tile"
      width={channel.cols}
      height={channel.rows}
      role="img"
      aria-label={label}
    />
  );
}

function slopeOf(channels: TerrainChannel[]): TerrainChannel {
  const found = channels.find((entry) => entry.name === "slope_deg");
  if (!found) throw new DataError("The terrain file does not hold slope.");
  return found;
}

function PairTiles({ base, first, fit }: { base: PatchAnalogs; first: AnalogMatch; fit: AnalogMatch }) {
  const loaded = useData(`home-tiles:${base.record.tile_id}`, async () => {
    const [moon, closest, best] = await Promise.all([
      loadMoonTerrain(base.patches, base.record),
      loadEarthTerrain(base.earth, candidateOf(base.earth, first)),
      loadEarthTerrain(base.earth, candidateOf(base.earth, fit)),
    ]);
    return { moon: slopeOf(moon), closest: slopeOf(closest), best: slopeOf(best) };
  });
  if (loaded.status === "loading")
    return (
      <div className="slope-tiles-placeholder" role="status">
        Loading terrain…
      </div>
    );
  if (loaded.status === "error") return <p className="inline-error">Terrain tiles are unavailable. {loaded.message}</p>;
  const { moon, closest, best } = loaded.data;
  // One fitted domain shared by the three tiles, so equal colours mean equal slopes.
  const max = niceCeiling(Math.max(...moon.values, ...closest.values, ...best.values));
  const short = (match: AnalogMatch) =>
    siteName(base.earth, candidateOf(base.earth, match).site).split(/[,(]/)[0].trim();
  const tiles = [
    { key: "moon", who: "Moon", whoClass: "text-moon", name: base.record.slug, mono: true, channel: moon, best: false },
    {
      key: "first",
      who: `Earth · rank ${first.overall_rank}`,
      whoClass: "text-earth",
      name: short(first),
      mono: false,
      channel: closest,
      best: false,
    },
    {
      key: "fit",
      who: `Earth · rank ${fit.overall_rank}`,
      whoClass: "text-earth",
      name: short(fit),
      mono: false,
      channel: best,
      best: true,
    },
  ];
  return (
    <div className="slope-tiles">
      {tiles.map((tile) => (
        <figure key={tile.key} className={tile.best ? "is-best" : undefined}>
          <SlopeTile channel={tile.channel} max={max} label={`Slope of ${tile.who}, ${tile.name}`} />
          <figcaption>
            <span className={`tile-who ${tile.whoClass}`}>{tile.who}</span>
            <span className={tile.mono ? "data" : undefined}>{tile.name}</span>
          </figcaption>
        </figure>
      ))}
      <div className="slope-tiles-legend">
        <span className="legend-bar" style={{ background: legendGradient("slope") }} />
        <span className="legend-ticks">
          <span>Slope 0°</span>
          <span>{max / 2}°</span>
          <span>{max}°</span>
        </span>
      </div>
    </div>
  );
}

function LooksAlike() {
  const loaded = useData(`analogs:${DEMO.region}/${DEMO.patch}`, () => loadPatchAnalogs(DEMO.region, DEMO.patch));
  if (loaded.status !== "ready" || !loaded.data.tile) return null;
  const base = loaded.data;
  const matches = base.tile!.matches;
  const first = matches[0];
  const fit = bestFit(matches);
  if (!first || !fit || fit === first) return null;
  const total = first.within.length;
  const site = (match: AnalogMatch) => siteName(base.earth, candidateOf(base.earth, match).site);
  const shortName = (match: AnalogMatch) => site(match).split(/[,(]/)[0].trim();
  const firstIn = checksWithin(first);
  const rows = [
    { match: first, note: "closest shape" },
    { match: fit, note: "best physical fit" },
  ];
  return (
    <section className="card looks-alike" aria-labelledby="looks-alike-title">
      <div className="looks-alike-copy">
        <h2 id="looks-alike-title" className="section-title">
          Looks alike, measures different
        </h2>
        <p>
          Patch <span className="data">{base.record.slug}</span> in {base.patches.region.name}. Its closest Earth
          terrain by shape is {shortName(first)}, yet {firstIn === 0 ? "none" : `only ${word(firstIn)}`} of the{" "}
          {word(total)} physical checks {firstIn === 1 ? "lands" : "land"} in band. Rank {fit.overall_rank},{" "}
          {shortName(fit)}, is the better stand-in.
        </p>
        <ul className="versus">
          {rows.map(({ match, note }) => (
            <li key={match.overall_rank}>
              <span>
                <span className="text-earth versus-site">{site(match)}</span>
                <span className="versus-rank">
                  Rank {match.overall_rank} of {matches.length} · {note}
                </span>
              </span>
              <span className="data">cosine {match.cosine.toFixed(3)}</span>
              <span>
                <CheckCount within={checksWithin(match)} total={match.within.length} />
                <span className="versus-band"> in band</span>
              </span>
            </li>
          ))}
        </ul>
        <a className="button" href={links.pair(DEMO.region, DEMO.patch, candidateOf(base.earth, fit).id)}>
          Compare the Moon and {shortName(fit)} <Arrow />
        </a>
      </div>
      <PairTiles base={base} first={first} fit={fit} />
    </section>
  );
}

// ───────── Page ─────────

export function RegionsPage() {
  const loaded = useData("home", loadHome);
  useEffect(() => {
    document.title = "Regions · Lunar Analog Finder";
  }, []);

  if (loaded.status === "loading") return <Loading what="regions" />;
  if (loaded.status === "error") {
    return (
      <PageMessage title="Region data is unavailable" tone="error">
        {loaded.message}
      </PageMessage>
    );
  }
  const { regions, environment } = loaded.data;
  const entries = regions.regions;
  if (entries.length === 0) return <PageMessage title="No regions have been exported yet" />;

  const artemis = environment?.scenarios.filter((scenario) => scenario.kind === "artemis") ?? null;
  const bySource = new Map((artemis ?? []).map((scenario) => [scenario.terrain_region, scenario]));
  const failed = new Set(
    entries.filter((entry) => bySource.get(entry.source_id)?.operations.status === "Fail").map((entry) => entry.slug),
  );
  const withTerrain = new Set(entries.map((entry) => entry.source_id));
  const environmentOnly =
    artemis?.filter((scenario) => !scenario.terrain_region || !withTerrain.has(scenario.terrain_region)).length ?? 0;
  const total = entries.reduce((sum, entry) => sum + entry.exported_patch_count, 0);
  const sites = regions.pipeline.earth_sites.length;
  // The demo region, or the first region when this export does not hold it.
  const demo = entries.find((entry) => entry.slug === DEMO.region);

  return (
    <>
      <Hero
        entries={entries}
        artemis={artemis?.length ?? null}
        sites={sites}
        perPatch={sites * regions.pipeline.top_k_per_site}
        start={demo ?? entries[0]}
      />

      <div className="sky-row">
        <SkyPanel />
        <section className="card" aria-labelledby="where-title">
          <div className="panel-head">
            <div>
              <h2 id="where-title">Where the regions are</h2>
              <p className="panel-sub">South polar view · 0° toward Earth</p>
            </div>
          </div>
          <PolarOverview regions={entries} selected={demo?.slug} failed={failed} />
        </section>
      </div>

      <section className="home-regions" aria-labelledby="regions-title">
        <div className="section-head">
          <div>
            <h2 id="regions-title" className="section-title">
              {capital(word(entries.length))} {entries.length === 1 ? "region" : "regions"} with terrain
            </h2>
            <p>
              {total.toLocaleString("en")} patches. Rover classes are predicted by the terrain CNN; Operations and
              Survival are separate 0–100 scores, shown only after a Pass.
            </p>
          </div>
          <ClassLegend />
        </div>
        <ul className="region-cards">
          {entries.map((entry, index) => (
            <RegionCard
              key={entry.slug}
              entry={entry}
              number={index + 1}
              scenario={bySource.get(entry.source_id)}
              environment={environment}
            />
          ))}
          {environmentOnly > 0 && (
            <li>
              <a className="region-card is-more" href={links.environment()}>
                <span className="region-card-name">
                  {environmentOnly} more {environmentOnly === 1 ? "region" : "regions"}
                </span>
                <span className="region-card-text">
                  Environment checks only, no terrain patches yet. Operations and Survival for all {artemis?.length}{" "}
                  regions.
                </span>
                <span className="region-card-go" aria-hidden="true">
                  Environment checks <Arrow />
                </span>
              </a>
            </li>
          )}
        </ul>
      </section>

      {demo && <LooksAlike />}

      <Limitations points={LIMITS} />
      <p className="muted source-line">
        {regions.source.claim_boundary}. {regions.pipeline.caveat}
      </p>
    </>
  );
}
