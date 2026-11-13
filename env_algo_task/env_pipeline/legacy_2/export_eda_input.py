"""Export accepted EDA quantities to sites.csv, keeping nonlocal evidence context-only."""
from __future__ import annotations

import argparse
import csv
from datetime import timedelta
import hashlib
import json
from pathlib import Path
import statistics

import run_pipeline as engine

HERE = Path(__file__).resolve().parent
DATA = HERE.parents[1] / "data/processed/analysis"


def accepted_table(run, name, consumed):
    folder = (HERE / run).resolve()
    if not folder.is_relative_to(DATA.resolve()):
        raise ValueError("EDA source must remain under local accepted analysis outputs")
    provenance = folder / "provenance.json"
    record = engine.read_json(provenance)
    if record.get("status") != "complete":
        raise ValueError(f"EDA source is not complete: {folder}")
    matches = [x for x in record["outputs"] if x["path"] == name]
    path = folder / name
    if len(matches) != 1 or engine.sha256(path) != matches[0]["sha256"]:
        raise ValueError(f"Unregistered or changed EDA output: {path}")
    consumed[str(provenance)] = engine.sha256(provenance)
    consumed[str(path)] = matches[0]["sha256"]
    with path.open(encoding="utf-8-sig", newline="") as handle:
        rows = list(csv.DictReader(handle))
    return rows, str(path), matches[0]["sha256"]


def daily_summary(rows, series, start, stop, relation, statistic="median"):
    selected = [r for r in rows if r["series_id"] == series]
    if not selected:
        raise ValueError(f"Declared source series is absent: {series}")
    if relation in {"historical_reference", "source_span"}:
        start = min(engine.utc(r["date"]) for r in selected)
        stop = max(engine.utc(r["date"]) for r in selected) + timedelta(days=1)
    if start is None or stop is None:
        raise ValueError("Daily summary needs a requested window or an explicit source-span relation")
    selected = [r for r in selected if start <= engine.utc(r["date"]) < stop]
    dates = [engine.utc(r["date"]) for r in selected]
    if len(set(dates)) != len(dates):
        raise ValueError(f"Repeated source day for series {series}")
    field = "daily_max" if statistic == "maximum_daily_max" else "daily_median"
    valid = [r for r in selected if r.get(field, "") != "" and engine.number(r["valid_samples"], "valid_samples") > 0]
    support = {
        "evidence_start_utc": start.isoformat(), "evidence_stop_utc": stop.isoformat(),
        "time_relation": relation, "valid_days": len(valid), "recorded_days": len(selected),
        "expected_days": (stop - start).total_seconds() / 86400,
        "support_count": sum(int(engine.number(r["valid_samples"], "valid_samples")) for r in valid),
        "aggregation": "maximum of reported daily maxima" if statistic == "maximum_daily_max" else "median of daily values; equal weight per valid day",
        "first_supported_utc": min((engine.utc(r["date"]).isoformat() for r in valid), default=""),
        "last_supported_utc": max((engine.utc(r["date"]).isoformat() for r in valid), default=""),
    }
    if not valid:
        return "", {**support, "missing_reason": "No supported observations in requested window; no historical fallback"}
    values = [engine.number(r[field], field) for r in valid]
    return (max(values) if statistic == "maximum_daily_max" else statistics.median(values)), support


