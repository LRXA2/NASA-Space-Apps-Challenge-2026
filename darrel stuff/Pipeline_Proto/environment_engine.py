"""Explainable environmental companion to the terrain CNN, NOT a trained CNN.

Verified EDA -> qualified evidence -> hard checks -> soft preferences -> report.
Only an explicitly diagnostic policy can compare the current static/phase proxies.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import numpy as np
import pandas as pd

LOCAL = Path(__file__).resolve().parents[1]
ROOT = LOCAL.parent
PIPELINE = Path(__file__).resolve().parent
OUTPUTS = PIPELINE / "outputs"
SAMPLE_FIXTURE = PIPELINE / "sample_data/synthetic_10_candidates.csv"
sys.path[:0] = [str(LOCAL / "EDA"), str(LOCAL), str(ROOT)]
from data_maintenance import atomic_text
from decision_eda import accepted_input
from environment_workflow import LocalRun
from notebooks.shared.processing import Run
import stage3_assessment
import evidence_rules

# Metric scope is part of its contract, not a field a caller may relabel.
METRICS = {
    "solar_visibility_median": ("fraction", "static_map_cell_summary", True),
    "earth_visibility_median": ("fraction", "static_map_cell_summary", True),
    "slope_q90_deg": ("degree", "static_map_cell_summary", True),
    "thermal_phase_median_span_K": ("K", "fixed_common_phase_point_context", True),
    "thermal_phase_median_min_K": ("K", "fixed_common_phase_point_context", True),
    "thermal_phase_median_max_K": ("K", "fixed_common_phase_point_context", True),
    "minirf_cpr_median": ("dimensionless", "associated_native_centres_context_only", False),
    "shadowcam_radiance_median": ("W m^-2 sr^-1 um^-1", "associated_native_centres_context_only", False),
}


class PrototypeRun(LocalRun):
    """Reuse established atomic local provenance, with a script entry point."""
    def __init__(self, config, run_kind=None):
        self.project_root = ROOT.resolve()
        Run.__init__(self, LOCAL, "env_cnn_prototype", config, "")
        kind = run_kind or config["policy"]["mode"]
        if kind not in {"environment_comparison", "evidence_only", "diagnostic", "synthetic_demo"}:
            raise ValueError("Unsupported pipeline run kind")
        self.directory = (OUTPUTS / kind / self.directory.name).resolve()
        if not self.directory.is_relative_to(PIPELINE.resolve()):
            raise ValueError("Pipeline output must remain inside Pipeline_Proto")
        self.record["run_kind"] = kind
        self.notebook = Path(__file__).resolve()

    def path(self, relative):
        result = (self.directory / relative).resolve()
        if not result.is_relative_to(self.directory) or not result.is_relative_to(PIPELINE.resolve()):
            raise ValueError("Output escapes the pipeline run")
        result.parent.mkdir(parents=True, exist_ok=True)
        return result


def validate_policy(policy):
    if policy.get("schema") != 1 or policy.get("mode") not in {"evidence_only", "diagnostic"}:
        raise ValueError("Expected schema 1 and evidence_only/diagnostic mode")
    if type(policy.get("top_k")) is not int or policy["top_k"] < 1:
        raise ValueError("top_k must be a positive integer")
    ids, soft_metrics = set(), set()
    for kind in ("hard_rules", "soft_preferences"):
        if not isinstance(policy.get(kind), list):
            raise ValueError(f"Expected a list: {kind}")
        for rule in policy[kind]:
            name = rule.get("id")
            if not isinstance(name, str) or not name.strip() or name in ids:
                raise ValueError("Each rule/preference needs a unique nonempty ID")
            ids.add(name)
            if not isinstance(rule.get("reason"), str) or not rule["reason"].strip():
                raise ValueError("Every criterion needs a documented reason")
            metric = rule.get("metric")
            if metric is None:
                missing = rule.get("missing_inputs")
                if (kind != "hard_rules" or not isinstance(missing, list) or not missing
                        or any(not isinstance(x, str) or not x.strip() for x in missing)):
                    raise ValueError("Unimplemented requirements need missing_inputs and cannot be scored")
                continue
            if policy["mode"] != "diagnostic" or metric not in METRICS or not METRICS[metric][2]:
                raise ValueError("Current evidence permits only explicit diagnostic proxy criteria; CPR/image values are context-only")
            unit, scope, _ = METRICS[metric]
            if (rule.get("unit"), rule.get("scope")) != (unit, scope):
                raise ValueError(f"Criterion unit/scope mismatch: {metric}")
            if kind == "hard_rules":
                if rule.get("operator") not in {"ge", "le"} or not finite_number(rule.get("limit")):
                    raise ValueError("Hard comparisons need ge/le and a finite limit")
            else:
                if metric in soft_metrics:
                    raise ValueError("Duplicate soft metric would double-count evidence")
                soft_metrics.add(metric)
                if (rule.get("direction") not in {"higher", "lower"}
                        or not finite_number(rule.get("weight")) or rule["weight"] <= 0
                        or not finite_number(rule.get("lower")) or not finite_number(rule.get("upper"))
                        or rule["lower"] >= rule["upper"]):
                    raise ValueError("Preferences need explicit finite bounds, positive weights and direction")


def finite_number(value):
    return type(value) in {int, float} and np.isfinite(value)


def validate_evidence(candidates, evidence):
    if candidates.empty or candidates.candidate_id.isna().any() or candidates.candidate_id.duplicated().any():
        raise ValueError("Expected unique nonempty candidate identities")
    if evidence.duplicated(["candidate_id", "metric"]).any():
        raise ValueError("Repeated candidate/metric evidence")
    if not set(evidence.candidate_id) <= set(candidates.candidate_id):
        raise ValueError("Evidence references an unknown candidate")
    for row in evidence.itertuples():
        if row.metric not in METRICS or (row.unit, row.scope) != METRICS[row.metric][:2]:
            raise ValueError("Unregistered metric or changed unit/support meaning")
        if row.status not in {"observed", "unknown"}:
            raise ValueError("Unknown evidence status")
        if row.status == "observed" and (not np.isfinite(row.value) or row.support_count <= 0):
            raise ValueError("Observed evidence must have a finite value and actual support")
        if row.status == "unknown" and pd.notna(row.value):
            raise ValueError("Unknown evidence cannot contain a numeric substitute")
        if not np.isfinite(row.support_count) or row.support_count < 0 or row.support_count != int(row.support_count):
            raise ValueError("Evidence support must be a nonnegative integer count")
        if row.status == "observed":
            if row.unit == "fraction" and not 0 <= row.value <= 1:
                raise ValueError("Visibility is a fraction, not percent")
            if row.metric == "slope_q90_deg" and not 0 <= row.value <= 90:
                raise ValueError("Slope outside degree domain")
            if (row.metric.startswith("thermal_") or row.metric == "minirf_cpr_median") and row.value < 0:
                raise ValueError("Negative value outside the declared analysis cohort")


def run_eligibility(candidates, evidence, policy):
    """prototype2-style hard stage: retain all candidates and all rule reasons."""
    validate_policy(policy)
    validate_evidence(candidates, evidence)
    lookup = evidence.set_index(["candidate_id", "metric"])
    checks, gates = [], []
    for candidate in candidates.candidate_id:
        states = []
        for rule in policy["hard_rules"]:
            metric = rule.get("metric")
            key = (candidate, metric)
            value = np.nan
            if metric is None:
                state, reason = "unknown", "missing applicable inputs/models: " + "; ".join(rule["missing_inputs"])
            elif key not in lookup.index or lookup.loc[key, "status"] != "observed":
                state, reason = "unknown", "missing qualifying evidence; no substitution"
            else:
                value = float(lookup.loc[key, "value"])
                passed = value >= rule["limit"] if rule["operator"] == "ge" else value <= rule["limit"]
                state, reason = ("pass" if passed else "fail"), rule["reason"]
            states.append(state)
            checks.append({"candidate_id": candidate, "rule_id": rule["id"], "metric": metric,
                           "value": value, "operator": rule.get("operator"), "limit": rule.get("limit"),
                           "unit": rule.get("unit"), "scope": rule.get("scope"),
                           "status": state, "reason": reason})
        gate = ("unconfigured" if not states else "fail" if "fail" in states
                else "unknown" if "unknown" in states else "pass")
        gates.append({"candidate_id": candidate, "gate_status": gate})
    columns = ["candidate_id", "rule_id", "metric", "value", "operator", "limit", "unit", "scope", "status", "reason"]
    return pd.DataFrame(gates), pd.DataFrame(checks, columns=columns)


def run_scoring(gates, evidence, policy):
    """Score only approved scope; no score for failed/unknown/unconfigured gates."""
    validate_policy(policy)
    validate_evidence(gates, evidence)
    if not set(gates.gate_status) <= {"pass", "fail", "unknown", "unconfigured"}:
        raise ValueError("Unrecognized eligibility state")
    lookup = evidence.set_index(["candidate_id", "metric"])
    scores, summaries = [], []
    for candidate, gate in gates[["candidate_id", "gate_status"]].itertuples(index=False, name=None):
        parts, total_weight, complete = [], 0., True
        for preference in policy["soft_preferences"]:
            key = (candidate, preference["metric"])
            value, score, reason = np.nan, np.nan, "hard requirements not all passed"
            if gate == "pass":
                if key in lookup.index and lookup.loc[key, "status"] == "observed":
                    value = float(lookup.loc[key, "value"])
                    score = float(np.clip((value - preference["lower"]) /
                                          (preference["upper"] - preference["lower"]), 0, 1))
                    if preference["direction"] == "lower":
                        score = 1 - score
                    parts.append(score * preference["weight"])
                    total_weight += preference["weight"]
                    reason = "declared bounded diagnostic utility; clipped at configured bounds"
                else:
                    reason = "missing soft evidence; aggregate withheld, weights not renormalized"
                    complete = False
            scores.append({"candidate_id": candidate, "preference_id": preference["id"],
                           "metric": preference["metric"], "weight": preference["weight"],
                           "value": value, "lower": preference["lower"], "upper": preference["upper"],
                           "direction": preference["direction"],
                           "utility": score, "reason": reason})
        aggregate = sum(parts) / total_weight if gate == "pass" and complete and total_weight else np.nan
        summaries.append({"candidate_id": candidate, "gate_status": gate,
                          "diagnostic_preference_score": aggregate,
                          "operational_status": "not_assessed",
                          "ranking_status": "diagnostic_only" if np.isfinite(aggregate) else "not_ranked"})
    columns = ["candidate_id", "preference_id", "metric", "weight", "value", "lower", "upper", "direction", "utility", "reason"]
    return pd.DataFrame(summaries), pd.DataFrame(scores, columns=columns)


def run_recommendations(assessments, top_k):
    """Stable gate-first top-k; preserve the independent terrain retrieval stage."""
    if type(top_k) is not int or top_k < 1:
        raise ValueError("top_k must be a positive integer")
    ranking = assessments.loc[assessments.gate_status.eq("pass") &
                              np.isfinite(assessments.diagnostic_preference_score)].sort_values(
        ["diagnostic_preference_score", "candidate_id"], ascending=[False, True]).copy()
    ranking["diagnostic_rank"] = np.arange(1, len(ranking) + 1)
    return ranking.head(top_k)


def evaluate(candidates, evidence, policy):
    """Existing API, composed from the sample's eligibility/scoring/reco stages."""
    gates, checks = run_eligibility(candidates, evidence, policy)
    scored, utilities = run_scoring(gates, evidence, policy)
    summary = candidates.merge(scored, on="candidate_id", validate="one_to_one")
    return summary, checks, utilities, run_recommendations(summary, policy["top_k"])


