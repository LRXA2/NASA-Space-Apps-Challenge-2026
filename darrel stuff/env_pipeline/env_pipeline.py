"""Standalone Moon environmental CSV scorer. Runtime inputs: CSV and YAML only."""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
import os
from pathlib import Path
import tempfile

try:
    import yaml
except ImportError as exc:
    raise SystemExit("Missing dependency. Install with: python -m pip install PyYAML==6.0.3") from exc

SCORES = {
    "radiation": "rad_score", "thermal": "thermal_score",
    "solar_illumination": "solar_illumination_score", "dust": "dust_score",
    "plasma_charging": "plasma_charging_score", "uv": "uv_score",
    "seismic": "seismic_score", "exosphere": "exosphere_score",
}
# Keep internal assessment keys compatible; export human-readable CSV headings.
OUTPUT_COLUMN_NAMES = {
    "rad_score": "radiation_score",
    "rad_score_status": "radiation_score_status",
    "final_rec_score": "final_recommendation_score",
    "config_sha256": "configuration_file_hash",
}


def finite(value, label, *, config=False):
    if isinstance(value, bool) or config and not isinstance(value, (int, float)):
        raise ValueError(f"{label}: expected a number, not a Boolean or quoted config value")
    try:
        result = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{label}: expected a finite number") from exc
    if not math.isfinite(result):
        raise ValueError(f"{label}: NaN/infinity is invalid; leave missing CSV values blank")
    return result


def positive(value, label):
    result = finite(value, label, config=True)
    if result <= 0:
        raise ValueError(f"{label}: multiplier must be positive")
    return result


def keys(mapping, allowed, label):
    if not isinstance(mapping, dict) or any(not isinstance(k, str) for k in mapping):
        raise ValueError(f"{label}: expected a mapping with string keys")
    extra = set(mapping) - set(allowed)
    if extra:
        raise ValueError(f"{label}: unknown settings {sorted(extra)}")


def reject_duplicate_yaml(node, seen=None):
    """Safe loading alone does not reject accidental duplicate threshold keys."""
    seen = set() if seen is None else seen
    if node is None or id(node) in seen:
        return
    seen.add(id(node))
    if isinstance(node, yaml.MappingNode):
        names = set()
        for key, value in node.value:
            if not isinstance(key, yaml.ScalarNode) or key.value == "<<" or key.value in names:
                raise ValueError("YAML needs unique scalar keys; merge overrides are not supported")
            names.add(key.value)
            reject_duplicate_yaml(value, seen)
    elif isinstance(node, yaml.SequenceNode):
        for value in node.value:
            reject_duplicate_yaml(value, seen)


def load_config(path):
    content = Path(path).read_bytes()
    text = content.decode("utf-8-sig")
    reject_duplicate_yaml(yaml.compose(text, Loader=yaml.SafeLoader))
    config = yaml.safe_load(text)
    validate_config(config)
    return config, hashlib.sha256(content).hexdigest()


def gate_operator(gate):
    operator = gate.get("operator")
    aliases = {"ge": "above_threshold", "le": "below_threshold"}
    if not isinstance(operator, str):
        raise ValueError("Hard operator must be above_threshold/below_threshold/between")
    operator = aliases.get(operator, operator)
    if operator not in {"above_threshold", "below_threshold", "between"}:
        raise ValueError("Hard operator must be above_threshold/below_threshold/between")
    return operator


