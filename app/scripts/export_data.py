"""Export the integrated Moon pipeline run to the static files the app reads (schema version 2).

Reads one `data/processed/moon_pipeline/<run>/` folder (written by `python -m integration.run_all`)
plus the two runs it names: Hanxi's walkability inference run (terrain grids) and Aarron's prepared
dataset (Earth terrain grids). Writes:

    <output-dir>/regions.json
    <output-dir>/patches/<region>.json        one record per tile: classes, probabilities, tile_id
    <output-dir>/grids/<region>.bin           Moon relative elevation and slope, Int16 x 10
    <output-dir>/analogs/<region>.json        Earth matches per tile with their physical checks
    <output-dir>/earth/candidates.json        every Earth patch that appears in a match
    <output-dir>/earth/grids.bin              their relative elevation and slope, Int16 x 10
    <output-dir>/environment.json             Operations and Survival per scenario
    <output-dir>/environment/sample_input.csv the scorer's input template, unchanged
    <output-dir>/environment/scorer/          the scorer and helpers the browser upload runs, unchanged

It never loads model weights and never changes the source files. Values are copied, not recomputed.
Run from the repository root. See app/README.md for commands.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import sys
from pathlib import Path, PurePosixPath

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from environment_data import EnvironmentDataError, scenarios_from_rows  # noqa: E402

SCHEMA_VERSION = 2
PIPELINE_STAGE = "moon_pipeline"
TERRAIN_STAGE = "terrain_human_walkability_lunar_inference"

GRID_CELLS = 32
GRID_SCALE = 10  # stored integer = round(physical value * GRID_SCALE)
GRID_CHANNELS = (("relative_elevation_m", "m"), ("slope_deg", "deg"))
# Aarron's prepared tensors hold (relative_elevation_m, slope_deg, local_elevation_std_m) in this order
# (notebooks/modeling/terrain_similarity/terrain_dataset.py CHANNELS). The files carry no channel names.
SIMILARITY_CHANNEL_INDEX = (0, 1)
INT16_MIN, INT16_MAX = -32768, 32767
BYTES_PER_PATCH = len(GRID_CHANNELS) * GRID_CELLS * GRID_CELLS * 2

# Source region ID -> (route name, display name). Names follow Darrel's README.
REGIONS = {
    "A3CLR22_10_Leibnitz_Beta_Plateau": ("leibnitz-beta-plateau", "Leibnitz Beta Plateau"),
    "A3CLR22_11_Malapert_Massif": ("malapert-massif", "Malapert Massif"),
    "A3CLR22_12_deGerlache_Kocher_Massif": ("de-gerlache-kocher-massif", "de Gerlache–Kocher Massif"),
    "A3CLR22_2_Haworth": ("haworth", "Haworth"),
    "A3CLR22_3_Faustini_Rim_A": ("faustini-rim-a", "Faustini Rim A"),
    "A3CLR22_4_deGerlache_Rim_2": ("de-gerlache-rim-2", "de Gerlache Rim 2"),
    "A3CLR22_5_Connecting_Ridge_Extension": ("connecting-ridge-extension", "Connecting Ridge Extension"),
}
SLUG_TO_REGION = {slug: source_id for source_id, (slug, _) in REGIONS.items()}
EARTH_SITES = {
    "atacama_san_pedro": "Atacama (San Pedro), Chile",
    "death_valley": "Death Valley, USA",
    "lanzarote": "Lanzarote, Spain",
    "northern_arizona": "Northern Arizona, USA",
    "wadi_rum": "Wadi Rum, Jordan",
}
# The similarity pipeline's five physical checks, in its own order (pipeline/main.py FEATURES).
SCORER = "env_algo_task/env_pipeline/env_pipeline.py"
DEFAULT_SCORER_CONFIG = "env_algo_task/env_pipeline/config.yml"
CHECKS = ("slope_median_deg", "slope_p90_deg", "central_relief_m", "plane_residual_fraction", "local_sd_median_m")

ROVER_CLASSES = ("operable", "marginal", "non_operable")
WALKING_CLASSES = ("easy", "caution", "unsuitable")
CROSSING_AXES = ("north_south", "east_west", "northwest_southeast", "northeast_southwest")


class ExportError(Exception):
    """A source record or file that the export refuses to publish."""


# ---------- small readers ----------

def _number(row: dict[str, str], column: str, label: str | None = None) -> float:
    label = label or row.get("patch_id", "?")
    try:
        value = float(row[column])
    except (KeyError, ValueError) as error:
        raise ExportError(f"{label}: {column} is missing or not a number") from error
    if not math.isfinite(value):
        raise ExportError(f"{label}: {column} is not finite")
    return value


def _whole(row: dict[str, str], column: str, label: str | None = None) -> int:
    value = _number(row, column, label)
    if value != int(value):
        raise ExportError(f"{label or row['patch_id']}: {column} is not a whole number")
    return int(value)


def _flag(row: dict[str, str], column: str, label: str | None = None) -> bool:
    text = row.get(column, "")
    if text not in ("True", "False"):
        raise ExportError(f"{label or row.get('patch_id', '?')}: {column} must be True or False, got {text!r}")
    return text == "True"


def _choice(row: dict[str, str], column: str, allowed: tuple[str, ...]) -> str:
    text = row.get(column, "")
    if text not in allowed:
        raise ExportError(f"{row.get('patch_id', '?')}: {column} has unknown class {text!r}")
    return text


def read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if not path.is_file():
        raise ExportError(f"Missing file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        reader = csv.DictReader(handle)
        rows = list(reader)
        return list(reader.fieldnames or []), rows


def read_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise ExportError(f"Cannot read {path}") from error


def inside(root: Path, relative: str, what: str) -> Path:
    """Resolve a path named by a run's provenance and keep it inside the repository."""
    path = (root / PurePosixPath(relative.replace("\\", "/"))).resolve()
    if not path.is_relative_to(root.resolve()):
        raise ExportError(f"The {what} path leaves the repository: {relative}")
    if not path.exists():
        raise ExportError(f"Missing {what}: {path}")
    return path