def load_evidence(run, config):
    """Use pinned completed EDA, checking hashes of every consumed output."""
    data = LOCAL / "data"
    source = config["sources"]
    def read(key, name):
        folder = (data / source[key]).resolve()
        if not folder.is_relative_to((data / "processed/analysis").resolve()):
            raise ValueError("EDA input must stay within local analysis outputs")
        return pd.read_csv(accepted_input(run, folder, name))

    candidates = read("candidates", "candidate_manifest.csv")
    static = read("candidates", "candidate_static_profiles.csv")
    thermal = read("candidates", "candidate_thermal_summary.csv")
    support = read("candidates", "candidate_thermal_association_support.csv")
    rows = []
    for variable, metric, statistic in [
        ("solar_visibility", "solar_visibility_median", "median"),
        ("earth_visibility", "earth_visibility_median", "median"),
        ("slope_deg", "slope_q90_deg", "q90"),
    ]:
        frame = static.loc[static.variable.eq(variable)]
        if set(frame.candidate_id) != set(candidates.candidate_id) or frame.candidate_id.duplicated().any():
            raise ValueError("Static profiles do not align with candidates")
        for item in frame.to_dict("records"):
            if item["unit"] != METRICS[metric][0] or not 0 <= item["finite_cells"] <= item["cells"]:
                raise ValueError("Static profile unit/count differs from its declared contract")
            # Do not let a partially observed cell summary pass a whole-summary check.
            known = item["finite_cells"] == item["cells"] and item["cells"] > 0 and np.isfinite(item[statistic])
            rows.append(evidence_row(item["candidate_id"], metric, item[statistic] if known else np.nan,
                                     item["finite_cells"], "observed" if known else "unknown", source["candidates"]))
    fixed = thermal.loc[thermal.cohort.eq("fixed_common")].merge(
        support[["candidate_id", "expected_common_products"]], on="candidate_id", validate="one_to_one")
    if set(fixed.candidate_id) != set(candidates.candidate_id):
        raise ValueError("Fixed thermal cohorts do not align with candidates")
    for item in fixed.to_dict("records"):
        known = (item["expected_common_products"] > 0
                 and item["supported_products"] == item["expected_common_products"]
                 and item["minimum_centers_per_product"] > 0)
        for field, metric in [
            ("span_of_product_medians_K", "thermal_phase_median_span_K"),
            ("minimum_product_median_K", "thermal_phase_median_min_K"),
            ("maximum_product_median_K", "thermal_phase_median_max_K"),
        ]:
            value = item[field] if known else np.nan
            rows.append(evidence_row(item["candidate_id"], metric, value,
                item["minimum_centers_per_product"], "observed" if known else "unknown", source["candidates"]))

    # Associate only the already documented candidate centres, NOT region averages.
    centres = read("candidates", "associated_center_phase_spans.csv")
    centres = centres.merge(candidates[["candidate_id", "region"]], on="candidate_id", validate="many_to_one")
    if centres.duplicated(["region", "clon", "clat"]).any():
        raise ValueError("Candidate-centre identity overlaps; association must be reviewed")
    context_records = []
    for key, metric in [("shadowcam", "shadowcam_radiance_median"), ("minirf", "minirf_cpr_median")]:
        pixels = read(key, "source_at_environment_centres.csv.gz")
        paired = centres.merge(pixels[["region", "clon", "clat", "analysis_value", "pixel_status", "source_row", "source_col"]],
            on=["region", "clon", "clat"], how="left", validate="one_to_one")
        for candidate in candidates.candidate_id:
            points = paired.loc[paired.candidate_id.eq(candidate)]
            ordinary = points.loc[points.analysis_value.notna()]
            unique = ordinary.drop_duplicates(["source_row", "source_col"])
            value = unique.analysis_value.median()
            count = len(unique)
            rows.append(evidence_row(candidate, metric, value, count, "observed" if count else "unknown", source[key]))
            context_records.append({"candidate_id": candidate, "metric": metric,
                "associated_centres": len(points), "supported_centres": len(ordinary),
                "distinct_supported_source_pixels": count, "median": value,
                "scope": METRICS[metric][1], "scoring_allowed": False})
    return candidates, pd.DataFrame(rows), pd.DataFrame(context_records), static, support


