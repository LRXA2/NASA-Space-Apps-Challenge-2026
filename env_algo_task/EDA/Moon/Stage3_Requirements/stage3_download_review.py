"""Frozen acquisition review and dated thermal EDA; no candidate/safety promotion."""
from pathlib import Path
import argparse
import collections
import datetime
import hashlib
import json
import re
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[2] / "shared"), str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[4])]

import matplotlib

matplotlib.use("Agg")  # This batch exports plots; no Tk/display dependency.
import matplotlib.pyplot as plt
import pandas as pd

from environment_workflow import LocalRun
from stage3_mission_eda import (
    ROOT, external_input, read_diviner_query, thermal_quality, save_figure,
)
from stage3_annual_radiation_eda import missing_dates

CONFIG = Path(__file__).with_name("stage3_download_review_config.json")
NOTEBOOK = "Moon/Stage3_Requirements/Dar_040_download_refresh_thermal_quality.ipynb"


def freeze(results, external_root):
    """Freeze one result snapshot; receipt/size readiness is not a full archive hash audit."""
    external_root = Path(external_root).resolve()
    results = Path(results).resolve()
    rows = json.loads(results.read_text(encoding="utf-8"))
    statuses = collections.Counter((r["key"], r["status"]) for r in rows)
    ready, holds, products, seen = [], [], [], set()
    for row in rows:
        if row["status"] not in {"downloaded", "verified_existing"}:
            continue
        inventory = Path(row["checkpoint"]).resolve()
        if not inventory.is_relative_to(external_root):
            raise ValueError("Inventory outside selected external root")
        data = json.loads(inventory.read_text(encoding="utf-8"))
        files = []
        for item in data["files"]:
            path = (external_root / item["relative_path"]).resolve()
            receipt = Path(str(path) + ".json")
            if not path.is_relative_to(external_root):
                raise ValueError("Payload outside selected root")
            if not path.is_file() or not receipt.is_file():
                holds.append({"path": item["relative_path"], "reason": "payload or receipt missing"})
                continue
            saved = json.loads(receipt.read_text(encoding="utf-8"))
            if path.stat().st_size != saved["source"]["size_bytes"] or saved["source"]["url"] != item["url"]:
                holds.append({"path": item["relative_path"], "reason": "receipt identity/size mismatch"})
                continue
            record = {"relative_path": path.relative_to(external_root).as_posix(),
                      "size_bytes": path.stat().st_size, "sha256": saved["sha256"],
                      "receipt": receipt.relative_to(external_root).as_posix(), "url": item["url"]}
            files.append(record)
            if record["relative_path"] not in seen:
                ready.append({"dataset": row["key"], **record})
                seen.add(record["relative_path"])
        if row["key"] == "D20" and len(files) == 2 and {Path(f["relative_path"]).suffix.lower() for f in files} == {".tab", ".lbl"}:
            job = data["job"]
            products.append({"job_id": row["id"], "region": job["region"],
                             "month": job["params"]["minobtime"][:7],
                             "channel": job["params"]["channel"].index("t") + 1,
                             "files": files})
    baseline = json.loads(Path(__file__).with_name("stage3_eda_config.json").read_text(encoding="utf-8"))
    config = {"schema": 1, "cutoff_utc": datetime.datetime.now(datetime.timezone.utc).isoformat(),
              "external_root": str(external_root), "results_path": str(results),
              # The live result file can change during this audit. Pin the parsed
              # snapshot itself, not a later version of that live file.
              "result_snapshot_sha256": hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest(),
              "result_snapshot": rows,
              "status_counts": [{"dataset": k, "status": s, "jobs": n} for (k, s), n in sorted(statuses.items())],
              "ready_files": ready, "holds": holds, "thermal_products": products,
              "region_bounds_m": baseline["region_bounds_m"],
              "readiness_scope": "One result snapshot only; receipt identity and size, not all archive files or rehashed payloads"}
    CONFIG.write_text(json.dumps(config, indent=2), encoding="utf-8")
    print(json.dumps({"cutoff_utc": config["cutoff_utc"], "ready_files": len(ready),
                      "thermal_products": len(products), "holds": len(holds)}, indent=2))


def availability(files):
    """Preserve instrument families/platforms; presence does not establish qualified coverage."""
    dates = collections.defaultdict(list)
    for item in files:
        name = Path(item["relative_path"]).name
        crater = re.fullmatch(r"CRAT_L2_(SEC|PRI)_(\d{7})_V\d+\.TAB", name, re.I)
        goes = re.search(r"_g(\d+)_d(\d{8})_", name)
        if crater:
            dates["CRaTER_" + crater[1].upper()].append(pd.to_datetime(crater[2], format="%Y%j"))
        elif goes and name.endswith(".nc"):
            dates["GOES_" + goes[1]].append(pd.to_datetime(goes[2], format="%Y%m%d"))
    rows = []
    for family, values in sorted(dates.items()):
        unique = sorted(set(values))
        gap = pd.Series(unique).diff().dt.days.fillna(1)
        blocks = gap.gt(1).cumsum()
        longest = int(pd.Series(1, index=blocks.index).groupby(blocks).sum().max())
        rows.append({"instrument_family": family, "files": len(values), "unique_dates": len(unique),
                     "start": str(unique[0].date()), "end": str(unique[-1].date()),
                     "missing_dates_within_span": len(missing_dates(unique)),
                     "longest_consecutive_available_dates": longest,
                     "two_year_uninterrupted_availability": longest >= 730,
                     "scope": "receipt/size-ready availability only; not qualified instrument rows or lunar dose"})
    return pd.DataFrame(rows)