def latest_pipeline_run(root: Path) -> Path:
    """The newest completed `moon_pipeline` run."""
    folder = root / "data" / "processed" / PIPELINE_STAGE
    runs = sorted(
        path for path in folder.glob("*")
        if (path / "provenance.json").is_file() and read_json(path / "provenance.json").get("status") == "complete"
    ) if folder.is_dir() else []
    if not runs:
        raise ExportError(f"No completed pipeline run in {folder}. Run: python -m integration.run_all")
    return runs[-1]


# ---------- Moon patches (Hanxi's run, keyed by the shared tile_id) ----------

def read_predictions(run_dir: Path) -> list[dict[str, str]]:
    """Read predictions.csv and reject duplicate or unsupported records."""
    _, rows = read_csv(run_dir / "predictions.csv")
    if not rows:
        raise ExportError(f"No patch records in {run_dir / 'predictions.csv'}")
    seen: set[str] = set()
    for row in rows:
        patch_id = row.get("patch_id", "")
        if not patch_id:
            raise ExportError("A record has no patch_id")
        if patch_id in seen:
            raise ExportError(f"Duplicate patch_id: {patch_id}")
        seen.add(patch_id)
        if row.get("region") not in REGIONS:
            raise ExportError(f"{patch_id}: unsupported region {row.get('region')!r}")
    return rows


def read_tiles(pipeline_run: Path) -> dict[str, dict[str, str]]:
    """moon_tiles.csv rows keyed by Hanxi's patch ID."""
    _, rows = read_csv(pipeline_run / "moon_tiles.csv")
    tiles = {}
    for row in rows:
        patch_id = row.get("walkability_patch_id", "")
        if patch_id:
            if patch_id in tiles:
                raise ExportError(f"Two tiles claim walkability patch {patch_id}")
            tiles[patch_id] = row
    return tiles