def evidence_row(candidate, metric, value, count, status, source):
    unit, scope, _ = METRICS[metric]
    return {"candidate_id": candidate, "metric": metric, "value": value, "unit": unit,
            "scope": scope, "support_count": count, "status": status, "source_run": source}


def fixture_boolean(value):
    if isinstance(value, (bool, np.bool_)):
        return bool(value)
    if value in {"True", "False"}:
        return value == "True"
    raise ValueError("Synthetic fixture Boolean must explicitly be True or False")


def load_sample_fixture(run):
    """Ten explicit fictional cases, passed through the SAME assessment functions."""
    run.input(SAMPLE_FIXTURE)
    fixture = pd.read_csv(SAMPLE_FIXTURE, keep_default_na=False)
    if (len(fixture) != 10 or fixture.candidate_id.duplicated().any()
            or not fixture.data_basis.eq("synthetic_fixture_only").all()):
        raise ValueError("Expected ten uniquely identified, explicitly synthetic fixture rows")
    candidates = fixture[["candidate_id", "scenario", "data_basis", "expected_stage3_status",
                          "expected_diagnostic_status"]].copy()
    candidates["region"] = "synthetic_nonphysical_test_region"
    start, stop = "2026-01-01T00:00:00Z", "2026-01-02T00:00:00Z"
    profile = {"schema": 1, "body": "Moon", "start_utc": start, "stop_utc": stop,
        "crew_count": 2, "activities": ["synthetic_rule_verification_only"],
        "equipment_configuration": {"id": "fictional_test_equipment", "data_basis": "synthetic_fixture_only"},
        "requirements_inventory_complete": True, "candidate_inputs": {},
        "note": "Complete only for these five synthetic test requirements; NOT a real complete mission inventory.",
        "requirements": [
            {"id": "consumables", "kind": "consumable", "mandatory": True, "settings": {}},
            {"id": "power", "kind": "power", "mandatory": True, "settings": {
                "battery_usable_Wh": 100, "initial_energy_Wh": 50, "reserve_Wh": 10,
                "charge_efficiency": 1, "discharge_efficiency": 1}},
            {"id": "thermal", "kind": "thermal", "mandatory": True,
             "settings": {"minimum_operating_K": 270, "maximum_operating_K": 310}},
            {"id": "communications", "kind": "communications", "mandatory": True,
             "settings": {"maximum_outage_hours": 4}},
            {"id": "support_load", "kind": "capacity_demand", "mandatory": True,
             "settings": {"quantity": "fixture_support_load", "unit": "N"}},
        ]}
    for rule in profile["requirements"]:
        rule.update(source="synthetic_fixture_only_not_a_published_requirement",
                    reason="Fictional scenario for software verification only; not an adopted mission limit")
    evidence, static = [], []
    for case in fixture.to_dict("records"):
        candidate = case["candidate_id"]
        profile["candidate_inputs"][candidate] = {}
        for metric, variable in [("solar_visibility_median", "solar_visibility"),
                                 ("earth_visibility_median", "earth_visibility"), ("slope_q90_deg", "slope_deg")]:
            value = float(case[metric])
            evidence.append(evidence_row(candidate, metric, value, 1, "observed", "synthetic_fixture_only"))
            static.append({"candidate_id": candidate, "variable": variable, "unit": METRICS[metric][0],
                           "cells": 1, "finite_cells": 1, "median": value, "q90": value,
                           "data_basis": "synthetic_fixture_only"})
        intervals = {"start_utc": start, "stop_utc": stop}
        frames = {
            "consumables": {"rate_kg_per_crew_day": 1, "recovery_fraction": 0,
                            "available_kg": case["available_kg"], "reserve_kg": case["reserve_kg"]},
            "power": {**intervals, "generation_W": case["generation_W"], "load_W": case["load_W"]},
            "thermal": {**intervals, "minimum_component_K": case["minimum_component_K"],
                        "maximum_component_K": case["maximum_component_K"]},
            "communications": {**intervals, "contact_available": fixture_boolean(case["contact_available"])},
            "support_load": {"quantity": "fixture_support_load", "unit": "N", "capacity": case["capacity_N"],
                             "demand": case["demand_N"], "reserve": case["reserve_N"]},
        }
        if case["omit_requirement"] not in {"", *frames}:
            raise ValueError("Unknown deliberately omitted fixture requirement")
        for requirement, fields in frames.items():
            if requirement == case["omit_requirement"]:
                continue
            path = run.path(f"sample_inputs/{candidate}/{requirement}.csv")
            pd.DataFrame([fields]).to_csv(path, index=False)
            item = {"body": "Moon", "basis": "modeled", "support": "candidate_validated",
                    **intervals, "input_file": path.relative_to(PIPELINE).as_posix(),
                    "applicability_note": "Synthetic assertion for software test, NOT validated physical terrain/equipment"}
            if requirement in {"power", "communications"}:
                item.update(terrain_aware=True, time_model="piecewise_constant")
            if requirement == "thermal":
                item["quantity"] = ("surface_brightness_temperature" if fixture_boolean(case["wrong_thermal_quantity"])
                                    else "component_response_temperature")
            profile["candidate_inputs"][candidate][requirement] = item
    policy_path = PIPELINE / "diagnostic_policy.json"
    run.input(policy_path)
    policy = json.loads(policy_path.read_text(encoding="utf-8"))
    profile["soft_preferences"] = policy["soft_preferences"]
    profile_path = run.path("sample_inputs/mission_profile.json")
    atomic_text(profile_path, json.dumps(profile, indent=2) + "\n")
    run.input(profile_path)
    context = pd.DataFrame(columns=["candidate_id", "metric", "associated_centres", "supported_centres",
        "distinct_supported_source_pixels", "median", "scope", "scoring_allowed"])
    support = pd.DataFrame(columns=["candidate_id", "expected_common_products", "supported_products",
                                    "minimum_centers_per_product"])
    return candidates, pd.DataFrame(evidence), context, pd.DataFrame(static), support, profile