def execute(sample=False):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported download review schema")
    snapshot_hash = hashlib.sha256(json.dumps(config["result_snapshot"], sort_keys=True).encode()).hexdigest()
    if snapshot_hash != config["result_snapshot_sha256"]:
        raise ValueError("Frozen acquisition snapshot identity changed")
    stage = "analysis/stage3_download_review" + ("_sample" if sample else "")
    with LocalRun(ROOT, stage, config, NOTEBOOK) as run:
        for path in [CONFIG, Path(__file__), Path(__file__).with_name("stage3_mission_eda.py"),
                     Path(__file__).with_name("stage3_annual_radiation_eda.py")]:
            run.input(path)
        counts = pd.DataFrame(config["status_counts"])
        counts.to_csv(run.path("download_job_status.csv"), index=False)
        available = availability(config["ready_files"])
        available.to_csv(run.path("radiation_file_availability.csv"), index=False)
        pd.DataFrame(config["holds"], columns=["path", "reason"]).to_csv(run.path("acquisition_holds.csv"), index=False)
        summaries, flags, profiles = [], [], []
        products = config["thermal_products"]
        if sample:
            # Different regions, channels and longitude-side requests before the full batch.
            chosen = {}
            for product in products:
                chosen.setdefault((product["region"], product["channel"]), product)
            products = list(chosen.values())[::max(1, len(chosen) // 8)][:8]
        for i, product in enumerate(products):
            paths = [external_input(run, config, f) for f in product["files"]]
            f = read_diviner_query(next(p for p in paths if p.suffix.lower() == ".tab"),
                                   next(p for p in paths if p.suffix.lower() == ".lbl"))
            if not f.c.eq(product["channel"]).all() or f.duplicated(["sclk", "c", "det"]).any():
                raise ValueError("Ambiguous channel or duplicate native identities within query")
            f = thermal_quality(f, config["region_bounds_m"][product["region"]])
            identity = {k: product[k] for k in ["job_id", "region", "month", "channel"]}
            summaries.append({**identity, "rows": len(f), "in_region_rows": int(f.in_region.sum()),
                              "nonpositive_or_missing_tb": int((~f.physical_temperature).sum()),
                              "strict_rows": int(f.strict_quality.sum()),
                              "diagnostic_rows": int(f.download_policy_diagnostic.sum()),
                              "observed_days": f.timestamp.dt.floor("D").nunique(),
                              "start": f.timestamp.min(), "end": f.timestamp.max()})
            for key, n in f.groupby(["qca", "qge", "qmi"]).size().items():
                flags.append({**identity, "qca": key[0], "qge": key[1], "qmi": key[2], "rows": n})
            for cohort in ["strict_quality", "download_policy_diagnostic"]:
                for row in f.loc[f[cohort]].groupby("local_hour").tb.agg(["count", "median", "min", "max"]).reset_index().to_dict("records"):
                    profiles.append({**identity, "cohort": cohort, **row})
            if i % 50 == 0:
                print("Thermal queries checked:", i + 1, "/", len(products), flush=True)
        summary = pd.DataFrame(summaries)
        if summary.job_id.duplicated().any():
            raise ValueError("Duplicate query jobs in frozen snapshot")
        summary.to_csv(run.path("dated_thermal_support.csv"), index=False)
        pd.DataFrame(flags).to_csv(run.path("dated_thermal_quality_flags.csv"), index=False)
        pd.DataFrame(profiles).to_csv(run.path("dated_thermal_local_hour_profiles.csv"), index=False)
        region = summary.groupby("region").agg(queries=("job_id", "size"),
            months=("month", "nunique"), channels=("channel", "nunique"),
            query_rows=("rows", "sum"), exact_roi_query_rows=("in_region_rows", "sum"),
            strict_query_rows=("strict_rows", "sum"), diagnostic_query_rows=("diagnostic_rows", "sum"))
        region.to_csv(run.path("region_thermal_support.csv"))
        fig, ax = plt.subplots(figsize=(11, 5), layout="constrained")
        region[["strict_query_rows", "diagnostic_query_rows"]].plot.bar(ax=ax)
        ax.set(ylabel="Query rows (not deduplicated across requests)", title="Dated thermal support: strict vs flagged diagnostic")
        ax.tick_params(axis="x", labelrotation=75, labelsize=7)
        save_figure(run, fig, "thermal_quality_by_region")
        findings = {"sample": sample, "cutoff_utc": config["cutoff_utc"], "products": len(summary),
                    "regions": int(summary.region.nunique()), "months": int(summary.month.nunique()),
                    "channels": sorted(summary.channel.unique().tolist()),
                    "query_rows": int(summary.rows.sum()), "exact_roi_query_rows": int(summary.in_region_rows.sum()),
                    "strict_query_rows": int(summary.strict_rows.sum()),
                    "diagnostic_query_rows": int(summary.diagnostic_rows.sum()),
                    "holds": ["Query rows can overlap across requests: not independent unique observations",
                              "Radiation availability is not new row-level EDA; retain earlier qualified findings separately",
                              "Do not merge GOES platforms or CRaTER product families as one calibrated series",
                              "Channel brightness temperature is not component or bolometric temperature",
                              "No changes to candidate measurements, weights, safety cutoffs or operational passes"]}
        run.path("findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
        folder = run.directory
    print(json.dumps(findings, indent=2))
    return folder, findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--freeze-results", type=Path)
    parser.add_argument("--external-root", type=Path, default=Path(r"D:\projects\NASA Dataset"))
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    if args.freeze_results:
        freeze(args.freeze_results, args.external_root)
    else:
        print(execute(args.sample)[0])
