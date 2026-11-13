"""Standalone Moon Operations/Survival environmental comparison scorer.
One CSV and one YAML; comparison scores are not qualified mission survival.
Schema 1 remains supported for archived single-score configurations.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
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
    "communications_geometry": "communications_geometry_score",
    "soil": "soil_score",
}
# Keep internal assessment keys compatible; export human-readable CSV headings.
OUTPUT_COLUMN_NAMES = {
    "rad_score": "radiation_score",
    "rad_score_status": "radiation_score_status",
    "final_rec_score": "final_recommendation_score",
    "config_sha256": "configuration_file_hash",
    "fail_reason": "Fail Reason",
}
ASSESSMENTS = ("operations", "survival")


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
    if isinstance(config, dict) and config.get("schema") == 2:
        validate_dual_config(config)
        return
    keys(config, {"schema", "body", "name", "pipeline_mode", "metadata_columns", "comparison_group_columns", "domains"}, "config")
    if config.get("pipeline_mode", "strict") not in ("strict", "available_data"):
        raise ValueError("pipeline_mode must be strict or available_data")
    if type(config.get("schema")) is not int or config["schema"] != 1 or config.get("body") != "Moon":
        raise ValueError("Expected schema: 1 and body: Moon")
    if not isinstance(config.get("name"), str) or not config["name"].strip():
        raise ValueError("Config needs a nonempty name")
    metadata = config.get("metadata_columns", [])
    if not isinstance(metadata, list) or any(not isinstance(x, str) or not x for x in metadata) or len(metadata) != len(set(metadata)):
        raise ValueError("metadata_columns must be a unique list of column names")
    computed = {"pipeline_mode", "time_mode", "comparison_start_utc", "comparison_stop_utc", "comparison_preference_score",
                "final_habitability_score", "hard_gate_status", "final_rec_score", "rank", "score_scope", "evidence_coverage",
                "reason", "fail_reason", "operational_suitability", "config_name", "config_sha256", "hard_gate_details", "score_details", "domain_score_details"}
    computed |= set(SCORES.values()) | {c + "_status" for c in SCORES.values()} | set(OUTPUT_COLUMN_NAMES.values())
    if set(metadata) & computed:
        raise ValueError("metadata_columns cannot shadow computed output columns")
    domains = config.get("domains")
    required = set(SCORES) - {"communications_geometry", "soil"}
    if not isinstance(domains, dict) or not required <= set(domains) <= set(SCORES):
        raise ValueError("Declare the eight environmental domains plus optional communications_geometry and soil; terrain is not supported")
    groups = config.get("comparison_group_columns", [])
    if not isinstance(groups, list) or any(not isinstance(c, str) or c not in metadata for c in groups) or len(groups) != len(set(groups)):
        raise ValueError("comparison_group_columns must be unique registered metadata columns")
    columns, scored_families = set(), set()
    for name, domain in domains.items():
        keys(domain, {"priority", "enabled", "hard_gates_enabled", "include_in_score", "multiplier", "metrics"}, name)
        if type(domain.get("enabled", True)) is not bool:
            raise ValueError(f"{name}: enabled must be true or false")
        if type(domain.get("hard_gates_enabled", True)) is not bool:
            raise ValueError(f"{name}: hard_gates_enabled must be true or false")
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
            if not isinstance(metric.get("unit"), str) or not metric["unit"].strip():
                raise ValueError(f"{column}: an explicit unit is required")
            if metric.get("role") not in {"score", "context", "gate"}:
                raise ValueError(f"{column}: role must be score, context or gate")
            if metric["role"] == "gate" and (metric.get("preference") is not None or metric.get("hard_gate") is None):
                raise ValueError(f"{column}: gate-only metrics need a hard_gate and cannot have a preference")
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
                keys(preference, {"direction", "lower", "upper", "preferred_lower", "preferred_upper", "curve"}, f"{column}.preference")
                validate_curve(preference.get("curve"))
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
                if domain.get("enabled", True) and domain["include_in_score"]:
                    family = metric.get("evidence_family")
                    if not isinstance(family, str) or not family or family in scored_families:
                        raise ValueError("Scored metrics need distinct evidence_family values; shared proxies cannot be counted twice")
                    scored_families.add(family)
            gate = metric.get("hard_gate")
            if gate is not None:
                keys(gate, {"operator", "threshold", "lower", "upper", "rationale", "cap_to_window_duration"}, f"{column}.hard_gate")
                operator = gate_operator(gate)
                if type(gate.get("cap_to_window_duration", False)) is not bool:
                    raise ValueError(f"{column}: cap_to_window_duration must be Boolean")
                if gate.get("cap_to_window_duration", False) and (operator != "above_threshold" or metric["unit"] != "h" or not metric.get("requires_time_window", False)):
                    raise ValueError(f"{column}: window-capped gates require an hourly duration, above_threshold and requires_time_window")
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
    active_columns = {m["column"] for d in config["domains"].values() if d.get("enabled", True)
                      for m in d["metrics"] if m["role"] != "gate" or d.get("hard_gates_enabled", True)}
    if config.get("schema") == 2:
        effective = [assessment_config(config, a) for a in ASSESSMENTS]
        active_columns = {m["column"] for rules in effective for d in rules["domains"].values()
                          if d.get("enabled", True) for m in d["metrics"]
                          if m["role"] != "gate" or d.get("hard_gates_enabled", True)}
        allocated = set().union(*(config["assessments"][a]["weights"] for a in ASSESSMENTS))
        # Unallocated measurements remain context. Explicitly disabled allocated
        # domains stay disabled, but an assessment-specific re-enable is validated.
        active_columns |= {m["column"] for name, d in config["domains"].items()
                           if name not in allocated and d.get("enabled", True) for m in d["metrics"]}
    with Path(path).open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if "ID" in (reader.fieldnames or []) and "id" not in reader.fieldnames:
            reader.fieldnames = ["id" if name == "ID" else name for name in reader.fieldnames]
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
                if column not in active_columns:
                    continue
                raw = row.get(column, "").strip()
                if raw:
                    value = finite(raw, f"{row['id']}.{column}")
                    if metric.get("minimum") is not None and value < metric["minimum"] or metric.get("maximum") is not None and value > metric["maximum"]:
                        raise ValueError(f"{row['id']}.{column}: outside configured physical input bounds")
            rows.append(row)
    if not rows:
        raise ValueError("CSV contains no assessment rows")
    return rows


def normalized_utility(value, preference):
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


def validate_curve(curve):
    if curve is None:
        return
    keys(curve, {"type", "strength", "exponent", "steepness", "midpoint"}, "preference.curve")
    kind = curve.get("type")
    required = {"linear": set(), "logarithmic": {"strength"}, "power": {"exponent"}, "logistic": {"steepness", "midpoint"}}
    if not isinstance(kind, str) or kind not in required:
        raise ValueError("Curve type must be linear/logarithmic/power/logistic")
    if set(curve) != required[kind] | {"type"}:
        raise ValueError(f"{kind} curve requires exactly these parameters: {sorted(required[kind])}")
    for key in required[kind]:
        if key == "midpoint":
            midpoint = finite(curve[key], "curve.midpoint", config=True)
            if not 0 < midpoint < 1:
                raise ValueError("Logistic midpoint must lie strictly between 0 and 1")
        else:
            positive(curve[key], f"curve.{key}")
    if kind == "logistic":
        shape_utility(.5, curve)  # Reject numerically degenerate settings before reading input.


def shape_utility(value, curve):
    """Shape normalized preference, never raw measurements or mandatory limits."""
    if curve is None or curve["type"] == "linear":
        return value
    kind = curve["type"]
    if kind == "logarithmic":
        result = math.log1p(curve["strength"] * value) / math.log1p(curve["strength"])
    elif kind == "power":
        result = value ** curve["exponent"]
    else:
        def sigmoid(x):
            if x >= 0:
                return 1 / (1 + math.exp(-x))
            exponential = math.exp(x)
            return exponential / (1 + exponential)
        k, midpoint = curve["steepness"], curve["midpoint"]
        low, high = sigmoid(-k * midpoint), sigmoid(k * (1 - midpoint))
        if high - low <= 1e-12:
            raise ValueError("Logistic curve is numerically degenerate; choose a larger steepness")
        result = (sigmoid(k * (value - midpoint)) - low) / (high - low)
    return max(0.0, min(1.0, result))


def utility(value, preference):
    normalized = normalized_utility(value, preference)
    return None if normalized is None else shape_utility(normalized, preference.get("curve"))


def gate_margin(value, gate):
    """Signed screening-boundary distance in the metric's own units, not hardware reserve."""
    if value is None:
        return None
    operator = gate_operator(gate)
    if operator == "between":
        low, high = gate.get("lower"), gate.get("upper")
        return None if low is None or high is None else min(value - low, high - value)
    threshold = gate.get("threshold")
    if threshold is None:
        return None
    return value - threshold if operator == "above_threshold" else threshold - value


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


