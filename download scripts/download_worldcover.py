"""Inventory/download ESA WorldCover 2021 v200 land-cover Map GeoTIFFs.

  python "download scripts/download_worldcover.py" --project-areas
  python "download scripts/download_worldcover.py" --project-areas --download

Requires requests. No AWS account, notebook, extraction, or raster processing.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
import argparse
import csv
import hashlib
import json
import math
import re
import shutil
import sys
import time
import xml.etree.ElementTree as ET

import requests

BASE_URL = "https://esa-worldcover.s3.eu-central-1.amazonaws.com/"
PREFIX = "v200/2021/map/"
PATTERN = re.compile(r"ESA_WorldCover_10m_2021_v200_([NS])(\d{2})([EW])(\d{3})_Map\.tif")
Bounds = tuple[float, float, float, float]
PROJECT_AREAS: dict[str, Bounds] = {
    "Northern Arizona": (-112.5, 35.0, -111.0, 36.0),
    "Lanzarote": (-13.95, 28.8, -13.35, 29.3),
    "Atacama near San Pedro": (-68.6, -23.2, -67.8, -22.6),
}
LEGEND_URL = "https://esa-worldcover.s3.amazonaws.com/v100/2020/docs/ESAWorldCover_ColorLegend.qml"
CLASSES = {10: "Tree cover", 20: "Shrubland", 30: "Grassland", 40: "Cropland", 50: "Built-up", 60: "Bare / sparse vegetation", 70: "Snow and ice", 80: "Permanent water bodies", 90: "Herbaceous wetland", 95: "Mangroves", 100: "Moss and lichen"}


@dataclass(frozen=True)
class Tile:
    filename: str
    url: str
    size_bytes: int
    etag: str
    bounds: tuple[float, float, float, float]


def parse_catalog_page(xml: str) -> tuple[list[Tile], str | None]:
    root = ET.fromstring(xml)
    ns = {"s": "http://s3.amazonaws.com/doc/2006-03-01/"}
    if root.tag != "{http://s3.amazonaws.com/doc/2006-03-01/}ListBucketResult":
        raise ValueError("Unexpected S3 catalog response")
    tiles = []
    for content in root.findall("s:Contents", ns):
        key = content.findtext("s:Key", namespaces=ns) or ""
        filename = key.removeprefix(PREFIX)
        match = PATTERN.fullmatch(filename)
        if match is None or key != PREFIX + filename:
            continue
        lat_sign, lat, lon_sign, lon = match.groups()
        south = int(lat) * (-1 if lat_sign == "S" else 1)
        west = int(lon) * (-1 if lon_sign == "W" else 1)
        if not (-90 <= south <= 87 and -180 <= west <= 177) or south % 3 or west % 3:
            raise ValueError(f"Unexpected 3-degree grid: {filename}")
        size = int(content.findtext("s:Size", namespaces=ns) or "0")
        etag = content.findtext("s:ETag", namespaces=ns) or ""
        if size <= 0 or not etag:
            raise ValueError(f"Missing size or ETag: {filename}")
        tiles.append(Tile(filename, BASE_URL + key, size, etag, (west, south, west + 3, south + 3)))
    truncated = root.findtext("s:IsTruncated", namespaces=ns)
    if truncated not in {"true", "false"}:
        raise ValueError("Missing S3 pagination status")
    token = root.findtext("s:NextContinuationToken", namespaces=ns) if truncated == "true" else None
    if truncated == "true" and not token:
        raise ValueError("Truncated catalog has no continuation token")
    return tiles, token


def download_tile(session: requests.Session, tile: Tile, output: Path,
                  timeout: int = 90, attempts: int = 3) -> Path:
    if timeout < 1 or attempts < 1 or tile.size_bytes < 1:
        raise ValueError("Timeout, attempts and size must be positive")
    output.mkdir(parents=True, exist_ok=True)
    final = output / tile.filename
    partial = output / (tile.filename + ".part")
    partial_info = output / (tile.filename + ".part.json")
    receipt = output / (tile.filename + ".json")
    for path in (final, partial, partial_info, receipt):
        if Path(tile.filename).name != tile.filename or not path.resolve().is_relative_to(output.resolve()):
            raise ValueError("Tile path escapes output directory")
    source = {"url": tile.url, "size_bytes": tile.size_bytes, "etag": tile.etag}
    if final.exists():
        recorded = json.loads(receipt.read_text()) if receipt.is_file() else {}
        if any(recorded.get(key) != value for key, value in source.items()):
            raise RuntimeError(f"Existing file lacks a matching source receipt; preserved: {final}")
        validate_tiff(final, tile.size_bytes)
        if sha256_file(final) != recorded.get("sha256"):
            raise RuntimeError(f"Existing file SHA-256 mismatch; preserved: {final}")
        print(f"SKIP verified: {tile.filename}", flush=True)
        return final
    if partial.exists():
        if not partial_info.is_file() or json.loads(partial_info.read_text()) != source:
            raise RuntimeError(f"Partial source identity changed or is unknown; preserved: {partial}")
    else:
        save_json(partial_info, source)
    for attempt in range(1, attempts + 1):
        start = partial.stat().st_size if partial.exists() else 0
        if start > tile.size_bytes:
            raise RuntimeError(f"Oversized partial; preserved: {partial}")
        if start == tile.size_bytes:
            break
        try:
            headers = {"Accept-Encoding": "identity", "If-Match": tile.etag}
            if start:
                headers["Range"] = f"bytes={start}-"
            with session.get(tile.url, headers=headers, stream=True, timeout=(20, timeout)) as response:
                response.raise_for_status()
                if response.headers.get("ETag") != tile.etag:
                    raise RuntimeError("Remote ETag changed; refresh inventory")
                if response.status_code == 206:
                    if response.headers.get("Content-Range") != f"bytes {start}-{tile.size_bytes - 1}/{tile.size_bytes}":
                        raise RuntimeError("Unexpected Content-Range; partial preserved")
                    mode = "ab" if start else "wb"
                elif response.status_code == 200:
                    if start:
                        print("Range ignored; restarting current tile.", flush=True)
                    start, mode = 0, "wb"
                else:
                    raise RuntimeError(f"Unexpected HTTP status {response.status_code}")
                length = response.headers.get("Content-Length")
                if length is not None and int(length) != tile.size_bytes - start:
                    raise RuntimeError("Response size disagrees with catalog")
                total = start
                began = last_report = time.monotonic()
                with partial.open(mode) as handle:
                    for chunk in response.iter_content(1024 * 1024):
                        if not chunk:
                            continue
                        if total + len(chunk) > tile.size_bytes:
                            raise RuntimeError("Response exceeds catalog size")
                        handle.write(chunk)
                        total += len(chunk)
                        now = time.monotonic()
                        if now - last_report >= 10:
                            speed = (total - start) / max(now - began, 0.001) / 1e6
                            print(f"  {total / tile.size_bytes:.1%} | {total / 1e6:.1f} MB | {speed:.2f} MB/s", flush=True)
                            last_report = now
                if total != tile.size_bytes:
                    raise RuntimeError("Incomplete transfer")
            break
        except (requests.RequestException, OSError, ValueError, RuntimeError) as exc:
            print(f"Attempt {attempt}/{attempts}: {exc}", flush=True)
            if attempt == attempts:
                raise RuntimeError(f"Download failed; partial retained: {exc}") from exc
            time.sleep(min(2**attempt, 15))
    validate_tiff(partial, tile.size_bytes)
    save_json(receipt, {**source, "sha256": sha256_file(partial), "verified_utc": datetime.now(timezone.utc).isoformat()})
    partial.replace(final)
    partial_info.unlink()
    print(f"OK: {tile.filename}", flush=True)
    return final


def validate_tiff(path: Path, expected_bytes: int) -> None:
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"Size mismatch: {path}")
    with path.open("rb") as handle:
        if handle.read(4) not in (b"II\x2a\x00", b"II\x2b\x00", b"MM\x00\x2a", b"MM\x00\x2b"):
            raise RuntimeError(f"Invalid TIFF header; file preserved: {path}")


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def validate_bounds(bounds: Bounds) -> None:
    west, south, east, north = bounds
    if not all(math.isfinite(v) for v in bounds) or not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Use WEST SOUTH EAST NORTH with west < east and south < north; split date-line crossings into two boxes")


def select_tiles(tiles: Sequence[Tile], boxes: Sequence[Bounds]) -> list[Tile]:
    for box in boxes:
        validate_bounds(box)
    return [tile for tile in tiles if any(tile.bounds[0] < east and tile.bounds[2] > west and tile.bounds[1] < north and tile.bounds[3] > south for west, south, east, north in boxes)]


def fetch_catalog(session: requests.Session, timeout: int) -> tuple[list[Tile], list[str]]:
    params = {"list-type": "2", "prefix": PREFIX, "max-keys": "1000"}
    entries: dict[str, Tile] = {}
    pages, tokens = [], set()
    while True:
        response = session.get(BASE_URL, params=params, timeout=(20, timeout))
        response.raise_for_status()
        tiles, token = parse_catalog_page(response.text)
        pages.append(response.text)
        for tile in tiles:
            if tile.filename in entries:
                raise ValueError(f"Duplicate tile in catalog: {tile.filename}")
            entries[tile.filename] = tile
        if token is None:
            break
        if token in tokens:
            raise ValueError("Repeated catalog continuation token")
        tokens.add(token)
        params["continuation-token"] = token
    if not entries:
        raise ValueError("No 2021 v200 Map tiles found")
    return sorted(entries.values(), key=lambda t: t.filename), pages


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    choice = parser.add_mutually_exclusive_group(required=True)
    choice.add_argument("--project-areas", action="store_true", help="Use the three Arizona, Lanzarote and Atacama boxes used for FABDEM")
    choice.add_argument("--bbox", nargs=4, type=float, action="append", metavar=("WEST", "SOUTH", "EAST", "NORTH"), help="Select intersecting tiles; repeat for multiple boxes")
    parser.add_argument("--output", type=Path, default=Path("data/raw/earth/worldcover"))
    parser.add_argument("--download", action="store_true", help="Transfer selected maps; default inventory only")
    parser.add_argument("--timeout", type=int, default=90, help="HTTP read timeout in seconds (default: 90)")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per tile (default: 3)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.timeout < 1 or args.attempts < 1:
        parser.error("--timeout and --attempts must be positive")
    boxes: list[Bounds] = list(PROJECT_AREAS.values()) if args.project_areas else [tuple(b) for b in args.bbox]
    try:
        for box in boxes:
            validate_bounds(box)
    except ValueError as exc:
        parser.error(str(exc))
    output = args.output.expanduser().resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with requests.Session() as session:
        session.headers.update({"User-Agent": "WorldCover-Research-Downloader/1.0", "Accept-Encoding": "identity"})
        print("Reading ESA WorldCover 2021 v200 Map catalog...", flush=True)
        catalog, pages = fetch_catalog(session, args.timeout)
        selected = select_tiles(catalog, boxes)
        if not selected:
            print("No published Map tiles intersect the requested boxes.")
            return 2
        manifests = output / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        for index, page in enumerate(pages, 1):
            (manifests / f"{run_id}_catalog_{index}.xml").write_text(page, encoding="utf-8")
        with (manifests / f"{run_id}_selection.csv").open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["filename", "size_bytes", "etag", "west", "south", "east", "north", "url"])
            writer.writerows((t.filename, t.size_bytes, t.etag, *t.bounds, t.url) for t in selected)
        save_json(manifests / f"{run_id}_class_legend.json", {"source": LEGEND_URL, "note": "Shared class legend linked from ESA's data-access page; labels are categorical, not continuous values.", "classes": CLASSES})
        report_path = manifests / f"{run_id}_run.json"
        report = {"run_id": run_id, "dataset": "ESA WorldCover 2021 v200 Map", "doi": "10.5281/zenodo.7254221", "license": "CC BY 4.0", "attribution": "ESA WorldCover project 2021 / Contains modified Copernicus Sentinel data (2021) processed by ESA WorldCover consortium", "bbox": boxes, "project_areas": PROJECT_AREAS if args.project_areas else None, "status": "inventory", "completed": [], "failed": []}
        save_json(report_path, report)
        print(f"Selected {len(selected)} Map tiles, {sum(t.size_bytes for t in selected) / 1e6:.1f} MB")
        for tile in selected:
            print(f"  {tile.filename}: {tile.size_bytes / 1e6:.1f} MB")
        print(f"Inventory: {manifests}")
        if not args.download:
            print("Inventory only. Add --download to transfer Map GeoTIFFs.")
            return 0
        maps = output / "v200/2021/map"
        pending = sum(t.size_bytes for t in selected if not (maps / t.filename).exists())
        if shutil.disk_usage(output).free < pending:
            raise RuntimeError("Insufficient disk space for pending tiles")
        report["status"] = "downloading"
        save_json(report_path, report)
        try:
            for index, tile in enumerate(selected, 1):
                print(f"[{index}/{len(selected)}] {tile.filename}", flush=True)
                try:
                    path = download_tile(session, tile, maps, args.timeout, args.attempts)
                    report["completed"].append({"filename": tile.filename, **json.loads(path.with_name(path.name + ".json").read_text())})
                except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
                    report["failed"].append({"filename": tile.filename, "error": str(exc)})
                    print(f"FAILED: {exc}", file=sys.stderr)
                save_json(report_path, report)
        except KeyboardInterrupt:
            report["status"] = "interrupted"
            save_json(report_path, report)
            raise
        report["status"] = "failed" if report["failed"] else "complete"
        save_json(report_path, report)
        print(f"Finished: {len(report['completed'])}/{len(selected)} tiles. Audit: {report_path}")
        return 1 if report["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; rerun the same command to resume.", file=sys.stderr)
        raise SystemExit(130)
    except (requests.RequestException, OSError, RuntimeError, ValueError, ET.ParseError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
