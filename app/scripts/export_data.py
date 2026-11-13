"""Export pipeline outputs to the static files the app reads.

Reads Hanxi's lunar inference run (predictions.csv and tensors/*.npz) and writes:

    <output-dir>/regions.json
    <output-dir>/patches/<region-slug>.json
    <output-dir>/grids/<region-slug>.bin

It never loads model weights and never changes the source files.
Run from the repository root. See app/README.md for commands.
"""

from __future__ import annotations

import argparse
import csv
import json
import math
import sys
from pathlib import Path, PurePosixPath

import numpy as np

SCHEMA_VERSION = 1
STAGE = "terrain_human_walkability_lunar_inference"
DEFAULT_RUN_ID = "20261112T120422201915Z_101366"

GRID_CELLS = 32
GRID_SCALE = 10  # stored integer = round(physical value * GRID_SCALE)
GRID_CHANNELS = (("relative_elevation_m", "m"), ("slope_deg", "deg"))
INT16_MIN, INT16_MAX = -32768, 32767
BYTES_PER_PATCH = len(GRID_CHANNELS) * GRID_CELLS * GRID_CELLS * 2

# Source region ID -> (route name, display name). Names follow Darrel's README on dar_dev.
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

ROVER_CLASSES = ("operable", "marginal", "non_operable")
WALKING_CLASSES = ("easy", "caution", "unsuitable")
CROSSING_AXES = ("north_south", "east_west", "northwest_southeast", "northeast_southwest")


class ExportError(Exception):
    """A source record or file that the export refuses to publish."""


def _number(row: dict[str, str], column: str) -> float:
    try:
        value = float(row[column])
    except (KeyError, ValueError) as error:
        raise ExportError(f"{row.get('patch_id', '?')}: {column} is missing or not a number") from error
    if not math.isfinite(value):
        raise ExportError(f"{row.get('patch_id', '?')}: {column} is not finite")
    return value


def _whole(row: dict[str, str], column: str) -> int:
    value = _number(row, column)
    if value != int(value):
        raise ExportError(f"{row['patch_id']}: {column} is not a whole number")
    return int(value)


def _flag(row: dict[str, str], column: str) -> bool:
    text = row.get(column, "")
    if text not in ("True", "False"):
        raise ExportError(f"{row.get('patch_id', '?')}: {column} must be True or False, got {text!r}")
    return text == "True"


def _choice(row: dict[str, str], column: str, allowed: tuple[str, ...]) -> str:
    text = row.get(column, "")
    if text not in allowed:
        raise ExportError(f"{row.get('patch_id', '?')}: {column} has unknown class {text!r}")
    return text


def read_predictions(run_dir: Path) -> list[dict[str, str]]:
    """Read predictions.csv and reject duplicate or unsupported records."""
    path = run_dir / "predictions.csv"
    if not path.is_file():
        raise ExportError(f"Missing predictions file: {path}")
    with path.open(newline="", encoding="utf-8") as handle:
        rows = list(csv.DictReader(handle))
    if not rows:
        raise ExportError(f"No patch records in {path}")
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


