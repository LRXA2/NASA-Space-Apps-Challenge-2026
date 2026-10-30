#!/usr/bin/env python3
"""Download the 2016 LOLA Lunar Polar Illumination products from NASA.

Default scope: ALL ten SOUTH-pole maps, each as original IMG + PDS LBL,
converted PGDA GeoTIFF, and the 2016 source README (31 files total).

Read-only inventory by default; add --download for transfers.

Requires: pip install requests beautifulsoup4
"""
from __future__ import annotations

import argparse
import csv
import json
import re
import shutil
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup

PDS_BASE = (
    "https://pds-geosciences.wustl.edu/lro/lro-l-lola-3-rdr-v1/"
    "lrolol_1xxx/extras/illumination/"
)
PDS_IMG = PDS_BASE + "img/"
PGDA_PAGE = "https://pgda.gsfc.nasa.gov/products/69"
PGDA_DATA = "https://pgda.gsfc.nasa.gov/data/MoonIllumination/"
MIT_IMG = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/IMG/"
MIT_README = "https://imbrium.mit.edu/EXTRAS/ILLUMINATION/README_ILLUMINATION_2016.TXT"

HEADERS = {"User-Agent": "Lunar-Illumination-Research-Downloader/1.0 (NASA open science data; serial requests)"}


@dataclass
class FileSpec:
    category: str
    hemisphere: str
    resolution_m: int
    format: str
    filename: str
    url: str
    relative_path: str
    size_bytes: int | None = None
    size_status: str = "unknown"
    fallback_url: str = ""


def category_of(stem: str) -> str:
    s = stem.upper()
    if s.startswith("LPSR_"):
        return "permanent_shadow"
    if s.startswith("SKYV_"):
        return "sky_visibility"
    if s.startswith("AVGVISIB_") and s.endswith("_EARTH"):
        return "earth_visibility"
    if s.startswith("AVGVISIB_"):
        return "solar_illumination"
    raise ValueError(f"Unexpected NASA file name: {stem}")


def products(pole: str) -> list[tuple[str, str, int]]:
    suffix = "S" if pole == "south" else "N"
    result = []
    for lat, meters in [(65, 240), (75, 120), (85, 60)]:
        tag = f"{lat}{suffix}_{meters:03d}M_201608"
        result.extend([
            (f"AVGVISIB_{tag}", pole, meters),
            (f"AVGVISIB_{tag}_EARTH", pole, meters),
            (f"LPSR_{tag}", pole, meters),
        ])
    result.append((f"SKYV_65{suffix}_240M", pole, 240))
    return result


def size_from_index(anchor) -> int | None:
    # IIS listings put a decimal byte count immediately before <a>.
    text = str(anchor.previous_sibling or "").strip()
    matches = re.findall(r"(?<!\d)\d{4,}(?!\d)", text)
    return int(matches[-1]) if matches else None


def get_index(session: requests.Session, url: str, timeout: int) -> tuple[str, dict[str, tuple[str, int | None]]]:
    resp = session.get(url, timeout=(20, timeout))
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    index = {}
    for a in soup.find_all("a", href=True):
        href = a["href"].split("?", 1)[0]
        name = unquote(urlparse(href).path.rstrip("/").split("/")[-1])
        if not name or name in ("..", "."):
            continue
        index[name.lower()] = (urljoin(url, a["href"]), size_from_index(a))
    return resp.text, index


def probe_size(session: requests.Session, url: str, timeout: int) -> tuple[int | None, str]:
    # A HEAD request should never download the raster itself.
    try:
        r = session.head(url, allow_redirects=True, timeout=(20, timeout))
        if r.ok:
            value = r.headers.get("Content-Length", "")
            if value.isdigit():
                return int(value), "HEAD"
            return None, "HEAD_no_length"
        if r.status_code in (404, 410):
            return None, f"unavailable_HTTP_{r.status_code}"
        # HEAD unsupported by some file servers: use a 1-byte ranged GET.
        with session.get(url, headers={"Range": "bytes=0-0"},
                         stream=True, timeout=(20, timeout)) as r2:
            if r2.status_code in (404, 410):
                return None, f"unavailable_HTTP_{r2.status_code}"
            r2.raise_for_status()
            content_range = r2.headers.get("Content-Range", "")
            m = re.search(r"/(\d+)\s*$", content_range)
            if m:
                return int(m.group(1)), "GET_range"
            # Some servers ignore Range and return 200; stream=True prevents a full download.
            length = r2.headers.get("Content-Length", "")
            if length.isdigit() and r2.status_code == 200:
                return int(length), "GET_headers"
            return None, "size_unknown"
    except requests.RequestException as exc:
        return None, f"probe_failed_{type(exc).__name__}"