def patch_record(row: dict[str, str], tile: dict[str, str] | None) -> dict:
    """Convert one source row to the app's patch record. Values are copied, not recomputed."""
    if _whole(row, "size_m") != GRID_CELLS * _whole(row, "spacing_m"):
        raise ExportError(f"{row['patch_id']}: size and spacing do not give a {GRID_CELLS}-cell grid")
    if tile is None:
        raise ExportError(f"{row['patch_id']}: no tile in moon_tiles.csv")
    top_row, top_col = _whole(row, "top_row"), _whole(row, "top_col")
    shard = row.get("tensor_shard", "").replace("\\", "/")
    if not shard:
        raise ExportError(f"{row['patch_id']}: missing tensor reference")
    similarity = tile.get("similarity_full_context_patch_id") or None
    return {
        "slug": f"r{top_row}-c{top_col}",
        "source_id": row["patch_id"],
        "tile_id": tile["tile_id"],
        "similarity_patch_id": similarity,
        "top_row": top_row,
        "top_col": top_col,
        "center_x_m": _number(row, "center_x"),
        "center_y_m": _number(row, "center_y"),
        "tensor": {"shard": shard, "index": _whole(row, "tensor_index")},
        "rover": {
            "class": _choice(row, "predicted_rover_class", ROVER_CLASSES),
            "probabilities": {name: _number(row, f"rover_probability_{name}") for name in ROVER_CLASSES},
        },
        "walking": {
            "class": _choice(row, "predicted_human_terrain_class", WALKING_CLASSES),
            "probabilities": {name: _number(row, f"human_probability_{name}") for name in WALKING_CLASSES},
        },
        "crossing": {
            axis: {"predicted": _flag(row, f"predicted_{axis}"), "probability": _number(row, f"probability_{axis}")}
            for axis in CROSSING_AXES
        },
        "physical": {
            "slope_median_deg": _number(row, "slope_median_deg"),
            "slope_p90_deg": _number(row, "slope_p90_deg"),
            "relative_relief_m": _number(row, "relative_relief_m"),
        },
        "direct_rule": {
            "walking_class": _choice(row, "direct_human_terrain_rule", WALKING_CLASSES),
            "cnn_agrees": _flag(row, "cnn_agrees_with_direct_human_rule"),
        },
    }


def _safe_file(run_dir: Path, shard: str) -> Path:
    relative = PurePosixPath(shard.replace("\\", "/"))
    if relative.is_absolute() or ".." in relative.parts:
        raise ExportError(f"Tensor path leaves the selected run: {shard}")
    path = (run_dir / relative).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ExportError(f"Tensor path leaves the selected run: {shard}")
    if not path.is_file():
        raise ExportError(f"Missing tensor file: {shard}")
    return path


def load_patch_grids(run_dir: Path, shard: str, indices: list[int]) -> np.ndarray:
    """Hanxi's tensors: float grids shaped (patches, 2, 32, 32) for the exported channels."""
    with np.load(_safe_file(run_dir, shard), allow_pickle=False) as archive:
        names = [str(name) for name in archive["channels"]]
        physical = archive["physical"]
    if physical.ndim != 4 or physical.shape[1] != len(names) or physical.shape[2:] != (GRID_CELLS, GRID_CELLS):
        raise ExportError(f"{shard}: unexpected tensor shape {physical.shape}")
    missing = [name for name, _ in GRID_CHANNELS if name not in names]
    if missing:
        raise ExportError(f"{shard}: missing channels {missing}")
    return _select(physical, indices, [names.index(name) for name, _ in GRID_CHANNELS], shard)


