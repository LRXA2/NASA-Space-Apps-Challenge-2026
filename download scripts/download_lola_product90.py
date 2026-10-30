#!/usr/bin/env python3
"""Inventory and download the NASA PGDA Product 90 file links.

Usage (Windows PowerShell / terminal):
  pip install requests beautifulsoup4
  python download_lola_product90.py
  python download_lola_product90.py --download --output "D:/NASA/Lunar/LOLA_Product_90"
  python download_lola_product90.py --download --exclude-pointclouds

The default action only fetches the HTML catalog and writes a CSV manifest.
Downloads are streamed to .part files and can resume if interrupted.
"""

from __future__ import annotations

import argparse
import csv
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urljoin, urlparse, unquote

try:
    import requests
    from bs4 import BeautifulSoup
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
except ImportError as exc:
    raise SystemExit("Install dependencies first: pip install requests beautifulsoup4") from exc

PAGE = "https://pgda.gsfc.nasa.gov/products/90"
ALLOWED_HOST = "pgda.gsfc.nasa.gov"
DATA_PATH = "/data/LOLA_20mpp/"
EXTENSIONS = {".tif", ".csv", ".dbf", ".prj", ".shp", ".shx", ".xyzi"}


@dataclass(frozen=True)
class FileEntry:
    name: str
    url: str
    category: str
    stated_size: str
    stated_size_bytes: int | None


def category(name: str) -> str:
    upper = name.upper()
    if upper.endswith(".XYZI"):
        return "point_clouds"
    if upper.startswith("LPSR_"):
        return "permanent_shadow"
    if upper.startswith("LDRM_"):
        return "roughness"
    if upper.startswith("M") and "20MPP" in upper:
        return "nac_images"
    if upper.startswith(("LDEM_", "LDSM_", "LDEC_")):
        return "large_area_dem"
    return "other"


def parse_stated_size(anchor) -> tuple[str, int | None]:
    """Read the human-readable file size printed after a link on NASA's page."""
    bits = []
    sibling = anchor.next_sibling
    for _ in range(3):
        if sibling is None or getattr(sibling, "name", None) == "a":
            break
        bits.append(sibling.get_text(" ", strip=True) if hasattr(sibling, "get_text") else str(sibling))
        sibling = sibling.next_sibling
    text = " ".join(bits)
    match = re.search(r"\s*-\s*([\d.]+)\s*([KMGT])(?:i?B)?\b", text, flags=re.I)
    if not match:
        return "", None
    qty = float(match.group(1))
    unit = match.group(2).upper()
    return f"{qty:g}{unit}", int(qty * (1000 ** {"K": 1, "M": 2, "G": 3, "T": 4}[unit]))


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": "Lunar-Research-Archive-Downloader/1.0"})
    retry = Retry(
        total=5,
        connect=5,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({"GET", "HEAD"}),
        respect_retry_after_header=True,
    )
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def discover(session: requests.Session, output: Path) -> list[FileEntry]:
    response = session.get(PAGE, timeout=(20, 60))
    response.raise_for_status()
    (output / "source_page_snapshot.html").write_text(response.text, encoding="utf-8")
    soup = BeautifulSoup(response.text, "html.parser")
    found: dict[str, FileEntry] = {}
    for anchor in soup.find_all("a", href=True):
        url = urljoin(PAGE, anchor["href"])
        parsed = urlparse(url)
        if parsed.hostname != ALLOWED_HOST or not parsed.path.lower().startswith(DATA_PATH.lower()):
            continue  # Avoid links outside the Product 90 NASA-hosted dataset.
        name = Path(unquote(parsed.path)).name
        if Path(name).suffix.lower() not in EXTENSIONS:
            continue
        if not name or name in found:
            continue
        stated_size, size_bytes = parse_stated_size(anchor)
        found[name] = FileEntry(name, url, category(name), stated_size, size_bytes)
    if not found:
        raise RuntimeError("No matching NASA data links found; the website's layout may have changed.")
    return sorted(found.values(), key=lambda f: (f.category, f.name))