def readiness_tables(summary, evidence, operational_checks, profile):
    missing = "; ".join(stage3_assessment.profile_readiness(profile))
    rows = []
    for item in summary.to_dict("records"):
        metrics = evidence.loc[evidence.candidate_id.eq(item["candidate_id"])]
        rows.append({"candidate_id": item["candidate_id"], "stage3_status": item["stage3_status"],
            "diagnostic_gate_status": item["gate_status"],
            "observed_metric_count": int(metrics.status.eq("observed").sum()),
            "unknown_metric_count": int(metrics.status.eq("unknown").sum()),
            "unknown_metrics": "; ".join(metrics.loc[metrics.status.eq("unknown"), "metric"]),
            "missing_profile_inputs": missing, "mandatory_pass": item["mandatory_pass"],
            "mandatory_fail": item["mandatory_fail"], "mandatory_unknown": item["mandatory_unknown"]})
    grouped = operational_checks.groupby(["requirement", "status", "reason"], dropna=False).size()
    return pd.DataFrame(rows), grouped.rename("candidate_count").reset_index()


def environmental_tables(summary, evidence, checks, policy):
    """Report the existing qualified-data comparison, NOT operational eligibility.

    Reuse the declared policy and score without adding factors, filling values,
    or changing weights when a candidate lacks qualifying evidence.
    """
    identity = [name for name in ("candidate_id", "region") if name in summary]
    ranking = summary[identity + ["gate_status", "diagnostic_preference_score"]].rename(columns={
        "gate_status": "context_filter_status", "diagnostic_preference_score": "environmental_score"}).copy()
    ranking["comparison_status"] = [
        "ranked_context_only" if gate == "pass" and np.isfinite(score)
        else "excluded_by_context_filter" if gate == "fail"
        else "missing_comparable_evidence" if gate in {"pass", "unknown"}
        else "comparison_not_configured"
        for gate, score in ranking[["context_filter_status", "environmental_score"]].itertuples(index=False, name=None)]
    reasons = {}
    for candidate in ranking.candidate_id:
        parts = []
        for row in checks.loc[checks.candidate_id.eq(candidate) & checks.status.ne("pass")].to_dict("records"):
            if row["status"] == "unknown":
                parts.append(f"{row['rule_id']}: missing qualifying evidence for {row['metric']}; {row['reason']}")
            else:
                parts.append(f"{row['rule_id']}: {row['metric']}={row['value']} {row['unit']}; "
                             f"requires {row['operator']} {row['limit']}; {row['reason']}")
        reasons[candidate] = "; ".join(parts)
    ranking["reason"] = [
        "Passed configured context filters; complete declared preference score; not mission adequacy"
        if state == "ranked_context_only" else reasons[candidate] or
        ("Missing soft evidence; score withheld, weights unchanged" if state == "missing_comparable_evidence"
         else "No executable environmental comparison policy configured")
        for candidate, state in ranking[["candidate_id", "comparison_status"]].itertuples(index=False, name=None)]
    filter_metrics = {r["metric"] for r in policy["hard_rules"] if r.get("metric") is not None}
    score_metrics = {r["metric"] for r in policy["soft_preferences"]}
    configured_metrics = sorted(filter_metrics | score_metrics)
    known = evidence.loc[evidence.status.eq("observed")].pivot(index="candidate_id", columns="metric", values="value")
    ranking = ranking.merge(known.reindex(columns=configured_metrics), on="candidate_id", how="left", validate="one_to_one")
    ranked = ranking.loc[ranking.comparison_status.eq("ranked_context_only")].sort_values(
        ["environmental_score", "candidate_id"], ascending=[False, True])
    ranks = {candidate: i+1 for i, candidate in enumerate(ranked.candidate_id)}
    ranking["environmental_rank"] = ranking.candidate_id.map(ranks).astype("Int64")
    ranking = ranking.sort_values(["environmental_rank", "candidate_id"], na_position="last").reset_index(drop=True)
    top = ranking.loc[ranking.environmental_rank.notna()].head(policy["top_k"]).copy()
    usage = []
    for metric in sorted(evidence.metric.unique()):
        rows = evidence.loc[evidence.metric.eq(metric)]
        supported = int(rows.status.eq("observed").sum())
        active = metric in filter_metrics | score_metrics
        reason = ("Used only in the explicitly configured context filter/preference; no operational margin implied"
                  if active else "Context only: source/support contract forbids scoring" if not METRICS[metric][2]
                  else "Retained as context; not in the declared score. No automatic weight or missing-value substitution")
        usage.append({"metric": metric, "unit": METRICS[metric][0], "scope": METRICS[metric][1],
            "candidate_count": len(summary), "supported_candidates": supported,
            "unsupported_or_absent_candidates": len(summary)-supported,
            "used_in_context_filter": metric in filter_metrics, "used_in_score": metric in score_metrics,
            "reason": reason})
    return ranking, top, pd.DataFrame(usage)


