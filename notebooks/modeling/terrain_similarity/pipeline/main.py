"""Run the saved terrain CNN on prepared lunar patches without Jupyter."""

from __future__ import annotations

import argparse
import json
import re
import subprocess
from dataclasses import asdict
from pathlib import Path
from typing import TypedDict

import numpy as np
import pandas as pd
import torch
from rasterio.warp import transform

from notebooks.modeling.terrain_similarity.pipeline.artifacts import (
    ArtifactConfig,
    TerrainModel,
)
from notebooks.modeling.terrain_similarity.similarity_cnn import cosine_top_k
from notebooks.modeling.terrain_similarity.terrain_dataset import FEATURES
from notebooks.shared.inspection import file_hash
from notebooks.shared.moon_tiles import build_tile_table
from notebooks.shared.processing import Run
from notebooks.shared.retrieval_analysis import terrain_discrepancies

METRIC_LABELS = [
    "Median slope (degrees)",
    "P90 slope (degrees)",
    "Relief (m)",
    "Plane residual (fraction)",
    "Median local SD (m)",
]


class SiteComparison(TypedDict):
    moon_site: str
    earth_site: str
    direction: str
    moon_patch_count: int
    earth_patch_count: int
    top_k: int
    median_best_patch_cosine: float
    mean_best_patch_cosine: float
    median_top1_relief_difference_m: float
    median_top1_slope_p90_difference_deg: float
    queries_with_all_five_checks_in_top_k: int
    fraction_queries_with_all_five_checks_in_top_k: float
    distinct_top1_earth_patches: int
    maximum_replay_embedding_difference: float
    interpretation: str


def compare_sites(
    terrain: TerrainModel,
    moon_site: str,
    earth_site: str,
    top_k: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, SiteComparison]:
    """Compare every prepared lunar patch against only the requested Earth region."""
    moon = resolve_site(terrain.patches, "moon", moon_site)
    earth = resolve_site(terrain.patches, "earth", earth_site)
    selected = terrain.patches.loc[
        ((terrain.patches.body == "moon") & (terrain.patches.region == moon))
        | ((terrain.patches.body == "earth") & (terrain.patches.region == earth))
    ].sort_index()
    query_ids = tuple(selected.index[selected.body == "moon"])
    earth_count = int((selected.body == "earth").sum())
    if type(top_k) is not int or not 1 <= top_k <= earth_count:
        raise ValueError(
            f"top_k must be between 1 and {earth_count} for this Earth site"
        )
    vectors = terrain.vectors[terrain.patches.index.get_indexer(selected.index)]
    query_vectors = terrain.encode(list(query_ids))
    saved_queries = terrain.vectors[terrain.patches.index.get_indexer(query_ids)]
    if not np.allclose(query_vectors, saved_queries, atol=1e-5, rtol=0):
        raise ValueError(
            "Saved query embeddings disagree with the model and preprocessing"
        )
    matches, physical = retrieve_matches(
        selected, vectors, query_ids, query_vectors, top_k
    )
    first = matches.loc[matches["rank"] == 1]
    passes = matches.physical_checks_within_band.eq(5).groupby(matches.query_id).any()
    summary: SiteComparison = {
        "moon_site": moon,
        "earth_site": earth,
        "direction": "moon_to_earth_within_selected_site",
        "moon_patch_count": len(query_ids),
        "earth_patch_count": earth_count,
        "top_k": top_k,
        "median_best_patch_cosine": float(first.cosine_similarity.median()),
        "mean_best_patch_cosine": float(first.cosine_similarity.mean()),
        "median_top1_relief_difference_m": float(first.delta_relief_m.abs().median()),
        "median_top1_slope_p90_difference_deg": float(
            first.delta_slope_p90_deg.abs().median()
        ),
        "queries_with_all_five_checks_in_top_k": int(passes.sum()),
        "fraction_queries_with_all_five_checks_in_top_k": float(passes.mean()),
        "distinct_top1_earth_patches": int(first.candidate_id.nunique()),
        "maximum_replay_embedding_difference": float(
            np.abs(query_vectors - saved_queries).max()
        ),
        "interpretation": "Directed patch matching within these sites; cosine is not a percentage, "
        "region-wide equivalence, validated accuracy or practical suitability.",
    }
    return matches, physical, summary


