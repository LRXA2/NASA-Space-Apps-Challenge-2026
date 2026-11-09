"""Unified environmental downloader: core collections, Moon support and bounded research.

Default: inventory only. --download transfers; --dry-run is offline and writes nothing.
All data/manifests default to darrel stuff/data. Root download scripts are reused read-only.
Threaded per-file transfers, checked existing files, safe partials, bounded retries and logs.
See Download_Dataset_Instructions.md for scopes, exact selections and resume commands.

Targeted Diviner RDR (ODE/GDS), instead of the legacy D20 archive pilot:
  --diviner-ode --diviner-bbox WEST SOUTH EAST NORTH
  --diviner-start 2020-11-01 --diviner-stop 2020-11-08 --download
Dates/area are explicit research selections, not a mission profile. Default channels
are 7/8/9, all three quality flags default to zero, and count/byte caps apply.
--diviner-quality-max 0 12 0 explicitly includes definitive but unreprocessed
geometry for quality-aware EDA; it does not certify geometry or equipment suitability.
"""
from __future__ import annotations

import argparse

from datetime import datetime, timezone

from http.client import IncompleteRead

import json

import logging

import math

from pathlib import Path, PurePosixPath

import re

import shutil

import stat

import sys

import time

import zipfile

import zlib

import requests

from requests.adapters import HTTPAdapter

from urllib3.util.retry import Retry

from concurrent.futures import ThreadPoolExecutor, as_completed

import csv

import hashlib

import os

import struct

import threading

from urllib.parse import quote, unquote, urlencode, urljoin, urlsplit

import xml.etree.ElementTree as ET

from bs4 import BeautifulSoup

from pathlib import Path

import subprocess


ORIGINAL_SCRIPTS = Path(__file__).resolve().parents[2] / "download scripts"


DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data"

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_maintenance import atomic_text, cleanup_completed_transfer_state, write_error_log, resolve_data_path


def refresh_error_log(output):
    """Keep a human-readable current-gap index without changing transfer outcomes."""
    try:
        path = write_error_log(output)
        print("Missing/unresolved dataset report:", path, flush=True)
    except (OSError, ValueError) as error:
        print(f"Could not refresh error_log.txt; per-run logs retained: {error}", file=sys.stderr)


def clear_completed_transfer_state(output, path):
    try:
        cleanup_completed_transfer_state(output, path)
    except (OSError, ValueError) as error:
        LOG.warning("Completed file kept; redundant transfer metadata cleanup failed: %s", error)


ZENODO_RECORD = "17954508"


ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_RECORD}"


REGIONS = (
    "A3CLR22_10_Leibnitz_Beta_Plateau", "A3CLR22_11_Malapert_Massif",
    "A3CLR22_12_deGerlache_Kocher_Massif", "A3CLR22_2_Haworth",
    "A3CLR22_3_Faustini_Rim_A", "A3CLR22_4_deGerlache_Rim_2",
    "A3CLR22_5_Connecting_Ridge_Extension",
)


# These ancillary image/adjustment trees duplicate members kept in each original
# ZIP and are not inputs to the active environmental EDA/pipeline. Keep the ZIPs
# for recovery, but do not recreate the approved redundant extracted copies.
SDEM_ARCHIVE_ONLY_FOLDERS = frozenset({"LROC-NAC-maps", "LROC-NAC-adjust"})


LOLA_FILES = (
    "LDEM_80S_40MPP_ADJ.TIF", "LDEM_80S_40MPP_ADJ_EFFRES.TIF",
    "LDEM_80S_40MPP_ADJ_ERR.TIF", "LDEC_80S_40MPP_ADJ.TIF",
    "LDSM_80S_40MPP_ADJ.TIF", "LDSM_80S_40MPP_ADJ_ERR.TIF",
)


UNIT_POLICY = "reference/environment-readiness-20261028/native_layer_units.json"


LOG = logging.getLogger("darrel.environmental")


LOG.propagate = False


LOG.addHandler(logging.NullHandler())


def is_connection_error(error: BaseException) -> bool:
    """Recognise dropped connections even when an original helper wraps them."""
    pending, seen, chain = [error], set(), []
    while pending:
        current = pending.pop()
        if not isinstance(current, BaseException) or id(current) in seen:
            continue
        seen.add(id(current))
        chain.append(current)
        pending.extend([current.__cause__, current.__context__, getattr(current, "reason", None)])
        pending.extend(a for a in current.args if isinstance(a, BaseException))
    # SSL/certificate failures and HTTP responses are not a broken byte stream.
    if any(isinstance(e, (requests.exceptions.SSLError, requests.exceptions.HTTPError)) for e in chain):
        return False
    return any(isinstance(e, (requests.exceptions.ConnectionError, requests.exceptions.Timeout,
                              requests.exceptions.ChunkedEncodingError, IncompleteRead,
                              ConnectionError, TimeoutError)) for e in chain)


def is_transient_http_error(error):
    """Only typed responses qualify; never infer retryability from message text."""
    pending, seen = [error], set()
    while pending:
        current = pending.pop()
        if not isinstance(current, BaseException) or id(current) in seen:
            continue
        seen.add(id(current))
        if (isinstance(current, requests.HTTPError) and current.response is not None
                and current.response.status_code in {408, 429, 500, 502, 503, 504}):
            return True
        pending.extend([current.__cause__, current.__context__])
    return False


def retry_connections(operation, label, logger, retries=3, stop_event=None):
    """Initial attempt plus at most `retries` connection/transient-HTTP retries.

    Non-connection failures propagate to the caller's existing log-and-skip path.
    Each operation retains its normal bounded HTTP/body attempts and safe resume.
    """
    if type(retries) is not int or retries < 0:
        raise ValueError("Retries must be a non-negative integer")
    retry_count = 0
    while True:
        if stop_event is not None and stop_event.is_set():
            raise InterruptedError("Connection retry cancelled")
        try:
            return operation()
        except (requests.RequestException, RuntimeError, IncompleteRead, ConnectionError, TimeoutError) as error:
            if not (is_connection_error(error) or is_transient_http_error(error)):
                raise
            if retry_count >= retries:
                logger.error("Connection retry limit reached for %s; partial retained", label, exc_info=True)
                raise
            retry_count += 1
            delay = min(5 * 2 ** min(retry_count - 1, 4), 60)
            logger.warning("Connection failure for %s; retry batch=%s delay=%ss; partial retained",
                           label, retry_count, delay, exc_info=True)
            print(f"CONNECTION RETRY {retry_count}: {label} in {delay}s; partial retained. Ctrl+C to stop.",
                  file=sys.stderr, flush=True)
            if stop_event is None:
                time.sleep(delay)
            elif stop_event.wait(delay):
                raise InterruptedError("Connection retry cancelled")


def connection_attempts(operation, label, attempts):
    """One bounded batch, retrying connections only, never login/validation errors."""
    if type(attempts) is not int or attempts < 1:
        raise ValueError("Attempts must be a positive integer")
    if attempts == 1:
        return operation()
    return retry_connections(operation, label, LOG, retries=attempts - 1)


def original_helpers():
    """Reuse existing discovery, resumable transfer, checksums and atomic receipts."""
    if str(ORIGINAL_SCRIPTS) not in sys.path:
        sys.path.insert(0, str(ORIGINAL_SCRIPTS))
    import download_lola_product90 as lola
    import download_lunar_illumination_2016 as illumination
    import download_osm as transfer
    return lola, illumination, transfer