def operational_outputs(candidates, evidence, summary, profile, evidence_root, top_k, run):
    """Explicit opt-in Stage 3 path; never supplies defaults to a context comparison."""
    operational, checks = stage3_assessment.assess(candidates, profile, evidence_root, run)
    summary = summary.merge(operational, on="candidate_id", validate="one_to_one")
    summary["operational_status"] = summary.stage3_status
    preference_policy = {"schema": 1, "mode": "diagnostic", "top_k": top_k,
                         "hard_rules": [], "soft_preferences": profile.get("soft_preferences", [])}
    gates = operational[["candidate_id", "stage3_status"]].rename(columns={"stage3_status": "gate_status"})
    scores, utilities = run_scoring(gates, evidence, preference_policy)
    summary = summary.merge(scores[["candidate_id", "diagnostic_preference_score"]].rename(
        columns={"diagnostic_preference_score": "operational_preference_score"}), on="candidate_id", validate="one_to_one")
    summary["operational_ranking_status"] = np.where(summary.operational_preference_score.notna(),
        "configured_preference_only_not_certification", "not_ranked")
    ranking_input = summary.drop(columns=["diagnostic_preference_score", "gate_status"]).rename(
        columns={"operational_preference_score": "diagnostic_preference_score", "stage3_status": "gate_status"})
    top = run_recommendations(ranking_input, top_k).rename(
        columns={"diagnostic_preference_score": "operational_preference_score", "diagnostic_rank": "configured_preference_rank"})
    top["stage3_status"] = top["gate_status"]
    top["ranking_status"] = "configured_preference_only_not_certification"
    readiness, requirement_readiness = readiness_tables(summary, evidence, checks, profile)
    return summary, operational, checks, utilities, top, readiness, requirement_readiness


def product_tables(ranking, evidence, checks, utilities, usage, top_k):
    """Data-backed deliverables only; incomplete evidence is accounted for, not filled."""
    ranked = ranking.loc[ranking.environmental_score.notna()].copy()
    identity = [name for name in ("candidate_id", "region") if name in ranking]
    status = ranking[identity + ["comparison_status", "reason"]].copy()
    excluded = status.loc[status.comparison_status.ne("ranked_context_only")].copy()
    available = evidence.loc[evidence.status.eq("observed")].copy()
    known_checks = checks.loc[checks.status.isin(["pass", "fail"])].copy()
    contributions = utilities.loc[utilities.utility.notna()].copy()
    metrics = ["thermal_phase_median_min_K", "thermal_phase_median_max_K", "thermal_phase_median_span_K"]
    thermal = available.loc[available.metric.isin(metrics)].pivot(index="candidate_id", columns="metric", values="value")
    # This is an explicit complete common-cohort profile, not partial-profile imputation.
    thermal = thermal.reindex(columns=metrics).dropna(subset=metrics).reset_index()
    thermal = thermal.merge(ranking[identity], on="candidate_id", validate="one_to_one")
    thermal["scope"] = "fixed_common_phase_point_context_not_component_response"
    return [
        ("environmental_rankings.csv", "Ranked candidates with complete configured environmental scores", ranked,
         "No candidate has both passing configured filters and a complete preference score"),
        ("environmental_top_k.csv", "Top environmental comparisons", ranked.head(top_k), "No ranked candidates"),
        ("candidate_status.csv", "Every candidate accounted for, including exclusions", status, "No candidates"),
        ("excluded_candidates.csv", "Excluded or insufficient-evidence candidates and reasons", excluded, "No exclusions in this run"),
        ("soft_preference_results.csv", "Actual per-factor score contributions for ranked candidates", contributions,
         "No supported preference contributions"),
        ("hard_rule_results.csv", "Evaluated context filters with real values", known_checks,
         "No context-filter comparisons have sufficient evidence; see candidate_status and feature_usage"),
        ("environment_evidence.csv", "Available qualified environmental values only", available,
         "No observed qualified evidence; see feature_usage"),
        ("feature_usage.csv", "Coverage and score/filter/context roles for every available metric", usage,
         "No environmental metric records supplied"),
        ("thermal_profiles.csv", "Complete existing common-phase thermal profiles (K), not equipment limits", thermal,
         "No complete qualifying thermal profiles; coverage remains reported in feature_usage"),
    ]


