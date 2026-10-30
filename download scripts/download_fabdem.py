"""Inventory/download official FABDEM V1-2 ZIP bundles (no automatic extraction).

Examples, from the project root:
  python "download scripts/download_fabdem.py" --bbox -69 -24 -68 -23
  python "download scripts/download_fabdem.py" --bbox -69 -24 -68 -23 --download

Bounding boxes use WEST SOUTH EAST NORTH in decimal degrees. Selection uses
10-degree archive bounds; files are not cropped to your box. Inventory only
by default. Dependencies: python -m pip install requests beautifulsoup4
"""

from __future__ import annotations

from dataclasses import dataclass
from collections.abc import Sequence
from datetime import datetime, timezone
import argparse
import csv
import hashlib
import json
import math
import re
from pathlib import Path
import shutil
import sys
import time
from urllib.parse import urljoin, urlparse
import zipfile
import zlib

import requests
from bs4 import BeautifulSoup

Bounds = tuple[float, float, float, float]
NAME_PATTERN = re.compile(r"([NS])(\d{2})([EW])(\d{3})-([NS])(\d{2})([EW])(\d{3})_FABDEM_V1-2\.zip")
CATALOG_URL = "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/"
DATASET_URL = "https://research-information.bris.ac.uk/en/datasets/fabdem-v1-2/"


@dataclass(frozen=True)
class Archive:
    filename: str
    url: str
    size_bytes: int
    bounds: Bounds


def archive_bounds(filename: str) -> Bounds:
    match = NAME_PATTERN.fullmatch(filename)
    if match is None:
        raise ValueError(f"Unexpected FABDEM archive name: {filename}")
    a, b, c, d, e, f, g, h = match.groups()
    south = int(b) * (-1 if a == "S" else 1)
    west = int(d) * (-1 if c == "W" else 1)
    north = int(f) * (-1 if e == "S" else 1)
    east = int(h) * (-1 if g == "W" else 1)
    if west == 170 and east == -180:
        east = 180
    bounds = (float(west), float(south), float(east), float(north))
    validate_bounds(bounds)
    return bounds


def validate_bounds(bounds: Bounds) -> None:
    west, south, east, north = bounds
    if not all(math.isfinite(value) for value in bounds):
        raise ValueError("Bounding-box coordinates must be finite")
    if not (-180 <= west < east <= 180 and -90 <= south < north <= 90):
        raise ValueError("Use WEST SOUTH EAST NORTH with west < east and south < north; split dateline-crossing areas into two boxes")


def select_archives(archives: Sequence[Archive], boxes: Sequence[Bounds]) -> list[Archive]:
    for box in boxes:
        validate_bounds(box)
    return [archive for archive in archives if any(
        archive.bounds[0] < east and archive.bounds[2] > west
        and archive.bounds[1] < north and archive.bounds[3] > south
        for west, south, east, north in boxes
    )]


def download_archive(session: requests.Session, archive: Archive, output: Path,
                     timeout: int = 90, attempts: int = 3) -> Path:
    if attempts < 1 or timeout < 1 or archive.size_bytes < 1:
        raise ValueError("Attempts, timeout, and expected size must be positive")
    output.mkdir(parents=True, exist_ok=True)
    final = output / archive.filename
    partial = output / (archive.filename + ".part")
    for path in (final, partial):
        if Path(archive.filename).name != archive.filename or not path.resolve().is_relative_to(output.resolve()):
            raise ValueError("Archive path escapes output directory")
    if final.exists():
        verify_archive(final, archive.size_bytes)
        print(f"SKIP verified ZIP: {archive.filename}", flush=True)
        return final
    last_error = ""
    for attempt in range(1, attempts + 1):
        start = partial.stat().st_size if partial.exists() else 0
        if start > archive.size_bytes:
            raise RuntimeError(f"Partial exceeds expected size; preserve/move it aside before retrying: {partial}")
        if start == archive.size_bytes:
            verify_archive(partial, archive.size_bytes)
            partial.replace(final)
            return final
        try:
            headers = {"Accept-Encoding": "identity"}
            if start:
                headers["Range"] = f"bytes={start}-"
            with session.get(archive.url, headers=headers, stream=True, timeout=(20, timeout)) as response:
                response.raise_for_status()
                if response.status_code == 206:
                    expected_range = f"bytes {start}-{archive.size_bytes - 1}/{archive.size_bytes}"
                    if response.headers.get("Content-Range") != expected_range:
                        raise RuntimeError(f"Unexpected Content-Range: {response.headers.get('Content-Range')}")
                    mode = "ab" if start else "wb"
                elif response.status_code == 200:
                    if start:
                        print("Server ignored Range; restarting this file.", flush=True)
                    start = 0
                    mode = "wb"
                else:
                    raise RuntimeError(f"Unexpected HTTP status: {response.status_code}")
                content_length = response.headers.get("Content-Length")
                if content_length is not None and int(content_length) != archive.size_bytes - start:
                    raise RuntimeError("Remote Content-Length disagrees with catalog; refresh inventory")
                total = start
                began = last_report = time.monotonic()
                with partial.open(mode) as handle:
                    for chunk in response.iter_content(chunk_size=1024 * 1024):
                        if not chunk:
                            continue
                        if total + len(chunk) > archive.size_bytes:
                            raise RuntimeError("Response exceeds catalog size")
                        handle.write(chunk)
                        total += len(chunk)
                        now = time.monotonic()
                        if now - last_report >= 10:
                            speed = (total - start) / max(now - began, 0.001) / 1e6
                            print(f"  {100 * total / archive.size_bytes:.1f}% | {total / 1e6:.1f} MB | {speed:.2f} MB/s", flush=True)
                            last_report = now
                if total != archive.size_bytes:
                    raise RuntimeError(f"Incomplete response: {total}/{archive.size_bytes} bytes")
            break
        except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
            last_error = str(exc)
            print(f"Attempt {attempt}/{attempts}: {exc}", flush=True)
            if attempt == attempts:
                raise RuntimeError(f"Transfer failed; partial retained: {last_error}") from exc
            time.sleep(min(2**attempt, 15))
    verify_archive(partial, archive.size_bytes)
    partial.replace(final)
    print(f"OK: {archive.filename}", flush=True)
    return final