def make_manifest(session: requests.Session, poles: list[str], timeout: int,
                  include_originals: bool, include_tif: bool, output: Path) -> list[FileSpec]:
    output.joinpath("manifests").mkdir(parents=True, exist_ok=True)
    original_html, pds_files = get_index(session, PDS_IMG, timeout)
    output.joinpath("manifests/pds_img_index.html").write_text(original_html, encoding="utf-8")
    pgda_files = {}
    if include_tif:
        pgda_html, _ = get_index(session, PGDA_PAGE, timeout)
        output.joinpath("manifests/pgda_product69_snapshot.html").write_text(pgda_html, encoding="utf-8")
        soup = BeautifulSoup(pgda_html, "html.parser")
        for a in soup.find_all("a", href=True):
            resolved = urljoin(PGDA_PAGE, a["href"])
            path = urlparse(resolved).path
            if path.lower().startswith("/data/moonillumination/") and path.lower().endswith(".tif") and not path.lower().endswith("_cog.tif"):
                stem = Path(path).stem.upper()
                pgda_files[stem] = resolved

    manifest = []
    for pole in poles:
        for stem, hemisphere, resolution in products(pole):
            category = category_of(stem)
            for ext in ([".img", ".lbl"] if include_originals else []):
                name = (stem + ext).lower()
                entry = pds_files.get(name)
                if not entry:
                    raise RuntimeError(f"Expected original {name} not listed at {PDS_IMG}; NASA archive may have changed")
                url, size = entry
                manifest.append(FileSpec(
                    category, hemisphere, resolution, ext[1:].upper(), name, url,
                    str(Path("original_pds") / hemisphere / category / name),
                    size, "PDS_listing" if size is not None else "unknown",
                    MIT_IMG + name.upper(),
                ))
            if include_tif:
                if stem.upper() not in pgda_files:
                    raise RuntimeError(f"Expected TIF for {stem} missing from {PGDA_PAGE}. No URL will be guessed.")
                url = pgda_files[stem.upper()]
                filename = Path(urlparse(url).path).name
                manifest.append(FileSpec(
                    category, hemisphere, resolution, "TIF", filename, url,
                    str(Path("geotiff") / hemisphere / category / filename)
                ))

    if include_originals:
        _, pds_root = get_index(session, PDS_BASE, timeout)
        readme = pds_root.get("readme_illumination_2016.txt")
        if readme is None:
            raise RuntimeError(f"Expected 2016 README not listed at {PDS_BASE}")
        manifest.append(FileSpec(
            "documentation", "all", 0, "TXT", "readme_illumination_2016.txt",
            readme[0], "documentation/readme_illumination_2016.txt",
            readme[1], "PDS_listing" if readme[1] is not None else "unknown",
            MIT_README,
        ))

    for f in manifest:
        if f.size_bytes is None:
            f.size_bytes, f.size_status = probe_size(session, f.url, timeout)

    expected = 10 * len(poles) * ((2 if include_originals else 0) + (1 if include_tif else 0)) + (1 if include_originals else 0)
    if len(manifest) != expected:
        raise RuntimeError(f"Expected {expected} files, found {len(manifest)}")
    return manifest