def patch_record(row: dict[str, str]) -> dict:
    """Convert one source row to the app's patch record. Values are copied, not recomputed."""
    if _whole(row, "size_m") != GRID_CELLS * _whole(row, "spacing_m"):
        raise ExportError(f"{row['patch_id']}: size and spacing do not give a {GRID_CELLS}-cell grid")
    top_row, top_col = _whole(row, "top_row"), _whole(row, "top_col")
    shard = row.get("tensor_shard", "").replace("\\", "/")
    if not shard:
        raise ExportError(f"{row['patch_id']}: missing tensor reference")
    return {
        "slug": f"r{top_row}-c{top_col}",
        "source_id": row["patch_id"],
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


def load_patch_grids(run_dir: Path, shard: str, indices: list[int]) -> np.ndarray:
    """Return float grids shaped (patches, channels, 32, 32) for the two exported channels."""
    relative = PurePosixPath(shard)
    if relative.is_absolute() or ".." in relative.parts:
        raise ExportError(f"Tensor path leaves the selected run: {shard}")
    path = (run_dir / relative).resolve()
    if not path.is_relative_to(run_dir.resolve()):
        raise ExportError(f"Tensor path leaves the selected run: {shard}")
    if not path.is_file():
        raise ExportError(f"Missing tensor file: {shard}")
    with np.load(path, allow_pickle=False) as archive:
        names = [str(name) for name in archive["channels"]]
        physical = archive["physical"]
    if physical.ndim != 4 or physical.shape[1] != len(names) or physical.shape[2:] != (GRID_CELLS, GRID_CELLS):
        raise ExportError(f"{shard}: unexpected tensor shape {physical.shape}")
    missing = [name for name, _ in GRID_CHANNELS if name not in names]
    if missing:
        raise ExportError(f"{shard}: missing channels {missing}")
    out_of_range = [index for index in indices if not 0 <= index < physical.shape[0]]
    if out_of_range:
        raise ExportError(f"{shard}: tensor index {out_of_range[0]} is outside 0..{physical.shape[0] - 1}")
    channels = [names.index(name) for name, _ in GRID_CHANNELS]
    return physical[np.asarray(indices, dtype=np.intp)][:, channels].astype(np.float64)


def quantize(grids: np.ndarray, label: str) -> bytes:
    """Pack grids as little-endian signed 16-bit values of round(value * GRID_SCALE)."""
    if not np.isfinite(grids).all():
        raise ExportError(f"{label}: terrain grid has a non-finite value")
    scaled = np.rint(grids * GRID_SCALE)
    if scaled.min() < INT16_MIN or scaled.max() > INT16_MAX:
        raise ExportError(f"{label}: terrain value does not fit a signed 16-bit integer at scale {GRID_SCALE}")
    return scaled.astype("<i2").tobytes(order="C")


def export_region(run_dir: Path, run_id: str, region_id: str, rows: list[dict[str, str]], output_dir: Path) -> dict:
    """Write one region's patch metadata and grid binary. Return its regions.json entry."""
    slug, name = REGIONS[region_id]
    records = [patch_record(row) for row in rows]
    slugs = [record["slug"] for record in records]
    if len(set(slugs)) != len(slugs):
        raise ExportError(f"{region_id}: two patches share one grid position")

    by_shard: dict[str, list[int]] = {}
    for position, record in enumerate(records):
        by_shard.setdefault(record["tensor"]["shard"], []).append(position)
    blobs: list[bytes] = [b""] * len(records)
    for shard, positions in by_shard.items():
        indices = [records[position]["tensor"]["index"] for position in positions]
        if len(set(indices)) != len(indices):
            raise ExportError(f"{shard}: two patches share one tensor index")
        grids = load_patch_grids(run_dir, shard, indices)
        for position, grid in zip(positions, grids, strict=True):
            blobs[position] = quantize(grid, records[position]["source_id"])
    for position, record in enumerate(records):
        record["grid_offset"] = position * BYTES_PER_PATCH

    grid_file, patches_file = f"grids/{slug}.bin", f"patches/{slug}.json"
    (output_dir / "grids").mkdir(parents=True, exist_ok=True)
    (output_dir / "patches").mkdir(parents=True, exist_ok=True)
    (output_dir / grid_file).write_bytes(b"".join(blobs))
    first = rows[0]
    document = {
        "schema_version": SCHEMA_VERSION,
        "run_id": run_id,
        "region": {"slug": slug, "source_id": region_id, "name": name},
        "patch_size_m": _whole(first, "size_m"),
        "spacing_m": _whole(first, "spacing_m"),
        "patch_order": "The order of the patches array. Patch i starts at byte grid_offset.",
        "grid": {
            "file": grid_file,
            "dtype": "int16",
            "byte_order": "little",
            "scale": GRID_SCALE,
            "shape": [GRID_CELLS, GRID_CELLS],
            "cell_order": "row-major: row 0 first, column 0 first within a row",
            "channels": [{"name": channel, "unit": unit} for channel, unit in GRID_CHANNELS],
            "bytes_per_patch": BYTES_PER_PATCH,
            "byte_length": len(records) * BYTES_PER_PATCH,
        },
        "patches": records,
    }
    write_json(output_dir / patches_file, document)
    return {
        "slug": slug,
        "source_id": region_id,
        "name": name,
        "patches_file": patches_file,
        "grid_file": grid_file,
        "exported_patch_count": len(records),
    }


def write_json(path: Path, document: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(document, ensure_ascii=False, allow_nan=False, indent=1)
    path.write_text(text + "\n", encoding="utf-8", newline="\n")


def run_export(
    input_dir: Path,
    output_dir: Path,
    run_id: str = DEFAULT_RUN_ID,
    region_slugs: list[str] | None = None,
    patch_ids: list[str] | None = None,
) -> dict:
    """Export the selected regions and patches. Return the regions.json document."""
    run_dir = input_dir / STAGE / run_id
    if not run_dir.is_dir():
        raise ExportError(f"Missing inference run: {run_dir}")
    rows = read_predictions(run_dir)
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

    try:
        claim = json.loads((run_dir / "provenance.json").read_text(encoding="utf-8"))["config"]["claim_boundary"]
    except (OSError, KeyError, ValueError) as error:
        raise ExportError(f"Cannot read the claim boundary from {run_dir / 'provenance.json'}") from error

    entries = []
    for region_id in selected:
        region_rows = [row for row in rows if row["region"] == region_id]
        if patch_ids:
            region_rows = [row for row in region_rows if row["patch_id"] in set(patch_ids)]
        if not region_rows:
            raise ExportError(f"No patches to export for {REGIONS[region_id][0]}")
        entry = export_region(run_dir, run_id, region_id, region_rows, output_dir)
        entry["source_patch_count"] = source_counts[region_id]
        entries.append(entry)

    document = {
        "schema_version": SCHEMA_VERSION,
        "source": {"stage": STAGE, "run_id": run_id, "claim_boundary": claim},
        "regions": entries,
    }
    write_json(output_dir / "regions.json", document)
    return document


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--input-dir", type=Path, default=Path("temp"), help="Folder that holds the received pipeline outputs")
    parser.add_argument("--output-dir", type=Path, default=Path("app/public/data"), help="Folder the app serves data from")
    parser.add_argument("--run-id", default=DEFAULT_RUN_ID, help="Lunar inference run to read")
    parser.add_argument("--region", action="append", help="Region route name, e.g. leibnitz-beta-plateau. Repeat for more. Default: all seven")
    parser.add_argument("--patch-id", action="append", help="Source patch ID. Repeat for more. Needs one --region. Default: every patch")
    args = parser.parse_args(argv)
    try:
        document = run_export(args.input_dir, args.output_dir, args.run_id, args.region, args.patch_id)
    except ExportError as error:
        print(f"Export failed: {error}", file=sys.stderr)
        return 1
    for entry in document["regions"]:
        print(f"{entry['slug']}: exported {entry['exported_patch_count']} of {entry['source_patch_count']} patches")
    print(f"Wrote {args.output_dir / 'regions.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