def lunar_tile_ids(patches: pd.DataFrame) -> pd.Series:
    """Shared `moon_tiles` ID of every prepared lunar patch, indexed by patch ID."""
    _, mapping = build_tile_table(similarity=patches.rename_axis("patch_id").reset_index())
    return mapping.set_index("patch_id")["tile_id"]


def match_tiles(
    terrain: TerrainModel,
    tile_ids: list[str],
    earth_sites: list[str] | None = None,
    top_k: int = 3,
) -> tuple[pd.DataFrame, pd.DataFrame, dict]:
    """Match chosen lunar tiles against each Earth site, keeping top_k per site.

    Ranking within each site is unchanged from `compare_sites`; `overall_rank`
    orders a tile's matches across all sites by cosine. Sites with fewer than
    top_k prepared patches return all of them.
    """
    if not tile_ids or len(set(tile_ids)) != len(tile_ids):
        raise ValueError("Choose at least one unique lunar tile ID")
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    tiles = lunar_tile_ids(terrain.patches)
    patch_by_tile = pd.Series(tiles.index, index=tiles.to_numpy())
    unknown = sorted(set(tile_ids) - set(patch_by_tile.index))
    if unknown:
        raise ValueError(
            f"{len(unknown)} tile IDs have no prepared lunar patch in this view, "
            f"e.g. {', '.join(unknown[:3])}"
        )
    patches = terrain.patches
    available = sorted(patches.loc[patches.body == "earth", "region"].unique())
    sites = (
        available
        if earth_sites is None
        else [resolve_site(patches, "earth", name) for name in earth_sites]
    )
    if not sites or len(set(sites)) != len(sites):
        raise ValueError("Choose at least one unique Earth site")
    query_ids = tuple(patch_by_tile.loc[tile_ids])
    query_vectors = terrain.encode(list(query_ids))
    saved_queries = terrain.vectors[patches.index.get_indexer(query_ids)]
    if not np.allclose(query_vectors, saved_queries, atol=1e-5, rtol=0):
        raise ValueError(
            "Saved query embeddings disagree with the model and preprocessing"
        )
    match_frames, physical_frames, per_site = [], [], []
    for site in sites:
        selected = patches.loc[
            patches.index.isin(query_ids)
            | ((patches.body == "earth") & (patches.region == site))
        ].sort_index()
        site_count = int((selected.body == "earth").sum())
        vectors = terrain.vectors[patches.index.get_indexer(selected.index)]
        matches, physical = retrieve_matches(
            selected, vectors, query_ids, query_vectors, min(top_k, site_count)
        )
        match_frames.append(matches)
        physical_frames.append(physical)
        first = matches.loc[matches["rank"] == 1]
        passes = matches.physical_checks_within_band.eq(5).groupby(matches.query_id).any()
        per_site.append(
            {
                "earth_site": site,
                "earth_patch_count": site_count,
                "median_best_patch_cosine": float(first.cosine_similarity.median()),
                "fraction_tiles_with_all_five_checks_in_top_k": float(passes.mean()),
            }
        )
    matches = pd.concat(match_frames, ignore_index=True).drop(columns="example")
    physical = pd.concat(physical_frames, ignore_index=True).drop(columns="example")
    for frame in (matches, physical):
        frame.insert(0, "tile_id", frame.query_id.map(tiles))
        frame.rename(columns={"rank": "site_rank"}, inplace=True)
    matches = matches.sort_values(
        ["tile_id", "cosine_similarity", "earth_region", "site_rank"],
        ascending=[True, False, True, True],
        ignore_index=True,
    )
    matches.insert(
        matches.columns.get_loc("site_rank") + 1,
        "overall_rank",
        matches.groupby("tile_id").cumcount() + 1,
    )
    summary = {
        "direction": "moon_tiles_to_each_earth_site",
        "tile_count": len(tile_ids),
        "earth_sites": sites,
        "top_k_per_site": top_k,
        "per_site": per_site,
        "maximum_replay_embedding_difference": float(
            np.abs(query_vectors - saved_queries).max()
        ),
        "interpretation": "Per-site cosine ranking of lunar tiles; cosine is not a percentage, "
        "validated accuracy or practical suitability. Physical checks explain, not rerank.",
    }
    return matches, physical, summary