def load_similarity_grids(dataset_dir: Path, shard: str, indices: list[int]) -> np.ndarray:
    """Aarron's prepared tensors: float grids shaped (patches, 2, 32, 32)."""
    with np.load(_safe_file(dataset_dir, shard), allow_pickle=False) as archive:
        physical, valid = archive["physical"], archive["valid"]
    if physical.ndim != 4 or physical.shape[1:] != (3, GRID_CELLS, GRID_CELLS) or valid.shape != physical.shape:
        raise ExportError(f"{shard}: unexpected tensor shape {physical.shape}")
    grids = _select(physical, indices, list(SIMILARITY_CHANNEL_INDEX), shard)
    if not valid[np.asarray(indices, dtype=np.intp)].all():
        raise ExportError(f"{shard}: an exported Earth patch has invalid cells")
    return grids


def _select(physical: np.ndarray, indices: list[int], channels: list[int], shard: str) -> np.ndarray:
    out_of_range = [index for index in indices if not 0 <= index < physical.shape[0]]
    if out_of_range:
        raise ExportError(f"{shard}: tensor index {out_of_range[0]} is outside 0..{physical.shape[0] - 1}")
    return physical[np.asarray(indices, dtype=np.intp)][:, channels].astype(np.float64)


def quantize(grids: np.ndarray, label: str) -> bytes:
    """Pack grids as little-endian signed 16-bit values of round(value * GRID_SCALE)."""
    if not np.isfinite(grids).all():
        raise ExportError(f"{label}: terrain grid has a non-finite value")
    scaled = np.rint(grids * GRID_SCALE)
    if scaled.min() < INT16_MIN or scaled.max() > INT16_MAX:
        raise ExportError(f"{label}: terrain value does not fit a signed 16-bit integer at scale {GRID_SCALE}")
    return scaled.astype("<i2").tobytes(order="C")


def grid_format(file: str, count: int) -> dict:
    return {
        "file": file,
        "dtype": "int16",
        "byte_order": "little",
        "scale": GRID_SCALE,
        "shape": [GRID_CELLS, GRID_CELLS],
        "cell_order": "row-major: row 0 first, column 0 first within a row",
        "channels": [{"name": channel, "unit": unit} for channel, unit in GRID_CHANNELS],
        "bytes_per_patch": BYTES_PER_PATCH,
        "byte_length": count * BYTES_PER_PATCH,
    }


def pack_grids(items: list[tuple[str, int, str]], load) -> list[bytes]:
    """Grid bytes for (shard, index, label) items, in item order, opening each shard once."""
    blobs: list[bytes] = [b""] * len(items)
    by_shard: dict[str, list[int]] = {}
    for position, (shard, _, _) in enumerate(items):
        by_shard.setdefault(shard, []).append(position)
    for shard, positions in by_shard.items():
        indices = [items[position][1] for position in positions]
        if len(set(indices)) != len(indices):
            raise ExportError(f"{shard}: two patches share one tensor index")
        for position, grid in zip(positions, load(shard, indices), strict=True):
            blobs[position] = quantize(grid, items[position][2])
    return blobs


# ---------- Earth analogs ----------