def validate_config(config):
    keys(config, {"schema", "body", "name", "metadata_columns", "domains"}, "config")
    if type(config.get("schema")) is not int or config["schema"] != 1 or config.get("body") != "Moon":
        raise ValueError("Expected schema: 1 and body: Moon")
    if not isinstance(config.get("name"), str) or not config["name"].strip():
        raise ValueError("Config needs a nonempty name")
    metadata = config.get("metadata_columns", [])
    if not isinstance(metadata, list) or any(not isinstance(x, str) or not x for x in metadata) or len(metadata) != len(set(metadata)):
        raise ValueError("metadata_columns must be a unique list of column names")
    domains = config.get("domains")
    if not isinstance(domains, dict) or set(domains) != set(SCORES):
        raise ValueError("Declare exactly the eight environmental domains; terrain is not supported")
    columns, scored_families = set(), set()
    for name, domain in domains.items():
        keys(domain, {"priority", "include_in_score", "multiplier", "metrics"}, name)
        if type(domain.get("include_in_score")) is not bool:
            raise ValueError(f"{name}: include_in_score must be true or false")
        if domain.get("multiplier") is not None:
            positive(domain["multiplier"], f"{name}.multiplier")
        if not isinstance(domain.get("metrics"), list):
            raise ValueError(f"{name}: metrics must be a list")
        for metric in domain["metrics"]:
            keys(metric, {"column", "unit", "role", "evidence_family", "multiplier", "preference", "hard_gate",
                          "minimum", "maximum", "requires_time_window", "meaning"}, f"{name}.metric")
            column = metric.get("column")
            if not isinstance(column, str) or not column or column in columns or column in set(metadata) | {"id", "candidate_id", "start_utc", "stop_utc"}:
                raise ValueError("Metric columns must be unique and separate from ID/time/metadata columns")
            columns.add(column)
            if "earth_visibility" in column.lower():
                raise ValueError("Earth visibility is not an environmental scoring metric")
            if not isinstance(metric.get("unit"), str) or not metric["unit"].strip():
                raise ValueError(f"{column}: an explicit unit is required")
            if metric.get("role") not in {"score", "context"}:
                raise ValueError(f"{column}: role must be score or context")
            if type(metric.get("requires_time_window", False)) is not bool:
                raise ValueError(f"{column}: requires_time_window must be Boolean")
            for bound in ("minimum", "maximum"):
                if metric.get(bound) is not None:
                    finite(metric[bound], f"{column}.{bound}", config=True)
            if metric.get("minimum") is not None and metric.get("maximum") is not None and metric["minimum"] > metric["maximum"]:
                raise ValueError(f"{column}: inverted physical input bounds")
            if metric.get("role") == "context" and (metric.get("preference") is not None or metric.get("hard_gate") is not None):
                raise ValueError(f"{column}: context cannot be scored or determine a local hard gate")
            if metric.get("multiplier") is not None:
                positive(metric["multiplier"], f"{column}.multiplier")
            preference = metric.get("preference")
            if preference is not None:
                keys(preference, {"direction", "lower", "upper", "preferred_lower", "preferred_upper"}, f"{column}.preference")
                if preference.get("direction") not in {"higher", "lower", "target_range"}:
                    raise ValueError(f"{column}: preference needs higher/lower/target_range direction")
                for key in ("lower", "upper", "preferred_lower", "preferred_upper"):
                    if preference.get(key) is not None:
                        finite(preference[key], f"{column}.{key}", config=True)
                low, high = preference.get("lower"), preference.get("upper")
                if low is not None and high is not None:
                    if low >= high:
                        raise ValueError(f"{column}: preference lower must be below upper")
                    if preference["direction"] == "target_range" and preference.get("preferred_lower") is not None and preference.get("preferred_upper") is not None:
                        if not low < preference["preferred_lower"] <= preference["preferred_upper"] < high:
                            raise ValueError(f"{column}: preferred plateau must lie inside outer bounds")
                if domain["include_in_score"]:
                    family = metric.get("evidence_family")
                    if not isinstance(family, str) or not family or family in scored_families:
                        raise ValueError("Scored metrics need distinct evidence_family values; shared proxies cannot be counted twice")
                    scored_families.add(family)
            gate = metric.get("hard_gate")
            if gate is not None:
                keys(gate, {"operator", "threshold", "lower", "upper", "rationale"}, f"{column}.hard_gate")
                operator = gate_operator(gate)
                for key in ("threshold", "lower", "upper"):
                    if gate.get(key) is not None:
                        finite(gate[key], f"{column}.hard_gate.{key}", config=True)
                if operator == "between" and gate.get("lower") is not None and gate.get("upper") is not None and gate["lower"] > gate["upper"]:
                    raise ValueError(f"{column}: inverted hard-gate range")


def time_window(start="", stop=""):
    start, stop = start or "", stop or ""
    if bool(start.strip()) != bool(stop.strip()):
        raise ValueError("Provide both start_utc and stop_utc, or omit both")
    if not start.strip():
        return "", ""
    try:
        values = [datetime.fromisoformat(v.replace("Z", "+00:00")) for v in (start, stop)]
    except ValueError as exc:
        raise ValueError("Invalid UTC timestamps") from exc
    if any(v.tzinfo is None for v in values) or values[1] <= values[0]:
        raise ValueError("Dates must be timezone-aware, with stop after start")
    return tuple(v.astimezone(timezone.utc).isoformat() for v in values)


