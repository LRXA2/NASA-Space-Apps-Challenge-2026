"""Inventory/download dated Geofabrik OSM PBF extracts for Earth support zones.

Requires requests. No clipping, feature extraction, or notebooks are run.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from datetime import UTC, datetime
from pathlib import Path
from urllib.parse import urlparse

import requests

BASE = "https://download.geofabrik.de/"
REGIONS = {
    "arizona": "north-america/us/arizona",
    "canary-islands": "africa/canary-islands",
    "chile": "south-america/chile",
    "bolivia": "south-america/bolivia",
    "northern-california": "north-america/us/california/norcal",
    "jordan": "asia/jordan",
}
PROJECT_REGIONS = ("arizona", "canary-islands", "chile", "bolivia")


def save_json(path: Path, value: object) -> None:
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(json.dumps(value, indent=2) + "\n", encoding="utf-8")
    temporary.replace(path)


def checksums(path: Path) -> tuple[str, str]:
    md5, sha = hashlib.md5(), hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            md5.update(chunk)
            sha.update(chunk)
    return md5.hexdigest(), sha.hexdigest()


def parse_checksum(text: str, filename: str) -> str:
    match = re.fullmatch(r"([0-9a-fA-F]{32})\s+\*?([^\r\n]+)\s*", text.strip())
    if match is None or match[2] != filename:
        raise ValueError(f"Unexpected publisher MD5 for {filename}")
    return match[1].lower()


def discover(session: requests.Session, region: str, timeout: int, date: str | None = None) -> dict:
    latest = BASE + REGIONS[region] + "-latest.osm.pbf"
    requested = BASE + REGIONS[region] + f"-{date}.osm.pbf" if date else latest
    with session.head(requested, allow_redirects=True, timeout=(20, timeout)) as response:
        response.raise_for_status()
        url = response.url
        prefix = BASE + REGIONS[region]
        if not re.fullmatch(re.escape(prefix) + r"-\d{6}\.osm\.pbf", url):
            raise ValueError(f"Expected dated Geofabrik URL, got {url}")
        if date and url != requested:
            raise ValueError(f"Requested date redirected to a different source: {url}")
        size = int(response.headers.get("Content-Length", "0"))
        modified = response.headers.get("Last-Modified")
        if size <= 0 or not modified:
            raise ValueError(f"Missing size/date for {url}")
    filename = urlparse(url).path.rsplit("/", 1)[-1]
    checksum = session.get(url + ".md5", timeout=(20, timeout))
    checksum.raise_for_status()
    return {"region": region, "url": url, "filename": filename, "size_bytes": size,
            "md5": parse_checksum(checksum.text, filename), "checksum_text": checksum.text,
            "last_modified": modified, "latest_url": latest,
            "source_page": BASE + REGIONS[region] + ".html"}


def promote(partial: Path, final: Path, receipt: Path, source: dict, sha: str) -> None:
    """Record a verified transfer before publishing the completed filename."""
    save_json(receipt, {"source": source, "sha256": sha,
                       "verified_utc": datetime.now(UTC).isoformat()})
    partial.replace(final)


def download(session: requests.Session, source: dict, output: Path,
             timeout: int, attempts: int, chunk_bytes: int | None = None) -> str:
    if chunk_bytes is not None and (isinstance(chunk_bytes, bool) or not isinstance(chunk_bytes, int) or chunk_bytes < 1):
        raise ValueError("Chunk bytes must be a positive integer")
    filename = source["filename"]
    if Path(filename).name != filename or "/" in filename or "\\" in filename:
        raise ValueError("Invalid extract filename")
    output.mkdir(parents=True, exist_ok=True)
    final = output / filename
    partial = output / (filename + ".part")
    receipt = output / (filename + ".json")
    if final.exists():
        recorded = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        md5, sha = checksums(final)
        if (recorded.get("source") != source or final.stat().st_size != source["size_bytes"]
                or md5 != source["md5"] or recorded.get("sha256") != sha):
            raise ValueError(f"Existing file/receipt mismatch; preserved: {final}")
        return "verified_existing"
    restart = False
    for attempt in range(attempts):
        try:
            offset = partial.stat().st_size if partial.exists() and not restart else 0
            if offset == source["size_bytes"]:
                md5, sha = checksums(partial)
                if md5 == source["md5"]:
                    promote(partial, final, receipt, source, sha)
                    return "downloaded"
            if offset >= source["size_bytes"]:
                offset = 0
            while offset < source["size_bytes"]:
                end = min(offset + chunk_bytes, source["size_bytes"]) - 1 if chunk_bytes else source["size_bytes"] - 1
                headers = {"Accept-Encoding": "identity"}
                if chunk_bytes:
                    headers["Range"] = f"bytes={offset}-{end}"
                elif offset:
                    headers["Range"] = f"bytes={offset}-"
                with session.get(source["url"], headers=headers, stream=True,
                                 timeout=(20, timeout)) as response:
                    response.raise_for_status()
                    if response.status_code == 206:
                        expected = f"bytes {offset}-{end}/{source['size_bytes']}"
                        if response.headers.get("Content-Range") != expected:
                            raise ValueError("Unexpected Content-Range; partial preserved")
                    elif response.status_code == 200:
                        offset = 0
                        end = source['size_bytes'] - 1
                    else:
                        raise ValueError(f"Unexpected HTTP status {response.status_code}")
                    with partial.open("ab" if offset else "wb") as stream:
                        for chunk in response.iter_content(1024 * 1024):
                            stream.write(chunk)
                offset = partial.stat().st_size
                if offset != end + 1:
                    raise ValueError("Range response body size differs from requested span")
                if chunk_bytes:
                    print(f"  {filename}: {offset}/{source['size_bytes']} bytes", flush=True)
            if partial.stat().st_size != source["size_bytes"]:
                raise ValueError("Downloaded size differs from pinned source")
            md5, sha = checksums(partial)
            if md5 != source["md5"]:
                restart = True
                raise ValueError("Publisher MD5 mismatch; retry will restart this file")
            promote(partial, final, receipt, source, sha)
            return "downloaded"
        except (requests.RequestException, OSError, ValueError) as error:
            if attempt + 1 == attempts:
                raise RuntimeError(f"Failed {filename}: {error}") from error
            print(f"Attempt {attempt + 1}/{attempts}: {error}", flush=True)
            time.sleep(min(2 ** attempt, 10))
    raise ValueError("Attempts must be positive")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    selection = parser.add_mutually_exclusive_group(required=True)
    selection.add_argument("--project-areas", action="store_true",
                           help="Arizona, Canary Islands, Chile and Bolivia (Atacama border coverage)")
    selection.add_argument("--regions", choices=list(REGIONS), nargs="+")
    parser.add_argument("--output", type=Path, default=Path("data/raw/earth/osm"))
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=3)
    parser.add_argument("--date", help="Pin an available Geofabrik extract date, YYMMDD; otherwise discover latest")
    parser.add_argument("--chunk-bytes", type=int, help="Optional positive maximum HTTP Range span for large transfers")
    args = parser.parse_args()
    if args.date:
        try:
            if not re.fullmatch(r"\d{6}", args.date):
                raise ValueError("Expected six digits")
            datetime.strptime(args.date, "%y%m%d")
        except ValueError:
            parser.error("Date must be a valid YYMMDD calendar date")
    if args.timeout < 1 or args.attempts < 1:
        parser.error("Timeout and attempts must be positive")
    if args.chunk_bytes is not None and args.chunk_bytes < 1:
        parser.error("Chunk bytes must be positive")
    regions = list(PROJECT_REGIONS) if args.project_areas else list(dict.fromkeys(args.regions))
    manifests = args.output / "manifests"
    manifests.mkdir(parents=True, exist_ok=True)
    selection_path = manifests / "selection.json"
    with requests.Session() as session:
        if selection_path.exists():
            plan = json.loads(selection_path.read_text(encoding="utf-8"))
            if set(plan["regions"]) != set(regions):
                parser.error("Output already has a different pinned selection; choose a new --output")
            sources = plan["sources"]
            if args.date and any(not source["filename"].endswith(f"-{args.date}.osm.pbf") for source in sources):
                parser.error("Output has a different pinned date; choose a new --output")
            print("Reusing saved dated selection.", flush=True)
        else:
            sources = [discover(session, region, args.timeout, args.date) for region in regions]
            plan = {"regions": regions, "sources": sources,
                    "created_utc": datetime.now(UTC).isoformat(),
                    "attribution": "© OpenStreetMap contributors; extracts by Geofabrik",
                    "license": "ODbL 1.0", "license_url": "https://www.openstreetmap.org/copyright",
                    "purpose": "Support-zone logistics; not terrain CNN inputs"}
            save_json(selection_path, plan)
        for source in sources:
            print(f"{source['filename']}: {source['size_bytes'] / 1e6:.1f} MB", flush=True)
        print(f"Total: {sum(s['size_bytes'] for s in sources) / 1e6:.1f} MB", flush=True)
        if not args.download:
            print(f"Plan saved to {selection_path}. Add --download to fetch PBF files.")
            return 0
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S%fZ")
        run_path = manifests / f"{stamp}_run.json"
        record = {"status": "running", "selection": plan, "completed": [],
                  "timeout": args.timeout, "attempts": args.attempts, "chunk_bytes": args.chunk_bytes}
        save_json(run_path, record)
        try:
            for source in sources:
                print(f"Downloading/verifying {source['filename']}", flush=True)
                status = download(session, source, args.output / "extracts", args.timeout, args.attempts, args.chunk_bytes)
                record["completed"].append({"filename": source["filename"], "status": status})
                save_json(run_path, record)
        except (Exception, KeyboardInterrupt) as error:
            record["status"] = "interrupted" if isinstance(error, KeyboardInterrupt) else "failed"
            record["error"] = str(error)
            save_json(run_path, record)
            raise
        record["status"] = "complete"
        save_json(run_path, record)
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
        print(f"Error: {error}", file=sys.stderr)
        sys.exit(1)
