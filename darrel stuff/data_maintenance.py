"""Conservative generated-file cleanup and an offline download-gap report.

Never prune completed analysis runs, source datasets, archives, receipts or logs.
The CLI previews cleanup unless --apply is explicitly supplied.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

DEFAULT_DATA = Path(__file__).resolve().parent / "data"
RUNTIME_NAMES = ("ipythondir", "jupyter_runtime_dir", "jupyter_config_dir")


def checked_path(root, path):
    root = Path(root).resolve()
    path = Path(path)
    if not path.is_absolute():
        path = root / path
    absolute = path.absolute()
    resolved = path.resolve()
    if resolved == root or not resolved.is_relative_to(root):
        raise ValueError(f"Path escapes or equals the data root: {path}")
    for part in (absolute, *absolute.parents):
        if part == root:
            break
        if part.is_symlink() or (hasattr(part, "is_junction") and part.is_junction()):
            raise ValueError(f"Refusing a linked/junction path: {part}")
    return resolved


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def resolve_data_path(root, path):
    """Resolve a journalled local move without rewriting historical inventories."""
    root = Path(root).resolve()
    original = checked_path(root, path)
    journal = root / "manifests/file_relocations.json"
    if not journal.is_file():
        return original
    records = read_json(journal)
    if records.get("schema") != 1:
        raise ValueError("Unsupported file relocation journal")
    matches = [r for r in records["files"] if checked_path(root, r["from"]) == original]
    if not matches:
        return original
    if len(matches) != 1:
        raise ValueError(f"Ambiguous relocation: {original}")
    target = checked_path(root, matches[0]["to"])
    if original.exists() and target.exists():
        raise ValueError(f"Both original and relocated file exist: {original}")
    if original.exists():
        return original  # A journalled move may not have started yet.
    if not target.is_file() or target.stat().st_size != matches[0]["bytes"]:
        raise ValueError(f"Relocated file missing or wrong size: {target}")
    return target


def organize_manual_data(data_root, *, apply=False):
    """Move only the five registered loose D27/D30 products and their receipts.

    Hash every file before moving, journal first, then rename on the same volume.
    A partial operation is recoverable by rerunning; no overwrite or data deletion.
    """
    root = Path(data_root).resolve()
    journal = checked_path(root, "manifests/file_relocations.json")
    if journal.is_file():
        record = read_json(journal)
        if record.get("schema") != 1:
            raise ValueError("Unsupported relocation journal")
    else:
        products = {
            "M013049982S_map_raw.tif": "moon/eda_pilots/D27/manual_M013049982S/",
            "M013049982S_map_raw.xml.txt": "moon/eda_pilots/D27/manual_M013049982S/",
            "global_cpr_128ppd_simp_0c.img": "moon/eda_pilots/D30/manual_global_cpr_128ppd/",
            "global_cpr_128ppd_simp_0c.xml": "moon/eda_pilots/D30/manual_global_cpr_128ppd/",
            "global_cpr_128ppd_simp_0c.lbl": "moon/eda_pilots/D30/manual_global_cpr_128ppd/",
        }
        files = []
        for name, folder in products.items():
            source = checked_path(root, name)
            receipt = checked_path(root, name + ".json")
            if not source.is_file() or not receipt.is_file():
                raise FileNotFoundError(f"Registered source/receipt missing: {source}")
            saved = read_json(receipt)
            sha = digest(source)
            if source.stat().st_size != saved["source"]["size_bytes"] or sha != saved["sha256"]:
                raise ValueError(f"Source differs from receipt: {source}")
            for path in (source, receipt):
                files.append({"from": path.name, "to": folder + path.name,
                              "bytes": path.stat().st_size,
                              "sha256": sha if path == source else digest(path)})
        record = {"schema": 1, "status": "planned", "files": files,
                  "reason": "User-requested organization; historical inventories/receipts remain unchanged"}
    # Preflight ALL entries, including a resumed operation, before any rename.
    for item in record["files"]:
        old, new = checked_path(root, item["from"]), checked_path(root, item["to"])
        if old.exists() and new.exists():
            raise FileExistsError(f"Conflicting target preserved: {new}")
        current = old if old.exists() else new
        if not current.is_file() or current.stat().st_size != item["bytes"] or digest(current) != item["sha256"]:
            raise ValueError(f"Relocation preflight failed: {current}")
    if not apply:
        return record
    atomic_text(journal, json.dumps(record, indent=2) + "\n")
    for item in record["files"]:
        old, new = checked_path(root, item["from"]), checked_path(root, item["to"])
        if old.exists():
            new.parent.mkdir(parents=True, exist_ok=True)
            old.rename(new)
        if digest(new) != item["sha256"]:
            raise ValueError(f"Post-move hash mismatch; data retained: {new}")
    record["status"] = "complete"
    atomic_text(journal, json.dumps(record, indent=2) + "\n")
    return record


def atomic_text(path, text, *, logger=None):
    """Atomically publish a closed owned temporary, tolerating brief Windows locks.

    Retry only Windows access/sharing/lock denials, at most three times. Never
    delete the previous target, change permissions or fall back to an in-place
    write; persistent failures propagate and only our own temporary is removed.
    """
    import logging
    import tempfile
    import time
    log = logger if logger is not None else logging.getLogger(__name__)
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, name = tempfile.mkstemp(prefix=path.name + ".", suffix=".tmp", dir=path.parent)
    temporary = Path(name)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as stream:
            stream.write(text)
        for attempt in range(4):
            try:
                temporary.replace(path)
                break
            except PermissionError as error:
                if getattr(error, "winerror", None) not in {5, 32, 33} or attempt == 3:
                    raise
                delay = .5 * 2 ** attempt
                log.warning("Windows file replacement denied (WinError %s); retry %s/3 in %.1fs: %s. "
                            "Existing target preserved.", error.winerror, attempt + 1, delay, path)
                time.sleep(delay)
    finally:
        temporary.unlink(missing_ok=True)


def digest(path):
    h = hashlib.sha256()
    with Path(path).open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(block)
    return h.hexdigest()


def cleanup_completed_transfer_state(data_root, path, *, apply=True):
    """Discard only redundant identity metadata, never resumable partial bytes."""
    path = checked_path(data_root, path)
    identity = checked_path(data_root, path.with_name(path.name + ".part.json"))
    receipt = checked_path(data_root, path.with_name(path.name + ".json"))
    partial = path.with_name(path.name + ".part")
    if not identity.is_file() or not receipt.is_file() or not path.is_file() or partial.exists():
        return []
    item, saved = read_json(identity), read_json(receipt)
    if (not isinstance(item, dict) or not isinstance(saved, dict)
            or saved.get("source") != item or item.get("size_bytes") != path.stat().st_size
            or not re.fullmatch(r"[0-9a-f]{64}", str(saved.get("sha256", "")))):
        return []
    result = [{"path": str(identity), "bytes": identity.stat().st_size,
               "reason": "redundant completed-transfer identity; final receipt retained"}]
    if apply:
        identity.unlink()
    return result


def referenced_inputs(data_root):
    root = Path(data_root).resolve()
    references = set()
    for manifest in (root / "processed").rglob("provenance.json"):
        for name in read_json(manifest).get("inputs", {}):
            p = Path(name)
            if p.is_absolute():
                references.add(p.resolve())
            else:
                # LocalRun records repository-relative keys; original Run may
                # record paths relative to darrel stuff instead.
                references.update(((root.parent.parent / p).resolve(), (root.parent / p).resolve()))
    # Explicit notebook/script/document pins also protect historical runs even
    # when their consumer has not executed yet.
    source_files = list((root.parent / "EDA").rglob("*.ipynb"))
    source_files += list((root.parent / "EDA").glob("*.md"))
    source_files += list((root / "verification").rglob("*.py"))
    source_files += list(root.parent.glob("*.md"))
    source_files += list(root.parent.glob("*.py"))
    source_files += list((root.parent / "download_script").glob("*.py"))
    source_files += list((root.parent / "research").glob("*.md"))
    source = "\n".join(p.read_text(encoding="utf-8") for p in source_files)
    for run in (root / "processed/analysis").glob("*/*"):
        if run.is_dir() and run.name in source:
            references.add((run / "provenance.json").resolve())
    return references


def cleanup_failed_run(run_dir, data_root, *, apply=True, references=None):
    """Prune unchanged, declared failed-run intermediates; retain failure evidence."""
    root = Path(data_root).resolve()
    run = checked_path(root, run_dir)
    if not run.is_relative_to(root / "processed/analysis"):
        raise ValueError("Only isolated analysis runs may have failed outputs pruned")
    manifest = checked_path(root, run / "provenance.json")
    record = read_json(manifest)
    if record.get("status") != "failed":
        return []
    references = referenced_inputs(root) if references is None else references
    if manifest in references:
        return []
    removed = []
    for item in record.get("outputs", []):
        path = checked_path(run, item["path"])
        if not path.is_file() or path in references:
            continue
        if not (path.name.endswith(".csv.gz") or path.suffix.lower() in {".csv", ".png", ".npy", ".npz"}):
            continue
        if path.stat().st_size != item.get("bytes") or digest(path) != item.get("sha256"):
            continue  # Changed/user-edited artifacts are not disposable.
        removed.append({"path": str(path), "bytes": item["bytes"], "sha256": item["sha256"],
                        "reason": "unreferenced intermediate from a failed analysis run"})
    if apply and removed:
        # Write the audit before deletion. Original provenance remains immutable.
        audit = run / "cleanup.json"
        previous = read_json(audit).get("removed", []) if audit.exists() else []
        atomic_text(audit, json.dumps({"removed": previous + removed}, indent=2) + "\n")
        for item in removed:
            checked_path(run, item["path"]).unlink()
    return removed


def runtime_in_use(run):
    """Conservatively keep runtime state if a Python/Jupyter process uses it."""
    try:
        import psutil
    except ImportError:
        return True
    for process in psutil.process_iter(["name", "cmdline"]):
        try:
            name = (process.info["name"] or "").lower()
            if "python" not in name and "jupyter" not in name:
                continue
            command = " ".join(process.info["cmdline"] or []).casefold()
            if str(run).casefold() in command:
                return True
        except (psutil.AccessDenied, psutil.NoSuchProcess):
            return True
    return False


def cleanup_execution_runtime(run_dir, data_root, *, apply=True):
    """Only the three runner-owned Jupyter/IPython folders, after kernel shutdown."""
    root = Path(data_root).resolve()
    run = checked_path(root, run_dir)
    if run.parent != root / "verification":
        raise ValueError("Execution runtime must be directly under data/verification")
    if runtime_in_use(run):
        return []
    trees, result = [], []
    for name in RUNTIME_NAMES:
        folder = checked_path(root, run / name)
        if not folder.is_dir():
            continue
        descendants = [checked_path(root, p) for p in folder.rglob("*")]
        trees.append((folder, descendants))
        result.extend({"path": str(p), "bytes": p.stat().st_size,
                       "reason": "runner-owned kernel runtime/cache after shutdown"}
                      for p in descendants if p.is_file())
    if apply:
        for folder, descendants in trees:
            for path in sorted(descendants, key=lambda p: len(p.parts), reverse=True):
                if path.is_file():
                    path.unlink()
                elif path.is_dir():
                    path.rmdir()
            folder.rmdir()
    return result


def safe_runtime_cleanup(run_dir, data_root):
    """Exit hook: cleanup errors must not replace a notebook execution failure."""
    try:
        cleanup_execution_runtime(run_dir, data_root)
    except (OSError, ValueError) as error:
        print(f"Runtime cleanup incomplete; state preserved where possible: {error}", file=sys.stderr)


def clean_generated(data_root, *, apply=False):
    root = Path(data_root).resolve()
    removed, warnings = [], []
    references = referenced_inputs(root)
    for manifest in sorted((root / "processed/analysis").glob("*/*/provenance.json")):
        removed.extend(cleanup_failed_run(manifest.parent, root, apply=apply, references=references))
    for identity in sorted(root.rglob("*.part.json")):
        try:
            removed.extend(cleanup_completed_transfer_state(
                root, identity.with_name(identity.name[:-len(".part.json")]), apply=apply))
        except (OSError, ValueError) as error:
            warnings.append(f"Preserved {identity}: {error}")
    for run in sorted((root / "verification").glob("*")):
        if not run.is_dir() or not (run / "verification.json").is_file():
            continue
        removed.extend(cleanup_execution_runtime(run, root, apply=apply))
    return {"apply": apply, "files": removed, "bytes": sum(x["bytes"] for x in removed), "warnings": warnings}


def public_url(value):
    """Retain download parameters, but omit credentials and signed query secrets."""
    if not value:
        return "URL not recorded; inspect the referenced manifest"
    urls = str(value).split(" | ")
    result = []
    for url in urls:
        parts = urlsplit(url)
        host = parts.hostname or ""
        if parts.port:
            host += f":{parts.port}"
        query = [(key, value) for key, value in parse_qsl(parts.query, keep_blank_values=True)
                 if not any(word in key.lower() for word in
                            ("token", "secret", "password", "signature", "credential", "auth", "session", "cookie", "key", "x-amz-"))
                 and key.lower() != "sig"]
        result.append(urlunsplit((parts.scheme, host, parts.path, urlencode(query), "")))
    return " | ".join(result)


def write_error_log(data_root):
    """Latest recorded selections, checked offline for presence/size (not rehashed)."""
    root = Path(data_root).resolve()
    selections, notices = {}, []
    patterns = ("manifests/eda_datasets/*/download.json", "manifests/eda_datasets/*/inventory.json",
                "manifests/core/*/*/download.json", "manifests/core/*/*/inventory.json",
                "manifests/moon_support/*/run.json", "earth/**/manifests/*_run.json")
    manifests = {p for pattern in patterns for p in root.glob(pattern)}
    # Prefer transfer outcomes to inventory within the same run; the timestamped
    # run name, not a mutable mtime, establishes chronology.
    manifests = sorted(manifests, key=lambda p: (p.parent.name if p.name in {"download.json", "inventory.json", "run.json"}
                                                else p.name, p.name == "download.json"))
    for manifest in manifests:
        try:
            record = read_json(manifest)
            if not isinstance(record, dict):
                raise ValueError("Expected a JSON object")
            if "jobs" in record:
                key = "earth-climate-expansion" if "environment_expansion" in manifest.parts else "earth-climate"
                files = []
                for job in record["jobs"]:
                    source = job.get("source", {})
                    url = source.get("url", "")
                    if source.get("params"):
                        url += ("&" if "?" in url else "?") + urlencode(source["params"])
                    files.append({"relative_path": str((manifest.parent.parent / job["path"]).relative_to(root)),
                                  "url": url, "error": job.get("error"), "transfer_status": job.get("status")})
                datasets = [{"id": key, "name": key, "status": record.get("status"), "files": []}]
            else:
                files, datasets = record.get("files", []), record.get("datasets", [])
                if "moon_support" in manifest.parts:
                    datasets = [{"id": "moon-support", "name": "Moon terrain/metadata support",
                                 "status": record.get("status"), "error": record.get("error")}]
            for dataset in datasets:
                key = dataset["id"]
                chosen = [f for f in files if isinstance(f, dict) and
                          (f.get("dataset") == key or key in {"moon-support", "earth-climate", "earth-climate-expansion"})]
                outcome = record.get("dataset_outcomes", {}).get(key, {})
                selections[key] = (dataset, outcome, chosen, manifest, record.get("file_errors", []),
                                   {x.get("path"): x for x in record.get("transfers", [])})
        except (OSError, ValueError, KeyError, TypeError) as error:
            notices.append(f"Manifest could not be interpreted: {manifest.relative_to(root)}: {type(error).__name__}")
    lines = ["ENVIRONMENTAL DATA — MISSING / UNRESOLVED DOWNLOADS",
             "Updated UTC: " + datetime.now(timezone.utc).isoformat(),
             "Offline: latest recorded selection per dataset; existence/size only, not a fresh checksum or source-availability audit.",
             "Bounded subsets are not full archives. Historical resolved errors are not replayed as current missing files.", ""]
    unresolved = 0
    for key, (dataset, outcome, files, manifest, failures, transfers) in sorted(selections.items()):
        issues = []
        for item in files:
            relative = item.get("relative_path")
            if not relative:
                continue
            try:
                path = resolve_data_path(root, relative)
                transfer = transfers.get(relative, {})
                if transfer.get("status", item.get("transfer_status")) in {"failed", "error"}:
                    reason = "recorded transfer failure: " + str(transfer.get("error", item.get("error")) or "see per-run errors.txt")
                elif not path.is_file():
                    reason = "missing selected file"
                elif item.get("size_bytes") is not None and path.stat().st_size != item["size_bytes"]:
                    reason = "selected file has unexpected size"
                else:
                    continue
            except (OSError, ValueError) as error:
                reason = f"unusable destination: {type(error).__name__}"
            issues.append(f"  {reason}: {relative}\n  URL: {public_url(item.get('url'))}")
        status = outcome.get("status", dataset.get("status", "unknown"))
        is_gap = status not in {"complete", "planned", "partial_selection"}
        if issues or is_gap or status == "partial_selection":
            unresolved += 1
            lines.extend([f"[{key}] {dataset.get('name', key)}", f"Status: {status}",
                          f"Evidence: {manifest.relative_to(root)}"])
            lines.extend(issues)
            if not issues:
                lines.append("Selected files present by size, or no files selected; status is a selection/access/run limitation, not proof of missing bytes.")
            if status == "partial_selection":
                lines.append("Selected subset is present if no missing files are listed; broader groups were excluded by pilot bounds.")
            if dataset.get("sources"):
                lines.append("Source: " + public_url(dataset["sources"]))
            if dataset.get("error"):
                lines.append("Recorded reason: " + re.sub(r"https?://[^\s'\"]+", lambda m: public_url(m[0]), str(dataset["error"])))
            for excluded in dataset.get("excluded", []):
                if excluded.get("reason") == "pilot_byte_limit":
                    lines.append("Excluded by configured byte limit (not a failed transfer):")
                    lines.extend("  URL: " + public_url(url) for url in excluded.get("urls", []))
                    break
            for failure in failures:
                lines.append(f"Discovery error: {failure.get('path', '')}; URL: {public_url(failure.get('url'))}")
            lines.append("")
    lines.extend(notices)
    if not unresolved:
        lines.append("No missing/unresolved selections found in the available manifests." if selections else
                     "No download manifests found: download completeness is UNKNOWN.")
    lines.extend(["", "Mission/crew/equipment limits and response models are project inputs, not missing downloadable datasets.",
                  "Keep per-run debug.txt/errors.txt, receipts and inventories; use their exact product URLs for manual retrieval."])
    target = checked_path(root, root / "error_log.txt")
    atomic_text(target, "\n".join(lines) + "\n")
    return target


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path, default=DEFAULT_DATA)
    parser.add_argument("--apply", action="store_true", help="Remove confirmed disposable generated files")
    parser.add_argument("--report-only", action="store_true", help="Refresh error_log.txt without cleanup")
    parser.add_argument("--organize-manual", action="store_true", help="Preview the registered loose D27/D30 moves; --apply performs them")
    args = parser.parse_args(argv)
    root = args.data_root.expanduser().resolve()
    if not root.is_dir():
        parser.error(f"Data root does not exist: {root}")
    if args.organize_manual:
        print(json.dumps(organize_manual_data(root, apply=args.apply), indent=2))
    elif not args.report_only:
        report = clean_generated(root, apply=args.apply)
        if args.apply:
            atomic_text(root / "cleanup_log.json", json.dumps(report, indent=2) + "\n")
        print(json.dumps(report, indent=2))
    if args.apply or args.report_only:
        print("Download-gap report:", write_error_log(root))


if __name__ == "__main__":
    main()