def verify_archive(path: Path, expected_bytes: int) -> None:
    if path.stat().st_size != expected_bytes:
        raise RuntimeError(f"Size mismatch; existing file preserved: {path}")
    try:
        with zipfile.ZipFile(path) as archive:
            if not archive.infolist():
                raise RuntimeError(f"Invalid ZIP (empty): {path}")
            bad = archive.testzip()
            if bad is not None:
                raise RuntimeError(f"Invalid ZIP CRC for {bad}: {path}")
    except (zipfile.BadZipFile, EOFError, zlib.error) as exc:
        raise RuntimeError(f"Invalid ZIP; preserve/move it aside before retrying: {path}") from exc


def parse_catalog(html: str) -> list[Archive]:
    soup = BeautifulSoup(html, "html.parser")
    entries: dict[str, Archive] = {}
    for row in soup.find_all("tr"):
        anchor = row.find("a", href=True)
        if anchor is None:
            continue
        url = urljoin(CATALOG_URL, str(anchor.get("href")))
        filename = Path(urlparse(url).path).name
        if NAME_PATTERN.fullmatch(filename) is None or url != CATALOG_URL + filename:
            continue
        cells = row.find_all("td")
        size_text = cells[-1].get_text(strip=True) if cells else ""
        if not size_text.isdecimal() or int(size_text) <= 0:
            raise ValueError(f"Missing exact byte size for {filename}; catalog layout may have changed")
        entry = Archive(filename, url, int(size_text), archive_bounds(filename))
        if filename in entries and entries[filename] != entry:
            raise ValueError(f"Conflicting catalog entries: {filename}")
        entries[filename] = entry
    if not entries:
        raise ValueError("No FABDEM V1-2 archive links found; inspect the official catalog")
    return sorted(entries.values(), key=lambda entry: entry.filename)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(4 * 1024 * 1024):
            digest.update(chunk)
    return digest.hexdigest()