def resolve_site(patches: pd.DataFrame, body: str, name: str) -> str:
    """Resolve a full region ID or its readable name without fuzzy matching."""

    def canonical(value: str) -> str:
        return re.sub(r"[\s_-]+", "", value).casefold()

    available = sorted(patches.loc[patches.body == body, "region"].unique().tolist())
    requested = canonical(name)
    matches = [
        region
        for region in available
        if requested
        in {
            canonical(region),
            canonical(re.sub(r"^A3CLR22_\d+_", "", region)),
        }
    ]
    if len(matches) != 1:
        raise ValueError(
            f"Unknown or ambiguous {body} site {name!r}. Available: {', '.join(available)}"
        )
    return matches[0]


def run_inference(
    root: Path,
    config: ArtifactConfig,
    moon_site: str,
    earth_site: str,
    *,
    top_k: int = 3,
    plots: bool = True,
    rebuild_cache: bool = False,
) -> Path:
    """Write a versioned site comparison; failures retain a failed run manifest."""
    root = root.resolve()
    settings = {
        "artifacts": asdict(config),
        "moon_site": moon_site,
        "earth_site": earth_site,
        "top_k": top_k,
        "plots": plots,
        "rebuild_cache": rebuild_cache,
    }
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    with Run(
        root,
        "terrain_similarity_pipeline",
        settings,
        "modeling/terrain_similarity/pipeline/main.py",
    ) as run:
        record_code_inputs(run, root)
        terrain = TerrainModel(root, config, rebuild_cache=rebuild_cache)
        matches, physical, summary = compare_sites(
            terrain, moon_site, earth_site, top_k
        )
        matches.to_csv(run.path("retrieval.csv"), index=False)
        physical.to_csv(run.path("physical_comparison.csv"), index=False)
        run.path("summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        terrain.patches.loc[
            terrain.patches.region.isin([summary["moon_site"], summary["earth_site"]])
        ].to_csv(run.path("selected_patches.csv"))
        examples = select_report_examples(matches)
        examples.to_csv(run.path("report_examples.csv"), index=False)
        if rebuild_cache:
            terrain.check_orientations().to_csv(
                run.path("orientation_checks.csv"), index=False
            )
            np.savez_compressed(
                run.path("embeddings.npz"),
                patch_ids=terrain.patches.index.to_numpy(dtype=str),
                cnn=terrain.vectors,
            )
            run.path("preprocessing.json").write_text(
                json.dumps(terrain.preprocessing, indent=2), encoding="utf-8"
            )
            terrain.patches.to_csv(run.path("patches.csv"))
        if plots:
            from notebooks.modeling.terrain_similarity.pipeline.report import (
                write_report,
            )

            run.input(root / "notebooks/modeling/terrain_similarity/pipeline/report.py")
            report_dir = (
                root / "reports/terrain-similarity-pipeline" / run.directory.name
            ).resolve()
            if not report_dir.is_relative_to(root / "reports"):
                raise ValueError("Report directory must stay within project reports")
            report_dir.mkdir(parents=True, exist_ok=False)
            write_report(
                report_dir,
                terrain.patches,
                terrain.physical_patch,
                matches,
                physical,
                summary,
                examples,
            )
            report_outputs = {
                p.name: file_hash(p)
                for p in sorted(report_dir.iterdir())
                if p.is_file()
            }
            (report_dir / "provenance.json").write_text(
                json.dumps(
                    {
                        "data_run": run.directory.relative_to(root).as_posix(),
                        "outputs": report_outputs,
                    },
                    indent=2,
                ),
                encoding="utf-8",
            )
            run.record["optional_reports"] = report_dir.relative_to(root).as_posix()
        check_evidence(run, root, terrain)
        run.record["summary"] = summary
    return run.directory