def gate_failure_reason(gate):
    """Explain an evaluated blocking check using its actual value and YAML limit."""
    label = f"{gate['domain']}: {gate['column']}"
    if gate["status"] == "Unknown":
        return f"{label}: {gate['reason']}"
    condition = gate["condition"]
    operator = gate_operator(condition)
    if operator == "between":
        required = f"between {condition['lower']} and {condition['upper']}"
    else:
        symbol = ">=" if operator == "above_threshold" else "<="
        required = f"{symbol} {condition['threshold']}"
    return f"{label} = {gate['value']} {gate['unit']}; required {required} {gate['unit']}"


def _assess_single(rows, config, config_hash):
    validate_config(config)
    available_data = config.get("pipeline_mode", "strict") == "available_data"
    results = []
    for row in rows:
        start, stop = time_window(row.get("start_utc", ""), row.get("stop_utc", ""))
        result = {"id": row["id"], "candidate_id": row.get("candidate_id", ""),
                  "start_utc": row.get("start_utc", ""), "stop_utc": row.get("stop_utc", ""),
                  "time_mode": "specified_window" if start else "unspecified",
                  "comparison_start_utc": start, "comparison_stop_utc": stop,
                  "config_name": config["name"], "config_sha256": config_hash,
                  "pipeline_mode": config.get("pipeline_mode", "strict"),
                  "final_habitability_score": "", "final_rec_score": "", "rank": "", "operational_suitability": "Not assessed"}
        result.update({c: row.get(c, "") for c in config.get("metadata_columns", [])
                       if c not in result})
        result["comparison_preference_score"] = ""
        gates, details, domain_details, issues, weighted, weights = [], [], [], [], [], []
        complete = True
        used = supported = 0
        for name, score_column in SCORES.items():
            if name not in config["domains"]:  # Backward-compatible eight-domain YAML.
                result[score_column] = ""
                result[score_column + "_status"] = "Context_only"
                continue
            domain = config["domains"][name]
            if not domain.get("enabled", True):
                result[score_column] = ""
                result[score_column + "_status"] = "Disabled"
                domain_details.append({"domain": name, "priority_label": domain.get("priority"),
                                       "included_in_final_score": False, "enabled": False,
                                       "domain_multiplier": domain.get("multiplier"), "domain_score": "",
                                       "status": "Disabled", "domain_weight_fraction": None,
                                       "final_score_contribution": None})
                continue
            parts, metric_weights = [], []
            detail_start = len(details)
            selected = [m for m in domain["metrics"] if m["role"] == "score"]
            domain_complete = bool(selected)
            for metric in domain["metrics"]:
                if metric["role"] == "gate" and not domain.get("hard_gates_enabled", True):
                    continue
                column = metric["column"]
                raw = row.get(column, "").strip()
                value = finite(raw, column) if raw else None
                missing_time = metric.get("requires_time_window", False) and not start
                usable = None if missing_time else value
                item = {"domain": name, "column": column, "unit": metric["unit"], "value": value, "role": metric["role"]}
                if metric.get("hard_gate") is not None and domain.get("hard_gates_enabled", True):
                    gate = metric["hard_gate"]
                    window_hours = None
                    if gate.get("cap_to_window_duration", False) and start and gate.get("threshold") is not None:
                        window_hours = (datetime.fromisoformat(stop) - datetime.fromisoformat(start)).total_seconds() / 3600
                        if usable is not None and usable > window_hours + 1e-9:
                            raise ValueError(f"{row['id']}.{column}: duration exceeds the requested {window_hours} h window")
                        gate = {**gate, "threshold": min(gate["threshold"], window_hours)}
                    state, reason = hard_check(usable, gate)
                    bounds = ("lower", "upper") if gate_operator(gate) == "between" else ("threshold",)
                    if available_data and value is None and all(gate.get(k) is not None for k in bounds):
                        state, reason = "Skipped_missing", "Blank measurement omitted in available_data mode; not a physical pass"
                    gates.append({**item, "condition": gate, "status": state, "reason": reason,
                                  **({"configured_threshold": metric["hard_gate"]["threshold"], "window_duration_hours": window_hours} if window_hours is not None else {}),
                                  "screening_margin": gate_margin(usable, gate)})
                if metric["role"] == "score":
                    score = utility(usable, metric.get("preference")) if usable is not None else None
                    item.update(utility=score, multiplier=metric.get("multiplier"),
                                base_utility=normalized_utility(usable, metric.get("preference")) if usable is not None else None,
                                curve=(metric.get("preference") or {}).get("curve") or {"type": "linear"},
                                metric_weight_fraction=None, domain_score_contribution=None)
                    if domain["include_in_score"]:
                        used += 1
                        supported += usable is not None
                    omit_missing = (available_data and value is None and metric.get("multiplier") is not None
                                    and normalized_utility(0, metric.get("preference")) is not None)
                    if omit_missing:
                        item["reason"] = "Blank measurement omitted; available metric weights are renormalized"
                    elif score is None or metric.get("multiplier") is None:
                        domain_complete = False
                        item["reason"] = "Missing measurement/time, preference bounds or metric multiplier"
                    else:
                        parts.append(score * metric["multiplier"])
                        metric_weights.append(metric["multiplier"])
                details.append(item)
            domain_omitted = available_data and domain_complete and not metric_weights
            domain_complete = domain_complete and bool(metric_weights)
            if domain_complete:
                result[score_column] = 100 * sum(parts) / sum(metric_weights)
                result[score_column + "_status"] = "Scored"
            else:
                result[score_column] = ""
                result[score_column + "_status"] = "Skipped_missing" if domain_omitted else "Context_only" if not selected else "Unknown"
            if domain_complete:
                for item in details[detail_start:]:
                    if item["role"] == "score" and item.get("utility") is not None:
                        item["metric_weight_fraction"] = item["multiplier"] / sum(metric_weights)
                        item["domain_score_contribution"] = 100 * item["utility"] * item["metric_weight_fraction"]
            domain_details.append({"domain": name, "priority_label": domain.get("priority"),
                                   "included_in_final_score": domain["include_in_score"] and not domain_omitted,
                                   "hard_gates_enabled": domain.get("hard_gates_enabled", True),
                                   "domain_multiplier": domain.get("multiplier"), "domain_score": result[score_column],
                                   "status": result[score_column + "_status"],
                                   "domain_weight_fraction": None, "final_score_contribution": None})
            if domain["include_in_score"] and domain_omitted:
                issues.append(f"{name}: blank scoring measurements omitted in available_data mode")
            elif domain["include_in_score"]:
                if not domain_complete or domain.get("multiplier") is None:
                    complete = False
                    issues.append(f"{name}: selected domain needs complete preferences and a domain multiplier")
                else:
                    weighted.append(result[score_column] * domain["multiplier"])
                    weights.append(domain["multiplier"])
        states = [g["status"] for g in gates if g["status"] != "Skipped_missing"]
        hard = "Failed" if "Failed" in states else "Unknown" if not states or "Unknown" in states else "Passed"
        if available_data and not gates and complete and weights:
            hard = "Passed"
            issues.append("No hard gates selected; preference-only available-data assessment")
        if not states:
            if gates:
                issues.append("All selected hard checks lack measurements; no evaluated gate can establish eligibility")
            elif hard != "Passed":
                issues.append("No mandatory hard gates configured; empty gate cannot establish eligibility")
        for gate in gates:
            if gate["status"] != "Passed":
                issues.append(f"{gate['column']}: {gate['status']}: {gate['reason']}")
        if complete and weights:
            # Diagnostic only: never ranked or substituted for gate-qualified results.
            result["comparison_preference_score"] = sum(weighted) / sum(weights)
        if hard == "Passed" and complete and weights:
            result["final_habitability_score"] = result["final_rec_score"] = result["comparison_preference_score"]
            for item in domain_details:
                if item["included_in_final_score"]:
                    item["domain_weight_fraction"] = item["domain_multiplier"] / sum(weights)
                    item["final_score_contribution"] = item["domain_score"] * item["domain_weight_fraction"]
        if not weights and complete:
            issues.append("No domains selected for aggregate scoring")
        failures = []
        if result["final_habitability_score"] == "":
            failures = [gate_failure_reason(g) for g in gates if g["status"] in {"Failed", "Unknown"}]
            failures.extend(issue for issue in issues if "selected domain needs" in issue)
            if hard == "Unknown" and not states:
                failures.append("No hard gates evaluated; eligibility is unknown")
            if not weights:
                failures.append("No scoring domains with usable data and configured weights")
        result.update(hard_gate_status=hard, evidence_coverage=f"{supported}/{used}",
                      fail_reason=" | ".join(failures),
                      score_scope=";".join(d["domain"] for d in domain_details if d["included_in_final_score"]),
                      reason="; ".join(issues) or "Passed configured screens with complete preferences; not operational approval",
                      hard_gate_details=json.dumps(gates, separators=(",", ":"), allow_nan=False),
                      domain_score_details=json.dumps(domain_details, separators=(",", ":"), allow_nan=False),
                      score_details=json.dumps(details, separators=(",", ":"), allow_nan=False))
        if config["name"] == "assumption_NASA_values":
            result["reason"] = "assumption_NASA_values: project assumptions for software testing, not official NASA limits; " + result["reason"]
        results.append(result)
    group = lambda r: (r["time_mode"], r["comparison_start_utc"], r["comparison_stop_utc"],
                       *(r[c] for c in config.get("comparison_group_columns", [])))
    for period in {group(r) for r in results}:
        candidates = [r for r in results if group(r) == period and r["final_rec_score"] != ""]
        for rank, item in enumerate(sorted(candidates, key=lambda r: (-r["final_rec_score"], r["id"])), 1):
            item["rank"] = rank
    return results