def export(output_dir, start=None, stop=None, *, limit=None, sources_path=None, overwrite=False):
    start, stop = engine.optional_window(start, stop)
    if start is not None and (start.hour or start.minute or start.second or start.microsecond or stop.hour or stop.minute or stop.second or stop.microsecond):
        raise ValueError("EDA daily summaries require a positive midnight-to-midnight UTC window")
    if limit is not None and limit < 1:
        raise ValueError("--limit must be positive")
    config_path = Path(sources_path or HERE / "eda_sources.json").resolve()
    config = engine.read_json(config_path)
    policy_path = HERE / "environmental_policy.json"
    policy = engine.read_json(policy_path)
    metrics, _ = engine.validate_policy(policy)
    if set(config["features"]) != set(metrics):
        raise ValueError("EDA mapping and default metric registry disagree")
    consumed = {str(config_path): engine.sha256(config_path), str(policy_path): engine.sha256(policy_path),
                str(Path(__file__).resolve()): engine.sha256(__file__)}
    consumed[str(Path(engine.__file__).resolve())] = engine.sha256(engine.__file__)
    cache = {}

    def table(source, filename):
        key = (source, filename)
        if key not in cache:
            cache[key] = accepted_table(config["sources"][source], filename, consumed)
        return cache[key]

    candidates, _, _ = table("candidates", "candidate_manifest.csv")
    if len({r["candidate_id"] for r in candidates}) != len(candidates):
        raise ValueError("Ambiguous candidate identities")
    if limit:
        candidates = candidates[:limit]
    output_dir = Path(output_dir).resolve()
    paths = [output_dir / name for name in ("sites.csv", "evidence.json", "column_guide.csv", "export_provenance.json")]
    if any(p.exists() for p in paths) and not overwrite:
        raise FileExistsError("Export would replace existing inputs; choose a new output directory")
    daily_cache, sites, metadata, guides = {}, [], {}, []
    for position, candidate in enumerate(candidates, 1):
        rid = f"eda_{position:03d}"
        row = dict(id=rid, candidate_id=candidate["candidate_id"], start_utc=start.isoformat() if start else "", stop_utc=stop.isoformat() if stop else "", evidence_ref="evidence.json")
        metadata[rid] = {}
        for mid, metric in metrics.items():
            spec = config["features"][mid]
            frame, path, digest = table(spec["source"], spec["file"])
            meta = dict(body="Moon", candidate_id=candidate["candidate_id"], unit=metric["unit"], quantity=metric["quantity"],
                        basis=spec["basis"], quality="context_only" if metric.get("usage") == "context" else "qualified",
                        scope=spec["scope"], temporal_support=metric["temporal_support"], source=path, source_sha256=digest,
                        interpretation=spec["interpretation"], support_count=0,
                        time_relation="static_reference" if metric["temporal_support"] == "static" else spec.get("relation"))
            kind = spec["kind"]
            value = ""
            if kind == "daily":
                key = (mid, start, stop)
                if key not in daily_cache:
                    relation = "source_span" if start is None and spec["relation"] == "requested_window" else spec["relation"]
                    daily_cache[key] = daily_summary(frame, spec["series"], start, stop, relation, spec.get("statistic", "median"))
                value, support = daily_cache[key]
                meta.update(support, series_id=spec["series"])
                if spec.get("unit_catalog"):
                    catalog, _, _ = table(spec["source"], spec["unit_catalog"])
                    matches = [r for r in catalog if r["series_id"] == spec["series"]]
                    if len(matches) != 1 or matches[0]["unit"] != metric["unit"]:
                        raise ValueError(f"Native series unit differs from mapping: {mid}")
            elif kind == "static":
                matches = [r for r in frame if r["candidate_id"] == candidate["candidate_id"] and r["variable"] == spec["variable"]]
                if len(matches) != 1:
                    raise ValueError("Static candidate/variable association is missing or ambiguous")
                item = matches[0]
                if item["unit"] != metric["unit"]:
                    raise ValueError("Static unit changed")
                if int(item["cells"]) > 0 and int(item["finite_cells"]) == int(item["cells"]):
                    value = engine.number(item[spec["field"]], mid)
                    meta["support_count"] = int(item["finite_cells"])
                else:
                    meta["missing_reason"] = "Incomplete static candidate-cell coverage"
            elif kind == "science_profile":
                matches = [r for r in frame if r["candidate_id"] == candidate["candidate_id"] and r["region"] == candidate["region"]]
                if len(matches) != 1:
                    raise ValueError("Exact candidate science-profile association is missing or ambiguous")
                item = matches[0]
                complete = item.get(spec["field"], "") != ""
                if metric["domain"] == "thermal":
                    complete = complete and int(item["thermal_common_products"]) > 0 and int(item["thermal_minimum_centers"]) > 0
                if complete:
                    value = engine.number(item[spec["field"]], mid)
                    meta["support_count"] = int(item[spec["support_field"]])
                else:
                    meta["missing_reason"] = "No complete accepted fixed-common thermal point profile; available-only phases cannot substitute"
            elif kind == "region_geometry":
                matches = [r for r in frame if r["region"] == candidate["region"] and r["target"] == "SUN"
                           and float(r["height_m"]) == 2 and float(r["radius_m"]) == 20000
                           and r["period_kind"] == "two_year" and engine.utc(r["period_start_utc"]).year == 2020]
                if len(matches) != 1:
                    raise ValueError("Declared region-center geometry scenario is missing or ambiguous")
                item = matches[0]
                value = engine.number(item[spec["field"]], mid)
                if spec.get("transform") == "one_minus":
                    value = 1 - value
                meta.update(support_count=int(item["recorded_samples"]), evidence_start_utc=item["period_start_utc"],
                            evidence_stop_utc=item["period_stop_exclusive_utc"], region=candidate["region"],
                            height_m=2, radius_m=20000, left_censored_runs=item["left_censored_runs"], right_censored_runs=item["right_censored_runs"])
            else:
                raise ValueError(f"Unknown mapping kind: {kind}")
            row[metric["column"]] = value
            metadata[rid][mid] = meta
        sites.append(row)
    for mid, metric in metrics.items():
        example = metadata[sites[0]["id"]][mid]
        guides.append(dict(column=metric["column"], domain=metric["domain"], quantity=metric["quantity"], unit=metric["unit"],
                           usage=metric.get("usage", "candidate"), scope=example["scope"], time_relation=example["time_relation"],
                           evidence_start_utc=example.get("evidence_start_utc", ""), evidence_stop_utc=example.get("evidence_stop_utc", ""),
                           populated_rows=sum(r[metric["column"]] != "" for r in sites), total_rows=len(sites),
                           interpretation=example["interpretation"]))
    for path, digest in consumed.items():
        if engine.sha256(path) != digest:
            raise ValueError(f"Source changed during export: {path}")
    if any(str(path) in consumed for path in paths):
        raise ValueError("Export cannot overwrite accepted sources or configuration")
    files = {
        paths[0]: engine.csv_text(sites, engine.IDENTITY + ["evidence_ref"] + [m["column"] for m in metrics.values()]),
        paths[1]: json.dumps(dict(schema=1, rows=metadata), indent=2, allow_nan=False) + "\n",
        paths[2]: engine.csv_text(guides, list(guides[0])),
    }
    record = dict(schema=1, body="Moon", input_rows=len(sites), requested_start_utc=start.isoformat() if start else None, requested_stop_utc=stop.isoformat() if stop else None,
                  time_mode="specified_window" if start else "source_spans",
                  sources=[dict(path=p, sha256=h) for p, h in consumed.items()],
                  scope="Accepted EDA only; native quantities preserved; shared/historical/point/region context cannot be scored as local conditions",
                  populated_by_column={g["column"]: g["populated_rows"] for g in guides})
    record["outputs"] = [dict(path=str(p), sha256=hashlib.sha256(text.encode("utf-8")).hexdigest()) for p, text in files.items()]
    for path, text in files.items():
        engine.atomic_text(path, text)
    engine.atomic_text(paths[3], json.dumps(record, indent=2) + "\n")
    return record


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=HERE / "inputs")
    parser.add_argument("--start", help="Optional UTC start; provide with --stop, or omit both for per-source spans")
    parser.add_argument("--stop", help="Optional exclusive UTC stop; provide with --start")
    parser.add_argument("--limit", type=int, help="Small representative sample before full export")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace generated exports; upstream sources stay protected")
    args = parser.parse_args(argv)
    try:
        result = export(args.output_dir, args.start, args.stop, limit=args.limit, overwrite=args.overwrite)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, f"EDA input export error: {exc}\n")
    print(json.dumps({"rows": result["input_rows"], "populated_by_column": result["populated_by_column"]}, indent=2))


if __name__ == "__main__":
    main()