def record_code_inputs(run: Run, root: Path) -> None:
    """Hash the code and requirements a run depends on, plus its git revision."""
    for name in [
        "pipeline/artifacts.py",
        "pipeline/__init__.py",
        "pipeline/__main__.py",
        "model_weights.py",
        "similarity_cnn.py",
        "similarity_experiment.py",
        "terrain_dataset.py",
        "terrain_learning.py",
    ]:
        run.input(root / "notebooks/modeling/terrain_similarity" / name)
    for name in [
        "shared/inspection.py",
        "shared/retrieval_analysis.py",
        "shared/moon_tiles.py",
        "requirements-modeling.txt",
        "requirements-processing.txt",
    ]:
        run.input(root / "notebooks" / name)
    revision = subprocess.run(
        ["git", "rev-parse", "HEAD"],
        cwd=root,
        capture_output=True,
        text=True,
        check=False,
    )
    run.record.update(
        {
            "git_revision": revision.stdout.strip() or None,
            "torch": str(torch.__version__),
            "device": "cpu",
            "independent_relevance_validated": False,
            "reserves_opened": False,
        }
    )


def check_evidence(run: Run, root: Path, terrain: TerrainModel) -> None:
    """Fail the run if any verified model or data input changed while it ran."""
    for path, digest in terrain.evidence.items():
        run.input(Path(path))
        key = str(Path(path).relative_to(root))
        if run.record["inputs"][key]["sha256"] != digest:
            raise ValueError(f"Input changed during inference: {path}")


def run_tile_matching(
    root: Path,
    config: ArtifactConfig,
    tile_ids: list[str],
    *,
    earth_sites: list[str] | None = None,
    top_k: int = 3,
) -> Path:
    """Write `earth_matches.csv` for chosen lunar tiles as a versioned run."""
    root = root.resolve()
    settings = {
        "artifacts": asdict(config),
        "tile_count": len(tile_ids),
        "earth_sites": earth_sites or "all",
        "top_k_per_site": top_k,
    }
    torch.set_num_threads(2)
    torch.use_deterministic_algorithms(True)
    with Run(
        root,
        "terrain_similarity_tile_matches",
        settings,
        "modeling/terrain_similarity/pipeline/main.py",
    ) as run:
        record_code_inputs(run, root)
        terrain = TerrainModel(root, config)
        matches, physical, summary = match_tiles(terrain, tile_ids, earth_sites, top_k)
        matches.to_csv(run.path("earth_matches.csv"), index=False)
        physical.to_csv(run.path("physical_comparison.csv"), index=False)
        run.path("summary.json").write_text(
            json.dumps(summary, indent=2), encoding="utf-8"
        )
        check_evidence(run, root, terrain)
        run.record["summary"] = summary
    return run.directory


def read_tile_ids(path: Path) -> list[str]:
    """Tile IDs from a CSV with a `tile_id` column, e.g. `moon_tiles.csv` or a shortlist."""
    frame = pd.read_csv(path)
    if "tile_id" not in frame.columns:
        raise ValueError(f"{path} has no tile_id column")
    return frame["tile_id"].dropna().astype(str).drop_duplicates().tolist()