def destination(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Output escapes the data root: {relative}")
    return resolve_data_path(root, target)


def save_json(path: Path, value) -> None:
    atomic_text(path, json.dumps(value, indent=2, sort_keys=True) + "\n", logger=LOG)


def select_sdem_files(record: dict) -> list[dict]:
    """Select the exact seven development regions, never the unopened reserves."""
    if str(record.get("id")) != ZENODO_RECORD:
        raise ValueError("Unexpected Zenodo record; no substitute dataset is accepted")
    wanted = {region + ".zip" for region in REGIONS} | {"README.md"}
    selected = {}
    for item in record["files"]:
        name = item["key"]
        if name not in wanted:
            continue
        if name in selected:
            raise ValueError(f"Ambiguous archive entry: {name}")
        checksum = item["checksum"]
        if not re.fullmatch(r"md5:[0-9a-fA-F]{32}", checksum) or type(item["size"]) is not int or item["size"] <= 0:
            raise ValueError(f"Missing publisher size/checksum for {name}")
        url = item["links"]["self"]
        expected_url = f"https://zenodo.org/api/records/{ZENODO_RECORD}/files/{name}/content"
        if url != expected_url:
            raise ValueError(f"Unexpected archive URL: {url}")
        relative = "moon/sdem/archives/" + name if name.endswith(".zip") else "moon/sdem/README.md"
        selected[name] = {"filename": name, "url": url, "size_bytes": item["size"],
                          "md5": checksum[4:].lower(), "relative_path": relative,
                          "format": "ZIP" if name.endswith(".zip") else "MD",
                          "source_page": f"https://zenodo.org/records/{ZENODO_RECORD}"}
    if set(selected) != wanted:
        raise ValueError(f"Required Zenodo files missing: {sorted(wanted - set(selected))}")
    return [selected[name] for name in sorted(selected)]


def make_inventory(session: requests.Session, output: Path, run_dir: Path, timeout: int) -> list[dict]:
    lola, illumination, _ = original_helpers()
    response = session.get(ZENODO_API, timeout=(20, timeout))
    response.raise_for_status()
    record = response.json()
    save_json(run_dir / "zenodo_record.json", record)
    files = select_sdem_files(record)
    entries = {item.name: item for item in lola.discover(session, run_dir)}
    if not set(LOLA_FILES) <= set(entries):
        raise ValueError(f"Required LOLA products missing: {sorted(set(LOLA_FILES) - set(entries))}")
    for name in LOLA_FILES:
        item = entries[name]
        size, status = illumination.probe_size(session, item.url, timeout)
        if size is None or size <= 0:
            raise ValueError(f"Cannot establish exact remote size for {name}: {status}")
        files.append({"filename": name, "url": item.url, "size_bytes": size,
                      "relative_path": "moon/lola_product90/large_area_dem/" + name,
                      "format": "TIF", "source_page": lola.PAGE})
    # Labels/readme only: never request the large illumination IMG originals.
    for stem, category, resolution in illumination.products("south"):
        name = stem.lower() + ".lbl"
        url = illumination.PDS_IMG + name
        size, status = illumination.probe_size(session, url, timeout)
        if size is None or not 0 < size <= 1024 * 1024:
            raise ValueError(f"Unexpected/missing source-label size for {name}: {status}")
        files.append({"filename": name, "url": url, "size_bytes": size,
                      "relative_path": "moon/illumination_2016/documentation/labels/" + name,
                      "format": "LBL", "stem": stem, "category": category, "resolution_m": resolution})
    name = "readme_illumination_2016.txt"
    url = illumination.PDS_BASE + name
    size, status = illumination.probe_size(session, url, timeout)
    if size is None or not 0 < size <= 1024 * 1024:
        raise ValueError(f"Unexpected/missing illumination README: {status}")
    files.append({"filename": name, "url": url, "size_bytes": size,
                  "relative_path": "moon/illumination_2016/documentation/" + name, "format": "TXT"})
    for item in files:
        destination(output, item["relative_path"])
    return files


def saved_inventory(path: Path, output: Path) -> tuple[Path, list[dict]]:
    """Reuse an explicit prior discovery, never invent replacement URLs or sizes."""
    if str(path) == "latest":
        candidates = sorted((output / "manifests/moon_support").glob("*/run.json"), reverse=True)
        for candidate in candidates:
            record = json.loads(candidate.read_text(encoding="utf-8-sig"))
            if len(record.get("files", [])) == 25:
                path = candidate
                break
        else:
            raise ValueError("No prior complete 25-file Moon support inventory exists; source discovery must succeed first")
    record = json.loads(path.read_text(encoding="utf-8-sig"))
    files = record.get("files")
    if (not isinstance(files, list) or len(files) != 25 or record.get("regions") != list(REGIONS)
            or record.get("lola_files") != list(LOLA_FILES)):
        raise ValueError("Cached inventory must contain the exact original 25-file scope")
    publisher = json.loads(path.with_name("zenodo_record.json").read_text(encoding="utf-8-sig"))
    expected = {x["filename"]: x for x in select_sdem_files(publisher)}
    _, illumination, _ = original_helpers()
    for name in LOLA_FILES:
        expected[name] = {"filename": name, "url": "https://pgda.gsfc.nasa.gov/data/LOLA_20mpp/" + name,
                          "relative_path": "moon/lola_product90/large_area_dem/" + name, "format": "TIF"}
    for stem, category, resolution in illumination.products("south"):
        name = stem.lower() + ".lbl"
        expected[name] = {"filename": name, "url": illumination.PDS_IMG + name,
                          "relative_path": "moon/illumination_2016/documentation/labels/" + name,
                          "format": "LBL", "stem": stem, "category": category, "resolution_m": resolution}
    name = "readme_illumination_2016.txt"
    expected[name] = {"filename": name, "url": illumination.PDS_BASE + name,
                      "relative_path": "moon/illumination_2016/documentation/" + name, "format": "TXT"}
    cleaned, seen = [], set()
    for raw in files:
        item = {k: v for k, v in raw.items() if k != "status"}
        name = item.get("filename")
        if name not in expected or name in seen or type(item.get("size_bytes")) is not int or item["size_bytes"] <= 0:
            raise ValueError("Invalid, duplicate or unexpected cached file")
        if any(item.get(k) != v for k, v in expected[name].items()):
            raise ValueError(f"Cached source/path/metadata disagrees with the original product selection: {name}")
        destination(output, item["relative_path"])
        cleaned.append(item)
        seen.add(name)
    if seen != set(expected):
        raise ValueError("Cached Moon support inventory is incomplete")
    return path.resolve(), cleaned


def download_file(session: requests.Session, item: dict, output: Path, timeout: int, attempts: int) -> Path:
    """Preserve existing files; require receipts or a publisher checksum before reuse."""
    _, illumination, transfer = original_helpers()
    path = destination(output, item["relative_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    if "md5" in item:
        receipt = path.with_name(path.name + ".json")
        if path.exists() and not receipt.exists():
            md5, sha = transfer.checksums(path)
            if path.stat().st_size != item["size_bytes"] or md5 != item["md5"]:
                raise ValueError(f"Existing file disagrees with publisher checksum; preserved: {path}")
            # A publisher checksum can verify a previously downloaded archive without replacing it.
            save_json(receipt, {"source": item, "sha256": sha,
                                "verified_utc": datetime.now(timezone.utc).isoformat()})
            print(f"SKIP publisher-verified existing file: {path.name}", flush=True)
            return path
        # The original OSM helper is a generic byte/MD5 transfer routine; no OSM data is requested.
        connection_attempts(lambda: transfer.download(session, item, path.parent, timeout, 1), path.name, attempts)
        return path
    receipt = path.with_name(path.name + ".json")
    if path.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        if (saved.get("source") != item or path.stat().st_size != item["size_bytes"]
                or saved.get("sha256") != transfer.checksums(path)[1]):
            raise ValueError(f"Existing file/receipt mismatch; preserved: {path}")
        print(f"SKIP verified: {path.name}", flush=True)
        clear_completed_transfer_state(output, path)
        return path
    partial = path.with_name(path.name + ".part")
    identity = path.with_name(path.name + ".part.json")
    if partial.exists():
        if not identity.exists() or json.loads(identity.read_text(encoding="utf-8")) != item:
            raise ValueError(f"Partial source identity missing/changed; preserved: {partial}")
    else:
        save_json(identity, item)
    spec = illumination.FileSpec("moon_support", "south", item.get("resolution_m", 40), item["format"],
                                 item["filename"], item["url"], item["relative_path"], item["size_bytes"], "HEAD")
    def fetch_once():
        try:
            illumination.fetch_one(session, spec, path, timeout, 1, .5)
        except RuntimeError as error:
            # The unchanged original helper stringifies its final exception
            # without chaining it. Recover its typed last_error from that known
            # frame; never guess whether to retry from the message text.
            cursor = error.__traceback__
            helper_code = getattr(illumination.fetch_one, "__code__", None)
            while cursor is not None:
                if cursor.tb_frame.f_code is helper_code:
                    cause = cursor.tb_frame.f_locals.get("last_error")
                    if isinstance(cause, BaseException):
                        raise error from cause
                cursor = cursor.tb_next
            raise
    connection_attempts(fetch_once, path.name, attempts)
    if path.stat().st_size != item["size_bytes"]:
        raise ValueError(f"Unexpected downloaded size: {path}")
    if item["format"] == "TIF":
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            raise ValueError(f"Response is not a TIFF; preserved for inspection: {path}")
    save_json(receipt, {"source": item, "sha256": transfer.checksums(path)[1],
                        "verified_utc": datetime.now(timezone.utc).isoformat()})
    clear_completed_transfer_state(output, path)
    return path


def crc32_file(path: Path) -> int:
    crc = 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(8 * 1024 * 1024), b""):
            crc = zlib.crc32(block, crc)
    return crc & 0xFFFFFFFF


def archive_members(archive: zipfile.ZipFile, region: str, root: Path) -> list[tuple]:
    """Match notebook 01's extraction policy; validate every path before any write."""
    if region not in REGIONS:
        raise ValueError("Only the original seven SDEM regions are allowed")
    entries, seen = [], set()
    for entry in archive.infolist():
        # ZipInfo normalizes backslashes on Windows; check the unmodified archive name too.
        raw_name = entry.orig_filename
        relative = PurePosixPath(raw_name)
        if (relative.is_absolute() or ".." in relative.parts or "\\" in raw_name or "\x00" in raw_name
                or ":" in raw_name or stat.S_ISLNK(entry.external_attr >> 16) or entry.flag_bits & 1):
            raise ValueError(f"Unsafe/unsupported ZIP entry: {entry.filename}")
        if any(p in ("__MACOSX", ".DS_Store") or p.startswith("._") for p in relative.parts):
            continue
        if not relative.parts or relative.parts[0] != region:
            raise ValueError(f"Unexpected ZIP root: {entry.filename}")
        path = destination(root, "/".join(relative.parts))
        if entry.is_dir():
            continue
        key = str(path).casefold()
        if key in seen:
            raise ValueError(f"Duplicate ZIP destination: {entry.filename}")
        seen.add(key)
        entries.append((entry, path))
    names = [str(PurePosixPath(e.filename).relative_to(region)) for e, _ in entries]
    for suffix in ("_GLDELEV_005.tif", "_GLDMASK_005.tif"):
        if len([n for n in names if "/" not in n and n.endswith(suffix)]) != 1:
            raise ValueError(f"Missing/ambiguous {suffix} in {region}")
    if "README.txt" not in names:
        raise ValueError(f"Missing original region README in {region}")
    return entries


def extract_archive(path: Path, output: Path) -> None:
    root = destination(output, "moon/sdem/regions")
    region = path.stem
    root.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(path) as archive:
        all_entries = archive_members(archive, region, root)  # Validate even archive-only paths.
        archive_only = [(e, p) for e, p in all_entries
                        if p.relative_to(root / region).parts[0] in SDEM_ARCHIVE_ONLY_FOLDERS]
        entries = [(e, p) for e, p in all_entries
                   if p.relative_to(root / region).parts[0] not in SDEM_ARCHIVE_ONLY_FOLDERS]
        required = 0
        for entry, target in entries:
            if target.exists():
                if not target.is_file() or target.stat().st_size != entry.file_size or crc32_file(target) != entry.CRC:
                    raise ValueError(f"Existing extracted file conflicts; preserved: {target}")
            else:
                required += entry.file_size
        if shutil.disk_usage(root).free < required + 1024 ** 3:
            raise OSError(f"Insufficient extraction space for {region}: {required:,} bytes plus 1 GiB reserve")
        for entry, target in entries:
            if target.exists():
                continue  # Already CRC/size-verified above.
            target.parent.mkdir(parents=True, exist_ok=True)
            partial = target.with_name(target.name + ".extracting")
            with archive.open(entry) as source, partial.open("wb") as dest:
                shutil.copyfileobj(source, dest, length=1024 * 1024)
            if partial.stat().st_size != entry.file_size or crc32_file(partial) != entry.CRC:
                raise ValueError(f"Extraction CRC/size failed: {partial}")
            if target.exists():
                raise FileExistsError(f"Destination appeared during extraction; preserved: {target}")
            partial.replace(target)
    save_json(destination(output, f"moon/sdem/manifests/{region}_extracted.json"), {
        "archive": str(path), "region": region, "status": "complete",
        "files": [{"path": str(p.relative_to(root)), "bytes": e.file_size, "crc32": e.CRC} for e, p in entries],
        "archive_only_files": [{"path": str(p.relative_to(root)), "bytes": e.file_size, "crc32": e.CRC}
                               for e, p in archive_only],
        "extraction_policy": "Active terrain/quality layers extracted; ancillary LROC images/adjustments retained in original ZIP only",
    })
    print(f"Extracted/verified {region}: {len(entries)} active files; {len(archive_only)} ancillary files retained in ZIP only", flush=True)


def label_unit(text: str, stem: str) -> dict:
    """Validate the publisher's specific product/packing/semantics before documenting units."""
    text = text.replace("\r", "\n")

    def field(name):
        values = re.findall(r"^\s*" + re.escape(name) + r"\s*=\s*([^\n]+)", text, re.M)
        if len(values) != 1:
            raise ValueError(f"Missing/ambiguous PDS field {name}: {stem}")
        return values[0].strip().strip('"')

    if field("PRODUCT_ID") != stem or field("SAMPLE_TYPE") != "LSB_INTEGER" or field("SAMPLE_BITS") != "16":
        raise ValueError(f"Unexpected illumination product encoding: {stem}")
    if stem.startswith("SKYV_"):
        expected_scale, expected_offset, expected_unit, unit = .0002, 6.2832, "STERADIAN", "sr"
        if "solid angle" not in text.lower() or "steradian" not in text.lower():
            raise ValueError(f"Sky-view semantics not documented: {stem}")
    elif stem.startswith("LPSR_"):
        expected_scale, expected_offset, expected_unit, unit = .000025, .5, "NONE", "binary"
        if "binary" not in text.lower() or "permanent shadow" not in text.lower():
            raise ValueError(f"Shadow semantics not documented: {stem}")
    elif stem.startswith("AVGVISIB_"):
        expected_scale, expected_offset, expected_unit, unit = .00004, 0., "NONE", "fraction"
        if "visibility" not in text.lower() or not re.search(r"between\s+0", text, re.I):
            raise ValueError(f"Visibility fraction not documented: {stem}")
    else:
        raise ValueError(f"Unsupported illumination product: {stem}")
    scale, offset = float(field("SCALING_FACTOR")), float(field("OFFSET"))
    if (field("UNIT") != expected_unit or not math.isclose(scale, expected_scale, rel_tol=1e-12)
            or not math.isclose(offset, expected_offset, rel_tol=1e-12, abs_tol=1e-12)):
        raise ValueError(f"Publisher packing/units changed; review is required: {stem}")
    return {"unit": unit, "source_unit": expected_unit, "source_scale": scale, "source_offset": offset}


def write_unit_policy(output: Path, files: list[dict]) -> Path:
    _, _, transfer = original_helpers()
    rows = []
    for item in files:
        if item["format"] != "LBL":
            continue
        path = destination(output, item["relative_path"])
        units = label_unit(path.read_text(encoding="ascii"), item["stem"])
        digest = transfer.checksums(path)[1]
        for region in REGIONS:
            rows.append({"region": region, "file": item["stem"] + ".TIF", "status": "documented", **units,
                         "source_url": item["url"], "source_label": item["relative_path"],
                         "source_label_sha256": digest,
                         "evidence": "Publisher PDS label: product ID, description, UNIT and scale/offset verified"})
    if len(rows) != 70 or len({(r["region"], r["file"]) for r in rows}) != 70:
        raise ValueError("Expected all ten south-polar label products for each of seven regions")
    policy = destination(output, UNIT_POLICY)
    if policy.exists():
        existing = json.loads(policy.read_text(encoding="utf-8-sig"))
        if not isinstance(existing, list) or not all(isinstance(r, dict) and "region" in r and "file" in r for r in existing):
            raise ValueError(f"Unsupported existing unit-policy format; preserved: {policy}")
        lookup = {(r["region"], r["file"]): r for r in existing}
        if len(lookup) != len(existing):
            raise ValueError(f"Duplicate existing unit-policy rows; preserved: {policy}")
        core = {"AVGVISIB_85S_060M_201608.TIF", "AVGVISIB_85S_060M_201608_EARTH.TIF",
                "LPSR_85S_060M_201608.TIF", "SKYV_65S_240M.TIF"}
        for row in rows:
            if row["file"] not in core:
                continue
            old = lookup.get((row["region"], row["file"]), {})
            if old.get("status") != "documented" or old.get("unit") != row["unit"]:
                raise ValueError(f"Existing unit policy conflicts or is incomplete; preserved: {policy}")
        print(f"SKIP compatible existing unit policy: {policy}", flush=True)
    else:
        save_json(policy, rows)
        print(f"Documented unit policy written: {policy}", flush=True)
    return policy


def moon_support_main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--connection-retries", type=int, default=3,
                        help="Extra connection retries after the initial attempt (default 3; 0 disables)")
    parser.add_argument("--from-inventory", type=Path,
                        help="Use an exact previous run.json, or 'latest', without revisiting the NASA catalogue")
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.attempts < 1 or not 1 <= args.workers <= 16:
        parser.error("Timeout and attempts must be positive")
    if args.connection_retries < 0:
        parser.error("Connection retries must be non-negative")
    output = args.output.expanduser().resolve()
    print("Restore scope: seven original SDEM regions, six 40 m LOLA maps, illumination labels and documented units.")
    print("Data root:", output)
    if args.dry_run:
        for name in [*(r + ".zip" for r in REGIONS), *LOLA_FILES]:
            print(" ", name)
        print("Metadata: ten PDS labels, README; generate", UNIT_POLICY)
        print("Dry run only: no network, downloads, extraction or writes.")
        return 0
    run_dir = destination(output, "manifests/moon_support/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    run_dir.mkdir(parents=True, exist_ok=False)
    record = {"status": "inventory_started", "regions": list(REGIONS), "lola_files": list(LOLA_FILES),
              "connection_retry_batches": args.connection_retries, "attempts_per_batch": args.attempts}
    manifest = run_dir / "run.json"
    save_json(manifest, record)
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s %(message)s")
    formatter.converter = time.gmtime
    handlers = []
    for filename, level in (("debug.txt", logging.DEBUG), ("errors.txt", logging.WARNING)):
        handler = logging.FileHandler(run_dir / filename, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.setLevel(level)
        LOG.addHandler(handler)
        handlers.append(handler)
    LOG.setLevel(logging.DEBUG)
    LOG.info("Moon support start output=%s attempts=%s timeout=%s", output, args.attempts, args.timeout)
    LOG.info("Connection retry batches=%s (0=no extra retries); non-connection failures are logged/skipped", args.connection_retries)
    print("Debug log:", run_dir / "debug.txt", flush=True)
    print("Error log:", run_dir / "errors.txt", flush=True)
    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent": "Moon-Environmental-Support-Restorer/1.0", "Accept-Encoding": "identity"})
            retry = Retry(total=0)  # File/discovery operations own the retry budget.
            session.mount("https://", HTTPAdapter(max_retries=retry))
            if args.from_inventory:
                source, files = saved_inventory(args.from_inventory, output)
                _, _, helpers = original_helpers()
                record.update({"cached_inventory": str(source), "cached_inventory_sha256": helpers.checksums(source)[1],
                               "discovery_mode": "explicit cached selection; remote catalogue freshness not rechecked"})
                # Keep publisher evidence with this run so it can also be explicitly reused.
                save_json(run_dir / "zenodo_record.json", json.loads(source.with_name("zenodo_record.json").read_text(encoding="utf-8-sig")))
                print(f"Using prior exact inventory: {source}; bypassing catalogue discovery only.", flush=True)
                LOG.info("Using exact cached inventory %s sha256=%s", source, record["cached_inventory_sha256"])
            else:
                LOG.info("Fresh source discovery; HTTP retries enabled for transient status codes")
                files = retry_connections(lambda: make_inventory(session, output, run_dir, args.timeout),
                                          "Moon support source discovery", LOG, args.connection_retries)
            record.update({"status": "planned", "files": files, "download_bytes": sum(f["size_bytes"] for f in files)})
            save_json(manifest, record)
            print(f"Known transfers: {record['download_bytes'] / 1e9:.2f} GB. Extraction requires additional space.")
            print("Inventory:", manifest)
            LOG.info("Inventory ready files=%s total_bytes=%s download=%s", len(files), record["download_bytes"], args.download)
            if not args.download:
                print("Inventory only. Inspect the plan, then add --download to restore files and extract SDEMs.")
                return 0
            pending = sum(f["size_bytes"] for f in files if not destination(output, f["relative_path"]).exists())
            if shutil.disk_usage(output).free < pending + 1024 ** 3:
                raise OSError("Insufficient space for missing downloads plus a 1 GiB reserve; extraction is additional")
            record["status"] = "running"
            save_json(manifest, record)
            # First restore small documentation, then science files. All archives precede extraction.
            ordered = sorted(files, key=lambda f: f["format"] in ("ZIP", "TIF"))
            errors = []
            record["errors"] = errors
            original_helpers()
            STOP.clear()
            pool = ThreadPoolExecutor(max_workers=args.workers)
            futures = {pool.submit(moon_support_transfer, item, output, args): item for item in ordered}
            try:
                for future in as_completed(futures):
                    item = futures[future]
                    try:
                        future.result()
                    except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
                        LOG.exception("Skipping failed transfer %s source=%s", item["relative_path"], item["url"])
                        errors.append({"stage": "download", "path": item["relative_path"],
                                       "url": item["url"], "error": str(error)})
                        item["status"] = "failed"
                        print(f"SKIP failed {item['filename']}: {error}", file=sys.stderr, flush=True)
                    else:
                        item["status"] = "verified_present"
                    save_json(manifest, record)
            except KeyboardInterrupt:
                STOP.set()
                raise
            finally:
                pool.shutdown(wait=True, cancel_futures=True)
            # Independent postprocessing may proceed; never use failed/missing inputs.
            labels_ready = all(f["status"] == "verified_present" for f in files if f["format"] == "LBL")
            if labels_ready:
                try:
                    write_unit_policy(output, files)
                except (OSError, ValueError, RuntimeError) as error:
                    LOG.exception("Unit-policy generation failed; continuing with verified archives")
                    errors.append({"stage": "unit_policy", "error": str(error)})
            else:
                LOG.warning("Skipping unit policy: one or more required labels failed")
                record["unit_policy_status"] = "skipped_missing_labels"
            LOG.info("Begin independent extraction/CRC checks on verified archives")
            for item in files:
                if item["format"] == "ZIP" and item["status"] == "verified_present":
                    try:
                        extract_archive(destination(output, item["relative_path"]), output)
                    except (OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
                        LOG.exception("Skipping failed extraction %s; continuing with other archives", item["filename"])
                        errors.append({"stage": "extraction", "path": item["relative_path"], "error": str(error)})
                    save_json(manifest, record)
            regions_root = destination(output, "moon/sdem/regions")
            actual = {p.name for p in regions_root.iterdir() if p.is_dir()} if regions_root.exists() else set()
            record["missing_regions"] = sorted(set(REGIONS) - actual)
            if actual - set(REGIONS) or (not errors and actual != set(REGIONS)):
                raise ValueError("SDEM region scope differs from the original seven; no extra folders were removed")
            if errors:
                record["status"] = "failed"
                save_json(manifest, record)
                LOG.error("Restoration incomplete after continuing: %s errors; see errors.txt and run.json", len(errors))
                print(f"Finished remaining work; {len(errors)} errors recorded. Rerun to retry missing/failed inputs.", file=sys.stderr)
                return 1
            record["status"] = "complete"
            LOG.info("Moon support restoration complete")
            save_json(manifest, record)
            print("Moon support restoration complete. Run preprocessing 05/06/13, then EDA 25; TODO analyses remain separate.")
            return 0
    except KeyboardInterrupt:
        LOG.warning("Interrupted; files/partials preserved")
        record.update({"status": "interrupted", "error": "KeyboardInterrupt"})
        save_json(manifest, record)
        print("Interrupted; files/partials preserved. Rerun the same restore command.", file=sys.stderr)
        return 130
    except (requests.RequestException, OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        LOG.exception("Restoration failed; files/partials preserved")
        record.update({"status": "failed", "error": str(error)})
        save_json(manifest, record)
        print(f"Restore failed; existing data preserved: {error}", file=sys.stderr)
        if isinstance(error, requests.exceptions.SSLError):
            print("TLS verification remains enabled. Configure REQUESTS_CA_BUNDLE with a trusted CA if needed.", file=sys.stderr)
        elif isinstance(error, requests.RequestException):
            print("If catalogue discovery is unavailable, reuse a prior selection with --from-inventory latest. File-server outages may still require retrying later.", file=sys.stderr)
        return 1
    finally:
        for handler in handlers:
            LOG.removeHandler(handler)
            handler.close()


HERE = Path(__file__).resolve().parent


DEFAULT_OUTPUT = HERE.parent / "data"


REGISTER = HERE.parent / "research/environmental_data.csv"


PDS = "https://pds-geosciences.wustl.edu/"


DIVINER = PDS + "lro/urn-nasa-pds-lro_diviner_derived1/"


CATALOG = {
    "D01": {"kind": "core", "note": "Two seasonal PCP table/label groups; not the full 144 products."},
    "D02": {"kind": "core", "note": "60 m south solar visibility and permanent-shadow maps."},
    "D03": {"kind": "core", "note": "60 m south Earth visibility map."},
    "D04": {"kind": "core", "note": "240 m south sky-view map."},
    "D05": {"kind": "sdem", "note": "Original development regions only; archive-size cap applies. No extraction here."},
    "D06": {"kind": "lola", "note": "Selected original 40 m LOLA products only."},
    "D07": {"root": "https://pds-ppi.igpp.ucla.edu/data/lro-crater/data-der-sec/", "pattern": r"\.(tab|csv|dat)$", "note": "Derived secondary-detector daily products; not primary event tables or crew dose."},
    "D08": {"root": "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/goes16/l2/data/sgps-l2-avg5m/", "pattern": r"\.nc$"},
    "D09": {"kind": "direct", "urls": ["https://lasp.colorado.edu/data/sorce/ssi_data/solstice/fuv/txt/sorce_fuv_latest.txt.zip", "https://lasp.colorado.edu/data/sorce/ssi_data/solstice/muv/txt/sorce_muv_latest.txt.zip"], "note": "Two small published SOLSTICE FUV/MUV daily-mean packages; full time span within each file. URL validators are pinned in inventory."},
    "D10": {"root": "https://atmos.nmsu.edu/PDS/data/PDS4/LADEE/ldex_bundle/data_calibrated/", "pattern": r"\.(tab|csv|dat)$"},
    "D11": {"root": "https://spdf.gsfc.nasa.gov/pub/data/themis/thb/l2/merged/cdf/2013/", "pattern": r"\.cdf$", "note": "THB/P1 merged data, 2013; deterministic file pilot, not a complete event."},
    "D12": {"root": "https://pds-ppi.igpp.ucla.edu/data/lp-mag-calibrated/data-lunarcrds/", "pattern": r"\.(tab|csv|dat)$"},
    "D13": {"root": PDS + "lunar/urn-nasa-pds-apollo_seismic_event_catalog/data/", "pattern": r"(gagnepian_2006_catalog|lognonne_2003_catalog)\.csv$"},
    "D14": {"root": PDS + "lunar/urn-nasa-pds-apollo_pse/data/xa/continuous_waveform/s11/1969/", "pattern": r"\.(mseed|seed|csv|gz)$", "note": "Apollo station S11, 1969 waveform pilot; station response metadata still needed for physical interpretation."},
    "D15": {"kind": "s3", "base": "https://pds.mcp.nasa.gov/data/store/img/",
            "prefix": "lunar_reconnaissance_orbiter/pds4/lroc/lro-l-lroc-3-cdr/LROLRC_1001/DATA/MAP/",
            "pattern": r"M.*[LR]C\.IMG$", "note": "Calibrated NAC mapping-phase pilot from NASA's migrated PDS archive; no study-footprint overlap is asserted."},
    "D16": {"root": PDS + "lunar/lcross-e_l-mir1-2-raw-v1/lcro_0001/data/20091009104100_preimpact/nsp1/cal/", "pattern": r"\.(tab|dat|csv)$", "note": "LCROSS NSP1 calibrated pre-impact spectra only; parent archive also contains raw data, which is excluded by this collection root."},
    "D18": {"kind": "osdr", "note": "OSD-82 science/processed files plus study metadata; no claim of a complete sequence study."},
    "D19": {"kind": "direct", "group_urls": [
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/lsk/naif0012.tls",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/pck00011.tpc",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/spk/planets/a_old_versions/de421.bsp",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/pck/moon_pa_de421_1900-2050.bpc",
        "https://naif.jpl.nasa.gov/pub/naif/generic_kernels/fk/satellites/moon_080317.tf"],
        "note": "One five-kernel DE421/Moon-frame bundle; inspect actual kernel coverage before a dated calculation. Terrain horizons and operating geometry are separate inputs."},
    "D20": {"root": PDS + "lro/lro-l-dlre-4-rdr-v1/lrodlr_1001/data/2013/", "pattern": r"\.(tab|dat|zip)$", "note": "2013 calibrated records; individual files, not continuous ground sampling."},
    "D21": {"kind": "login", "note": "PRADAN ChaSTE release: authorised product/label URLs required via --selections."},
    "D22": {"kind": "login", "note": "PRADAN RAMBHA-LP release: authorised product/label URLs required via --selections."},
    "D23": {"kind": "login", "note": "PRADAN ILSA release: authorised product/label URLs required via --selections."},
    "D24": {"kind": "login", "note": "PRADAN DFSAR science mode/product and authorised URLs required via --selections."},
    "D26": {"root": "https://data.darts.isas.jaxa.jp/pub/pds3/sln-l-tc-5-dtm-map-v2.0/lon000/data/", "pattern": r"\.img$", "detached_pds3": True, "note": "Longitude-000 raw DTM pilot with separate PDS3 labels; footprint overlap with study regions is NOT asserted."},
    "D27": {"root": "https://pds.shadowcam.im-ldi.com/observation/2023/", "pattern": r"_map_raw\.tif$",
            "float32_tiff": True, "note": "2023 map-projected, unstretched calibrated-radiance COG pilot. Reject stretched COGs and require float32 TIFF samples."},
    "D28": {"root": PDS + "lunar/urn-nasa-pds-a15_17_hfe_concatenated/data/clean/", "pattern": r"\.(tab|csv|txt|dat)$"},
    "D29": {"root": PDS + "lro/lro-l-lend-2-edr-v1/lrolen_0xxx/data/", "pattern": r"(rdr|rdrs|rdrr)[^/]*\.(dat|tab|csv)$", "note": "Reduced products only; raw EDR is not a substitute."},
    "D30": {"root": PDS + "lro/lro-l-mrflro-5-global-mosaic-v1/lromrf_1001/data/", "pattern": r"\.(img|tif)$"},
    "D31": {"kind": "zenodo", "record": "7504128", "pattern": r"\.txt$"},
    "D32": {"root": "https://planetarydata.jpl.nasa.gov/img/data/lro/lro_lamp/gdr/LROLAM_2001/DATA/", "pattern": r"\.(img|fit|fits)$"},
    "D33": {"kind": "direct", "urls": ["https://pds.lroc.im-ldi.com/data/LRO-L-LROC-5-RDR-V1.0/LROLRC_2001/EXTRAS/SHAPEFILE/GLOBAL_NEW_CRATERS/GLOBAL_NEW_CRATERS_180.ZIP"], "note": "One complete published new-crater shapefile package in the -180/180 convention."},
    "D34": {"root": "https://planetarydata.jpl.nasa.gov/img/data/m3/CH1M3_0003/DATA/20081118_20090214/200811/L1B/", "pattern": r"_RDN\.IMG$", "note": "2008-11 M3 L1B calibrated radiance pilot plus labels; not a reflectance/mineral map or a verified polar overlap."},
    "D35": {"root": "https://atmos.nmsu.edu/PDS/data/PDS4/LADEE/nms_bundle/data_derived/", "pattern": r"\.(tab|csv|dat)$"},
    "D36": {"root": DIVINER + "data_derived_gdr_l3/cylindrical/", "pattern": r"\.(tab|img)$", "note": "Level-3 fitted surface-product pilot; check actual coverage before polar use."},
    "D37": {"kind": "direct", "urls": ["https://asc-astropedia.s3.us-west-2.amazonaws.com/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2.zip"], "note": "One published GIS package; may exceed the pilot byte limit."},
    "D38": {"root": DIVINER + "data_derived_gcp/", "pattern": r"global_cumul_avg_cyl_90s80s_002\.tab$", "note": "80S-90S cumulative product; not dated exposure or extremes."},
}


REFERENCE_SOURCES = {
    "R01": {
        "name": "NASA PCoE Li-ion battery reference experiments",
        "sources": "https://www.nasa.gov/intelligent-systems-division/discovery-and-systems-health/pcoe/pcoe-data-set-repository/",
        "kind": "direct",
        "group_urls": ["https://phm-datasets.s3.amazonaws.com/NASA/5.+Battery+Data+Set.zip"],
        "relative_root": "reference/battery_tests",
        "note": "One published reference ZIP (~200 MiB); lab charge/discharge/impedance data, not our battery specification or lunar qualification. No automatic extraction.",
    },
    "R02": {
        "name": "Apollo 15 LSRP soil-mechanics reference tables",
        "sources": "https://pds-geosciences.wustl.edu/missions/apollo/a15lsrp.htm",
        "kind": "direct",
        "group_urls": [
            "https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-a15lsrp_soil_mechanics/data/"
            + f"a15_smss_71_m016935_{run:03d}.{ext}"
            for run in range(11, 17) for ext in ("tab", "txt", "xml")
        ] + [
            "https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-a15lsrp_soil_mechanics/document/" + name
            for name in ("dataset_description.txt", "dataset_description.xml", "a15l_lsrp.txt", "a15l_lsrp.xml")
        ],
        "relative_root": "reference/apollo15_soil",
        "note": "One small group: all six digitized Apollo 15 runs, numeric tables/headers/PDS4 labels and dataset/instrument documentation. Historical non-polar reference, not site-specific mobility certification. No thumbnails or obsolete FTP URLs.",
    },
}
CATALOG.update({key: {k: v for k, v in item.items() if k not in {"name", "sources"}}
                for key, item in REFERENCE_SOURCES.items()})
MAX_METADATA = 4 * 1024**2


METADATA_EXTENSIONS = {".xml", ".lbl", ".hdr", ".fmt"}


STOP = threading.Event()


def start_debug_log(run_dir):
    """Per-run UTF-8 diagnostics; never dump cookies, headers or response bodies."""
    formatter = logging.Formatter("%(asctime)sZ %(levelname)s [%(threadName)s] %(message)s")
    formatter.converter = time.gmtime
    handlers = []
    for filename, level in (("debug.txt", logging.DEBUG), ("errors.txt", logging.WARNING)):
        handler = logging.FileHandler(run_dir / filename, encoding="utf-8")
        handler.setFormatter(formatter)
        handler.setLevel(level)
        LOG.addHandler(handler)
        handlers.append(handler)
    LOG.setLevel(logging.DEBUG)
    LOG.info("Python %s; run directory %s", sys.version.split()[0], run_dir)
    return handlers


def catalog(register=REGISTER):
    with register.open(encoding="utf-8-sig", newline="") as stream:
        rows = {re.search(r"[DMC]\d{2}", r["Priority ID"])[0]: r for r in csv.DictReader(stream)}
    if set(CATALOG) - set(rows) - set(REFERENCE_SOURCES):
        raise ValueError("The dataset register is missing configured IDs")
    return {key: {**value, "id": key,
                  "name": REFERENCE_SOURCES[key]["name"] if key in REFERENCE_SOURCES else rows[key]["Dataset"],
                  "sources": REFERENCE_SOURCES[key]["sources"] if key in REFERENCE_SOURCES else rows[key]["Source"]}
            for key, value in CATALOG.items()}


def session(cookies=None):
    result = requests.Session()
    result.headers.update({"User-Agent": "Bounded-Lunar-EDA-Downloader/1.0", "Accept-Encoding": "identity"})
    from requests.adapters import HTTPAdapter
    from urllib3.util.retry import Retry
    retry = Retry(total=0)  # A single outer retry budget; no hidden adapter retries.
    result.mount("https://", HTTPAdapter(max_retries=retry))
    if cookies:
        from http.cookiejar import MozillaCookieJar
        jar = MozillaCookieJar(str(cookies))
        jar.load(ignore_discard=True, ignore_expires=False)
        result.cookies.update(jar)
    return result


def safe_url(url):
    parsed = urlsplit(url)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password or parsed.fragment:
        raise ValueError("Science URLs must be absolute HTTPS URLs without embedded credentials/fragments")
    return url


def json_save(path, value):
    save_json(path, value)


def metadata(client, url, timeout):
    """Bound directory/API responses; never accidentally read a science payload here."""
    safe_url(url)
    with client.get(url, stream=True, timeout=(20, timeout)) as response:
        response.raise_for_status()
        safe_url(response.url)
        chunks, total = [], 0
        for chunk in response.iter_content(64 * 1024):
            total += len(chunk)
            if total > MAX_METADATA:
                raise ValueError(f"Metadata response exceeds {MAX_METADATA} bytes: {url}")
            chunks.append(chunk)
        return b"".join(chunks), response.url


def remote_info(client, url, timeout):
    """Establish exact size/validators without downloading the file body."""
    safe_url(url)
    with client.head(url, allow_redirects=True, timeout=(20, timeout)) as response:
        if response.status_code not in (403, 405, 501):
            response.raise_for_status()
            if response.headers.get("Content-Length", "").isdigit():
                headers, final = response.headers.copy(), response.url
            else:
                headers = None
        else:
            headers = None
    if headers is None:
        with client.get(url, headers={"Range": "bytes=0-0"}, stream=True, timeout=(20, timeout)) as response:
            response.raise_for_status()
            headers, final = response.headers.copy(), response.url
            match = re.fullmatch(r"bytes 0-0/(\d+)", headers.get("Content-Range", ""))
            if response.status_code == 206 and match:
                headers["Content-Length"] = match[1]
            elif response.status_code != 200:
                raise ValueError(f"Cannot establish remote size: {url}")
    safe_url(final)
    size = int(headers.get("Content-Length", 0))
    if size <= 0:
        raise ValueError(f"Exact remote size unavailable: {url}")
    if "text/html" in headers.get("Content-Type", "").lower():
        raise ValueError(f"Expected science/label bytes, got a web/login page: {url}")
    return {"url": url, "size_bytes": size, "etag": headers.get("ETag"),
            "last_modified": headers.get("Last-Modified")}


def listing(client, config, timeout, pages, count):
    """Depth-first, same-root, page-bounded listing; deterministic file-count pilot."""
    root = config["root"]
    pattern = re.compile(config["pattern"], re.I)
    pending, visited, products = [(root, 0)], set(), []
    while pending and len(visited) < pages and len(products) < count:
        url, depth = pending.pop()
        if url in visited:
            continue
        visited.add(url)
        raw, final = metadata(client, url, timeout)
        # A redirected directory may change its canonical URL, but cannot escape this collection.
        if not final.startswith(root):
            raise ValueError(f"Directory redirected outside the selected collection: {final}")
        links = sorted({urljoin(final, a["href"]) for a in BeautifulSoup(raw, "html.parser").select("a[href]")})
        links = [u for u in links if u.startswith(root) and not urlsplit(u).query and not urlsplit(u).fragment]
        siblings = set(links)
        for link in links:
            name = unquote(urlsplit(link).path.rsplit("/", 1)[-1])
            if (not name or name.lower().startswith(("collection", "readme", "aareadme", "index", "data_index"))
                    or not pattern.search(name)):
                continue
            stem = link.rsplit(".", 1)[0]
            companions = sorted(u for u in siblings if u.rsplit(".", 1)[0] == stem
                                and Path(urlsplit(u).path).suffix.lower() in METADATA_EXTENSIONS)
            if config.get("detached_pds3") and not any(Path(urlsplit(u).path).suffix.lower() == ".lbl" for u in companions):
                continue
            if config.get("id") == "D34":
                scene = link.rsplit("_RDN.", 1)[0]
                required = [scene + suffix for suffix in ("_L1B.LBL", "_LOC.IMG", "_LOC.HDR", "_OBS.IMG", "_OBS.HDR")]
                if not all(u in siblings for u in required):
                    continue
                companions = sorted(set(companions) | set(required))
            # Detached-label binary/PDS table formats must not be downloaded without their labels.
            if Path(name).suffix.lower() in {".img", ".tab", ".dat"} and not companions and not config.get("embedded_label"):
                continue
            primary = {"url": link}
            if config.get("embedded_label"):
                primary["embedded_label"] = True
            if config.get("float32_tiff"):
                primary["float32_tiff"] = True
            products.append([primary, *({"url": u, "metadata": True} for u in companions)])
            if len(products) == count:
                break
        if depth < 5:
            children = [u for u in links if u.endswith("/") and u != url and u not in visited
                        and urlsplit(u).path.rstrip("/").rsplit("/", 1)[-1].lower()
                        not in {"browse", "catalog", "document", "docs", "index", "xml_schema"}]
            pending.extend((u, depth + 1) for u in reversed(children))
    return products, {"visited_pages": sorted(visited), "scope": config.get("note", "First deterministic science-file groups; not representative site/time coverage")}


def s3_listing(client, config, timeout, pages, count):
    """Bounded NASA PDS object listing, including pagination; never use the JS index as data."""
    base, root_prefix = config["base"], config["prefix"]
    pending, visited, groups = [(root_prefix, None)], [], []
    pattern = re.compile(config["pattern"], re.I)
    while pending and len(visited) < pages and len(groups) < count:
        prefix, marker = pending.pop()
        query = {"delimiter": "/", "prefix": prefix, "max-keys": "1000"}
        if marker:
            query["marker"] = marker
        url = base + "?" + urlencode(query)
        raw, _ = metadata(client, url, timeout)
        visited.append(url)
        tree = ET.fromstring(raw)
        if tree.tag.rsplit("}", 1)[-1] != "ListBucketResult":
            raise ValueError("Expected NASA PDS object listing, not an index/login page")
        keys = sorted(x.text for x in tree.findall("{*}Contents/{*}Key") if x.text)
        if any(not k.startswith(root_prefix) or ".." in PurePosixPath(k).parts for k in keys):
            raise ValueError("Object listing escaped the selected collection")
        for key in keys:
            if not pattern.fullmatch(key.rsplit("/", 1)[-1]):
                continue
            stem = key.rsplit(".", 1)[0]
            labels = [x for x in keys if x.rsplit(".", 1)[0] == stem
                      and Path(x).suffix.lower() in METADATA_EXTENSIONS]
            # These migrated NAC IMG payloads retain PDS labels; detached XML is preferred.
            primary = {"url": base + quote(key, safe="/")}
            if not labels:
                primary["embedded_label"] = True
            groups.append([primary, *({"url": base + quote(x, safe="/"), "metadata": True} for x in labels)])
            if len(groups) == count:
                break
        if tree.findtext("{*}IsTruncated") == "true":
            next_marker = tree.findtext("{*}NextMarker") or (keys[-1] if keys else None)
            if not next_marker or next_marker == marker:
                raise ValueError("Object listing pagination marker is unavailable")
            pending.append((prefix, next_marker))
        children = sorted(x.text for x in tree.findall("{*}CommonPrefixes/{*}Prefix") if x.text)
        for child in reversed(children):
            if child.startswith(root_prefix) and child != prefix and child.rsplit("/", 2)[-2] != "WAC":
                pending.append((child, None))
    return groups, {"scope": config["note"], "visited_pages": visited}


ODE_DIVINER = "https://oderest.rsl.wustl.edu/livegds"
DIVINER_RDR_SIS = ("https://pds-geosciences.wustl.edu/lro/lro-l-dlre-4-rdr-v1/"
                   "lrodlr_1001/document/diviner_rdr_sis.pdf")


def add_diviner_ode_arguments(parser):
    parser.add_argument("--diviner-ode", action="store_true",
                        help="D20 only: targeted ODE/GDS RDR CSV query, not the legacy archive pilot")
    parser.add_argument("--diviner-bbox", nargs=4, type=float, metavar=("WEST", "SOUTH", "EAST", "NORTH"),
                        help="Planetocentric degrees, east-positive longitudes 0..360; no meridian crossing")
    parser.add_argument("--diviner-start", help="Inclusive observation UTC start (ISO date or timestamp)")
    parser.add_argument("--diviner-stop", help="Inclusive observation UTC stop (ISO date means midnight)")
    parser.add_argument("--diviner-channels", nargs="+", type=int, default=[7, 8, 9],
                        help="Thermal channels 3..9; default 7 8 9")
    parser.add_argument("--diviner-max-points", type=int, default=100000,
                        help="Refuse generation above this observation count; default 100000")
    parser.add_argument("--diviner-quality-max", nargs=3, type=int, default=[0, 0, 0],
                        metavar=("CALIBRATION", "GEOMETRY", "MISC"),
                        help="Explicit quality-flag upper bounds 0..255; default 0 0 0. 0 12 0 includes definitive, unreprocessed geometry; inspect flags in EDA")


def diviner_ode_config(args, parser):
    """Keep an explicit bounded observation query separate from legacy D20 selection."""
    options = (args.diviner_bbox, args.diviner_start, args.diviner_stop)
    if not args.diviner_ode:
        if (any(value is not None for value in options) or args.diviner_channels != [7, 8, 9]
                or args.diviner_max_points != 100000 or args.diviner_quality_max != [0, 0, 0]):
            parser.error("Diviner query options require --diviner-ode")
        return None
    if (not all(value is not None for value in options) or args.selections or args.from_inventory
            or args.datasets not in (None, ["D20"])):
        parser.error("--diviner-ode requires bbox/start/stop and D20-only selection; do not combine with selections/from-inventory")
    west, south, east, north = args.diviner_bbox
    if (not all(math.isfinite(v) for v in args.diviner_bbox)
            or not 0 <= west < east <= 360 or not -90 <= south < north <= 90
            or east - west > .5 or north - south > .5):
        parser.error("Use a non-crossing 0..360 longitude bbox no larger than 0.5 by 0.5 degrees; split larger areas")
    try:
        times = [datetime.fromisoformat(value.replace("Z", "+00:00")) for value in options[1:]]
        times = [t.replace(tzinfo=timezone.utc) if t.tzinfo is None else t.astimezone(timezone.utc) for t in times]
    except ValueError:
        parser.error("Diviner start/stop must be ISO dates or timestamps")
    if not 0 < (times[1] - times[0]).total_seconds() <= 31 * 86400:
        parser.error("Use an increasing Diviner UTC window of at most 31 days; split longer periods")
    if any(t.microsecond % 1000 for t in times):
        parser.error("ODE timestamps support millisecond precision; use at most three fractional-second digits")
    channels = sorted(set(args.diviner_channels))
    if len(channels) != len(args.diviner_channels) or not channels or not set(channels) <= set(range(3, 10)):
        parser.error("Choose unique thermal channels from 3..9")
    if not 1 <= args.diviner_max_points <= 1000000:
        parser.error("Diviner point cap must be 1..1000000")
    if not all(0 <= value <= 255 for value in args.diviner_quality_max):
        parser.error("Diviner quality upper bounds must be 0..255")
    args.datasets = ["D20"]
    params = {"query": "divinerrdr", "output": "XML", "results": "v",
              "westernlon": west, "easternlon": east, "minlat": south, "maxlat": north,
              # GDS expects UTC without a zone suffix, with explicit milliseconds.
              # A trailing Z gets padded to Z000/Z999 and rejected inside a
              # nominally successful response (observed in the saved query XML).
              "minobtime": times[0].replace(tzinfo=None).isoformat(timespec="milliseconds"),
              "maxobtime": times[1].replace(tzinfo=None).isoformat(timespec="milliseconds"),
              "channel": "".join("t" if ch in channels else "f" for ch in range(1, 10)),
              "mincalibration": 0, "maxcalibration": args.diviner_quality_max[0],
              "mingeometry": 0, "maxgeometry": args.diviner_quality_max[1],
              "minmisc": 0, "maxmisc": args.diviner_quality_max[2]}
    fingerprint = hashlib.sha256(json.dumps(params, sort_keys=True).encode()).hexdigest()[:24]
    return {"kind": "ode_diviner", "ode_params": params, "ode_fingerprint": fingerprint,
            "ode_max_points": args.diviner_max_points,
            "sources": ODE_DIVINER + "?" + urlencode(params),
            "note": ("Explicit ODE/GDS dated RDR subset; not continuous ground monitoring or equipment temperature. "
                     f"Quality maxima (calibration, geometry, misc): {args.diviner_quality_max}; "
                     "nonzero flags require documented, application-specific review.")}


def ode_diviner_response(client, params, timeout, evidence_path):
    url = ODE_DIVINER + "?" + urlencode(params)
    raw, _ = metadata(client, url, timeout)
    evidence_path.write_bytes(raw)
    root = ET.fromstring(raw)
    fields = {node.tag.split("}")[-1].lower(): (node.text or "").strip() for node in root}
    details = [(node.tag.split("}")[-1].lower(), (node.text or "").strip()) for node in root.iter()]
    errors = [text for tag, text in details if text and (
        tag == "error" or tag == "statusnote" and re.search(r"\b(invalid|error|failed|exception)\b", text, re.I))]
    incomplete = [text for tag, text in details if tag == "state" and text.upper() not in {"FINISHED", "SUCCESS"}]
    if fields.get("status", "").upper() not in {"SUCCESS", "FINISHED"} or errors or incomplete:
        reason = "; ".join(errors or incomplete) or fields.get("statusnote") or fields.get("status")
        raise ValueError(f"ODE Diviner query failed: {reason}; URL: {url}")
    if not re.fullmatch(r"\d+", fields.get("count", "")):
        raise ValueError("ODE response lacks an exact observation count; see " + str(evidence_path))
    return root, int(fields["count"]), url


def discover_ode_diviner(client, config, timeout, evidence_dir):
    """Documented GDS REST: count first, then CSV only; no images or bulk archive crawl.

    API reference: https://oderest.rsl.wustl.edu/GDS_REST_V2.0.pdf (section 4.7).
    Small synchronous queries avoid background-job resubmission/polling ambiguity.
    """
    params = config["ode_params"]
    _, points, count_url = ode_diviner_response(client, {**params, "results": "c"}, timeout,
                                               evidence_dir / "D20_ode_count.xml")
    if points == 0:
        reason = "No observations match the explicit area/time/channel/quality selection; no filters were automatically relaxed"
        info = {"status": "no_observations", "reason": reason, "scope": config["note"],
                "ode_params": params, "ode_fingerprint": config["ode_fingerprint"],
                "ode_count_url": count_url, "ode_observation_count": 0}
        json_save(evidence_dir / "D20_ode_query.json", info)
        LOG.warning("%s. URL: %s", reason, count_url)
        return [], info
    if points > config["ode_max_points"]:
        raise ValueError(f"ODE returned {points} observations (allowed 1..{config['ode_max_points']}); change/split the explicit area/time window. URL: {count_url}")
    root, actual, query_url = ode_diviner_response(client, params, timeout, evidence_dir / "D20_ode_results.xml")
    if actual != points or actual > config["ode_max_points"]:
        raise ValueError("ODE result count changed/exceeds the count-first selection; result not accepted")
    prefix = "moon/diviner/ode_rdr/" + config["ode_fingerprint"] + "/"
    entries, seen = [], set()
    for node in root.iter():
        if node.tag.split("}")[-1].lower() not in {"resultfile", "resultsfile"}:
            continue
        fields = {c.tag.split("}")[-1].lower(): (c.text or "").strip() for c in node}
        url = fields.get("url")
        if not url:
            continue
        parsed = urlsplit(url)
        # Some official responses still publish HTTP links. Use HTTPS on the
        # same named PDS/ODE host; never disable TLS or switch to another host.
        if parsed.hostname not in {"oderest.rsl.wustl.edu", "ode.rsl.wustl.edu", "pds-geosciences.wustl.edu"}:
            raise ValueError("Unexpected ODE result host: " + url)
        url = safe_url(parsed._replace(scheme="https").geturl()) if parsed.scheme == "http" else safe_url(url)
        name = unquote(urlsplit(url).path.rsplit("/", 1)[-1])
        ext = Path(name).suffix.lower()
        if ext not in {".csv", ".tab", ".txt", ".lbl", ".xml"}:
            raise ValueError("Unexpected non-table/label ODE result: " + url)
        if name.casefold() in seen:
            raise ValueError("Duplicate ODE result filename: " + name)
        seen.add(name.casefold())
        entries.append({"url": url, "relative_path": prefix + name,
                        "metadata": ext in {".lbl", ".xml", ".txt"}})
    if not any(Path(e["relative_path"]).suffix.lower() in {".csv", ".tab"} for e in entries):
        raise ValueError("ODE returned no CSV/ASCII science table; result not accepted")
    entries.append({"url": DIVINER_RDR_SIS, "metadata": True,
                    "relative_path": "moon/diviner/ode_rdr/document/diviner_rdr_sis.pdf"})
    info = {"scope": config["note"], "ode_params": params, "ode_fingerprint": config["ode_fingerprint"],
            "ode_count_url": count_url, "ode_query_url": query_url, "ode_observation_count": actual,
            "limits": "Explicit quality bounds retained in ode_params; nonzero flag meanings, temperature sentinels and coverage still need EDA validation"}
    json_save(evidence_dir / "D20_ode_query.json", info)
    return [entries], info


def discover(client, config, timeout, pages, count, overrides, evidence_dir):
    key, kind = config["id"], config.get("kind", "listing")
    if key in overrides:
        entry = overrides[key]
        if not isinstance(entry, dict) or not entry.get("scope") or not isinstance(entry.get("groups"), list):
            raise ValueError(f"{key}: selections need scope and groups of explicit file objects")
        groups = entry["groups"]
        if not all(isinstance(g, list) and g and all(isinstance(x, dict) and "url" in x for x in g) for g in groups):
            raise ValueError(f"Invalid selection groups for {key}")
        return groups[:count], {"scope": entry["scope"], "selection": "explicit user-supplied product URLs"}
    if kind in {"login", "selection"}:
        return [], {"status": "login_required" if kind == "login" else "product_selection_required", "reason": config["note"]}
    if kind == "ode_diviner":
        return discover_ode_diviner(client, config, timeout, evidence_dir)
    if kind == "listing":
        return listing(client, config, timeout, pages, count)
    if kind == "s3":
        return s3_listing(client, config, timeout, pages, count)
    if kind in {"zenodo", "sdem"}:
        record_id = ZENODO_RECORD if kind == "sdem" else config["record"]
        raw, _ = metadata(client, f"https://zenodo.org/api/records/{record_id}", timeout)
        record = json.loads(raw)
        json_save(evidence_dir / (key + "_record.json"), record)
        if str(record.get("id")) != record_id:
            raise ValueError("Unexpected Zenodo record identity")
        if kind == "sdem":
            files = [x for x in select_sdem_files(record) if x["format"] == "ZIP"]
        else:
            files = []
            for item in sorted(record["files"], key=lambda f: f["key"]):
                if re.search(config["pattern"], item["key"], re.I):
                    checksum = item.get("checksum", "")
                    if not re.fullmatch(r"md5:[a-fA-F0-9]{32}", checksum):
                        raise ValueError("Zenodo publisher MD5 unavailable")
                    files.append({"url": item["links"]["self"], "size_bytes": item["size"], "md5": checksum[4:]})
        return [[x] for x in files[:count]], {"scope": config.get("note", "Published study text-file pilot"), "record": record_id}
    if kind == "core":
        lola, illum, _ = original_helpers()
        if key == "D01":
            import download_diviner_south_polar as diviner
            entries = diviner.fetch_inventory(client, "seasonal", timeout)
            tables = sorted((x for x in entries if x.filename.endswith(".tab")), key=lambda x: x.filename)[:count]
            if any(not any(e.filename == Path(x.filename).with_suffix(".xml").name for e in entries) for x in tables):
                raise ValueError("A selected Diviner table lacks its XML label")
            return [[{"url": x.url, "relative_path": "moon/diviner/seasonal/" + x.filename},
                     *({"url": e.url, "metadata": True, "relative_path": "moon/diviner/seasonal/" + e.filename}
                       for e in entries if e.filename == Path(x.filename).with_suffix(".xml").name)] for x in tables], {"scope": config["note"]}
        patterns = {"D02": ("AVGVISIB_85S_060M_201608", "LPSR_85S_060M_201608"),
                    "D03": ("AVGVISIB_85S_060M_201608_EARTH",), "D04": ("SKYV_65S_240M",)}
        # Existing helper discovers exact publisher TIFF links, including mirror provenance.
        specs = illum.make_manifest(client, ["south"], timeout, False, True, evidence_dir)
        selected = [s for s in specs if Path(s.filename).stem in patterns[key]]
        return [[{"url": s.url, "relative_path": "moon/illumination_2016/" + s.relative_path.replace("\\", "/")}]
                for s in selected[:count]], {"scope": config["note"]}
    if kind == "lola":
        lola, _, _ = original_helpers()
        selected = [x for x in lola.discover(client, evidence_dir) if x.name in LOLA_FILES]
        selected.sort(key=lambda x: LOLA_FILES.index(x.name))
        return [[{"url": x.url, "relative_path": "moon/lola_product90/large_area_dem/" + x.name}]
                for x in selected[:count]], {"scope": config["note"]}
    if kind == "direct":
        if config.get("group_urls"):
            return [[{"url": u} for u in config["group_urls"]]], {"scope": config["note"]}
        return [[{"url": u}] for u in config["urls"][:count]], {"scope": config["note"]}
    if kind == "osdr":
        raw, _ = metadata(client, "https://osdr.nasa.gov/osdr/data/osd/meta/82", timeout)
        json_save(evidence_dir / "D18_study.json", json.loads(raw))
        raw, _ = metadata(client, "https://osdr.nasa.gov/osdr/data/osd/files/82", timeout)
        file_listing = json.loads(raw)
        json_save(evidence_dir / "D18_files.json", file_listing)
        study = file_listing["studies"]["OSD-82"]
        files = [x for x in study["study_files"] if not x.get("restricted") and x.get("visible")]
        context = [{"url": urljoin("https://osdr.nasa.gov/", x["remote_url"]), "filename": x["file_name"],
                    "size_bytes": int(x["file_size"]), "metadata": True}
                   for x in files if x["category"] == "Study Metadata Files"]
        science = [x for x in files if x["category"] != "Study Metadata Files"]
        groups = [[{"url": urljoin("https://osdr.nasa.gov/", x["remote_url"]), "filename": x["file_name"],
                    "size_bytes": int(x["file_size"])}, *context] for x in science[:count]]
        return groups, {"scope": "OSD-82 published sequencing file(s) plus ISA metadata; inspect assay type in publisher metadata, not assumed CSV field names"}
    raise ValueError(f"Unimplemented dataset kind: {kind}")


def file_item(client, entry, key, timeout):
    url = safe_url(entry["url"])
    info = remote_info(client, url, timeout)
    name = unquote(urlsplit(url).path.rstrip("/").rsplit("/", 1)[-1])
    # Zenodo API URLs end in /content; caller-supplied filename is explicit, never an HTML title.
    name = entry.get("filename", name)
    if name == "content":
        name = unquote(urlsplit(url).path.split("/")[-2])
    if not name or re.search(r'[<>:"/\\|?*\x00-\x1f]', name) or name.endswith((".", " ")):
        raise ValueError(f"Unsafe local filename: {name!r}")
    if "size_bytes" in entry and entry["size_bytes"] != info["size_bytes"]:
        raise ValueError(f"Publisher size disagrees with HEAD for {name}")
    parent_url = url.rsplit("/", 1)[0]
    prefix = REFERENCE_SOURCES[key]["relative_root"] if key in REFERENCE_SOURCES else f"moon/eda_pilots/{key}"
    relative = entry.get("relative_path", prefix + "/" + hashlib.sha256(parent_url.encode()).hexdigest()[:12] + "/" + name)
    info.update({"relative_path": relative, "dataset": key, "metadata": bool(entry.get("metadata"))})
    if entry.get("embedded_label"):
        info["embedded_label"] = True
    if Path(relative).suffix.lower() in {".tif", ".tiff"} and (entry.get("float32_tiff") or key == "D27"):
        info["float32_tiff"] = True
    for field in ("md5", "sha256"):
        if field in entry:
            if not re.fullmatch(r"[0-9a-fA-F]{32}" if field == "md5" else r"[0-9a-fA-F]{64}", entry[field]):
                raise ValueError(f"Invalid {field} for {name}")
            info[field] = entry[field].lower()
    return info


def safe_path(root, relative):
    pure = PurePosixPath(relative)
    if pure.is_absolute() or ".." in pure.parts or "\\" in relative or ":" in relative:
        raise ValueError(f"Unsafe relative path: {relative}")
    for component in pure.parts:
        if (re.search(r'[<>"|?*\x00-\x1f]', component) or component.endswith((".", " "))
                or re.fullmatch(r"(CON|PRN|AUX|NUL|COM[1-9]|LPT[1-9])", component.split(".")[0], re.I)):
            raise ValueError(f"Unsafe Windows path component: {component}")
    return destination(root, relative)


def identity(item):
    return {k: item[k] for k in ("url", "relative_path", "size_bytes", "etag", "last_modified", "md5", "sha256", "embedded_label", "float32_tiff") if k in item}


def compatible_partial_state(saved, item):
    expected = identity(item)
    if saved == expected:
        return True
    # Permit only the two known validation-policy corrections. Every source,
    # byte count, validator, checksum and destination must still match exactly.
    ext = Path(item["relative_path"]).suffix.lower()
    obsolete = ("embedded_label" if item["dataset"] == "D26" and ext == ".img" else
                "float32_tiff" if item["dataset"] == "D27" and ext == ".xml" and item.get("metadata") else None)
    if (obsolete and isinstance(saved, dict) and saved.get(obsolete) is True and obsolete not in expected
            and {k: v for k, v in saved.items() if k != obsolete} == expected):
        LOG.warning("Correcting obsolete %s checkpoint flag for %s; source identity and partial bytes unchanged",
                    obsolete, item["relative_path"])
        return True
    return False


def validate_detached_dtm(path, item):
    data_name = Path(item["relative_path"]).name
    label_name = Path(data_name).with_suffix(".lbl").name
    label = path.with_name(label_name)
    if not label.is_file() or label.is_symlink() or label.stat().st_size > MAX_METADATA:
        raise ValueError("D26 requires its verified detached PDS3 label beside the raw image")
    raw = label.read_bytes()
    receipt = label.with_name(label.name + ".json")
    saved = json.loads(receipt.read_text(encoding="utf-8")) if receipt.is_file() else {}
    expected_url = urljoin(item["url"], label_name)
    if (saved.get("source", {}).get("url") != expected_url
            or saved.get("source", {}).get("size_bytes") != len(raw)
            or saved.get("sha256") != hashlib.sha256(raw).hexdigest()):
        raise ValueError("Detached D26 label lacks matching source/size/hash evidence")
    text = raw.decode("ascii")
    if not re.search(r'^PDS_VERSION_ID\s*=\s*"PDS3"\s*$', text, re.M):
        raise ValueError("Expected a PDS3 DTM label")
    if not re.search(r'^FILE_NAME\s*=\s*"' + re.escape(data_name) + r'"\s*$', text, re.M):
        raise ValueError("D26 label FILE_NAME does not match this image")
    if not re.search(r'^\^IMAGE\s*=\s*\("' + re.escape(data_name) + r'",\s*1\s*<BYTES>\)\s*$', text, re.M):
        raise ValueError("D26 label must reference this detached image starting at byte 1")
    image = re.search(r'^\s*OBJECT\s*=\s*IMAGE\s*$([\s\S]*?)^\s*END_OBJECT\s*=\s*IMAGE\s*$', text, re.M)
    if not image:
        raise ValueError("D26 image layout is not documented in its label")
    dimensions = {}
    for field in ("BANDS", "LINES", "LINE_SAMPLES", "SAMPLE_BITS"):
        values = re.findall(r'^\s*' + field + r'\s*=\s*(\d+)\s*$', image[1], re.M)
        if len(values) != 1 or int(values[0]) < 1:
            raise ValueError(f"Invalid/ambiguous D26 label field: {field}")
        dimensions[field] = int(values[0])
    if dimensions["SAMPLE_BITS"] % 8 or dimensions["BANDS"] != 1:
        raise ValueError("Unsupported D26 sample layout")
    expected_bytes = (dimensions["LINES"] * dimensions["LINE_SAMPLES"]
                      * dimensions["BANDS"] * dimensions["SAMPLE_BITS"] // 8)
    if expected_bytes != item["size_bytes"] or path.stat().st_size != expected_bytes:
        raise ValueError("D26 raw-image size disagrees with its detached label dimensions")


def verify_existing(path, item, output=DEFAULT_OUTPUT):
    """Verify checksum evidence, not merely filename or equal size; never overwrite conflicts."""
    if not path.exists():
        return None
    _, _, helpers = original_helpers()
    if not path.is_file() or path.stat().st_size != item["size_bytes"]:
        raise ValueError(f"Existing file size/type conflicts; preserved: {path}")
    md5, sha = helpers.checksums(path)
    if item.get("md5") and item["md5"] != md5 or item.get("sha256") and item["sha256"] != sha:
        raise ValueError(f"Existing publisher checksum mismatch; preserved: {path}")
    if item.get("md5") or item.get("sha256"):
        return sha
    receipt = path.with_name(path.name + ".json")
    if receipt.is_file():
        saved = json.loads(receipt.read_text(encoding="utf-8"))
        if not isinstance(saved, dict) or not isinstance(saved.get("source"), dict):
            raise ValueError(f"Malformed existing receipt; preserved: {receipt}")
        source = saved.get("source", {})
        if (source.get("url") == item["url"] and saved.get("sha256") == sha
                and source.get("size_bytes") == item["size_bytes"]
                and all(not source.get(k) or source[k] == item.get(k) for k in ("etag", "last_modified"))):
            return sha
    # Legacy downloaders did not save hashes. Establish a local SHA receipt from
    # their exact source/size records; explicitly do NOT claim a publisher checksum.
    root = output.resolve()
    legacy_match = False
    if path.is_relative_to(root / "moon/illumination_2016"):
        manifest = root / "moon/illumination_2016/manifests/completed_downloads.json"
        if manifest.is_file():
            saved = json.loads(manifest.read_text(encoding="utf-8"))
            rel = str(path.relative_to(root / "moon/illumination_2016")).replace("\\", "/")
            for key, record in saved.items():
                if (key.replace("\\", "/") == rel and record.get("url") == item["url"]
                        and record.get("size_bytes") == item["size_bytes"]):
                    legacy_match = True
    elif path.is_relative_to(root / "moon/diviner/seasonal"):
        manifest = root / "moon/diviner/download_manifest.csv"
        if manifest.is_file():
            with manifest.open(encoding="utf-8-sig", newline="") as stream:
                legacy_match = any(r["filename"] == path.name and r["url"] == item["url"]
                                   and int(r["size_bytes"]) == item["size_bytes"] for r in csv.DictReader(stream))
    if legacy_match:
        validate_payload(path, item)
        json_save(receipt, {"source": identity(item), "sha256": sha,
                  "verification": "legacy source/size record + local SHA256 baseline; no publisher checksum"})
        print(f"Established local hash baseline for legacy file: {path.name} (not publisher-verified)", flush=True)
        return sha
    raise ValueError(f"Existing file lacks matching checksum/source receipt; preserved: {path}")


def validate_payload(path, item):
    with path.open("rb") as stream:
        first = stream.read(512)
    if first.lstrip().lower().startswith((b"<!doctype html", b"<html")):
        raise ValueError("Downloaded a web/login page, not a science/label product")
    ext = Path(item["relative_path"]).suffix.lower()
    if item.get("dataset") == "D26" and ext == ".img":
        validate_detached_dtm(path, item)
    elif item.get("embedded_label") and b"PDS_VERSION_ID" not in first:
        raise ValueError("Required embedded PDS label missing")
    if ext in {".tif", ".tiff"} and first[:4] not in {b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"}:
        raise ValueError("Invalid TIFF header")
    if ext == ".zip" and first[:4] not in {b"PK\x03\x04", b"PK\x05\x06"}:
        raise ValueError("Invalid ZIP header")
    if ext == ".pdf" and not first.startswith(b"%PDF-"):
        raise ValueError("Invalid PDF document header")
    if item.get("dataset") == "D27" and ext == ".xml":
        if path.stat().st_size > MAX_METADATA:
            raise ValueError("Unexpected ShadowCam XML label size")
        try:
            label = ET.fromstring(path.read_bytes())
        except ET.ParseError as error:
            raise ValueError("Invalid ShadowCam XML label") from error
        names = [e.text for e in label.iter() if e.tag.rsplit("}", 1)[-1] == "file_name"]
        if Path(item["relative_path"]).with_suffix(".tif").name not in names:
            raise ValueError("ShadowCam XML label does not reference the selected TIFF")
    if ext in {".tif", ".tiff"} and (item.get("float32_tiff") or item.get("dataset") == "D27"):
        if len(first) < 16:
            raise ValueError("Truncated TIFF header")
        order = "<" if first[:2] == b"II" else ">"
        magic = struct.unpack(order + "H", first[2:4])[0]
        if magic == 42:
            offset = struct.unpack(order + "I", first[4:8])[0]
            count_fmt, entry_fmt = "H", "HHII"
        elif magic == 43 and struct.unpack(order + "H", first[4:6])[0] == 8:
            offset = struct.unpack(order + "Q", first[8:16])[0]
            count_fmt, entry_fmt = "Q", "HHQQ"
        else:
            raise ValueError("Unsupported TIFF layout for float32 verification")
        with path.open("rb") as stream:
            stream.seek(offset)
            raw = stream.read(struct.calcsize(order + count_fmt))
            if len(raw) != struct.calcsize(order + count_fmt):
                raise ValueError("Truncated TIFF directory")
            count = struct.unpack(order + count_fmt, raw)[0]
            if count > 4096:
                raise ValueError("Unexpected TIFF directory size")
            tags = {}
            for _ in range(count):
                raw = stream.read(struct.calcsize(order + entry_fmt))
                if len(raw) != struct.calcsize(order + entry_fmt):
                    raise ValueError("Truncated TIFF tag")
                tag, dtype, number, value = struct.unpack(order + entry_fmt, raw)
                if tag in (258, 339) and dtype == 3 and number == 1:
                    tags[tag] = struct.unpack(order + "H", raw[-(8 if magic == 43 else 4):][:2])[0]
            if tags.get(258) != 32 or tags.get(339) != 3:
                raise ValueError("Expected 32-bit floating-point radiance, not stretched/browse TIFF samples")


def transfer(item, output, timeout, attempts, cookies=None):
    """One worker/session per file; lock output, resume only verified source identity."""
    if STOP.is_set():
        return "cancelled"
    path = safe_path(output, item["relative_path"])
    LOG.info("Transfer start %s %s expected_bytes=%s", item["dataset"], path, item["size_bytes"])
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".download.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        sha = verify_existing(path, item, output)
        if sha:
            LOG.info("Verified existing file; skipped %s", path)
            print(f"SKIP verified {item['dataset']}: {path.name}", flush=True)
            clear_completed_transfer_state(output, path)
            return "verified_existing"
        part = path.with_name(path.name + ".part")
        state_path = path.with_name(path.name + ".eda-part.json")
        for sidecar in (part, state_path, path.with_name(path.name + ".json")):
            safe_path(output, str(sidecar.relative_to(output)).replace("\\", "/"))
        state = identity(item)
        if part.exists() and (not state_path.exists() or not compatible_partial_state(json.loads(state_path.read_text()), item)):
            raise ValueError(f"Partial source identity missing/changed; preserved: {part}")
        json_save(state_path, state)
        _, _, helpers = original_helpers()
        with session(cookies) as client:
            for attempt in range(attempts):
                if STOP.is_set():
                    return "cancelled"
                offset = part.stat().st_size if part.exists() else 0
                LOG.info("Attempt %s/%s path=%s resume_offset=%s", attempt + 1, attempts, path, offset)
                if offset > item["size_bytes"]:
                    raise ValueError("Partial exceeds expected size; preserved")
                try:
                    if offset != item["size_bytes"]:
                        headers = {}
                        if offset:
                            etag = item.get("etag")
                            validator = etag if etag and not etag.startswith("W/") else item.get("last_modified")
                            if not validator and not (item.get("md5") or item.get("sha256")):
                                raise ValueError("Safe resume needs a remote validator or publisher checksum; partial preserved")
                            headers["Range"] = f"bytes={offset}-"
                            if validator and not (item.get("md5") or item.get("sha256")):
                                headers["If-Range"] = validator
                        with client.get(item["url"], headers=headers, stream=True, timeout=(20, timeout)) as response:
                            response.raise_for_status()
                            safe_url(response.url)
                            if offset:
                                expected = f"bytes {offset}-{item['size_bytes']-1}/{item['size_bytes']}"
                                if response.status_code != 206 or response.headers.get("Content-Range") != expected:
                                    raise ValueError("Server ignored/changed resume range; partial preserved, not appended")
                            elif response.status_code != 200:
                                raise ValueError("Unexpected initial response status")
                            for field, header in (("etag", "ETag"), ("last_modified", "Last-Modified")):
                                expected_validator = item.get(field)
                                actual_validator = response.headers.get(header)
                                # ODE returns W/"tag" on HEAD but "tag" on GET.
                                # Accept only this same-opaque-tag upgrade; retain
                                # all real change checks and never use a weak If-Range.
                                weak_to_strong = (field == "etag" and expected_validator
                                                  and expected_validator.startswith("W/")
                                                  and actual_validator == expected_validator[2:])
                                if (not (item.get("md5") or item.get("sha256")) and item.get(field)
                                        and actual_validator != expected_validator and not weak_to_strong):
                                    raise ValueError(f"Remote {header} changed since inventory; partial preserved")
                            if "text/html" in response.headers.get("Content-Type", "").lower():
                                raise ValueError("Server returned a login/web page")
                            total = offset
                            last_logged = offset
                            with part.open("ab" if offset else "wb") as stream:
                                for block in response.iter_content(1024 * 1024):
                                    if STOP.is_set():
                                        return "cancelled"
                                    total += len(block)
                                    if total > item["size_bytes"]:
                                        raise ValueError("Transfer exceeds pinned size; stopped")
                                    stream.write(block)
                                    if total - last_logged >= 64 * 1024**2:
                                        LOG.info("Progress %s bytes=%s/%s", path, total, item["size_bytes"])
                                        print(f"  {item['dataset']} {path.name}: {total / 1024**2:.0f}/{item['size_bytes'] / 1024**2:.0f} MiB", flush=True)
                                        last_logged = total
                        if total != item["size_bytes"]:
                            raise requests.exceptions.ChunkedEncodingError("Short body; rerun/retry resumes partial")
                    md5, sha = helpers.checksums(part)
                    if item.get("md5") and md5 != item["md5"] or item.get("sha256") and sha != item["sha256"]:
                        raise ValueError("Publisher checksum mismatch; partial preserved")
                    validate_payload(part, item)
                    if path.exists():
                        raise FileExistsError("Final file appeared during transfer; preserved")
                    json_save(path.with_name(path.name + ".json"), {"source": identity(item), "sha256": sha,
                              "verified_utc": datetime.now(timezone.utc).isoformat(),
                              "verification": "expected checksum from publisher metadata or explicit selection" if item.get("md5") or item.get("sha256") else "TLS + exact size + local SHA256; no publisher checksum"})
                    part.rename(path)
                    clear_completed_transfer_state(output, path)
                    LOG.info("Completed %s sha256=%s", path, sha)
                    print(f"DONE {item['dataset']}: {path.name}", flush=True)
                    return "downloaded"
                except requests.RequestException as error:
                    if not is_connection_error(error):
                        raise
                    LOG.warning("Network attempt failed %s attempt=%s/%s", path, attempt + 1, attempts, exc_info=True)
                    if attempt + 1 == attempts:
                        raise
                    time.sleep(min(2**attempt, 30))
        raise RuntimeError("Transfer attempts exhausted")
    finally:
        lock.unlink()


def inventory(configs, output, run_dir, args, overrides):
    record = {"schema": 1, "status": "inventory", "pilot_only": True, "datasets": [], "files": [],
              "connection_retry_batches": getattr(args, "connection_retries", 3),
              "limits": {k: getattr(args, k) for k in ("files_per_dataset", "max_file_mib", "max_dataset_mib", "max_total_mib", "pages_per_dataset")}}
    paths, reserved = {}, 0
    # Source discovery is intentionally serial; payload file transfers use the bounded pool.
    with session(args.cookies) as client:
        for config in configs:
            LOG.info("Inventory start %s %s", config["id"], config["name"])
            result = {"id": config["id"], "name": config["name"], "sources": config["sources"], "status": "pending", "files": []}
            record["datasets"].append(result)
            try:
                # Inspect a bounded surplus of candidates so an oversized first
                # product does not hide a later file that fits the pilot budget.
                candidate_limit = args.files_per_dataset * 4
                groups, info = retry_connections(
                    lambda: discover(client, config, args.timeout, args.pages_per_dataset, candidate_limit, overrides, run_dir),
                    f"{config['id']} source discovery", LOG, getattr(args, "connection_retries", 3), STOP)
                result.update(info)
                dataset_bytes = 0
                accepted_groups = 0
                for group in groups:
                    if accepted_groups >= args.files_per_dataset:
                        break
                    try:
                        items = retry_connections(
                            lambda: [file_item(client, e, config["id"], args.timeout) for e in group],
                            f"{config['id']} science/label metadata", LOG, getattr(args, "connection_retries", 3), STOP)
                    except (requests.RequestException, ValueError, KeyError, OSError, RuntimeError) as error:
                        LOG.exception("Skipping failed science/label candidate group for %s", config["id"])
                        result.setdefault("file_errors", []).append({"urls": [e.get("url") for e in group], "error": str(error)})
                        print(f"SKIP failed inventory candidate {config['id']}: {error}", file=sys.stderr, flush=True)
                        continue
                    group_bytes = sum(i["size_bytes"] for i in items)
                    missing_items = [i for i in items if not safe_path(output, i["relative_path"]).exists()]
                    new_bytes = sum(i["size_bytes"] for i in missing_items)
                    if (any(i["size_bytes"] > args.max_file_mib * 1024**2 for i in missing_items)
                            or dataset_bytes + new_bytes > args.max_dataset_mib * 1024**2
                            or reserved + new_bytes > args.max_total_mib * 1024**2):
                        result.setdefault("excluded", []).append({"reason": "pilot_byte_limit", "urls": [i["url"] for i in items], "bytes": group_bytes})
                        continue
                    for item in items:
                        path = safe_path(output, item["relative_path"])
                        key = str(path).casefold()
                        if key in paths and paths[key] != item["url"]:
                            raise ValueError(f"Multiple sources target one file: {path}")
                        paths[key] = item["url"]
                        result["files"].append(item["relative_path"])
                        if key not in {str(safe_path(output, x["relative_path"])).casefold() for x in record["files"]}:
                            record["files"].append(item)
                    dataset_bytes += new_bytes
                    reserved += new_bytes
                    accepted_groups += 1
                if result["files"]:
                    result["status"] = "partial_inventory" if result.get("file_errors") else "planned"
                elif result.get("file_errors"):
                    result["status"] = "inventory_failed"
                elif "status" not in info:
                    result["status"] = "byte_limit" if result.get("excluded") else "no_science_files_found"
            except (requests.RequestException, ValueError, KeyError, OSError, RuntimeError, ET.ParseError) as error:
                LOG.exception("Inventory failed for %s", config["id"])
                result.update({"status": "inventory_failed", "reason": str(error)})
            json_save(run_dir / "inventory.json", record)
            print(f"{result['id']} {result['status']}: {len(result['files'])} files", flush=True)
            LOG.info("Inventory outcome %s status=%s files=%s reason=%s exclusions=%s", result["id"], result["status"], len(result["files"]), result.get("reason", ""), result.get("excluded", []))
            if result["status"] != "planned" or result.get("excluded"):
                LOG.warning("Dataset incomplete/skipped %s status=%s reason=%s; see inventory.json for exclusions/file_errors", result["id"], result["status"], result.get("reason", ""))
    record["selected_bytes"] = sum(x["size_bytes"] for x in record["files"])
    record["status"] = "inventory_incomplete" if any(d["status"] != "planned" or d.get("excluded") for d in record["datasets"]) else "inventory_complete"
    record["inventory_finished_utc"] = datetime.now(timezone.utc).isoformat()
    json_save(run_dir / "inventory.json", record)
    return record


def transfer_with_connection_retries(item, output, args, dependency=None):
    if dependency is not None:
        try:
            label_status = dependency.result()
        except (requests.RequestException, OSError, ValueError, RuntimeError):
            raise ValueError("Required detached-label transfer failed; image partial retained") from None
        if label_status not in {"downloaded", "verified_existing"}:
            raise ValueError("Required detached-label transfer did not complete; image partial retained")
    try:
        return retry_connections(
            lambda: transfer(item, output, args.timeout, args.attempts, args.cookies),
            item["relative_path"], LOG, getattr(args, "connection_retries", 3), STOP)
    except InterruptedError:
        if STOP.is_set():
            return "cancelled"
        raise


def run_downloads(record, output, run_dir, args):
    STOP.clear()
    files = record["files"]
    targets = [str(safe_path(output, i["relative_path"])).casefold() for i in files]
    if len(targets) != len(set(targets)):
        raise ValueError("Duplicate output destinations; no workers started")
    missing = sum(i["size_bytes"] for i in files if not safe_path(output, i["relative_path"]).exists())
    if shutil.disk_usage(output).free < missing + 1024**3:
        raise OSError("Insufficient free space for selected downloads plus a 1 GiB reserve")
    results = []
    record["status"] = "running"
    json_save(run_dir / "download.json", record)
    pool = ThreadPoolExecutor(max_workers=args.workers)
    # Queue D26 labels first so even a one-worker pool cannot deadlock while an
    # image waits for the verified label that defines its raw binary layout.
    def dtm_label(item):
        return item["dataset"] == "D26" and Path(item["relative_path"]).suffix.lower() == ".lbl"
    label_futures, futures = {}, {}
    for item in sorted(files, key=lambda x: not dtm_label(x)):
        dependency = None
        if item["dataset"] == "D26" and Path(item["relative_path"]).suffix.lower() == ".img":
            dependency = label_futures.get(str(Path(item["relative_path"]).with_suffix(".lbl")))
        future = pool.submit(transfer_with_connection_retries, item, output, args, dependency)
        futures[future] = item
        if dtm_label(item):
            label_futures[str(Path(item["relative_path"]))] = future
    try:
        for future in as_completed(futures):
            item = futures[future]
            try:
                result = {"dataset": item["dataset"], "path": item["relative_path"], "status": future.result()}
            except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
                LOG.exception("File transfer failed: %s", item["relative_path"])
                result = {"dataset": item["dataset"], "path": item["relative_path"], "status": "failed", "error": str(error)}
                print(f"FAILED {item['dataset']}: {error}", file=sys.stderr, flush=True)
            results.append(result)
            record["transfers"] = results
            json_save(run_dir / "download.json", record)
    except KeyboardInterrupt:
        STOP.set()
        for future in futures:
            future.cancel()
        record["status"] = "interrupted"
        raise
    finally:
        pool.shutdown(wait=True, cancel_futures=True)
        json_save(run_dir / "download.json", record)
    unresolved = [x for x in record["datasets"] if x["status"] != "planned" or x.get("excluded")]
    failed = any(x["status"] in {"failed", "cancelled"} for x in results)
    record["status"] = "failed" if failed else "incomplete" if unresolved else "complete_pilot"
    record["dataset_outcomes"] = dataset_outcomes(record)
    LOG.info("Download outcome %s; unresolved=%s", record["status"],
             {key: value["status"] for key, value in record["dataset_outcomes"].items()
              if value["status"] not in {"planned", "complete"}})
    json_save(run_dir / "download.json", record)
    return 1 if failed else 2 if unresolved else 0


def dataset_outcomes(record):
    """Report transfer failures as well as source-selection problems."""
    transfers = {x["path"]: x for x in record.get("transfers", [])}
    outcomes = {}
    for dataset in record["datasets"]:
        key = dataset["id"]
        files = [x for x in record["files"] if x["dataset"] == key]
        completed = [x for x in files if transfers.get(x["relative_path"], {}).get("status") in {"downloaded", "verified_existing"}]
        failed = [x for x in files if transfers.get(x["relative_path"], {}).get("status") in {"failed", "cancelled"}]
        status = dataset["status"]
        if failed:
            status = "transfer_failed"
        elif status == "planned" and dataset.get("excluded"):
            status = "partial_selection"
        elif status == "planned" and "transfers" in record:
            status = "complete" if files and len(completed) == len(files) else "pending"
        outcomes[key] = {"status": status, "selected_files": len(files), "completed_files": len(completed),
                         "failed_files": [x["relative_path"] for x in failed]}
    return outcomes


def validate_inventory(record, output, args):
    if (not isinstance(record, dict) or record.get("schema") != 1 or record.get("pilot_only") is not True
            or not isinstance(record.get("files"), list) or not isinstance(record.get("datasets"), list)
            or not record["datasets"]):
        raise ValueError("Unsupported or empty pinned inventory")
    datasets = record["datasets"]
    if (any(not isinstance(d, dict) or d.get("id") not in CATALOG or "status" not in d for d in datasets)
            or len({d["id"] for d in datasets}) != len(datasets)):
        raise ValueError("Invalid/duplicate dataset in pinned inventory")
    declared = {d["id"] for d in datasets}
    paths, pending_by_dataset = set(), {}
    for item in record["files"]:
        if (not isinstance(item, dict) or item.get("dataset") not in declared
                or type(item.get("size_bytes")) is not int or item["size_bytes"] < 1):
            raise ValueError("Invalid file in pinned inventory")
        path = safe_path(output, item["relative_path"])
        safe_url(item["url"])
        ext = Path(item["relative_path"]).suffix.lower()
        obsolete = ("embedded_label" if item["dataset"] == "D26" and ext == ".img" else
                    "float32_tiff" if item["dataset"] == "D27" and ext == ".xml" and item.get("metadata") else None)
        if obsolete and item.get(obsolete):
            item.pop(obsolete)
            correction = {"path": item["relative_path"], "removed_obsolete_validation_flag": obsolete}
            record.setdefault("validation_policy_corrections", []).append(correction)
            LOG.warning("Correcting historical validation flag: %s", correction)
        key = str(path).casefold()
        if key in paths:
            raise ValueError("Duplicate output in pinned inventory")
        paths.add(key)
        if not path.exists():
            if item["size_bytes"] > args.max_file_mib * 1024**2:
                raise ValueError("Pinned file exceeds current byte limit")
            dataset = item["dataset"]
            pending_by_dataset[dataset] = pending_by_dataset.get(dataset, 0) + item["size_bytes"]
    if (sum(pending_by_dataset.values()) > args.max_total_mib * 1024**2
            or any(n > args.max_dataset_mib * 1024**2 for n in pending_by_dataset.values())):
        raise ValueError("Pinned inventory exceeds current dataset/total byte limits")
    record["selected_bytes"] = sum(i["size_bytes"] for i in record["files"])


def completed_ode_inventory(output, config, args):
    """Reuse checked local results even after ODE's temporary result URLs expire."""
    cache = safe_path(output, "moon/diviner/ode_rdr/" + config["ode_fingerprint"] + "/selection.json")
    if not cache.is_file():
        return None
    record = json.loads(cache.read_text(encoding="utf-8"))
    validate_inventory(record, output, args)
    datasets = record["datasets"]
    if (len(datasets) != 1 or datasets[0]["id"] != "D20"
            or datasets[0].get("ode_params") != config["ode_params"]
            or datasets[0].get("ode_fingerprint") != config["ode_fingerprint"]):
        raise ValueError("Cached ODE selection identity differs; preserved: " + str(cache))
    if (not record["files"] or datasets[0]["status"] != "planned" or datasets[0].get("excluded")
            or not 0 < datasets[0]["ode_observation_count"] <= config["ode_max_points"]):
        return None
    complete = True
    for item in record["files"]:
        if not verify_existing(safe_path(output, item["relative_path"]), item, output):
            complete = False
    return record if complete else None


def eda_main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", nargs="+", choices=CATALOG, help="Default: 36 Dxx datasets plus R01/R02 references")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--files-per-dataset", type=int, default=2, help="Primary science groups, each with listed companion labels")
    parser.add_argument("--max-file-mib", type=int, default=512)
    parser.add_argument("--max-dataset-mib", type=int, default=1024)
    parser.add_argument("--max-total-mib", type=int, default=8192)
    parser.add_argument("--pages-per-dataset", type=int, default=12)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=1)
    parser.add_argument("--connection-retries", type=int, default=3,
                        help="Extra connection retries after the initial attempt (default 3; 0 disables)")
    parser.add_argument("--selections", type=Path, help="JSON mapping dataset IDs to scope and explicit groups of science/label URLs")
    parser.add_argument("--cookies", type=Path, help="Optional Netscape cookie file for authorised archive access; never saved in manifests")
    parser.add_argument("--from-inventory", type=Path, help="Reuse exact inventory.json selections; no source rediscovery")
    add_diviner_ode_arguments(parser)
    args = parser.parse_args(argv)
    for name in ("workers", "files_per_dataset", "max_file_mib", "max_dataset_mib", "max_total_mib", "pages_per_dataset", "timeout", "attempts"):
        if getattr(args, name) < 1:
            parser.error(f"--{name.replace('_', '-')} must be positive")
    if args.workers > 16:
        parser.error("Use at most 16 workers to avoid overwhelming archive servers")
    if args.connection_retries < 0:
        parser.error("Connection retries must be non-negative")
    ode_config = diviner_ode_config(args, parser)
    selected = args.datasets or list(CATALOG)
    if len(selected) != len(set(selected)):
        parser.error("Dataset IDs must be unique")
    configs = catalog()
    if ode_config:
        configs["D20"] = {**configs["D20"], **ode_config}
    if args.dry_run:
        if args.from_inventory:
            if args.datasets or args.selections:
                parser.error("Do not combine --from-inventory with --datasets/--selections")
            try:
                record = json.loads(args.from_inventory.read_text(encoding="utf-8-sig"))
                validate_inventory(record, args.output.expanduser().resolve(), args)
            except (OSError, ValueError, KeyError) as error:
                parser.error(str(error))
            for item in record["files"]:
                print(item["dataset"], item["relative_path"], item["size_bytes"])
            print("Offline pinned preview: no network or writes.")
            return 0
        for key in selected:
            cfg = configs[key]
            print(key, cfg["name"], "|", cfg.get("note") or cfg.get("root") or cfg["sources"])
            if ode_config:
                print("ODE query:", ODE_DIVINER + "?" + urlencode(ode_config["ode_params"]))
                print("Observation cap:", ode_config["ode_max_points"], "| CSV + supplied labels + RDR SIS; no images")
        print(f"Offline preview: workers={args.workers}, groups/dataset={args.files_per_dataset}, total cap={args.max_total_mib} MiB. No writes/network.")
        return 0
    output = args.output.expanduser().resolve()
    STOP.clear()
    run_dir = safe_path(output, "manifests/eda_datasets/" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ"))
    handlers = []
    try:
        run_dir.mkdir(parents=True, exist_ok=False)
        handlers = start_debug_log(run_dir)
        LOG.info("Selected dataset IDs %s; workers=%s; file/dataset/total MiB=%s/%s/%s", selected, args.workers, args.max_file_mib, args.max_dataset_mib, args.max_total_mib)
        LOG.info("Connection retry batches=%s (0=no extra retries); attempts per batch=%s", args.connection_retries, args.attempts)
        print("Debug log:", run_dir / "debug.txt", flush=True)
        print("Error log:", run_dir / "errors.txt", flush=True)
        original_helpers()  # Import originals once, before any worker threads.
        overrides = json.loads(args.selections.read_text(encoding="utf-8-sig")) if args.selections else {}
        if not isinstance(overrides, dict) or set(overrides) - set(CATALOG):
            raise ValueError("Selections must map configured dataset IDs to explicit product selections")
        if args.from_inventory:
            if args.datasets or args.selections:
                raise ValueError("Do not combine --from-inventory with --datasets/--selections")
            record = json.loads(args.from_inventory.read_text(encoding="utf-8-sig"))
            validate_inventory(record, output, args)
            LOG.info("Pinned inventory dataset IDs: %s", [d["id"] for d in record["datasets"]])
            json_save(run_dir / "inventory.json", record)
        else:
            record = completed_ode_inventory(output, ode_config, args) if ode_config else None
            if record is None:
                record = inventory([configs[k] for k in selected], output, run_dir, args, overrides)
                if (ode_config and record["files"] and record["status"] == "inventory_complete"):
                    cache = safe_path(output, "moon/diviner/ode_rdr/" + ode_config["ode_fingerprint"] + "/selection.json")
                    json_save(cache, record)
            else:
                LOG.info("Reusing complete hash-verified ODE selection; no remote query or HEAD needed")
                print("Reusing verified ODE files; no query regeneration or redownload.", flush=True)
                json_save(run_dir / "inventory.json", record)
        print(f"Inventory: {run_dir / 'inventory.json'}\nSelected bytes: {record['selected_bytes']:,}. Pilot selections do not replace full preprocessing inputs.")
        if args.download:
            result = run_downloads(record, output, run_dir, args)
        else:
            result = 2 if any(x["status"] != "planned" or x.get("excluded") for x in record["datasets"]) else 0
        outcomes = dataset_outcomes(record)
        print("Unresolved entries:", ", ".join(key + ":" + value["status"] for key, value in outcomes.items()
                                              if value["status"] not in {"planned", "complete"}) or "none")
        LOG.info("Run finished exit_code=%s selected_bytes=%s", result, record["selected_bytes"])
        return result
    except KeyboardInterrupt:
        LOG.warning("Run interrupted; partial files preserved")
        print("Interrupted; partials preserved. Resume using the pinned inventory.", file=sys.stderr)
        return 130
    except (requests.RequestException, OSError, ValueError, RuntimeError, KeyError) as error:
        LOG.exception("Run failed")
        print(f"EDA downloader failed: {error}", file=sys.stderr)
        return 1
    finally:
        for handler in handlers:
            LOG.removeHandler(handler)
            handler.close()


DATASETS = ("earth-climate", "earth-climate-expansion", "lunar-temperature", "lunar-illumination")


SCRIPT_DIRECTORY = Path(__file__).resolve().parents[2] / "download scripts"


DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data"


def build_commands(output: Path, datasets: list[str], *, download: bool = False,
                   timeout: int = 120, attempts: int = 3) -> list[tuple[str, list[str]]]:
    """Build a fixed P1-only plan; do not import children, write files or use the network."""
    if not datasets or len(datasets) != len(set(datasets)) or not set(datasets) <= set(DATASETS):
        raise ValueError("Select unique datasets from the four P1 entries")
    if type(timeout) is not int or timeout < 1 or type(attempts) is not int or attempts < 1:
        raise ValueError("Timeout and attempts must be positive integers")
    output = output.expanduser().resolve()
    climate = ["--start-year", "2015", "--end-year", "2024",
               "--variables", "tmin", "tmax", "ppt", "ws", "srad"]
    jobs = {
        "earth-climate": (
            "download_terraclimate.py", ["--project-areas", *climate],
            output / "earth/terraclimate", "--attempts"),
        "earth-climate-expansion": (
            "download_terraclimate.py",
            ["--bbox", "-117.1", "36.0", "-116.6", "36.5",
             "--bbox", "35.2", "29.4", "35.65", "29.8", *climate],
            output / "earth/environment_expansion/20261030/terraclimate", "--attempts"),
        "lunar-temperature": (
            "download_diviner_south_polar.py", ["--collections", "seasonal"],
            output / "moon/diviner", "--attempts"),
        "lunar-illumination": (
            "download_lunar_illumination_2016.py", ["--hemisphere", "south", "--skip-img"],
            output / "moon/illumination_2016", "--retries"),
    }
    commands = []
    for name in datasets:
        script, selection, destination, retry_flag = jobs[name]
        command = [sys.executable, str(SCRIPT_DIRECTORY / script), *selection,
                   "--output", str(destination), "--timeout", str(timeout), retry_flag, str(attempts)]
        if download:
            command.append("--download")
        commands.append((name, command))
    return commands


def core_main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--datasets", choices=DATASETS, nargs="+", default=None,
                        help="Restrict to selected P1 entries (default: all four plus required Moon support)")
    parser.add_argument("--restore-moon-support", action="store_true",
                        help="Restore only Moon support, or add support to an explicit --datasets selection")
    parser.add_argument("--moon-support-inventory", type=Path,
                        help="Use a prior Moon support run.json or 'latest' to bypass catalogue discovery")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT,
                        help="Data root, created if missing (default: darrel stuff/data)")
    parser.add_argument("--download", action="store_true", help="Transfer source files; default is inventory only")
    parser.add_argument("--dry-run", action="store_true", help="Print the plan only, without network or writes")
    parser.add_argument("--timeout", type=int, default=120, help="Child HTTP read timeout in seconds")
    parser.add_argument("--workers", type=int, default=4, help="Per-file workers in each consolidated child")
    parser.add_argument("--attempts", type=int, default=1, help="Child transfer attempts per source URL")
    parser.add_argument("--connection-retries", type=int,
                        help="Connection retries after initial attempt; 0 disables extra retries")
    parser.add_argument("--continue-on-error", action="store_true",
                        help="Log failed child jobs and continue; final exit status still reports failure")
    args = parser.parse_args(argv)
    if args.connection_retries is not None and args.connection_retries < 0:
        parser.error("Connection retries must be non-negative")
    selected = args.datasets if args.datasets is not None else ([] if args.restore_moon_support else list(DATASETS))
    try:
        commands = build_commands(args.output, selected, download=args.download,
                                  timeout=args.timeout, attempts=args.attempts) if selected else []
        if args.restore_moon_support or args.datasets is None:
            if args.timeout < 1 or args.attempts < 1:
                raise ValueError("Timeout and attempts must be positive integers")
            command = [sys.executable, str(Path(__file__).resolve()), "--scope", "moon-support",
                       "--output", str(args.output.expanduser().resolve()),
                       "--timeout", str(args.timeout), "--attempts", str(args.attempts)]
            command.extend(["--workers", str(args.workers)])
            if args.download:
                command.append("--download")
            if args.moon_support_inventory:
                command.extend(["--from-inventory", str(args.moon_support_inventory)])
            if args.connection_retries is not None:
                command.extend(["--connection-retries", str(args.connection_retries)])
            commands.append(("moon-support", command))
        elif args.moon_support_inventory:
            raise ValueError("--moon-support-inventory requires Moon support in the selection")
    except ValueError as error:
        parser.error(str(error))
    if not 1 <= args.workers <= 16:
        parser.error("Workers must be between 1 and 16")
    # Execute this file only. build_commands remains the core selection contract,
    # not a second path that could revert to serial/fail-fast original transfers.
    commands = [(name, [sys.executable, str(Path(__file__).resolve()), "--internal-core", name,
                        *command[2:], "--data-root", str(args.output.expanduser().resolve()),
                        "--workers", str(args.workers), "--connection-retries",
                        str(args.connection_retries if args.connection_retries is not None else 3)])
                if name != "moon-support" else (name, command) for name, command in commands]
    # Check all required child scripts before any inventory or data transfer starts.
    for _, command in commands:
        if not Path(command[1]).is_file():
            parser.error(f"Required downloader is missing: {command[1]}")
    mode = "download" if args.download else "inventory only"
    print(f"Environmental scope: {', '.join(name for name, _ in commands)} ({mode}).", flush=True)
    for name, command in commands:
        print(f"\n{name}:\n  {subprocess.list2cmdline(command)}", flush=True)
    if args.dry_run:
        print("\nDry run only: no network requests, manifests or datasets written.")
        return 0
    output = args.output.expanduser().resolve()
    try:
        # Reuse an existing directory; create it and any missing parents otherwise.
        output.mkdir(parents=True, exist_ok=True)
    except OSError as error:
        print(f"Unable to create data directory {output}: {error}", file=sys.stderr)
        return 1
    print("\nRunning sequentially. Each downloader retains its own manifests and resume/verification rules.", flush=True)
    failures = []
    error_log = output / "manifests/environmental_runner" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ") / "errors.txt"
    try:
        for name, command in commands:
            print(f"\nStarting {name}...", flush=True)
            try:
                subprocess.run(command, check=True)
            except (subprocess.CalledProcessError, OSError) as error:
                if isinstance(error, subprocess.CalledProcessError) and error.returncode == 130:
                    return 130
                if not args.continue_on_error:
                    raise
                failures.append(name)
                error_log.parent.mkdir(parents=True, exist_ok=True)
                with error_log.open("a", encoding="utf-8") as stream:
                    stream.write(f"{datetime.now(timezone.utc).isoformat()} {name}: {error}\n")
                print(f"SKIP failed job {name}: {error}; continuing. Error log: {error_log}", file=sys.stderr, flush=True)
    except subprocess.CalledProcessError as error:
        print(f"Stopped: {name} failed with exit code {error.returncode}; remaining entries were not run.", file=sys.stderr)
        return error.returncode if error.returncode > 0 else 1
    except OSError as error:
        print(f"Unable to start {name}: {error}", file=sys.stderr)
        return 1
    except KeyboardInterrupt:
        print("\nInterrupted. Rerun with the same options to reuse existing downloads/partials.", file=sys.stderr)
        return 130
    if failures:
        print(f"\nRemaining jobs finished; failed: {', '.join(failures)}. See {error_log}", file=sys.stderr)
        return 1
    print(f"\nAll selected environmental {mode} jobs completed.", flush=True)
    return 0


def moon_support_transfer(item, output, args):
    """Independent session and exclusive destination lock for every Moon file."""
    path = destination(output, item["relative_path"])
    path.parent.mkdir(parents=True, exist_ok=True)
    lock = path.with_name(path.name + ".download.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        with session() as client:
            return retry_connections(
                lambda: download_file(client, item, output, args.timeout, 1),
                item["relative_path"], LOG, args.connection_retries, STOP)
    finally:
        lock.unlink()


def climate_transfer(job, folder, args):
    """Retain the original NetCDF/receipt validation; one finite retry budget."""
    import download_terraclimate as climate
    target = destination(folder, job["path"])
    target.parent.mkdir(parents=True, exist_ok=True)
    lock = target.with_name(target.name + ".download.lock")
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        with os.fdopen(descriptor, "w") as stream:
            stream.write(str(os.getpid()))
        with session() as client:
            return retry_connections(
                lambda: climate.download(client, target, job["source"], job["variable"],
                                         job["year"], tuple(job["bounds"]), args.timeout, 1),
                job["path"], LOG, args.connection_retries, STOP)
    finally:
        lock.unlink()


def core_worker(argv):
    """Internal same-file child: threaded core files, retaining canonical paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("name", choices=DATASETS)
    parser.add_argument("--data-root", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--workers", type=int, default=4)
    parser.add_argument("--connection-retries", type=int, default=3)
    parser.add_argument("--attempts", "--retries", type=int, default=1)
    parser.add_argument("--project-areas", action="store_true")
    parser.add_argument("--bbox", type=float, nargs=4, action="append")
    parser.add_argument("--start-year", type=int, default=2015)
    parser.add_argument("--end-year", type=int, default=2024)
    parser.add_argument("--variables", nargs="+", default=["tmin", "tmax", "ppt", "ws", "srad"])
    parser.add_argument("--collections", nargs="+", default=["seasonal"])
    parser.add_argument("--hemisphere", default="south")
    parser.add_argument("--skip-img", action="store_true")
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16 or args.connection_retries < 0 or args.timeout < 1:
        parser.error("Invalid worker/retry/timeout settings")
    root, output = args.data_root.expanduser().resolve(), args.output.expanduser().resolve()
    if not output.is_relative_to(root):
        parser.error("Core output must remain inside the data root")
    output.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    run_dir = destination(root, "manifests/core/" + args.name + "/" + stamp)
    run_dir.mkdir(parents=True)
    handlers = start_debug_log(run_dir)
    STOP.clear()
    try:
        original_helpers()
        with session() as client:
            if args.name.startswith("earth-climate"):
                import download_terraclimate as climate
                raw, _ = retry_connections(lambda: metadata(client, climate.CATALOG, args.timeout),
                                          "TerraClimate source catalogue", LOG, args.connection_retries, STOP)
                available = climate.catalog_entries(raw.decode("utf-8"))
                areas = climate.AREAS if args.project_areas else {
                    f"region_{i:02d}": tuple(box) for i, box in enumerate(args.bbox or [], 1)}
                if not areas:
                    raise ValueError("No climate areas selected")
                jobs = []
                for area, bounds in areas.items():
                    box_id = hashlib.sha256(json.dumps(bounds).encode()).hexdigest()[:12]
                    for year in range(args.start_year, args.end_year + 1):
                        for variable in dict.fromkeys(args.variables):
                            key = f"TERRACLIMATE_ALL/data/TerraClimate_{variable}_{year}.nc"
                            if key not in available:
                                raise ValueError(f"Requested source unavailable: {key}")
                            source = climate.request_spec(variable, year, bounds)
                            source["catalog_modified"] = available[key]
                            jobs.append({"area": area, "bounds": bounds, "year": year, "variable": variable,
                                         "source": source,
                                         "path": f"subsets/{area}/{box_id}/TerraClimate_v1.1_{variable}_{year}.nc"})
                record = {"status": "planned", "jobs": jobs, "connection_retries": args.connection_retries,
                          "workers": args.workers, "catalog_url": climate.CATALOG, "timeout": args.timeout,
                          "attempts": args.connection_retries + 1,
                          "dataset": "https://www.climatologylab.org/terraclimate.html"}
                manifest = output / "manifests" / (stamp + "_run.json")
                save_json(manifest, record)
                manifest.with_name(stamp + "_catalog.xml").write_bytes(raw)
                print("Climate requests:", len(jobs), "Inventory:", manifest, flush=True)
                if not args.download:
                    return 0
                record["status"] = "running"
                save_json(manifest, record)
                pool = ThreadPoolExecutor(max_workers=args.workers)
                futures = {pool.submit(climate_transfer, job, output, args): job for job in jobs}
                try:
                    for future in as_completed(futures):
                        job = futures[future]
                        try:
                            job["status"] = future.result()
                        except (requests.RequestException, OSError, ValueError, RuntimeError, KeyError) as error:
                            job.update(status="failed", error=str(error))
                            LOG.exception("Climate file failed; continuing: %s source=%s", job["path"], job["source"])
                            print("FAILED", job["path"], error, file=sys.stderr, flush=True)
                        else:
                            print(job["status"], job["path"], flush=True)
                        save_json(manifest, record)
                except KeyboardInterrupt:
                    STOP.set()
                    record["status"] = "interrupted"
                    save_json(manifest, record)
                    raise
                finally:
                    pool.shutdown(wait=True, cancel_futures=True)
                failed = any(job.get("status") == "failed" for job in jobs)
                record["status"] = "failed" if failed else "complete"
                save_json(manifest, record)
                return 1 if failed else 0

            if args.name == "lunar-temperature":
                import download_diviner_south_polar as diviner
                entries = retry_connections(lambda: diviner.fetch_inventory(client, "seasonal", args.timeout),
                                            "Complete south-polar seasonal catalogue", LOG, args.connection_retries, STOP)
                pairs = [(entry, "moon/diviner/seasonal/" + entry.filename) for entry in entries]
                formats = {Path(entry.filename).suffix.lower() for entry in entries}
                if not entries or not formats <= {".tab", ".xml", ".lbl"}:
                    raise ValueError("Unexpected seasonal source collection")
            else:
                _, illumination, _ = original_helpers()
                entries = retry_connections(
                    lambda: illumination.make_manifest(client, ["south"], args.timeout, False, True, run_dir),
                    "Complete south-polar illumination catalogue", LOG, args.connection_retries, STOP)
                pairs = [(entry, "moon/illumination_2016/" + entry.relative_path.replace("\\", "/")) for entry in entries]
            files, failures, resolved_entries = [], [], []
            for entry, relative in pairs:
                url = entry.url
                try:
                    item = retry_connections(
                        lambda e=entry, r=relative: file_item(client, {"url": e.url, "relative_path": r,
                            "metadata": Path(r).suffix.lower() == ".xml"}, args.name, args.timeout),
                        relative + " source metadata", LOG, args.connection_retries, STOP)
                    if args.name == "lunar-temperature":
                        resolved_entries.append(diviner.RemoteFile(entry.collection, entry.filename,
                                                                    entry.url, item["size_bytes"]))
                    else:
                        entry.size_bytes = item["size_bytes"]
                    files.append(item)
                except (requests.RequestException, OSError, ValueError, RuntimeError) as error:
                    LOG.exception("Core file inventory failed; continuing: %s source=%s", relative, url)
                    failures.append({"path": relative, "url": url, "error": str(error)})
            record = {"schema": 1, "pilot_only": False, "status": "planned", "files": files,
                      "datasets": [{"id": args.name, "status": "partial_inventory" if failures else "planned"}],
                      "selected_bytes": sum(item["size_bytes"] for item in files), "file_errors": failures}
            save_json(run_dir / "inventory.json", record)
            if not args.download:
                print("Core inventory:", run_dir / "inventory.json", flush=True)
                return 1 if failures else 0
            args.cookies = None
            args.attempts = 1
            result = run_downloads(record, root, run_dir, args)
            record["status"] = "complete" if result == 0 else "failed" if result == 1 else "incomplete"
            save_json(run_dir / "download.json", record)
            # Keep original manifest locations for existing downstream consumers.
            # Only publish complete selection manifests; existing evidence is never
            # replaced by a partial catalogue discovery.
            if not failures:
                if args.name == "lunar-temperature":
                    diviner.write_manifest(output / "download_manifest.csv", resolved_entries)
                else:
                    illumination.write_manifest(entries, output)
            return result
    except KeyboardInterrupt:
        STOP.set()
        LOG.warning("Core interrupted; existing files/partials retained")
        return 130
    except (requests.RequestException, OSError, ValueError, RuntimeError, KeyError) as error:
        LOG.exception("Core source failed; other selected scopes may continue")
        print("Core source failed:", error, "Log:", run_dir / "errors.txt", file=sys.stderr)
        return 1
    finally:
        for handler in handlers:
            LOG.removeHandler(handler)
            handler.close()


STAGE3_SOURCES = [
    {"id": "S03", "name": "NASA-STD-3001 Volume 1 Rev C crew-health reference (2023)",
     "sources": "https://standards.nasa.gov/node/238", "kind": "direct",
     "group_urls": ["https://standards.nasa.gov/sites/default/files/standards/NASA/C//nasa-std-3001-vol-1-rev-c-signature.pdf"],
     "relative_root": "reference/stage3/nasa_std_3001_v1_c",
     "note": "Program requirement reference; not an automatically selected exposure limit or medical assessment"},
    {"id": "S01", "name": "Life Support Baseline Values and Assumptions Rev2 (2022)",
     "sources": "https://ntrs.nasa.gov/citations/20210024855", "kind": "direct",
     "group_urls": ["https://ntrs.nasa.gov/api/citations/20210024855/downloads/BVAD_2.15.22-final.pdf"],
     "relative_root": "reference/stage3/bvad_rev2",
     "note": "Reference assumptions, not selected crew/equipment capabilities or approved requirements"},
    {"id": "S02", "name": "NASA-STD-3001 Volume 2 Rev F (2026)",
     "sources": "https://standards.nasa.gov/standard/NASA/NASA-STD-3001_VOL_2", "kind": "direct",
     "group_urls": ["https://standards.nasa.gov/system/files/tmp/NASA-STD-3001%20Vol%202%20Rev%20F.pdf"],
     "relative_root": "reference/stage3/nasa_std_3001_v2_f",
     "note": "Requirement reference; program applicability/tailoring is not assumed"},
]


def stage3_reference_main(argv=None):
    """Additional Golden references; reuse threaded transfers/retries, preserve legacy catalog."""
    parser = argparse.ArgumentParser(description="Golden Stage 3 public reference documents")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--workers", type=int, default=2)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--connection-retries", type=int, default=3)
    args = parser.parse_args(argv)
    if not 1 <= args.workers <= 16 or args.timeout < 1 or args.connection_retries < 0:
        parser.error("Invalid workers/timeout/retry budget")
    if args.dry_run:
        print(json.dumps(STAGE3_SOURCES, indent=2))
        return 0
    args.attempts, args.cookies = 1, None
    for key, value in {"files_per_dataset": 2, "max_file_mib": 32, "max_dataset_mib": 32,
                       "max_total_mib": 64, "pages_per_dataset": 1}.items():
        setattr(args, key, value)
    output = args.output.expanduser().resolve()
    folder = output / "manifests/eda_datasets" / datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    folder.mkdir(parents=True, exist_ok=False)
    handlers = start_debug_log(folder)
    try:
        record = inventory(STAGE3_SOURCES, output, folder, args, {})
        json_save(folder / "inventory.json", record)
        code = run_downloads(record, output, folder, args) if args.download else 0
        print("Golden reference inventory:", folder / "inventory.json")
        refresh_error_log(output)
        return code
    finally:
        for handler in handlers:
            LOG.removeHandler(handler)
            handler.close()


def main(argv=None):
    """Single public CLI; sequential scopes, parallel files, finite failure policy."""
    argv = list(sys.argv[1:] if argv is None else argv)
    if "--stage3-references" in argv:
        argv.remove("--stage3-references")
        return stage3_reference_main(argv)
    if argv[:1] == ["--internal-core"]:
        return core_worker(argv[1:])
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--scope", choices=("all", "core", "moon-support", "research", "references"))
    parser.add_argument("--stage3-references", action="store_true", help="Separate Golden public-reference selection; accepts --download/--dry-run, output, workers, timeout and retries")
    parser.add_argument("--datasets", nargs="+", choices=[*DATASETS, *CATALOG])
    parser.add_argument("--restore-moon-support", action="store_true", help="Alias for support-only if no datasets/scope")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true", help="Transfer data; default is inventory only")
    parser.add_argument("--dry-run", action="store_true", help="Offline preview; no writes/network")
    parser.add_argument("--workers", type=int, default=4, help="1-16 simultaneous files; default 4")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--connection-retries", type=int, help="Extra attempts after the initial one; default 3, 0 disables")
    parser.add_argument("--attempts", type=int, help="Legacy total-attempt alias, used only if --connection-retries is absent")
    parser.add_argument("--continue-on-error", action="store_true", help="Compatibility flag; continuation is always enabled")
    parser.add_argument("--moon-support-inventory", type=Path)
    parser.add_argument("--from-inventory", type=Path, help="Pinned research inventory, or support run.json/latest with support scope")
    parser.add_argument("--selections", type=Path)
    parser.add_argument("--cookies", type=Path)
    for name, default in [("files-per-dataset", 2), ("max-file-mib", 512), ("max-dataset-mib", 1024),
                          ("max-total-mib", 8192), ("pages-per-dataset", 12)]:
        parser.add_argument("--" + name, type=int, default=default)
    add_diviner_ode_arguments(parser)
    args = parser.parse_args(argv)
    ode_config = diviner_ode_config(args, parser)
    if ode_config and (args.scope not in (None, "research") or args.restore_moon_support or args.moon_support_inventory):
        parser.error("--diviner-ode is a D20-only research query; run core/Moon support separately")
    retries = args.connection_retries if args.connection_retries is not None else (
        args.attempts - 1 if args.attempts is not None else 3)
    if retries < 0 or (args.attempts is not None and args.attempts < 1):
        parser.error("Retries must be non-negative; attempts must be positive")
    if not 1 <= args.workers <= 16 or args.timeout < 1:
        parser.error("Use 1-16 workers and a positive timeout")
    for key in ("files_per_dataset", "max_file_mib", "max_dataset_mib", "max_total_mib", "pages_per_dataset"):
        if getattr(args, key) < 1:
            parser.error(key.replace("_", "-") + " must be positive")
    selected = args.datasets or []
    if len(selected) != len(set(selected)):
        parser.error("Dataset IDs must be unique")
    core_ids, research_ids = [x for x in selected if x in DATASETS], [x for x in selected if x in CATALOG]
    scope = args.scope
    if scope is None:
        scope = ("all" if core_ids and research_ids else "core" if core_ids else "research" if research_ids
                 else "moon-support" if args.restore_moon_support else "all")
        if args.from_inventory and not selected and not args.restore_moon_support:
            if str(args.from_inventory) == "latest":
                scope = "moon-support"
            else:
                try:
                    pinned = json.loads(args.from_inventory.read_text(encoding="utf-8-sig"))
                except (OSError, ValueError) as error:
                    parser.error(str(error))
                scope = "research" if pinned.get("schema") == 1 and pinned.get("pilot_only") else "moon-support"
    if (scope in {"research", "references", "moon-support"} and core_ids
            or scope in {"core", "moon-support"} and research_ids
            or scope == "references" and any(key not in REFERENCE_SOURCES for key in research_ids)):
        parser.error("Dataset selection conflicts with --scope")
    if args.from_inventory and (selected or args.selections or scope not in {"research", "moon-support"}):
        parser.error("Pinned inventory requires research/support-only scope without datasets/selections")
    include_support = scope in {"all", "core", "moon-support"} and not selected or args.restore_moon_support
    if args.moon_support_inventory and not include_support:
        parser.error("Moon support inventory requires Moon support in the selection")
    if (args.selections or args.cookies) and scope not in {"all", "research", "references"}:
        parser.error("Selections/cookies apply to research/reference sources")
    common = ["--output", str(args.output.expanduser().resolve()), "--timeout", str(args.timeout),
              "--workers", str(args.workers), "--connection-retries", str(retries)]
    if args.download:
        common.append("--download")
    if args.dry_run:
        common.append("--dry-run")
    print(f"Unified downloader: scope={scope}; workers={args.workers}; initial attempt + {retries} retries; errors logged and continued.", flush=True)
    outcomes = []
    if scope == "moon-support":
        flags = list(common) + ["--attempts", "1"]
        support_inventory = args.moon_support_inventory or args.from_inventory
        if support_inventory:
            flags += ["--from-inventory", str(support_inventory)]
        result = moon_support_main(flags)
        if not args.dry_run:
            refresh_error_log(args.output)
        return result
    if core_ids or include_support:
        flags = list(common) + ["--attempts", "1", "--continue-on-error"]
        if core_ids:
            flags += ["--datasets", *core_ids]
        elif selected or scope == "moon-support":
            flags.append("--restore-moon-support")
        if args.restore_moon_support:
            flags.append("--restore-moon-support")
        support_inventory = args.moon_support_inventory or (args.from_inventory if scope == "moon-support" else None)
        if support_inventory:
            flags += ["--moon-support-inventory", str(support_inventory)]
        result = core_main(flags)
        outcomes.append(result)
        if result == 130:
            if not args.dry_run:
                refresh_error_log(args.output)
            return 130
    if scope in {"all", "research", "references"} and (research_ids or not selected):
        flags = list(common) + ["--attempts", "1"]
        if research_ids or scope == "references":
            flags += ["--datasets", *(research_ids or list(REFERENCE_SOURCES))]
        if args.from_inventory:
            flags += ["--from-inventory", str(args.from_inventory)]
        if args.selections:
            flags += ["--selections", str(args.selections)]
        if args.cookies:
            flags += ["--cookies", str(args.cookies)]
        if ode_config:
            flags += ["--diviner-ode", "--diviner-bbox", *map(str, args.diviner_bbox),
                      "--diviner-start", args.diviner_start, "--diviner-stop", args.diviner_stop,
                      "--diviner-channels", *map(str, args.diviner_channels),
                      "--diviner-quality-max", *map(str, args.diviner_quality_max),
                      "--diviner-max-points", str(args.diviner_max_points)]
        for key in ("files_per_dataset", "max_file_mib", "max_dataset_mib", "max_total_mib", "pages_per_dataset"):
            flags += ["--" + key.replace("_", "-"), str(getattr(args, key))]
        result = eda_main(flags)
        outcomes.append(result)
        if result == 130:
            if not args.dry_run:
                refresh_error_log(args.output)
            return 130
    if not args.dry_run:
        refresh_error_log(args.output)
    return 1 if 1 in outcomes else 2 if 2 in outcomes else 0


if __name__ == "__main__":
    raise SystemExit(main())