def read_matches(pipeline_run: Path, tile_ids: set[str]) -> tuple[dict[str, list[dict]], dict[str, dict], dict]:
    """Matches per tile, Earth candidates and the check labels, from earth_matches + physical_comparison."""
    _, rows = read_csv(pipeline_run / "earth_matches.csv")
    _, checks = read_csv(pipeline_run / "physical_comparison.csv")
    physical: dict[tuple[str, str], dict[str, dict[str, str]]] = {}
    labels: dict[str, str] = {}
    for row in checks:
        if row["tile_id"] not in tile_ids:
            continue
        key = (row["tile_id"], row["candidate_id"])
        if row["feature"] not in CHECKS:
            raise ExportError(f"Unknown physical check {row['feature']!r}")
        if row["feature"] in physical.setdefault(key, {}):
            raise ExportError(f"Duplicate physical check {row['feature']} for {key}")
        physical[key][row["feature"]] = row
        labels[row["feature"]] = row["measurement"]

    tiles: dict[str, list[dict]] = {}
    moon: dict[str, list[float]] = {}
    candidates: dict[str, dict] = {}
    for row in rows:
        tile = row["tile_id"]
        if tile not in tile_ids:
            continue
        label = f"{tile} -> {row['candidate_id']}"
        site = row["earth_region"]
        if site not in EARTH_SITES:
            raise ExportError(f"{label}: unknown Earth site {site!r}")
        found = physical.pop((tile, row["candidate_id"]), None)
        if found is None or set(found) != set(CHECKS):
            raise ExportError(f"{label}: missing physical checks")
        ordered = [found[name] for name in CHECKS]
        moon_values = [_number(check, "moon", label) for check in ordered]
        earth_values = [_number(check, "earth", label) for check in ordered]
        if tile in moon and not np.allclose(moon[tile], moon_values, rtol=0, atol=1e-6):
            raise ExportError(f"{tile}: Moon check values differ between matches")
        moon[tile] = moon_values
        latitude, longitude = _number(row, "latitude", label), _number(row, "longitude", label)
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ExportError(f"{label}: coordinates outside the globe")
        candidate = candidates.setdefault(row["candidate_id"], {
            "id": row["candidate_id"], "site": site, "latitude": latitude, "longitude": longitude,
            "checks": earth_values,
        })
        if candidate["site"] != site or not np.allclose(candidate["checks"], earth_values, rtol=0, atol=1e-6):
            raise ExportError(f"{row['candidate_id']}: Earth values differ between matches")
        within = [_flag(check, "within_band", label) for check in ordered]
        if sum(within) != _whole(row, "physical_checks_within_band", label):
            raise ExportError(f"{label}: physical check count disagrees with physical_comparison.csv")
        tiles.setdefault(tile, []).append({
            "candidate": row["candidate_id"],
            "query_id": row["query_id"],
            "site_rank": _whole(row, "site_rank", label),
            "overall_rank": _whole(row, "overall_rank", label),
            "cosine": _number(row, "cosine_similarity", label),
            "bands": [_number(check, "comparison_band", label) for check in ordered],
            "within": within,
        })
    if physical:
        raise ExportError(f"{len(physical)} physical-check groups have no match row, e.g. {next(iter(physical))}")
    for tile, matches in tiles.items():
        ranks = sorted(match["overall_rank"] for match in matches)
        if ranks != list(range(1, len(matches) + 1)):
            raise ExportError(f"{tile}: overall ranks are not 1..{len(matches)}")
    return tiles, candidates, {"labels": [labels.get(name, name) for name in CHECKS], "moon": moon}


def analog_document(run_id: str, region_id: str, records: list[dict], tiles: dict[str, list[dict]],
                    moon: dict[str, list[float]], index: dict[str, int], pool: dict) -> dict:
    slug, name = REGIONS[region_id]
    entries = {}
    for record in records:
        matches = sorted(tiles.get(record["tile_id"], []), key=lambda match: match["overall_rank"])
        if not matches:
            continue
        queries = {match.pop("query_id") for match in matches}
        if queries != {record["similarity_patch_id"]}:
            raise ExportError(f"{record['tile_id']}: matches name query {queries}, not the tile's similarity patch")
        entries[record["slug"]] = {
            "tile_id": record["tile_id"],
            "query_id": record["similarity_patch_id"],
            "moon_checks": [round(value, 4) for value in moon[record["tile_id"]]],
            "matches": [
                {
                    "candidate": index[match["candidate"]],
                    "overall_rank": match["overall_rank"],
                    "site_rank": match["site_rank"],
                    "cosine": round(match["cosine"], 4),
                    "bands": [round(value, 4) for value in match["bands"]],
                    "within": match["within"],
                }
                for match in matches
            ],
        }
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_run": run_id,
        "region": {"slug": slug, "source_id": region_id, "name": name},
        "candidate_pool": pool,
        "tiles": entries,
    }