def write_manifest(entries: list[FileEntry], output: Path) -> None:
    with (output / "download_manifest.csv").open("w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(["filename", "category", "advertised_size", "estimated_bytes", "url"])
        for entry in entries:
            writer.writerow([entry.name, entry.category, entry.stated_size,
                             entry.stated_size_bytes or "", entry.url])


def print_plan(entries: list[FileEntry], output: Path) -> None:
    print(f"\nNASA source: {PAGE}")
    print(f"Discovered {len(entries)} dataset files, writing to: {output}")
    print("File categories:")
    for name in sorted({e.category for e in entries}):
        subset = [e for e in entries if e.category == name]
        print(f"  {name:23} {len(subset):4} files")
    known_bytes = sum(e.stated_size_bytes or 0 for e in entries)
    if known_bytes:
        missing = sum(e.stated_size_bytes is None for e in entries)
        print(f"NASA-advertised combined size: ~{known_bytes / 1e9:.1f} GB"
              + (f" (+ {missing} files without listed sizes)" if missing else ""))
    print("Saved download_manifest.csv and source_page_snapshot.html.")
    print("WARNING: full download includes two very large .XYZI point clouds (13G and 48G).")


def transfer(session: requests.Session, entry: FileEntry, output: Path) -> None:
    folder = output / entry.category
    folder.mkdir(exist_ok=True, parents=True)
    final = folder / entry.name
    partial = folder / f"{entry.name}.part"
    if final.is_file() and final.stat().st_size > 0:
        print(f"SKIP (exists): {entry.name}")
        return
    for attempt in range(1, 5):
        downloaded = partial.stat().st_size if partial.exists() else 0
        headers = {"Range": f"bytes={downloaded}-"} if downloaded else {}
        try:
            with session.get(entry.url, headers=headers, stream=True, timeout=(30, 120)) as response:
                if response.status_code == 416:
                    # A stale partial file; restart rather than accepting an unverified file.
                    partial.unlink(missing_ok=True)
                    continue
                response.raise_for_status()
                resumed = downloaded > 0 and response.status_code == 206
                if resumed:
                    start = response.headers.get("Content-Range", "")
                    if not start.startswith(f"bytes {downloaded}-"):
                        raise RuntimeError(f"Unexpected Content-Range: {start}")
                elif downloaded:
                    print(f"  Range request not honored; restarting {entry.name} from zero")
                mode = "ab" if resumed else "wb"
                expected = response.headers.get("Content-Length")
                expected_bytes = int(expected) if expected and expected.isdigit() else None
                received = 0
                with partial.open(mode) as file:
                    for chunk in response.iter_content(chunk_size=4 * 1024 * 1024):
                        if chunk:
                            file.write(chunk)
                            received += len(chunk)
                if expected_bytes is not None and received != expected_bytes:
                    raise OSError(f"Incomplete transfer: received {received}; expected {expected_bytes}")
                partial.replace(final)
                print(f"OK: {entry.category}/{entry.name} ({final.stat().st_size / 1e9:.2f} GB)")
                return
        except (requests.RequestException, OSError, RuntimeError) as exc:
            print(f"ERROR {entry.name} (attempt {attempt}/4): {exc}", file=sys.stderr)
            if attempt < 4:
                time.sleep(min(3 * attempt, 15))
    raise RuntimeError(f"Could not finish {entry.url}. Partial file retained for next run.")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="NASA_LOLA_Product_90", help="Folder for manifest and downloaded files")
    parser.add_argument("--download", action="store_true", help="Download all NASA-hosted files (default: inventory only)")
    parser.add_argument("--exclude-pointclouds", action="store_true", help="Skip two huge .XYZI source point clouds")
    parser.add_argument("--limit", type=int, default=0, help="For testing: download only first N matching files")
    parser.add_argument("--match", default="", help="Optional regex to download files matching their filename only")
    args = parser.parse_args()
    if args.limit < 0:
        parser.error("--limit must not be negative")
    output = Path(args.output).expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    with make_session() as session:
        entries = discover(session, output)
        write_manifest(entries, output)
        print_plan(entries, output)
        selected = [e for e in entries if not (args.exclude_pointclouds and e.category == "point_clouds")]
        if args.match:
            try:
                matcher = re.compile(args.match, flags=re.I)
            except re.error as exc:
                parser.error(f"Invalid --match regex: {exc}")
            selected = [e for e in selected if matcher.search(e.name)]
        if args.limit:
            selected = selected[:args.limit]
        if not args.download:
            print("\nInventory-only mode. Add --download to start downloading the listed files.")
            return
        print(f"\nDownloading {len(selected)} files. Press Ctrl+C to stop; rerun to resume.")
        failures = []
        for idx, entry in enumerate(selected, 1):
            print(f"[{idx}/{len(selected)}] {entry.category}/{entry.name}")
            try:
                transfer(session, entry, output)
            except RuntimeError as exc:
                failures.append((entry.name, str(exc)))
        if failures:
            with (output / "failed_downloads.csv").open("w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["filename", "error"])
                writer.writerows(failures)
            raise SystemExit(f"{len(failures)} files failed. Rerun to resume; see failed_downloads.csv")
        print("\nAll selected files downloaded successfully.")


if __name__ == "__main__":
    main()
