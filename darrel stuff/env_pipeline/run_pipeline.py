"""Moon-only CSV environmental screening; no equipment defaults or downloads."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import sys

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE.parent))
from data_maintenance import atomic_text, digest as sha256

DOMAIN_COLUMNS = {
    "radiation": "rad_score",
    "uv": "uv_score",
    "solar_illumination": "solar_illumination_score",
    "terrain": "terrain_score",
    "thermal": "thermal_score",
    "plasma_charging": "plasma_charging_score",
    "dust": "dust_score",
    "seismic": "seismic_score",
    "exosphere": "exosphere_score",
}
IDENTITY = ["id", "candidate_id", "start_utc", "stop_utc"]
RESULT_COLUMNS = IDENTITY + ["policy_id", "policy_mode", "score_scope"] + [
    name for score in DOMAIN_COLUMNS.values() for name in (score, score + "_status")
] + ["habitability_score", "hard_gate_status", "final_rec_score", "rank",
     "evidence_coverage", "reason", "operational_suitability"]
EVIDENCE_COLUMNS = IDENTITY + ["metric", "value", "unit", "quantity", "status", "reason",
                               "scope", "basis", "source", "support_count", "evidence_ref"]
GATE_COLUMNS = ["id", "candidate_id", "rule_id", "metric", "value", "operator", "limit",
                "status", "reason", "authority"]
UTILITY_COLUMNS = ["id", "candidate_id", "domain", "metric", "value", "utility",
                   "metric_weight", "domain_weight", "status", "reason"]


def number(value, label):
    if isinstance(value, bool):
        raise ValueError(f"{label}: Boolean is not a measurement")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: expected a finite number, got {value!r}") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label}: non-finite measurements are invalid; use blank for missing")
    return result


def positive(value, label):
    result = number(value, label)
    if result <= 0:
        raise ValueError(f"{label}: must be positive")
    return result


def utc(value):
    try:
        result = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except ValueError as exc:
        raise ValueError(f"Invalid timestamp: {value!r}") from exc
    if result.tzinfo is None:
        raise ValueError("Timestamps require Z or an explicit UTC offset")
    return result.astimezone(timezone.utc)


def unique_object(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON key: {key}")
        result[key] = value
    return result


def read_json(path):
    result = json.loads(Path(path).read_text(encoding="utf-8-sig"), object_pairs_hook=unique_object)
    if not isinstance(result, dict):
        raise ValueError(f"Expected a JSON object: {path}")
    return result


def validate_policy(policy):
    if policy.get("schema") != 1 or policy.get("body") != "Moon":
        raise ValueError("Expected schema 1, Moon-only policy")
    if not isinstance(policy.get("id"), str) or not policy["id"].strip():
        raise ValueError("Policy needs a nonempty id")
    if policy.get("mode") not in {"unconfigured", "exploratory", "environmental", "synthetic_demo"}:
        raise ValueError("Unknown policy mode")
    for field in ("metrics", "domains", "hard_rules"):
        if not isinstance(policy.get(field), list):
            raise ValueError(f"Policy needs a {field} list")
    for collection in (policy["metrics"], policy["domains"], policy["hard_rules"]):
        if any(not isinstance(item, dict) for item in collection):
            raise ValueError("Policy entries must be objects")
    metrics, columns = {}, set()
    for metric in policy["metrics"]:
        key, column = metric.get("id"), metric.get("column")
        if not isinstance(key, str) or not key.strip() or key in metrics:
            raise ValueError("Unique nonempty metric IDs required")
        if not isinstance(column, str) or not column.strip() or column in columns or column in IDENTITY + ["evidence_ref"]:
            raise ValueError("Unique environmental metric columns required")
        if "earth_visibility" in key.lower() or "earth_visibility" in column.lower():
            raise ValueError("Earth visibility is outside this environmental-only pipeline")
        if metric.get("domain") not in DOMAIN_COLUMNS:
            raise ValueError(f"Unknown environmental domain: {key}")
        if not all(isinstance(metric.get(f), str) and metric[f].strip() for f in ("unit", "quantity", "evidence_family")):
            raise ValueError(f"Metric {key} needs units, quantity and shared-evidence family")
        if metric.get("temporal_support") not in {"static", "window"}:
            raise ValueError(f"Metric {key} needs static/window temporal_support")
        for bound in ("minimum", "maximum"):
            if bound in metric:
                number(metric[bound], f"{key}.{bound}")
        if "minimum" in metric and "maximum" in metric and metric["minimum"] > metric["maximum"]:
            raise ValueError(f"Inverted physical domain: {key}")
        metrics[key] = metric
        columns.add(column)
    domains, used_metrics, used_families = {}, set(), set()
    for domain in policy["domains"]:
        key = domain.get("id")
        if key not in DOMAIN_COLUMNS or key in domains or type(domain.get("scored")) is not bool:
            raise ValueError("Unique known domains with explicit scored Boolean required")
        if not isinstance(domain.get("preferences"), list):
            raise ValueError(f"Domain {key} needs preferences list")
        if domain.get("weight") is not None:
            positive(domain["weight"], f"{key}.weight")
        if not domain["scored"] and domain["preferences"]:
            raise ValueError("Context-only domains cannot contain scored preferences")
        for pref in domain["preferences"]:
            if not isinstance(pref, dict):
                raise ValueError("Preferences must be objects")
            metric_id = pref.get("metric")
            if metric_id not in metrics or metrics[metric_id]["domain"] != key or metric_id in used_metrics:
                raise ValueError("Preferences need unique metrics in their declared domain")
            family = metrics[metric_id]["evidence_family"]
            if family in used_families:
                raise ValueError(f"Repeated scored evidence family: {family}; consolidate shared proxies")
            used_metrics.add(metric_id)
            used_families.add(family)
            if pref.get("direction") not in {"higher", "lower", "target_range"}:
                raise ValueError("Preference direction must be higher/lower/target_range")
            low, high = number(pref.get("lower"), "lower"), number(pref.get("upper"), "upper")
            if low >= high:
                raise ValueError("Preference lower must be below upper")
            if pref["direction"] == "target_range":
                a, b = number(pref.get("preferred_lower"), "preferred_lower"), number(pref.get("preferred_upper"), "preferred_upper")
                if not low < a <= b < high:
                    raise ValueError("Target plateau must be inside utility bounds")
            positive(pref.get("weight"), f"{metric_id}.weight")
            if not pref.get("reason") or not pref.get("source"):
                raise ValueError("Every preference needs a rationale and source")
        domains[key] = domain
    if set(domains) != set(DOMAIN_COLUMNS):
        raise ValueError("Declare all nine domains; mark context-only domains scored=false")
    ids = set()
    for rule in policy["hard_rules"]:
        if not isinstance(rule.get("id"), str) or not rule["id"].strip() or rule["id"] in ids:
            raise ValueError("Unique nonempty hard-rule IDs required")
        ids.add(rule["id"])
        if rule.get("metric") not in metrics or rule.get("operator") not in {"ge", "le"} or not rule.get("reason"):
            raise ValueError("Hard rules need a known metric, ge/le operator and reason")
        if rule.get("limit") is not None:
            number(rule["limit"], "hard limit")
            if not rule.get("source"):
                raise ValueError("A numerical hard limit needs an explicit authority/source")
    # CSV values may be numeric strings; policy arithmetic must use JSON numbers.
    numeric_fields = {"minimum", "maximum", "weight", "lower", "upper", "preferred_lower", "preferred_upper", "limit"}
    entries = policy["metrics"] + policy["domains"] + policy["hard_rules"] + [p for d in domains.values() for p in d["preferences"]]
    for entry in entries:
        for field in numeric_fields & entry.keys():
            value = entry[field]
            if value is not None and (isinstance(value, bool) or not isinstance(value, (int, float))):
                raise ValueError(f"Policy {field} must be a JSON number, not a numeric string")
    if policy["mode"] == "unconfigured" and (
        any(r.get("limit") is not None for r in policy["hard_rules"])
        or any(d.get("weight") is not None or d["preferences"] for d in domains.values())
    ):
        raise ValueError("Select an explicit assessment mode before configuring numerical screening/scoring")
    return metrics, domains


def load_rows(path, metrics):
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        header = reader.fieldnames or []
        if len(set(header)) != len(header):
            raise ValueError("Duplicate CSV column names")
        required = IDENTITY + ["evidence_ref"]
        if not set(required) <= set(header):
            raise ValueError(f"Missing required CSV columns: {sorted(set(required) - set(header))}")
        unexpected = set(header) - set(required) - {m["column"] for m in metrics.values()}
        if unexpected:
            raise ValueError(f"Unknown CSV columns (possible typo/unit mismatch): {sorted(unexpected)}")
        rows, seen = [], set()
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Ragged CSV row near line {reader.line_num}")
            if any(not row[f].strip() for f in IDENTITY):
                raise ValueError("Every row needs nonempty identity and period fields")
            if row["id"] in seen:
                raise ValueError(f"Duplicate assessment ID: {row['id']}")
            seen.add(row["id"])
            if utc(row["stop_utc"]) <= utc(row["start_utc"]):
                raise ValueError(f"Invalid assessment period: {row['id']}")
            rows.append(row)
    if not rows:
        raise ValueError("Input CSV contains no assessment rows")
    return rows


def qualify(row, metric, meta, mode):
    """Metadata is an explicit supplied declaration, not independent qualification."""
    raw = row.get(metric["column"], "").strip()
    item = {**{f: row[f] for f in IDENTITY}, "metric": metric["id"], "value": "",
            "unit": metric["unit"], "quantity": metric["quantity"], "status": "Unknown",
            "reason": "Missing measurement", "evidence_ref": row["evidence_ref"]}
    if not raw:
        return item
    value = number(raw, f"{row['id']}.{metric['column']}")
    if ("minimum" in metric and value < metric["minimum"]) or ("maximum" in metric and value > metric["maximum"]):
        raise ValueError(f"{row['id']}.{metric['column']}: outside declared physical domain")
    item["value"] = value
    if meta is None or meta == {}:
        item["reason"] = "Missing per-metric evidence metadata"
        return item
    if not isinstance(meta, dict):
        raise ValueError("Per-metric metadata must be an object")
    item.update({f: meta.get(f, "") for f in ("scope", "basis", "source", "support_count")})
    if not meta.get("unit") or not meta.get("quantity"):
        item["reason"] = "Missing evidence unit/quantity declaration"
        return item
    if meta.get("unit") != metric["unit"] or meta.get("quantity") != metric["quantity"]:
        raise ValueError(f"{row['id']}.{metric['id']}: metadata unit/quantity mismatch")
    if mode != "synthetic_demo" and meta.get("basis") == "synthetic":
        raise ValueError("Synthetic evidence cannot enter a real-data policy")
    if meta.get("basis") not in ({"synthetic"} if mode == "synthetic_demo" else {"observed", "modeled"}):
        item["reason"] = "Missing/inapplicable observed or modeled evidence basis"
    elif meta.get("body") != "Moon" or meta.get("scope") != "candidate" or meta.get("candidate_id") != row["candidate_id"]:
        item["reason"] = "Evidence is not associated with this Moon candidate; context is not local measurement"
    elif meta.get("quality") != "qualified" or not isinstance(meta.get("source"), str) or not meta["source"].strip():
        item["reason"] = "Missing qualifying quality/source declaration"
    elif number(meta.get("support_count", 0), "support_count") <= 0 or number(meta["support_count"], "support_count") % 1:
        item["reason"] = "No positive integer evidence support"
    elif meta.get("temporal_support") != metric["temporal_support"]:
        item["reason"] = "Static and window-supported quantities cannot be substituted"
    elif metric["temporal_support"] == "window" and (not meta.get("start_utc") or not meta.get("stop_utc")):
        item["reason"] = "Missing evidence period declaration"
    elif metric["temporal_support"] == "window" and (
        utc(meta.get("start_utc")) != utc(row["start_utc"]) or utc(meta.get("stop_utc")) != utc(row["stop_utc"])
    ):
        item["reason"] = "Evidence summary does not match the requested period"
    else:
        item.update(status="Supported", reason="Supplied candidate evidence passed schema/applicability checks; not independently certified")
    return item


def utility(value, preference):
    lower, upper = preference["lower"], preference["upper"]
    if preference["direction"] == "target_range":
        a, b = preference["preferred_lower"], preference["preferred_upper"]
        value = (value - lower) / (a - lower) if value < a else (upper - value) / (upper - b) if value > b else 1.0
    else:
        value = (value - lower) / (upper - lower)
        if preference["direction"] == "lower":
            value = 1 - value
    return max(0.0, min(1.0, value))


def assess(rows, policy, metadata):
    metrics, domains = validate_policy(policy)
    results, gates, utilities, evidence = [], [], [], []
    required = {r["metric"] for r in policy["hard_rules"]} | {
        p["metric"] for d in domains.values() if d["scored"] for p in d["preferences"]}
    scope = ";".join(k for k, d in domains.items() if d["scored"])
    for row in rows:
        supplied = metadata.get(row["id"], {})
        if not isinstance(supplied, dict):
            raise ValueError("Assessment metadata must map metric IDs to objects")
        if set(supplied) - set(metrics):
            raise ValueError(f"Unknown evidence metric IDs for {row['id']}")
        observed = {key: qualify(row, metric, supplied.get(key), policy["mode"]) for key, metric in metrics.items()}
        evidence.extend(observed.values())
        reasons, states = [], []
        for rule in policy["hard_rules"]:
            item = observed[rule["metric"]]
            status, reason = "Unknown", "Applicable numerical screening limit/authority not configured"
            if rule.get("limit") is not None:
                if item["status"] != "Supported":
                    reason = item["reason"]
                else:
                    passed = item["value"] >= rule["limit"] if rule["operator"] == "ge" else item["value"] <= rule["limit"]
                    status, reason = ("Passed" if passed else "Failed"), rule["reason"]
            states.append(status)
            if status != "Passed":
                reasons.append(f"{rule['id']}: {status}: {reason}")
            gates.append({"id": row["id"], "candidate_id": row["candidate_id"], "rule_id": rule["id"],
                          "metric": rule["metric"], "value": item["value"], "operator": rule["operator"],
                          "limit": rule.get("limit"), "status": status, "reason": reason, "authority": rule.get("source")})
        hard = "Failed" if "Failed" in states else "Unknown" if not states or "Unknown" in states else "Passed"
        if not states:
            reasons.append("Mandatory screening rules unconfigured; an empty gate cannot pass")
        result = {**{f: row[f] for f in IDENTITY}, "policy_id": policy["id"], "policy_mode": policy["mode"],
                  "score_scope": scope, "hard_gate_status": hard, "habitability_score": "", "final_rec_score": "",
                  "rank": "", "operational_suitability": "Not assessed",
                  "evidence_coverage": f"{sum(observed[m]['status'] == 'Supported' for m in required)}/{len(required)}"}
        weighted, weights, complete = [], [], True
        for key, column in DOMAIN_COLUMNS.items():
            domain = domains[key]
            value, status = "", "Context_only"
            if domain["scored"]:
                status = "Unknown"
                parts, metric_weights = [], []
                for pref in domain["preferences"]:
                    item = observed[pref["metric"]]
                    score = utility(item["value"], pref) if item["status"] == "Supported" else ""
                    utilities.append({"id": row["id"], "candidate_id": row["candidate_id"], "domain": key,
                                      "metric": pref["metric"], "value": item["value"], "utility": score,
                                      "metric_weight": pref["weight"], "domain_weight": domain.get("weight"),
                                      "status": item["status"], "reason": item["reason"]})
                    if score != "":
                        parts.append(score * pref["weight"])
                        metric_weights.append(pref["weight"])
                if domain.get("weight") is not None and metric_weights and len(parts) == len(domain["preferences"]):
                    value, status = 100 * sum(parts) / sum(metric_weights), "Scored"
                    weighted.append(value * domain["weight"])
                    weights.append(domain["weight"])
                else:
                    complete = False
                    reasons.append(f"{key}: missing selected evidence, preference definition or domain weight")
            result[column], result[column + "_status"] = value, status
        if hard == "Passed" and complete and weights:
            result["habitability_score"] = result["final_rec_score"] = sum(weighted) / sum(weights)
        elif not weights and complete:
            reasons.append("No scored domains configured")
        result["reason"] = "; ".join(reasons) or "Passed declared screening with complete preferences; not operational approval"
        results.append(result)
    # Compare identical UTC periods only; stable IDs break ties, never input order.
    periods = {(utc(r["start_utc"]), utc(r["stop_utc"])) for r in results}
    for start, stop in periods:
        eligible = [r for r in results if r["final_rec_score"] != "" and utc(r["start_utc"]) == start and utc(r["stop_utc"]) == stop]
        for rank, row in enumerate(sorted(eligible, key=lambda r: (-r["final_rec_score"], r["id"])), 1):
            row["rank"] = rank
    return results, gates, utilities, evidence


def csv_text(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=columns, extrasaction="raise", lineterminator="\n")
    writer.writeheader()
    writer.writerows(rows)
    return stream.getvalue()


def run(input_path, output_path, policy_path, *, overwrite=False):
    input_path, output_path, policy_path = (Path(p).resolve() for p in (input_path, output_path, policy_path))
    if output_path.suffix.lower() != ".csv":
        raise ValueError("--output must name a CSV file")
    tracked = {input_path: sha256(input_path), policy_path: sha256(policy_path), Path(__file__).resolve(): sha256(__file__)}
    helper_path = HERE.parent / "data_maintenance.py"
    tracked[helper_path] = sha256(helper_path)
    policy = read_json(policy_path)
    metrics, _ = validate_policy(policy)
    rows = load_rows(input_path, metrics)
    documents, metadata = {}, {}
    for row in rows:
        ref = row["evidence_ref"].strip()
        if not ref:
            metadata[row["id"]] = {}
            continue
        path = (input_path.parent / ref).resolve()
        if path not in documents:
            tracked[path] = sha256(path)
            document = read_json(path)
            if document.get("schema") != 1 or not isinstance(document.get("rows"), dict):
                raise ValueError("Evidence JSON needs schema 1 and a rows mapping")
            documents[path] = document
        metadata[row["id"]] = documents[path]["rows"].get(row["id"], {})
    results, gates, utilities, evidence = assess(rows, policy, metadata)
    files = {
        output_path: csv_text(results, RESULT_COLUMNS),
        output_path.with_name(output_path.stem + "_hard_gates.csv"): csv_text(gates, GATE_COLUMNS),
        output_path.with_name(output_path.stem + "_domain_preferences.csv"): csv_text(utilities, UTILITY_COLUMNS),
        output_path.with_name(output_path.stem + "_environmental_evidence.csv"): csv_text(evidence, EVIDENCE_COLUMNS),
    }
    provenance_path = output_path.with_name(output_path.stem + "_provenance.json")
    destinations = {*files, provenance_path}
    if destinations & set(tracked):
        raise ValueError("Output paths must not overwrite any input, policy, evidence or source file")
    for path in destinations:
        if path.exists() and not overwrite:
            raise FileExistsError(f"Output already exists; choose another path or explicitly use --overwrite: {path}")
    for path, digest in tracked.items():
        if sha256(path) != digest:
            raise ValueError(f"Input changed during assessment: {path}")
    provenance = {
        "schema": 1, "body": "Moon", "policy_id": policy["id"], "mode": policy["mode"],
        "created_utc": datetime.now(timezone.utc).isoformat(), "input_rows": len(rows),
        "ranked_rows": sum(r["rank"] != "" for r in results),
        "hard_status_counts": {s: sum(r["hard_gate_status"] == s for r in results) for s in ("Passed", "Failed", "Unknown")},
        "inputs": [{"path": str(p), "sha256": digest} for p, digest in tracked.items()],
        "outputs": [{"path": str(p), "sha256": hashlib.sha256(content.encode("utf-8")).hexdigest()} for p, content in files.items()],
        "policy": policy, "rank_grouping": "policy plus identical UTC start/stop; score desc, assessment ID asc",
        "qualification": "Supplied metadata checked, not independently validated science or operational certification",
        "habitability_meaning": "Environmental preference only; final_rec_score is its gate-qualified ranking copy",
    }
    for path, content in files.items():
        atomic_text(path, content)
    atomic_text(provenance_path, json.dumps(provenance, indent=2, allow_nan=False) + "\n")
    return provenance


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path, required=True, help="CSV: one row per candidate/time window")
    parser.add_argument("--output", type=Path, required=True, help="Results CSV; audit files written alongside")
    parser.add_argument("--policy", type=Path, default=HERE / "environmental_policy.json")
    parser.add_argument("--overwrite", action="store_true", help="Explicitly replace outputs, never inputs")
    args = parser.parse_args(argv)
    try:
        record = run(args.input, args.output, args.policy, overwrite=args.overwrite)
    except (ValueError, OSError, csv.Error) as exc:
        parser.exit(2, f"Environmental pipeline error: {exc}\n")
    print(json.dumps({"rows": record["input_rows"], "ranked": record["ranked_rows"],
                      "hard_gates": record["hard_status_counts"], "policy_mode": record["mode"],
                      "output": str(args.output.resolve())}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