def export_tables(run, tables, report, omit_empty=False):
    """Keep CSV schemas clean; explain titles/empty results in a separate catalog."""
    catalog = []
    for name, title, frame, empty_reason in tables:
        if not len(frame.columns):
            raise ValueError(f"Missing output schema: {name}")
        if report["is_synthetic"]:
            frame = frame.assign(data_basis="synthetic_fixture_only")
        written = not (omit_empty and frame.empty)
        if written:
            frame.to_csv(run.path(name), index=False)
        catalog.append({"file": name, "title": title, "rows": len(frame), "columns": len(frame.columns),
                        "data_basis": report["data_basis"],
                        "status": "has_rows" if len(frame) else "empty_expected" if written else "omitted_empty",
                        "reason": "Rows exported; inspect their status/scope before use" if len(frame) else empty_reason})
    pd.DataFrame(catalog).to_csv(run.path("output_catalog.csv"), index=False)
    report["output_tables"] = catalog
    lines = ["# Environmental pipeline run", "", f"**Run kind:** `{report['run_kind']}`",
             f"**Data basis:** {report['data_basis']}", "", f"Candidates: **{report['candidates']}**.", ""]
    if report.get("product_mode") or report.get("run_kind") == "environment_comparison":
        lines += ["## Primary result — existing-data environmental comparison", "",
                  ("Open **[environmental_rankings.csv](environmental_rankings.csv)** for complete scores and "
                   "**[environmental_top_k.csv](environmental_top_k.csv)** for the top-k."
                   if report["environmental_top_k_returned"] else
                   "No candidate currently has a supported score after the configured filters. See **candidate_status.csv** and the exclusion/coverage explanations; no empty ranking is fabricated."), "",
                  f"Comparison outcomes: **{report['environmental_comparison_statuses']}**; "
                  f"top-k returned: **{report['environmental_top_k_returned']}**.", "",
                  "Existing solar/Earth visibility preferences and slope context filters are used exactly as configured. "
                  "They are exploratory comparisons, NOT mission safety limits or equipment adequacy.",
                  "See `soft_preference_results.csv` for factor utilities/weights and `feature_usage.csv` for support and which factors are not scored.", ""]
    if report.get("product_mode"):
        lines += ["`candidate_status.csv` accounts for every input candidate; `excluded_candidates.csv` explains those not ranked.",
                  "`environment_evidence.csv` contains supported real values only. Missing coverage is counted in `feature_usage.csv`, not filled with numbers.",
                  "`thermal_profiles.csv`, when available, contains complete common-phase temperature profiles; it is not an equipment-response model.", ""]
    if report.get("stage3_assessment_requested", True):
        lines += ["## Separate Stage 3 readiness (not the environmental ranking)", "",
              f"Stage 3 states: **{report['stage3_statuses']}**; configured operational top-k: **{report['stage3_top_k_returned']}**.",
              f"Legacy diagnostic/context filters: **{report['gate_statuses']}**; diagnostic top-k: **{report['top_k_returned']}**.", ""]
    else:
        lines += ["**Mission/equipment qualification is not requested in this run.** No equipment is assumed adequate. "
                  "Use `--stage3` or supply `--mission-profile` to request that separate assessment.", ""]
    if report["is_synthetic"]:
        lines += ["**SYNTHETIC SOFTWARE TEST ONLY. No measured base sites, real equipment limits or mission-safety recommendation.**", ""]
    elif report.get("stage3_assessment_requested", True):
        lines += ["Stage 3 Unknown is not a failed site and does not mean every environmental measurement is missing.", ""]
    if report["profile_missing_inputs"]:
        lines += ["## Why operational results are Unknown", "",
                  *[f"- Missing: {name}" for name in report["profile_missing_inputs"]], ""]
    if report.get("stage3_assessment_requested", True):
        lines += ["See `candidate_readiness.csv` and `requirement_readiness.csv` for operational evidence gaps.", ""]
    if report.get("evidence_rules"):
        lines += ["## Evidence-backed rule explanations and new EDA", "",
                  "Open **[conditions -> rules -> candidate explanations](evidence_context/EVIDENCE_DECISIONS.md)**.",
                  "The register distinguishes sourced conditional requirements, historical references, evidence-use guards and exploratory comparison settings.",
                  "Evidence-use Failed rejects an unsupported inference, not the physical site. New orbital/global/reference-point data is not added to candidate scores or operational passes.", ""]
    lines += ["## Output tables", "", "CSV row 1 contains column headers. Empty optional products are not written in the default run.", "",
              "| File | Title | Rows | Explanation |", "| --- | --- | ---: | --- |"]
    lines += [f"| {r['file'] if r['status'] == 'omitted_empty' else '['+r['file']+']('+r['file']+')'} | {r['title']} | {r['rows']} | {r['reason']} |" for r in catalog]
    lines += ["", "Missing mandatory evidence is never replaced with a proxy pass. Diagnostic weights/thresholds are illustrative, not approved mission criteria.", ""]
    atomic_text(run.path("RUN_SUMMARY.md"), "\n".join(lines))