def read_csv(path, config):
    metrics = {m["column"]: m for d in config["domains"].values() for m in d["metrics"]}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        headers = reader.fieldnames or []
        allowed = set(metrics) | set(config.get("metadata_columns", [])) | {"id", "candidate_id", "start_utc", "stop_utc"}
        if "id" not in headers or len(headers) != len(set(headers)):
            raise ValueError("CSV needs an id column and unique headers")
        if set(headers) - allowed:
            raise ValueError(f"Unregistered CSV columns: {sorted(set(headers) - allowed)}")
        rows, ids = [], set()
        for row in reader:
            if None in row or any(v is None for v in row.values()):
                raise ValueError(f"Ragged CSV row near line {reader.line_num}")
            if not row["id"].strip() or row["id"] in ids:
                raise ValueError("Assessment IDs must be nonempty and unique")
            ids.add(row["id"])
            time_window(row.get("start_utc", ""), row.get("stop_utc", ""))
            for column, metric in metrics.items():
                raw = row.get(column, "").strip()
                if raw:
                    value = finite(raw, f"{row['id']}.{column}")
                    if metric.get("minimum") is not None and value < metric["minimum"] or metric.get("maximum") is not None and value > metric["maximum"]:
                        raise ValueError(f"{row['id']}.{column}: outside configured physical input bounds")
            rows.append(row)
    if not rows:
        raise ValueError("CSV contains no assessment rows")
    return rows


def utility(value, preference):
    if preference is None or preference.get("lower") is None or preference.get("upper") is None:
        return None
    low, high = preference["lower"], preference["upper"]
    if preference["direction"] == "target_range":
        a, b = preference.get("preferred_lower"), preference.get("preferred_upper")
        if a is None or b is None:
            return None
        result = (value - low) / (a - low) if value < a else (high - value) / (high - b) if value > b else 1.0
    else:
        result = (value - low) / (high - low)
        if preference["direction"] == "lower":
            result = 1 - result
    return max(0.0, min(1.0, result))


def hard_check(value, gate):
    operator = gate_operator(gate)
    if value is None:
        return "Unknown", "Missing required measurement or time window"
    if operator == "between":
        low, high = gate.get("lower"), gate.get("upper")
        if low is None or high is None:
            return "Unknown", "Hard bounds not configured"
        passed = low <= value <= high
    else:
        limit = gate.get("threshold")
        if limit is None:
            return "Unknown", "Hard threshold not configured"
        passed = value >= limit if operator == "above_threshold" else value <= limit
    return ("Passed" if passed else "Failed"), gate.get("rationale", "Configured environmental screening comparison")