def save_json(path: Path, value: dict) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2), encoding="utf-8")
    temporary.replace(path)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    choice = parser.add_mutually_exclusive_group()
    choice.add_argument("--bbox", nargs=4, type=float, action="append", metavar=("WEST", "SOUTH", "EAST", "NORTH"), help="Select intersecting archive blocks; repeat for multiple areas")
    choice.add_argument("--archive", action="append", metavar="FILENAME", help="Exact ZIP filename from the inventory; repeat for multiple archives")
    choice.add_argument("--all", action="store_true", help="Explicitly select the entire catalog (potentially very large)")
    parser.add_argument("--output", type=Path, default=Path("data/raw/earth/fabdem"), help="Output root (default: data/raw/earth/fabdem)")
    parser.add_argument("--download", action="store_true", help="Download selected ZIPs; default saves inventory only")
    parser.add_argument("--timeout", type=int, default=90, help="Read timeout in seconds (default: 90)")
    parser.add_argument("--attempts", type=int, default=3, help="Attempts per file (default: 3)")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    if args.timeout < 1 or args.attempts < 1:
        parser.error("--timeout and --attempts must be positive")
    if args.download and not (args.bbox or args.archive or args.all):
        parser.error("Choose --bbox, --archive, or explicitly --all before downloading")
    boxes: list[Bounds] = [tuple(box) for box in (args.bbox or [])]
    try:
        for box in boxes:
            validate_bounds(box)
    except ValueError as exc:
        parser.error(str(exc))
    output = args.output.expanduser().resolve()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    with requests.Session() as session:
        session.headers.update({"User-Agent": "FABDEM-Research-Downloader/1.0", "Accept-Encoding": "identity"})
        print("Reading official FABDEM V1-2 catalog...", flush=True)
        response = session.get(CATALOG_URL, timeout=(20, args.timeout))
        response.raise_for_status()
        catalog = parse_catalog(response.text)
        if boxes:
            selected = select_archives(catalog, boxes)
        elif args.archive:
            requested = set(args.archive)
            missing = requested - {entry.filename for entry in catalog}
            if missing:
                parser.error(f"Archives not in catalog: {', '.join(sorted(missing))}")
            selected = [entry for entry in catalog if entry.filename in requested]
        else:
            selected = catalog
        if not selected:
            print("No catalog archive blocks intersect this selection. No elevation data downloaded.")
            return 2
        manifests = output / "manifests"
        manifests.mkdir(parents=True, exist_ok=True)
        (manifests / f"{run_id}_catalog.html").write_text(response.text, encoding="utf-8")
        manifest_path = manifests / f"{run_id}_selection.csv"
        with manifest_path.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.writer(handle)
            writer.writerow(["filename", "size_bytes", "west", "south", "east", "north", "url"])
            writer.writerows((e.filename, e.size_bytes, *e.bounds, e.url) for e in selected)
        report_path = manifests / f"{run_id}_run.json"
        report = {
            "run_id": run_id, "dataset": "FABDEM V1-2", "license": "CC BY-NC-SA 4.0",
            "dataset_url": DATASET_URL, "catalog_url": CATALOG_URL,
            "selection_manifest": manifest_path.name, "bbox": boxes,
            "requested_archives": args.archive, "all": args.all, "download": args.download,
            "timeout_seconds": args.timeout, "attempts": args.attempts,
            "status": "inventory", "completed": [], "failed": [],
        }
        save_json(report_path, report)
        total = sum(entry.size_bytes for entry in selected)
        print(f"Selected {len(selected)} of {len(catalog)} archives: {total / 1e9:.3f} GB")
        for entry in selected[:12]:
            print(f"  {entry.filename}  {entry.size_bytes / 1e9:.3f} GB")
        if len(selected) > 12:
            print("  ...remaining archives listed in the selection manifest")
        print(f"Manifest: {manifest_path}")
        print("License: CC BY-NC-SA 4.0. Whole ZIP blocks are downloaded, not cropped regions.")
        if not args.download:
            print("Inventory only. Add --download to the same selection command to transfer ZIPs.")
            return 0
        archives_dir = output / "archives"
        pending = sum(entry.size_bytes for entry in selected if not (archives_dir / entry.filename).is_file())
        if shutil.disk_usage(output).free < pending:
            raise RuntimeError(f"Insufficient free space for {pending / 1e9:.3f} GB of pending archives")
        report["status"] = "downloading"
        save_json(report_path, report)
        try:
            for index, entry in enumerate(selected, 1):
                print(f"[{index}/{len(selected)}] {entry.filename}", flush=True)
                try:
                    path = download_archive(session, entry, archives_dir, args.timeout, args.attempts)
                    report["completed"].append({"filename": entry.filename, "bytes": path.stat().st_size, "sha256": file_sha256(path), "zip_crc_checked": True})
                except (requests.RequestException, OSError, RuntimeError, ValueError) as exc:
                    report["failed"].append({"filename": entry.filename, "error": str(exc)})
                    print(f"FAILED: {exc}", file=sys.stderr)
                save_json(report_path, report)
        except KeyboardInterrupt:
            report["status"] = "interrupted"
            save_json(report_path, report)
            raise
        report["status"] = "failed" if report["failed"] else "complete"
        save_json(report_path, report)
        print(f"Finished: {len(report['completed'])}/{len(selected)} verified archives. Audit: {report_path}")
        return 1 if report["failed"] else 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("Interrupted; rerun the same command to resume .part files.", file=sys.stderr)
        raise SystemExit(130)
    except (requests.RequestException, OSError, RuntimeError, ValueError) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