def write_manifest(files: list[FileSpec], output: Path):
    path = output / "manifests" / "download_manifest.csv"
    with path.open("w", newline="", encoding="utf-8-sig") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(asdict(files[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(f) for f in files)
    return path


def fmt_size(n: int | None) -> str:
    if n is None:
        return "unknown"
    return f"{n / 1024**2:,.1f} MiB ({n:,} bytes)"


def valid_existing(dest: Path, spec: FileSpec, completed: dict) -> bool:
    if not dest.is_file():
        return False
    size = dest.stat().st_size
    if spec.size_bytes is not None:
        return size == spec.size_bytes
    receipt = completed.get(spec.relative_path, {})
    return receipt.get("url") == spec.url and receipt.get("size_bytes") == size and size > 0


def fetch_one(session: requests.Session, spec: FileSpec, dest: Path,
              timeout: int, retries: int, delay: float) -> int:
    dest.parent.mkdir(parents=True, exist_ok=True)
    part = Path(str(dest) + ".part")
    last_error = None
    sources = [spec.url] + ([spec.fallback_url] if spec.fallback_url else [])
    for source_index, source_url in enumerate(sources):
        # We cannot safely append a partial transfer from another server
        # without a published checksum showing byte-for-byte identity.
        if source_index and part.exists():
            part.unlink()
        for attempt in range(1, retries + 1):
            existing = part.stat().st_size if part.exists() else 0
            if spec.size_bytes is not None and existing > spec.size_bytes:
                part.unlink()
                existing = 0
            headers = {"Range": f"bytes={existing}-"} if existing else {}
            try:
                with session.get(source_url, headers=headers, stream=True,
                                 timeout=(20, timeout)) as response:
                    if response.status_code == 416 and spec.size_bytes == existing:
                        part.replace(dest)
                        return existing
                    response.raise_for_status()
                    if existing and response.status_code == 206:
                        cr = response.headers.get("Content-Range", "")
                        m = re.match(r"bytes\s+(\d+)-\d+/", cr, re.I)
                        if not m or int(m.group(1)) != existing:
                            raise IOError(f"Unexpected Content-Range on resume: {cr!r}")
                        file_mode = "ab"
                    elif existing and response.status_code == 200:
                        # HTTP Range ignored: restart instead of corrupting file.
                        file_mode = "wb"
                        existing = 0
                    elif not existing and response.status_code in (200, 206):
                        file_mode = "wb"
                    else:
                        raise IOError(f"Unexpected HTTP status {response.status_code}")
                    total = existing
                    last_log = time.monotonic()
                    with part.open(file_mode) as out:
                        for chunk in response.iter_content(chunk_size=2 * 1024 * 1024):
                            if not chunk:
                                continue
                            out.write(chunk)
                            total += len(chunk)
                            if time.monotonic() - last_log >= 8:
                                print(f"      {total / 1024**2:,.1f} MiB received", flush=True)
                                last_log = time.monotonic()
                if spec.size_bytes is not None and total != spec.size_bytes:
                    raise IOError(f"Size mismatch: got {total}, expected {spec.size_bytes}")
                # Also check against the response's own length when available.
                part.replace(dest)
                return total
            except (requests.RequestException, OSError, IOError) as exc:
                last_error = exc
                print(f"    Attempt {attempt}/{retries} failed: {type(exc).__name__}: {exc}", file=sys.stderr)
                if attempt < retries:
                    time.sleep(min(15.0, delay + 2**(attempt-1)))
        if source_index == 0 and spec.fallback_url:
            print("    Primary source exhausted. Retrying from the MIT mirror from byte 0.")
    raise RuntimeError(f"All download attempts failed for {spec.filename}: {last_error}")


def persist_json(path: Path, values: dict):
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(values, indent=2, sort_keys=True), encoding="utf-8")
    tmp.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    parser.add_argument("--output", type=Path, default=Path("LOLA_Illumination_2016"), help="Output directory")
    parser.add_argument("--download", action="store_true", help="Transfer data files (default: INVENTORY ONLY)")
    parser.add_argument("--hemisphere", choices=("south", "both"), default="south", help="Default: south")
    parser.add_argument("--skip-img", action="store_true", help="Do not download IMG/LBL originals or README")
    parser.add_argument("--skip-tif", action="store_true", help="Do not download converted GeoTIFFs")
    parser.add_argument("--timeout", type=int, default=90, help="Read timeout per HTTP request in seconds")
    parser.add_argument("--retries", type=int, default=3)
    parser.add_argument("--delay", type=float, default=0.5, help="Delay between file transfers")
    args = parser.parse_args()
    if args.skip_img and args.skip_tif:
        parser.error("Cannot use --skip-img and --skip-tif together")
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    poles = ["south", "north"] if args.hemisphere == "both" else ["south"]
    with requests.Session() as session:
        session.headers.update(HEADERS)
        print("Retrieving NASA directory indexes...", flush=True)
        try:
            files = make_manifest(session, poles, args.timeout, not args.skip_img, not args.skip_tif, output)
        except (requests.RequestException, RuntimeError) as exc:
            print(f"ERROR building manifest: {exc}", file=sys.stderr)
            return 1
        manifest_path = write_manifest(files, output)
        known = sum(f.size_bytes for f in files if f.size_bytes is not None)
        unknown = sum(f.size_bytes is None for f in files)
        print(f"\nManifest: {manifest_path}")
        print(f"Files: {len(files)} ({unknown} with unknown remote size)")
        print(f"Known download total: {fmt_size(known)}")
        for category in ("solar_illumination", "permanent_shadow", "earth_visibility", "sky_visibility", "documentation"):
            subset = [f for f in files if f.category == category]
            if subset:
                print(f"  {category}: {len(subset)} files; {fmt_size(sum(f.size_bytes or 0 for f in subset))}")
        unavailable = [f for f in files if "unavailable" in f.size_status]
        if unavailable:
            print("Warning: URLs reporting unavailable during size checks:")
            for f in unavailable:
                print(" ", f.url)
        receipts_path = output / "manifests" / "completed_downloads.json"
        completed = json.loads(receipts_path.read_text(encoding="utf-8")) if receipts_path.exists() else {}
        remaining_known = sum(f.size_bytes or 0 for f in files if not valid_existing(output / f.relative_path, f, completed))
        free = shutil.disk_usage(output).free
        print(f"Remaining known bytes: {fmt_size(remaining_known)}")
        print(f"Free disk space: {fmt_size(free)}")
        if unknown:
            print("NOTE: Size unknown for some files; size total is a LOWER BOUND.")
        if not args.download:
            print("\nINVENTORY ONLY. To download, rerun with --download.")
            return 0
        if free < remaining_known:
            print("ERROR: Not enough free disk space for known files.", file=sys.stderr)
            return 2
        failure_log = []
        for n, spec in enumerate(files, start=1):
            dest = output / spec.relative_path
            if valid_existing(dest, spec, completed):
                print(f"[{n}/{len(files)}] SKIP {spec.filename} (already verified)")
                continue
            print(f"[{n}/{len(files)}] GET {spec.filename} [{spec.category}; {fmt_size(spec.size_bytes)}]", flush=True)
            try:
                actual_size = fetch_one(session, spec, dest, args.timeout, args.retries, args.delay)
                completed[spec.relative_path] = {"url": spec.url, "size_bytes": actual_size, "timestamp_utc": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())}
                persist_json(receipts_path, completed)
                print(f"    OK: {fmt_size(actual_size)}")
            except RuntimeError as exc:
                failure_log.append((spec.relative_path, str(exc)))
                print(f"    ERROR: {exc}", file=sys.stderr)
            time.sleep(args.delay)
        if failure_log:
            failure_path = output / "manifests" / "failed_downloads.csv"
            with failure_path.open("w", newline="", encoding="utf-8") as fh:
                writer = csv.writer(fh)
                writer.writerow(["relative_path", "error"])
                writer.writerows(failure_log)
            print(f"\n{len(failure_log)} failed files. See {failure_path}. Rerun --download to retry.", file=sys.stderr)
            return 1
        print(f"\nAll {len(files)} files present and accounted for in {output}.")
        return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nInterrupted. Existing .part files are preserved for resuming.", file=sys.stderr)
        sys.exit(130)