def publish_latest_results(directory, report):
    """One stable entry point; never deletes or promotes older/synthetic runs."""
    relative = directory.relative_to(OUTPUTS).as_posix()
    top = pd.read_csv(directory/"environmental_top_k.csv") if (directory/"environmental_top_k.csv").is_file() else None
    lines = ["# Latest environmental results", "", f"**Successful run:** `{directory.name}`", "",
             "Real existing EDA only; no assumed mission/equipment inputs.", "",
             f"Candidates assessed: **{report['candidates']}**. Results: **{report['environmental_comparison_statuses']}**.",
             "Score range: **0–1**; higher is preferred under the declared comparison policy, not a safety probability.", ""]
    if top is not None:
        lines += ["| Rank | Candidate | Environmental score |", "| ---: | --- | ---: |"]
        lines += [f"| {int(r.environmental_rank)} | {r.candidate_id} | {r.environmental_score:.5f} |"
                  for r in top.itertuples()]
    lines += ["", f"[Open this run's full results and factor explanations]({relative}/RUN_SUMMARY.md)", "",
              "Excluded candidates remain accounted for. Missing coverage is reported, not filled or passed.",
              "Historical runs are retained separately; their old readiness/empty exports are not current product outputs.", ""]
    if report.get("evidence_rules"):
        lines += [f"[New EDA, rule provenance and candidate explanations]({relative}/evidence_context/EVIDENCE_DECISIONS.md)", ""]
    atomic_text(OUTPUTS/"LATEST_RESULTS.md", "\n".join(lines))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("environment_experiment.json"))
    parser.add_argument("--policy", type=Path, help="Override the configured environmental comparison policy")
    parser.add_argument("--mission-profile", type=Path, help="Documented Stage 3 mission/equipment/requirements/evidence JSON; default is a blank template")
    parser.add_argument("--sample", action="store_true", help="Run ten explicit synthetic cases; no real EDA/mission inputs are substituted")
    parser.add_argument("--evidence-only", action="store_true", help="Explicit legacy readiness-only run; no context scoring")
    parser.add_argument("--stage3", action="store_true", help="Explicitly request operational readiness/requirements assessment")
    parser.add_argument("--audit", action="store_true", help="Include full legacy/intermediate tables under audit/ for a comparison run")
    args = parser.parse_args(argv)
    if args.sample and (args.policy or args.mission_profile or args.evidence_only or args.stage3
                        or args.config.resolve() != (PIPELINE / "environment_experiment.json").resolve()):
        parser.error("--sample is an isolated fictional experiment; do not combine it with a real policy/profile")
    if args.evidence_only and args.policy:
        parser.error("--evidence-only cannot be combined with a scoring-policy override")
    selected_kind, policy_path = None, args.policy
    if args.sample:
        config = {"policy": json.loads((PIPELINE / "diagnostic_policy.json").read_text(encoding="utf-8")),
                  "sample_fixture": str(SAMPLE_FIXTURE), "data_basis": "synthetic_fixture_only"}
    else:
        config = json.loads(args.config.read_text(encoding="utf-8"))
        if args.policy:
            config["policy"] = json.loads(args.policy.read_text(encoding="utf-8"))
        elif not args.evidence_only and config.get("comparison_policy"):
            policy_path = (args.config.parent / config["comparison_policy"]).resolve()
            config["policy"] = json.loads(policy_path.read_text(encoding="utf-8"))
            selected_kind = "environment_comparison"
    validate_policy(config["policy"])
    stage3_requested = bool(args.sample or args.stage3 or args.mission_profile or args.evidence_only)
    product_mode = not stage3_requested and config["policy"]["mode"] == "diagnostic"
    profile_path = args.mission_profile or Path(__file__).with_name("mission_profile_template.json")
    profile = {} if args.sample else json.loads(profile_path.read_text(encoding="utf-8")) if stage3_requested else None
    kind = "synthetic_demo" if args.sample else selected_kind or config["policy"]["mode"]
    with PrototypeRun(config, kind) as run:
        run.input(Path(stage3_assessment.__file__))
        if not args.sample:
            if stage3_requested:
                run.input(profile_path)
            run.input(args.config)
            if policy_path:
                run.input(policy_path)
        # Record the original pattern being followed without executing/training it.
        for name in ["similarity_experiment.py", "terrain_learning.py"]:
            run.input(ROOT / "notebooks/modeling/terrain_similarity" / name)
        run.input(LOCAL / "purposal.md")
        run.input(LOCAL / "EDA/decision_eda.py")
        run.input(ROOT / "notebooks/shared/inspection.py")
        if args.sample:
            candidates, evidence, context, static, support, profile = load_sample_fixture(run)
            evidence_root = PIPELINE
        else:
            candidates, evidence, context, static, support = load_evidence(run, config)
            evidence_root = LOCAL / "data"
        # Required Stage 3 EDA is consumed as traceable context, not new rule passes.
        for source_key, source_config in (config.get("stage3_analysis", {}) if stage3_requested or args.audit else {}).items():
            folder = (LOCAL / "data" / source_config["run"]).resolve()
            allowed = [LOCAL / "data/processed/analysis", LOCAL / "data/processed/lunar_terrain_views"]
            if not any(folder.is_relative_to(base.resolve()) for base in allowed):
                raise ValueError("Stage 3 analysis input escapes approved local output roots")
            for name in source_config["files"]:
                table = pd.read_csv(accepted_input(run, folder, name))
                table.to_csv(run.path("stage3_evidence/" + source_key + "/" + name), index=False)
        summary, checks, utilities, top = evaluate(candidates, evidence, config["policy"])
        if stage3_requested:
            summary, operational, operational_checks, operational_utilities, operational_top, readiness, requirement_readiness = operational_outputs(
                candidates, evidence, summary, profile, evidence_root, config["policy"]["top_k"], run)
        environmental_ranking, environmental_top, feature_usage = environmental_tables(summary, evidence, checks, config["policy"])
        sample_verification = None
        if args.sample:
            sample_verification = summary[["candidate_id", "scenario", "data_basis", "expected_stage3_status",
                "stage3_status", "expected_diagnostic_status", "gate_status"]].copy()
            sample_verification["matches_expected"] = (
                sample_verification.stage3_status.eq(sample_verification.expected_stage3_status)
                & sample_verification.gate_status.eq(sample_verification.expected_diagnostic_status))
            if not sample_verification.matches_expected.all():
                raise AssertionError("Synthetic pipeline outcomes differ from the declared fixture expectations")
        stage_counts = pd.DataFrame([
            {"stage": "verified_candidate_input", "candidates": len(candidates)},
            {"stage": "hard_pass", "candidates": int(summary.gate_status.eq("pass").sum())},
            {"stage": "hard_fail", "candidates": int(summary.gate_status.eq("fail").sum())},
            {"stage": "hard_unknown", "candidates": int(summary.gate_status.eq("unknown").sum())},
            {"stage": "hard_unconfigured", "candidates": int(summary.gate_status.eq("unconfigured").sum())},
            {"stage": "complete_soft_scores", "candidates": int(summary.diagnostic_preference_score.notna().sum())},
            {"stage": "recommended_top_k", "candidates": len(top)},
        ])
        if stage3_requested:
            stage_counts = pd.concat([stage_counts, pd.DataFrame([
                {"stage": "stage3_"+state, "candidates": int(summary.stage3_status.eq(state).sum())}
                for state in ("pass", "fail", "unknown")]+[
                {"stage": "stage3_recommended_top_k", "candidates": len(operational_top)}])], ignore_index=True)
        report = {"mode": config["policy"]["mode"], "candidates": len(candidates),
            "run_kind": kind, "is_synthetic": args.sample,
            "data_basis": "synthetic_fixture_only" if args.sample else "pinned_measured_eda_with_qualified_context",
            "profile_missing_inputs": stage3_assessment.profile_readiness(profile) if stage3_requested else [],
            "stage3_assessment_requested": stage3_requested,
            "product_mode": product_mode,
            "available_evidence_records": int(evidence.status.eq("observed").sum()),
            "primary_result": "environmental_rankings.csv" if product_mode or kind == "environment_comparison" else "candidate_assessments.csv",
            "environmental_comparison_statuses": environmental_ranking.comparison_status.value_counts().to_dict(),
            "environmental_top_k_returned": len(environmental_top),
            "comparison_policy_file": str(policy_path.relative_to(ROOT)) if policy_path and policy_path.is_relative_to(ROOT) else str(policy_path) if policy_path else None,
            "sample_verification_passed": bool(sample_verification.matches_expected.all()) if args.sample else None,
            "pipeline_stages": ["verified_evidence", "eligibility", "scoring", "recommendations", "inspection"],
            "gate_statuses": summary.gate_status.value_counts().to_dict(),
            "diagnostic_ranked_candidates": int(summary.diagnostic_preference_score.notna().sum()),
            "top_k_returned": len(top), "operational_suitability_assessed": bool(stage3_requested and not args.sample and operational_checks.margin.notna().any()),
            "margin_calculations_executed": bool(stage3_requested and operational_checks.margin.notna().any()),
            "mission_profile_origin": "not_requested" if not stage3_requested else "synthetic_fixture" if args.sample else "supplied" if args.mission_profile else "blank_template",
            "preliminary_model_only": True, "certified_suitability": False,
            "stage3_statuses": operational.stage3_status.value_counts().to_dict() if stage3_requested else {},
            "stage3_top_k_returned": len(operational_top) if stage3_requested else 0,
            "mission_profile_supplied": args.mission_profile is not None,
            "golden_target": "outline Stage 3: mission/equipment adequacy, operating margins, failed and uncertain requirements",
            "holds": (["Entire scenario, candidate data, capability values and limits are synthetic software-test inputs",
                       "Expected labels are compared only AFTER evaluation; never used to calculate rule outcomes",
                       "Five declared fixture requirements do not constitute a real complete mission inventory"] if args.sample else ["Purposive EDA components, not CNN patch identities or validated base footprints",
                      "Candidate selection already used proxy solar/Earth/slope conditions: not independent validation",
                      "Fixed-common phase summaries are not chronological extremes or equipment response",
                      "Mean visibility is not dated power/contact continuity",
                      "Image/CPR context, missingness and source support are not scoring rewards",
                      "No trained environmental CNN, suitability labels, calibrated weights or safe-site claim"])}
        if product_mode and environmental_top.empty:
            report["primary_result"] = "candidate_status.csv"
        no_proxy_preferences = "No diagnostic soft preferences configured" if not config["policy"]["soft_preferences"] else "No candidate rows available"
        no_operational_preferences = "No operational soft preferences configured" if not (profile or {}).get("soft_preferences") else "No candidate rows available"
        tables = [
            ("environmental_rankings.csv", "Existing-data environmental comparison; NOT operational eligibility", environmental_ranking, "No candidate comparisons"),
            ("environmental_top_k.csv", "Top environmental context comparisons", environmental_top, "No candidate has both passing configured context filters and a complete declared preference score"),
            ("feature_usage.csv", "Which existing environmental evidence is scored, filtered or context-only", feature_usage, "No environmental metrics provided"),
            ("candidate_manifest.csv", "Candidate identities and scope", candidates, "No candidates; unexpected for this experiment"),
            ("environment_evidence.csv", "Qualified environmental evidence", evidence, "No evidence; inspect source configuration"),
            ("image_radar_context.csv", "Image/radar context only", context, "Not simulated by the synthetic fixture; no fabricated image/radar observations"),
            ("candidate_assessments.csv", "All candidate assessments, including Unknown", summary, "No candidate assessments"),
            ("static_source_support.csv", "Static-map support (or explicit synthetic values)", static, "No static evidence supplied"),
            ("thermal_association_support.csv", "Real thermal association support", support, "Not simulated by the synthetic fixture; no fabricated phase/terrain association"),
            ("hard_rule_results.csv", "Diagnostic/evidence-only hard checks", checks, "No hard rules configured"),
            ("soft_preference_results.csv", "Diagnostic preference details", utilities, no_proxy_preferences),
            ("diagnostic_top_k.csv", "Diagnostic ranking, NOT operational eligibility", top, "No candidates with passed diagnostic gates AND a complete configured preference score"),
            ("pipeline_stage_counts.csv", "Separate diagnostic and Stage 3 funnels", stage_counts, "No pipeline stages"),
        ]
        if stage3_requested:
            tables += [
                ("stage3_operational_checks.csv", "Stage 3 requirements and margins", operational_checks, "No operational check rows"),
                ("stage3_preference_details.csv", "Configured Stage 3 preference details", operational_utilities, no_operational_preferences),
                ("stage3_top_k.csv", "Gate-first configured Stage 3 ranking", operational_top, "No candidates with all mandatory checks passed and complete preference data"),
                ("candidate_readiness.csv", "Candidate-specific evidence/profile readiness", readiness, "No candidate readiness rows"),
                ("requirement_readiness.csv", "Requirement states and reasons", requirement_readiness, "No requirement checks"),
            ]
        if sample_verification is not None:
            tables.append(("sample_verification.csv", "Synthetic expected-versus-actual outcomes", sample_verification, "Fixture verification unexpectedly absent"))
        if product_mode:
            if args.audit:
                audit_catalog = []
                for n, title, frame, reason in tables:
                    frame.to_csv(run.path("audit/"+n), index=False)
                    audit_catalog.append({"file": n, "title": title, "rows": len(frame), "reason": reason if frame.empty else "Full audit rows"})
                pd.DataFrame(audit_catalog).to_csv(run.path("audit/output_catalog.csv"), index=False)
            tables = product_tables(environmental_ranking, evidence, checks, utilities, feature_usage, config["policy"]["top_k"])
        if not args.sample and config.get("evidence_rules_manifest"):
            extra_tables, report["evidence_rules"] = evidence_rules.products(
                run, config["evidence_rules_manifest"], candidates, evidence, config["policy"],
                policy_path or args.config, checks, environmental_ranking)
            tables += extra_tables
        export_tables(run, tables, report, omit_empty=product_mode)
        atomic_text(run.path("report.json"), json.dumps(report, indent=2) + "\n")
    if product_mode:
        publish_latest_results(run.directory, report)
    if product_mode or kind == "environment_comparison":
        print("Existing-data environmental comparison (not mission/equipment adequacy)")
        print(json.dumps({key: report[key] for key in ["run_kind", "data_basis", "candidates", "primary_result",
            "environmental_comparison_statuses", "environmental_top_k_returned", "comparison_policy_file"]}, indent=2))
        if stage3_requested:
            print("Stage 3 readiness was explicitly requested; see requirement_readiness.csv.")
        else:
            print("Equipment/mission assessment not requested. Use --stage3 or --mission-profile only when needed.")
    else:
        print(json.dumps({key: value for key, value in report.items() if key != "output_tables"}, indent=2))
    print("Outputs:", run.directory)
    print("Readable summary:", run.directory / "RUN_SUMMARY.md")
    if product_mode:
        print("Start here:", OUTPUTS / "LATEST_RESULTS.md")
        if not environmental_top.empty:
            print(environmental_top[["environmental_rank", "candidate_id", "environmental_score"]].to_string(
                index=False, formatters={"environmental_score": lambda value: f"{value:.5f}"}))
        else:
            print("No rankable candidates under the configured criteria; see candidate_status.csv.")
    return run.directory


if __name__ == "__main__":
    main()