def select_report_examples(matches: pd.DataFrame) -> pd.DataFrame:
    """Show highest, median and lowest top-one scores; avoid presenting them as random samples."""
    ordered = matches.loc[matches["rank"] == 1].sort_values(
        ["cosine_similarity", "query_id"], ascending=[False, True]
    )
    rows = []
    seen: set[str] = set()
    for index, label in [
        (0, "Highest top-one cosine"),
        (len(ordered) // 2, "Median top-one cosine"),
        (len(ordered) - 1, "Lowest top-one cosine"),
    ]:
        item = ordered.iloc[index]
        if item.query_id not in seen:
            rows.append(
                {
                    "query_id": item.query_id,
                    "example": int(item.example),
                    "selection": label,
                }
            )
            seen.add(item.query_id)
    return pd.DataFrame(rows)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Compare a prepared Moon site with a prepared Earth site using the saved CNN."
    )
    parser.add_argument(
        "--root", type=Path, default=Path(__file__).resolve().parents[4]
    )
    parser.add_argument(
        "--config", type=Path, default=Path(__file__).with_name("config.json")
    )
    parser.add_argument(
        "--moon-site", help="Full lunar region ID or readable name, e.g. Haworth"
    )
    parser.add_argument(
        "--earth-site",
        help="Earth region ID or readable name, e.g. wadi_rum; with --tiles, optional (default: all)",
    )
    parser.add_argument(
        "--tiles",
        type=Path,
        help="CSV with a tile_id column (e.g. moon_tiles.csv); matches each tile against every Earth site",
    )
    parser.add_argument(
        "--top-k",
        type=int,
        default=3,
        help="Earth candidates per lunar patch (default: 3)",
    )
    parser.add_argument(
        "--list-sites",
        action="store_true",
        help="List prepared regions and patch counts",
    )
    parser.add_argument(
        "--no-plots", action="store_true", help="Export result tables and summary only"
    )
    parser.add_argument(
        "--rebuild-cache",
        action="store_true",
        help="Explicitly re-encode the prepared patches with the saved weights",
    )
    args = parser.parse_args()
    try:
        config = ArtifactConfig(**json.loads(args.config.read_text(encoding="utf-8")))
        if args.list_sites:
            terrain = TerrainModel(args.root, config)
            print(
                terrain.patches.groupby(["body", "region"])
                .size()
                .rename("patch_count")
                .to_string()
            )
            return
        if args.tiles is not None:
            if args.moon_site:
                parser.error("Use either --tiles or --moon-site, not both")
            output = run_tile_matching(
                args.root,
                config,
                read_tile_ids(args.tiles),
                earth_sites=[args.earth_site] if args.earth_site else None,
                top_k=args.top_k,
            )
            summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
            print(
                f"Matched {summary['tile_count']} lunar tiles against "
                f"{len(summary['earth_sites'])} Earth sites."
            )
            print(f"Results: {output / 'earth_matches.csv'}")
            return
        if not args.moon_site or not args.earth_site:
            parser.error(
                "Supply both --moon-site and --earth-site, or use --list-sites"
            )
        output = run_inference(
            args.root,
            config,
            args.moon_site,
            args.earth_site,
            top_k=args.top_k,
            plots=not args.no_plots,
            rebuild_cache=args.rebuild_cache,
        )
        summary = json.loads((output / "summary.json").read_text(encoding="utf-8"))
        print(
            f"Compared {summary['moon_patch_count']} lunar patches against {summary['earth_patch_count']} Earth patches."
        )
        print(
            f"Median best-patch cosine: {summary['median_best_patch_cosine']:.4f} (not a similarity percentage)."
        )
        print(f"Results: {output}")
        if not args.no_plots:
            print(
                f"Report: {args.root.resolve() / 'reports/terrain-similarity-pipeline' / output.name / 'REPORT.md'}"
            )
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))


