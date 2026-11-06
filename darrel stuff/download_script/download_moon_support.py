"""Restore only the supporting inputs required by the copied Moon environmental EDA.

Seven original SDEM archives, six exact LOLA maps, and illumination labels/docs.
Inventory only by default; --download also safely extracts SDEMs and builds an
evidence-backed unit policy. --dry-run performs no network requests or writes.
No additional Diviner, illumination IMG, reserve-region, OSM or Mars downloads.

Python 3.12, requests and beautifulsoup4. Original downloaders remain unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import math
from pathlib import Path, PurePosixPath
import re
import shutil
import stat
import sys
import zipfile
import zlib

import requests

ORIGINAL_SCRIPTS = Path(__file__).resolve().parents[2] / "download scripts"
DEFAULT_OUTPUT = Path(__file__).resolve().parents[1] / "data"
ZENODO_RECORD = "17954508"
ZENODO_API = f"https://zenodo.org/api/records/{ZENODO_RECORD}"
REGIONS = (
    "A3CLR22_10_Leibnitz_Beta_Plateau", "A3CLR22_11_Malapert_Massif",
    "A3CLR22_12_deGerlache_Kocher_Massif", "A3CLR22_2_Haworth",
    "A3CLR22_3_Faustini_Rim_A", "A3CLR22_4_deGerlache_Rim_2",
    "A3CLR22_5_Connecting_Ridge_Extension",
)
LOLA_FILES = (
    "LDEM_80S_40MPP_ADJ.TIF", "LDEM_80S_40MPP_ADJ_EFFRES.TIF",
    "LDEM_80S_40MPP_ADJ_ERR.TIF", "LDEC_80S_40MPP_ADJ.TIF",
    "LDSM_80S_40MPP_ADJ.TIF", "LDSM_80S_40MPP_ADJ_ERR.TIF",
)
UNIT_POLICY = "reference/environment-readiness-20261028/native_layer_units.json"


def original_helpers():
    """Reuse existing discovery, resumable transfer, checksums and atomic receipts."""
    sys.path.insert(0, str(ORIGINAL_SCRIPTS))
    import download_lola_product90 as lola
    import download_lunar_illumination_2016 as illumination
    import download_osm as transfer
    return lola, illumination, transfer


def destination(root: Path, relative: str) -> Path:
    target = (root / relative).resolve()
    if not target.is_relative_to(root.resolve()):
        raise ValueError(f"Output escapes the data root: {relative}")
    return target


def save_json(path: Path, value) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    _, _, transfer = original_helpers()
    transfer.save_json(path, value)


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
        transfer.download(session, item, path.parent, timeout, attempts)
        return path
    receipt = path.with_name(path.name + ".json")
    if path.exists():
        saved = json.loads(receipt.read_text(encoding="utf-8")) if receipt.exists() else {}
        if (saved.get("source") != item or path.stat().st_size != item["size_bytes"]
                or saved.get("sha256") != transfer.checksums(path)[1]):
            raise ValueError(f"Existing file/receipt mismatch; preserved: {path}")
        print(f"SKIP verified: {path.name}", flush=True)
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
    illumination.fetch_one(session, spec, path, timeout, attempts, .5)
    if path.stat().st_size != item["size_bytes"]:
        raise ValueError(f"Unexpected downloaded size: {path}")
    if item["format"] == "TIF":
        with path.open("rb") as handle:
            magic = handle.read(4)
        if magic not in (b"II*\x00", b"MM\x00*", b"II+\x00", b"MM\x00+"):
            raise ValueError(f"Response is not a TIFF; preserved for inspection: {path}")
    save_json(receipt, {"source": item, "sha256": transfer.checksums(path)[1],
                        "verified_utc": datetime.now(timezone.utc).isoformat()})
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
        entries = archive_members(archive, region, root)
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
    })
    print(f"Extracted/verified {region}: {len(entries)} files", flush=True)


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


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--attempts", type=int, default=3)
    args = parser.parse_args(argv)
    if args.timeout < 1 or args.attempts < 1:
        parser.error("Timeout and attempts must be positive")
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
    record = {"status": "inventory_started", "regions": list(REGIONS), "lola_files": list(LOLA_FILES)}
    manifest = run_dir / "run.json"
    save_json(manifest, record)
    try:
        with requests.Session() as session:
            session.headers.update({"User-Agent": "Moon-Environmental-Support-Restorer/1.0", "Accept-Encoding": "identity"})
            files = make_inventory(session, output, run_dir, args.timeout)
            record.update({"status": "planned", "files": files, "download_bytes": sum(f["size_bytes"] for f in files)})
            save_json(manifest, record)
            print(f"Known transfers: {record['download_bytes'] / 1e9:.2f} GB. Extraction requires additional space.")
            print("Inventory:", manifest)
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
            for index, item in enumerate(ordered, 1):
                print(f"[{index}/{len(ordered)}] {item['relative_path']}", flush=True)
                download_file(session, item, output, args.timeout, args.attempts)
                item["status"] = "verified_present"
                save_json(manifest, record)
            write_unit_policy(output, files)
            for item in files:
                if item["format"] == "ZIP":
                    extract_archive(destination(output, item["relative_path"]), output)
            actual = {p.name for p in destination(output, "moon/sdem/regions").iterdir() if p.is_dir()}
            if actual != set(REGIONS):
                raise ValueError("SDEM region scope differs from the original seven; no extra folders were removed")
            record["status"] = "complete"
            save_json(manifest, record)
            print("Moon support restoration complete. Run preprocessing 05/06/13, then EDA 25; TODO analyses remain separate.")
            return 0
    except KeyboardInterrupt:
        record.update({"status": "interrupted", "error": "KeyboardInterrupt"})
        save_json(manifest, record)
        print("Interrupted; files/partials preserved. Rerun the same restore command.", file=sys.stderr)
        return 130
    except (requests.RequestException, OSError, ValueError, RuntimeError, zipfile.BadZipFile) as error:
        record.update({"status": "failed", "error": str(error)})
        save_json(manifest, record)
        print(f"Restore failed; existing data preserved: {error}", file=sys.stderr)
        if isinstance(error, requests.exceptions.SSLError):
            print("TLS verification remains enabled. Configure REQUESTS_CA_BUNDLE with a trusted CA if needed.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