def candidates_document(run_id: str, ordered: list[dict], labels: list[str], site_counts: dict[str, int]) -> dict:
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_run": run_id,
        "sites": [{"id": site, "name": EARTH_SITES[site], "prepared_patch_count": site_counts.get(site, 0)}
                  for site in EARTH_SITES],
        "checks": [{"name": name, "label": label} for name, label in zip(CHECKS, labels, strict=True)],
        "grid": grid_format("earth/grids.bin", len(ordered)),
        "candidates": [
            {
                "id": candidate["id"],
                "site": candidate["site"],
                "latitude": round(candidate["latitude"], 6),
                "longitude": round(candidate["longitude"], 6),
                "checks": [round(value, 4) for value in candidate["checks"]],
                "grid_offset": position * BYTES_PER_PATCH,
            }
            for position, candidate in enumerate(ordered)
        ],
    }


# ---------- environment ----------

def environment_document(root: Path, pipeline_run: Path, run_id: str, scope: str | None,
                         input_relative: str | None, config_relative: str | None, output_dir: Path) -> dict | None:
    path = pipeline_run / "environment.csv"
    if scope is None or not path.is_file():
        return None
    columns, rows = read_csv(path)
    try:
        scenarios = scenarios_from_rows(columns, rows)
    except EnvironmentDataError as error:
        raise ExportError(f"environment.csv: {error}") from error
    sample = None
    if input_relative:
        source = inside(root, input_relative, "environment scorer input")
        target = output_dir / "environment" / "sample_input.csv"
        target.parent.mkdir(parents=True, exist_ok=True)
        data = lf_bytes(source)
        target.write_bytes(data)
        sample = {"file": "environment/sample_input.csv", "source": input_relative.replace("\\", "/"),
                  "sha256": hashlib.sha256(data).hexdigest()}
    return {
        "schema_version": SCHEMA_VERSION,
        "pipeline_run": run_id,
        "scope": scope,
        "scorer": f"{SCORER} --compact",
        "sample_input": sample,
        "upload_files": copy_scorer(root, config_relative, output_dir),
        "scenarios": scenarios,
    }


def copy_scorer(root: Path, config_relative: str | None, output_dir: Path) -> list[dict] | None:
    """Copy the scorer, its config and the app's two upload helpers, unchanged, for the browser upload.

    Returns None when the scorer is not in this checkout; the upload page then says it is unavailable.
    """
    sources = {
        "env_pipeline.py": root / SCORER,
        "config.yml": root / (config_relative or DEFAULT_SCORER_CONFIG),
        "environment_data.py": Path(__file__).with_name("environment_data.py"),
        "score_upload.py": Path(__file__).with_name("score_upload.py"),
    }
    if not all(path.is_file() for path in sources.values()):
        return None
    folder = output_dir / "environment" / "scorer"
    folder.mkdir(parents=True, exist_ok=True)
    files = []
    for name, source in sources.items():
        data = lf_bytes(source)
        (folder / name).write_bytes(data)
        files.append({"name": name, "file": f"environment/scorer/{name}", "sha256": hashlib.sha256(data).hexdigest()})
    return files


def lf_bytes(path: Path) -> bytes:
    """A text file's bytes with LF line endings, the form git stores.

    A Windows checkout (core.autocrlf) holds CRLF copies. Hashing those would publish hashes that no clean clone
    matches, and the browser upload refuses a scorer file whose hash differs. Only line endings change.
    """
    return path.read_bytes().replace(b"\r\n", b"\n")


# ---------- top level ----------