def assessment_config(config, assessment):
    """Compose independent schema-1 rules from shared inputs; never mutate YAML."""
    settings = config["assessments"][assessment]
    weights = settings["weights"]
    result = deepcopy({key: config[key] for key in (
        "body", "name", "pipeline_mode", "domains", "metadata_columns",
        "comparison_group_columns") if key in config})
    result.update(schema=1, name=f"{config['name']}:{assessment}")
    for name, domain in result["domains"].items():
        # Allocation comes from this flow's weight map. Unallocated domains
        # remain accepted input context but cannot score or gate this assessment.
        if name not in weights:
            domain.update(enabled=False, include_in_score=False, hard_gates_enabled=False)
            continue
        domain["multiplier"] = weights[name]
        domain.update(settings.get("domain_overrides", {}).get(name, {}))
        for metric in domain["metrics"]:
            metric.update(deepcopy(settings.get("metric_overrides", {}).get(metric["column"], {})))
    return result


def validate_dual_config(config):
    keys(config, {"schema", "body", "name", "pipeline_mode", "metadata_columns",
                  "comparison_group_columns", "domains", "assessments"}, "dual config")
    if type(config.get("schema")) is not int or config.get("body") != "Moon":
        raise ValueError("Expected schema: 2 and body: Moon")
    # Validate the shared measurement registry with the existing schema contract.
    base = {key: value for key, value in config.items() if key != "assessments"}
    validate_config({**base, "schema": 1})
    assessments = config.get("assessments")
    if not isinstance(assessments, dict) or set(assessments) != set(ASSESSMENTS):
        raise ValueError("Declare exactly operations and survival assessments")
    domains = config["domains"]
    owners = {metric["column"]: name for name, domain in domains.items() for metric in domain["metrics"]}
    for name, settings in assessments.items():
        keys(settings, {"weights", "domain_overrides", "metric_overrides"}, name)
        weights = settings.get("weights")
        if not isinstance(weights, dict) or not weights or set(weights) - set(domains):
            raise ValueError(f"{name}: nonempty weights must name declared domains")
        for domain, weight in weights.items():
            positive(weight, f"{name}.weights.{domain}")
        overrides = settings.get("domain_overrides", {})
        if not isinstance(overrides, dict) or set(overrides) - set(weights):
            raise ValueError(f"{name}: domain overrides must be allocated in this flow")
        for domain, override in overrides.items():
            keys(override, {"enabled", "hard_gates_enabled", "include_in_score", "priority"},
                 f"{name}.{domain}")
        overrides = settings.get("metric_overrides", {})
        if not isinstance(overrides, dict) or set(overrides) - set(owners):
            raise ValueError(f"{name}: metric overrides must name registered input columns")
        for column, override in overrides.items():
            if owners[column] not in weights:
                raise ValueError(f"{name}.{column}: override would be unused")
            keys(override, {"role", "preference", "hard_gate", "multiplier", "meaning"},
                 f"{name}.{column}")
        validate_config(assessment_config(config, name))
    if set(config.get("metadata_columns", [])) & set(dual_columns(config, compact=False)):
        raise ValueError("metadata_columns cannot shadow dual output fields")