def assess(rows, config, config_hash):
    validate_config(config)
    results = []
    for row in rows:
        start, stop = time_window(row.get("start_utc", ""), row.get("stop_utc", ""))
        result = {"id": row["id"], "candidate_id": row.get("candidate_id", ""),
                  "start_utc": row.get("start_utc", ""), "stop_utc": row.get("stop_utc", ""),
                  "time_mode": "specified_window" if start else "unspecified",
                  "comparison_start_utc": start, "comparison_stop_utc": stop,
                  "config_name": config["name"], "config_sha256": config_hash,
                  "habitability_score": "", "final_rec_score": "", "rank": "", "operational_suitability": "Not assessed"}
        gates, details, issues, weighted, weights = [], [], [], [], []
        complete = True
        used = supported = 0
        for name, score_column in SCORES.items():
            domain = config["domains"][name]
            parts, metric_weights = [], []
            selected = [m for m in domain["metrics"] if m["role"] == "score"]
            domain_complete = bool(selected)
            for metric in domain["metrics"]:
                column = metric["column"]
                raw = row.get(column, "").strip()
                value = finite(raw, column) if raw else None
                missing_time = metric.get("requires_time_window", False) and not start
                usable = None if missing_time else value
                item = {"domain": name, "column": column, "unit": metric["unit"], "value": value, "role": metric["role"]}
                if metric.get("hard_gate") is not None:
                    state, reason = hard_check(usable, metric["hard_gate"])
                    gates.append({**item, "condition": metric["hard_gate"], "status": state, "reason": reason})
                if metric["role"] == "score":
                    score = utility(usable, metric.get("preference")) if usable is not None else None
                    item.update(utility=score, multiplier=metric.get("multiplier"))
                    if domain["include_in_score"]:
                        used += 1
                        supported += usable is not None
                    if score is None or metric.get("multiplier") is None:
                        domain_complete = False
                        item["reason"] = "Missing measurement/time, preference bounds or metric multiplier"
                    else:
                        parts.append(score * metric["multiplier"])
                        metric_weights.append(metric["multiplier"])
                details.append(item)
            if domain_complete:
                result[score_column] = 100 * sum(parts) / sum(metric_weights)
                result[score_column + "_status"] = "Scored"
            else:
                result[score_column] = ""
                result[score_column + "_status"] = "Context_only" if not selected else "Unknown"
            if domain["include_in_score"]:
                if not domain_complete or domain.get("multiplier") is None:
                    complete = False
                    issues.append(f"{name}: selected domain needs complete preferences and a domain multiplier")
                else:
                    weighted.append(result[score_column] * domain["multiplier"])
                    weights.append(domain["multiplier"])
        states = [g["status"] for g in gates]
        hard = "Failed" if "Failed" in states else "Unknown" if not states or "Unknown" in states else "Passed"
        if not states:
            issues.append("No mandatory hard gates configured; empty gate cannot establish eligibility")
        for gate in gates:
            if gate["status"] != "Passed":
                issues.append(f"{gate['column']}: {gate['status']}: {gate['reason']}")
        if hard == "Passed" and complete and weights:
            result["habitability_score"] = result["final_rec_score"] = sum(weighted) / sum(weights)
        if not weights and complete:
            issues.append("No domains selected for aggregate scoring")
        result.update(hard_gate_status=hard, evidence_coverage=f"{supported}/{used}",
                      score_scope=";".join(n for n in SCORES if config["domains"][n]["include_in_score"]),
                      reason="; ".join(issues) or "Passed configured screens with complete preferences; not operational approval",
                      hard_gate_details=json.dumps(gates, separators=(",", ":"), allow_nan=False),
                      score_details=json.dumps(details, separators=(",", ":"), allow_nan=False))
        results.append(result)
    group = lambda r: (r["time_mode"], r["comparison_start_utc"], r["comparison_stop_utc"])
    for period in {group(r) for r in results}:
        candidates = [r for r in results if group(r) == period and r["final_rec_score"] != ""]
        for rank, item in enumerate(sorted(candidates, key=lambda r: (-r["final_rec_score"], r["id"])), 1):
            item["rank"] = rank
    return results


def run(input_path, output_path, config_path, *, overwrite=False):
    input_path, output_path, config_path = (Path(p).resolve() for p in (input_path, output_path, config_path))
    if output_path in {input_path, config_path, Path(__file__).resolve()}:
        raise ValueError("Output cannot overwrite the input, configuration or script")
    if output_path.suffix.lower() != ".csv":
        raise ValueError("Output must be a .csv file")
    if output_path.exists() and not overwrite:
        raise FileExistsError("Output exists; choose another path or explicitly use --overwrite")
    config, digest = load_config(config_path)
    results = assess(read_csv(input_path, config), config, digest)
    columns = ["id", "candidate_id", "start_utc", "stop_utc", "time_mode", "comparison_start_utc", "comparison_stop_utc"]
    columns += [field for name in SCORES.values() for field in (name, name + "_status")]
    columns += ["habitability_score", "hard_gate_status", "final_rec_score", "rank", "score_scope", "evidence_coverage",
                "reason", "operational_suitability", "config_name", "config_sha256", "hard_gate_details", "score_details"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=[OUTPUT_COLUMN_NAMES.get(c, c) for c in columns], lineterminator="\n")
    writer.writeheader()
    writer.writerows({OUTPUT_COLUMN_NAMES.get(key, key): value for key, value in row.items()} for row in results)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=output_path.name + ".", suffix=".tmp", dir=output_path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(stream.getvalue())
        Path(temporary).replace(output_path)
    finally:
        Path(temporary).unlink(missing_ok=True)
    return results


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yml"))
    parser.add_argument("--overwrite", action="store_true")
    args = parser.parse_args(argv)
    try:
        rows = run(args.input, args.output, args.config, overwrite=args.overwrite)
    except (ValueError, OSError, csv.Error, yaml.YAMLError) as exc:
        parser.exit(2, f"Environmental pipeline error: {exc}\n")
    print(json.dumps({"rows": len(rows), "ranked": sum(r["rank"] != "" for r in rows),
                      "hard_statuses": {s: sum(r["hard_gate_status"] == s for r in rows) for s in ("Passed", "Failed", "Unknown")},
                      "output": str(args.output.resolve())}, indent=2))


if __name__ == "__main__":
    main()