def retrieve_matches(
    patches: pd.DataFrame,
    vectors: np.ndarray,
    query_ids: tuple[str, ...],
    query_vectors: np.ndarray,
    top_k: int,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Rank Earth candidates by cosine only; physical measurements explain results."""
    if not patches.index.is_unique or len(patches) != len(vectors):
        raise ValueError("Patch IDs and embedding rows must align uniquely")
    if not query_ids or len(set(query_ids)) != len(query_ids):
        raise ValueError("Choose at least one unique lunar query ID")
    if len(query_vectors) != len(query_ids):
        raise ValueError("Query IDs and embeddings must align")
    lunar_ids = set(patches.index[patches.body == "moon"])
    if not set(query_ids) <= lunar_ids:
        raise ValueError(
            "Query IDs must belong to prepared lunar patches in the selected view"
        )
    pool = np.flatnonzero(patches.body.to_numpy() == "earth")
    if type(top_k) is not int or not 1 <= top_k <= len(pool):
        raise ValueError(
            "top_k must be positive and no larger than the Earth candidate pool"
        )
    earth = patches.iloc[pool]
    candidate_ids = earth.index.tolist()
    rows, comparisons = [], []
    for example, (query_id, vector) in enumerate(
        zip(query_ids, query_vectors, strict=True), 1
    ):
        query = patches.loc[query_id]
        order, scores = cosine_top_k(vector, vectors[pool], candidate_ids, top_k)
        query_features = query[FEATURES].to_numpy(dtype=float)
        for rank, (position, score) in enumerate(zip(order, scores, strict=True), 1):
            candidate_id = candidate_ids[position]
            candidate = earth.iloc[position]
            candidate_features = candidate[FEATURES].to_numpy(dtype=float)
            reference = terrain_discrepancies(
                query_features, candidate_features[None, :]
            )
            bands = np.array(
                [
                    1.0,
                    2.0,
                    max(5.0, 0.1 * min(query_features[2], candidate_features[2])),
                    0.1,
                    max(1.0, 0.1 * min(query_features[4], candidate_features[4])),
                ]
            )
            differences = np.abs(candidate_features - query_features)
            discrepancies = differences / bands
            within = discrepancies <= 1.0
            physical_discrepancy = max(
                float(reference["with_planarity"][0]),
                float(reference["with_local_sd"][0]),
            )
            x, y = (
                float((candidate["left"] + candidate["right"]) / 2),
                float((candidate["bottom"] + candidate["top"]) / 2),
            )
            lon, lat, *_ = transform(candidate["crs_wkt"], "EPSG:4326", [x], [y])
            back_x, back_y, *_ = transform("EPSG:4326", candidate["crs_wkt"], lon, lat)
            if (
                not np.allclose([back_x[0], back_y[0]], [x, y], rtol=0, atol=0.01)
                or not -180 <= lon[0] <= 180
                or not -90 <= lat[0] <= 90
            ):
                raise ValueError(
                    f"Invalid candidate coordinate conversion: {candidate_id}"
                )
            for i, feature in enumerate(FEATURES):
                comparisons.append(
                    {
                        "example": example,
                        "rank": rank,
                        "query_id": query_id,
                        "candidate_id": candidate_id,
                        "feature": feature,
                        "measurement": METRIC_LABELS[i],
                        "moon": float(query_features[i]),
                        "earth": float(candidate_features[i]),
                        "absolute_difference": float(differences[i]),
                        "comparison_band": float(bands[i]),
                        "difference_over_band": float(discrepancies[i]),
                        "within_band": bool(within[i]),
                    }
                )
            rows.append(
                {
                    "example": example,
                    "query_id": query_id,
                    "query_region": query["region"],
                    "query_fold": query["fold"],
                    "rank": rank,
                    "candidate_id": candidate_id,
                    "earth_region": candidate["region"],
                    "candidate_fold": candidate["fold"],
                    "cosine_similarity": float(score),
                    "latitude": lat[0],
                    "longitude": lon[0],
                    "query_relief_m": query["central_relief_m"],
                    "candidate_relief_m": candidate["central_relief_m"],
                    "delta_relief_m": candidate["central_relief_m"]
                    - query["central_relief_m"],
                    "query_slope_p90_deg": query["slope_p90_deg"],
                    "candidate_slope_p90_deg": candidate["slope_p90_deg"],
                    "delta_slope_p90_deg": candidate["slope_p90_deg"]
                    - query["slope_p90_deg"],
                    "candidate_local_sd_m": candidate["local_sd_median_m"],
                    "physical_checks_within_band": int(within.sum()),
                    "physical_discrepancy": physical_discrepancy,
                }
            )
    return pd.DataFrame(rows), pd.DataFrame(comparisons)


if __name__ == "__main__":
    main()