def assess(rows, config, config_hash):
    if config.get("schema") != 2:
        return _assess_single(rows, config, config_hash)
    validate_config(config)
    results = [{"id": row["id"]} for row in rows]
    for name in ASSESSMENTS:
        rules = assessment_config(config, name)
        records = _assess_single(rows, rules, config_hash)
        selected_gates = any(d.get("enabled", True) and d.get("hard_gates_enabled", True)
                             and any(m.get("hard_gate") is not None for m in d["metrics"])
                             for d in rules["domains"].values())
        for result, record in zip(results, records):
            score = record["final_habitability_score"]
            state = record["hard_gate_status"]
            # In either missing-data mode, a complete preference-only assessment
            # can pass its configured comparison policy without claiming safety.
            if not selected_gates and record["comparison_preference_score"] != "":
                score, state = record["comparison_preference_score"], "Passed"
            status = {"Passed": "Pass", "Failed": "Fail", "Unknown": "Unknown"}[state]
            if score == "" and status == "Pass":
                status = "Unknown"
            result.update({f"{name}_score": score, f"{name}_status": status,
                           f"{name}_fail_reason": record["fail_reason"] if score == "" else "",
                           f"{name}_coverage": record["evidence_coverage"],
                           f"{name}_details": record})
            for domain, column in SCORES.items():
                result[f"{name}_{domain}_score"] = record[column]
    return results