def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def run_export(
    root: Path,
    pipeline_run: Path,
    output_dir: Path,
    region_slugs: list[str] | None = None,
    patch_ids: list[str] | None = None,
) -> dict:
    """Export the selected regions and patches. Return the regions.json document."""
    root = root.resolve()
    pipeline_run = pipeline_run.resolve()
    provenance = read_json(pipeline_run / "provenance.json")
    if provenance.get("stage") != PIPELINE_STAGE or provenance.get("status") != "complete":
        raise ExportError(f"{pipeline_run} is not a completed {PIPELINE_STAGE} run")
    config = provenance["config"]
    summary = read_json(pipeline_run / "summary.json")
    run_id = pipeline_run.name
    terrain_run = inside(root, config["terrain_run"], "terrain run")
    dataset_run = inside(root, config["similarity"]["dataset_run"], "similarity dataset run")

    rows = read_predictions(terrain_run)
    tile_rows = read_tiles(pipeline_run)
    source_counts = {region_id: sum(row["region"] == region_id for row in rows) for region_id in REGIONS}

    unknown = [slug for slug in region_slugs or [] if slug not in SLUG_TO_REGION]
    if unknown:
        raise ExportError(f"Unknown region {unknown[0]!r}. Choose from: {', '.join(sorted(SLUG_TO_REGION))}")
    selected = [SLUG_TO_REGION[slug] for slug in region_slugs] if region_slugs else list(REGIONS)
    if patch_ids:
        if len(selected) != 1:
            raise ExportError("--patch-id needs exactly one --region")
        if len(set(patch_ids)) != len(patch_ids):
            raise ExportError("A --patch-id is repeated")
        known = {row["patch_id"]: row["region"] for row in rows}
        for patch_id in patch_ids:
            if patch_id not in known:
                raise ExportError(f"Unknown patch ID: {patch_id}")
            if known[patch_id] != selected[0]:
                raise ExportError(f"{patch_id} is not in region {REGIONS[selected[0]][0]}")

    claim = read_json(terrain_run / "provenance.json").get("config", {}).get("claim_boundary")
    if not claim:
        raise ExportError(f"Cannot read the claim boundary from {terrain_run / 'provenance.json'}")

    # Moon patches and grids, per region.
    by_region: dict[str, list[dict]] = {}
    for region_id in selected:
        region_rows = [row for row in rows if row["region"] == region_id]
        if patch_ids:
            region_rows = [row for row in region_rows if row["patch_id"] in set(patch_ids)]
        if not region_rows:
            raise ExportError(f"No patches to export for {REGIONS[region_id][0]}")
        records = [patch_record(row, tile_rows.get(row["patch_id"])) for row in region_rows]
        if len({record["slug"] for record in records}) != len(records):
            raise ExportError(f"{region_id}: two patches share one grid position")
        by_region[region_id] = records

    # Earth matches for the exported tiles.
    tile_ids = {record["tile_id"] for records in by_region.values() for record in records}
    matches, candidates, checks = read_matches(pipeline_run, tile_ids)
    ordered = sorted(candidates.values(), key=lambda candidate: (candidate["site"], candidate["id"]))
    index = {candidate["id"]: position for position, candidate in enumerate(ordered)}
    _, prepared = read_csv(dataset_run / "patches.csv")
    by_id = {row["patch_id"]: row for row in prepared}
    site_counts: dict[str, int] = {}
    for row in prepared:
        if row["body"] == "earth":
            site_counts[row["region"]] = site_counts.get(row["region"], 0) + 1
    missing = [candidate["id"] for candidate in ordered if candidate["id"] not in by_id]
    if missing:
        raise ExportError(f"{len(missing)} Earth candidates are not in the prepared dataset, e.g. {missing[0]}")
    pool = {
        "sites": summary.get("earth_sites", sorted(EARTH_SITES)),
        "top_k_per_site": summary.get("top_k_per_site", config.get("top_k_per_site")),
        "similarity_model": summary.get("similarity_model", config["similarity"]),
    }

    entries = []
    for region_id, records in by_region.items():
        slug, name = REGIONS[region_id]
        items = [(record["tensor"]["shard"], record["tensor"]["index"], record["source_id"]) for record in records]
        blobs = pack_grids(items, lambda shard, indices: load_patch_grids(terrain_run, shard, indices))
        for position, record in enumerate(records):
            record["grid_offset"] = position * BYTES_PER_PATCH
        grid_file, patches_file, analogs_file = f"grids/{slug}.bin", f"patches/{slug}.json", f"analogs/{slug}.json"
        (output_dir / "grids").mkdir(parents=True, exist_ok=True)
        (output_dir / grid_file).write_bytes(b"".join(blobs))
        first = next(row for row in rows if row["region"] == region_id)
        write_json(output_dir / patches_file, {
            "schema_version": SCHEMA_VERSION,
            "run_id": terrain_run.name,
            "pipeline_run": run_id,
            "region": {"slug": slug, "source_id": region_id, "name": name},
            "patch_size_m": _whole(first, "size_m"),
            "spacing_m": _whole(first, "spacing_m"),
            "patch_order": "The order of the patches array. Patch i starts at byte grid_offset.",
            "grid": grid_format(grid_file, len(records)),
            "patches": records,
        })
        analogs = analog_document(run_id, region_id, records, matches, checks["moon"], index, pool)
        write_json(output_dir / analogs_file, analogs)
        half = _whole(first, "size_m") / 2
        xs = [record["center_x_m"] for record in records]
        ys = [record["center_y_m"] for record in records]
        entries.append({
            "slug": slug,
            "source_id": region_id,
            "name": name,
            "patches_file": patches_file,
            "grid_file": grid_file,
            "analogs_file": analogs_file,
            "exported_patch_count": len(records),
            "source_patch_count": source_counts[region_id],
            "patches_with_analogs": len(analogs["tiles"]),
            # Outer edges of the exported tiles, in metres in the common lunar south polar stereographic CRS.
            "extent_m": {"xmin": min(xs) - half, "xmax": max(xs) + half, "ymin": min(ys) - half, "ymax": max(ys) + half},
        })

    earth_items = [(by_id[c["id"]]["shard"], _whole(by_id[c["id"]], "tensor_index", c["id"]), c["id"]) for c in ordered]
    earth_blobs = pack_grids(earth_items, lambda shard, indices: load_similarity_grids(dataset_run, shard, indices))
    (output_dir / "earth").mkdir(parents=True, exist_ok=True)
    (output_dir / "earth" / "grids.bin").write_bytes(b"".join(earth_blobs))
    write_json(output_dir / "earth" / "candidates.json",
               candidates_document(run_id, ordered, checks["labels"], site_counts))

    scope = summary.get("environment_scope")
    environment = environment_document(root, pipeline_run, run_id, scope, config.get("environment_input"),
                                       config.get("environment_config"), output_dir)
    if environment is not None:
        write_json(output_dir / "environment.json", environment)

    document = {
        "schema_version": SCHEMA_VERSION,
        "source": {"stage": TERRAIN_STAGE, "run_id": terrain_run.name, "claim_boundary": claim},
        "pipeline": {
            "run_id": run_id,
            "environment_scope": scope,
            "caveat": summary.get("caveat", ""),
            "earth_sites": pool["sites"],
            "top_k_per_site": pool["top_k_per_site"],
            "similarity_model": pool["similarity_model"],
        },
        "earth_file": "earth/candidates.json",
        "environment_file": "environment.json" if environment is not None else None,
        "regions": entries,
    }
    write_json(output_dir / "regions.json", document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--root", type=Path, default=Path("."), help="Repository root")
    parser.add_argument("--pipeline-run", type=Path, help="moon_pipeline run folder. Default: the newest completed run")
    parser.add_argument("--output-dir", type=Path, default=Path("app/public/data"), help="Folder the app serves data from")
    parser.add_argument("--region", action="append", help="Region route name, e.g. haworth. Repeat for more. Default: all seven")
    parser.add_argument("--patch-id", action="append", help="Hanxi patch ID. Repeat for more. Needs one --region")
    args = parser.parse_args(argv)
    try:
        pipeline_run = args.pipeline_run or latest_pipeline_run(args.root)
        document = run_export(args.root, pipeline_run, args.output_dir, args.region, args.patch_id)
    except ExportError as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1
    for entry in document["regions"]:
        print(f"{entry['slug']}: {entry['exported_patch_count']} of {entry['source_patch_count']} patches, "
              f"{entry['patches_with_analogs']} with Earth analogs")
    print(f"Pipeline run {document['pipeline']['run_id']}, wrote {args.output_dir}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