def dual_columns(config, *, compact):
    columns = ["ID"]
    for assessment in ASSESSMENTS:
        rules = assessment_config(config, assessment)
        columns += [f"{assessment}_{domain}_score" for domain in SCORES
                    if domain in rules["domains"] and rules["domains"][domain].get("enabled", True)
                    and rules["domains"][domain]["include_in_score"]]
    columns += [f"{a}_{field}" for field in ("status", "fail_reason") for a in ASSESSMENTS]
    if not compact:
        columns += [f"{a}_coverage" for a in ASSESSMENTS]
    columns += ["operations_score", "survival_score"]
    if not compact:
        columns += [f"{a}_details" for a in ASSESSMENTS]
    return columns


def run(input_path, output_path, config_path, *, overwrite=False, compact=False):
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
    columns += [c for c in config.get("metadata_columns", []) if c not in columns]
    columns += [field for name in SCORES.values() for field in (name, name + "_status")]
    columns += ["pipeline_mode", "comparison_preference_score", "hard_gate_status", "final_rec_score", "rank", "score_scope", "evidence_coverage",
                "reason", "operational_suitability", "config_name", "config_sha256", "hard_gate_details", "score_details", "domain_score_details", "fail_reason", "final_habitability_score"]
    stream = io.StringIO(newline="")
    writer = csv.DictWriter(stream, fieldnames=[OUTPUT_COLUMN_NAMES.get(c, c) for c in columns], lineterminator="\n")
    dual = config.get("schema") == 2
    if dual:
        columns = dual_columns(config, compact=compact)
        writer = csv.DictWriter(stream, fieldnames=columns, lineterminator="\n")
    elif compact:
        domains = [name for name in SCORES if name in config["domains"] and config["domains"][name].get("enabled", True)]
        writer = csv.DictWriter(stream, fieldnames=["ID", *("soil_score" if name == "soil" else name for name in domains), "hard_gate_status", "Fail Reason", "final_habitability_score"], lineterminator="\n")
    writer.writeheader()
    if dual:
        def display(value):
            if isinstance(value, float):
                return round(value, 2)
            if isinstance(value, dict):
                return json.dumps(value, separators=(",", ":"), allow_nan=False)
            return value
        writer.writerows({key: display(row["id"] if key == "ID" else row[key]) for key in columns}
                         for row in results)
    elif compact:
        display_score = lambda value: round(value, 2) if value != "" else ""
        writer.writerows({"ID": row["id"],
                          **{("soil_score" if name == "soil" else name): display_score(row[SCORES[name]]) for name in domains},
                          "hard_gate_status": row["hard_gate_status"],
                          "Fail Reason": row["fail_reason"],
                          "final_habitability_score": display_score(row["final_habitability_score"])}
                         for row in results)
    else:
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
    parser.add_argument("--input", type=Path, default=Path(__file__).parent / "inputs/sites.csv",
                        help="One measurement CSV (default: inputs/sites.csv)")
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("config.yml"))
    parser.add_argument("--overwrite", action="store_true")
    export = parser.add_mutually_exclusive_group()
    export.add_argument("--compact", dest="compact", action="store_true", help="Simple output (default): domain scores, separate statuses and Operations/Survival scores")
    export.add_argument("--detailed", dest="compact", action="store_false", help="Export full audit, contribution and ranking details")
    parser.set_defaults(compact=True)
    args = parser.parse_args(argv)
    try:
        rows = run(args.input, args.output, args.config, overwrite=args.overwrite, compact=args.compact)
    except (ValueError, OSError, csv.Error, yaml.YAMLError) as exc:
        parser.exit(2, f"Environmental pipeline error: {exc}\n")
    summary = {"rows": len(rows), "output": str(args.output.resolve())}
    if rows and "operations_score" in rows[0]:
        summary["statuses"] = {a: {s: sum(r[f"{a}_status"] == s for r in rows)
                                    for s in ("Pass", "Fail", "Unknown")} for a in ASSESSMENTS}
    else:
        summary.update(ranked=sum(r["rank"] != "" for r in rows),
                       hard_statuses={s: sum(r["hard_gate_status"] == s for r in rows)
                                      for s in ("Passed", "Failed", "Unknown")})
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    main()
