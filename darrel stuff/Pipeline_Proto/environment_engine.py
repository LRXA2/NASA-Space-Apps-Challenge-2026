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
sys.path[:0] = [str(LOCAL / "EDA"), str(LOCAL), str(ROOT)]
from data_maintenance import atomic_text
from decision_eda import accepted_input
from environment_workflow import LocalRun
from notebooks.shared.processing import Run
import stage3_assessment

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
    def __init__(self, config):
        self.project_root = ROOT.resolve()
        Run.__init__(self, LOCAL, "env_cnn_prototype", config, "")
        self.notebook = Path(__file__).resolve()


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


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=Path(__file__).with_name("environment_experiment.json"))
    parser.add_argument("--policy", type=Path, help="Optional explicit diagnostic policy; default is evidence-only")
    parser.add_argument("--mission-profile", type=Path, help="Documented Stage 3 mission/equipment/requirements/evidence JSON; default is a blank template")
    args = parser.parse_args(argv)
    config = json.loads(args.config.read_text(encoding="utf-8"))
    if args.policy:
        config["policy"] = json.loads(args.policy.read_text(encoding="utf-8"))
    validate_policy(config["policy"])
    profile_path = args.mission_profile or Path(__file__).with_name("mission_profile_template.json")
    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    with PrototypeRun(config) as run:
        run.input(profile_path)
        run.input(Path(stage3_assessment.__file__))
        run.input(args.config)
        if args.policy:
            run.input(args.policy)
        # Record the original pattern being followed without executing/training it.
        for name in ["similarity_experiment.py", "terrain_learning.py"]:
            run.input(ROOT / "notebooks/modeling/terrain_similarity" / name)
        run.input(LOCAL / "purposal.md")
        run.input(LOCAL / "EDA/decision_eda.py")
        run.input(ROOT / "notebooks/shared/inspection.py")
        candidates, evidence, context, static, support = load_evidence(run, config)
        # Required Stage 3 EDA is consumed as traceable context, not new rule passes.
        for source_key, source_config in config.get("stage3_analysis", {}).items():
            folder = (LOCAL / "data" / source_config["run"]).resolve()
            allowed = [LOCAL / "data/processed/analysis", LOCAL / "data/processed/lunar_terrain_views"]
            if not any(folder.is_relative_to(base.resolve()) for base in allowed):
                raise ValueError("Stage 3 analysis input escapes approved local output roots")
            for name in source_config["files"]:
                table = pd.read_csv(accepted_input(run, folder, name))
                table.to_csv(run.path("stage3_evidence/" + source_key + "/" + name), index=False)
        summary, checks, utilities, top = evaluate(candidates, evidence, config["policy"])
        operational, operational_checks = stage3_assessment.assess(candidates, profile, LOCAL / "data", run)
        summary = summary.merge(operational, on="candidate_id", validate="one_to_one")
        summary["operational_status"] = summary.stage3_status
        # Keep proxy demonstrations separate: never label their passes operational.
        preference_policy = {"schema": 1, "mode": "diagnostic", "top_k": config["policy"]["top_k"],
                             "hard_rules": [], "soft_preferences": profile.get("soft_preferences", [])}
        gates = operational[["candidate_id", "stage3_status"]].rename(columns={"stage3_status": "gate_status"})
        operational_scores, operational_utilities = run_scoring(gates, evidence, preference_policy)
        summary = summary.merge(operational_scores[["candidate_id", "diagnostic_preference_score"]].rename(
            columns={"diagnostic_preference_score": "operational_preference_score"}), on="candidate_id", validate="one_to_one")
        summary["operational_ranking_status"] = np.where(summary.operational_preference_score.notna(),
            "configured_preference_only_not_certification", "not_ranked")
        ranking_input = summary.drop(columns=["diagnostic_preference_score", "gate_status"]).rename(
            columns={"operational_preference_score": "diagnostic_preference_score", "stage3_status": "gate_status"})
        operational_top = run_recommendations(ranking_input, config["policy"]["top_k"]).rename(
            columns={"diagnostic_preference_score": "operational_preference_score", "diagnostic_rank": "configured_preference_rank"})
        operational_top["ranking_status"] = "configured_preference_only_not_certification"
        for name, frame in [("candidate_manifest.csv", candidates), ("environment_evidence.csv", evidence),
            ("image_radar_context.csv", context), ("candidate_assessments.csv", summary),
            ("static_source_support.csv", static), ("thermal_association_support.csv", support),
            ("hard_rule_results.csv", checks), ("soft_preference_results.csv", utilities), ("diagnostic_top_k.csv", top)]:
            frame.to_csv(run.path(name), index=False)
        operational_checks.to_csv(run.path("stage3_operational_checks.csv"), index=False)
        operational_utilities.to_csv(run.path("stage3_preference_details.csv"), index=False)
        operational_top.to_csv(run.path("stage3_top_k.csv"), index=False)
        stage_counts = pd.DataFrame([
            {"stage": "verified_candidate_input", "candidates": len(candidates)},
            {"stage": "hard_pass", "candidates": int(summary.gate_status.eq("pass").sum())},
            {"stage": "hard_fail", "candidates": int(summary.gate_status.eq("fail").sum())},
            {"stage": "hard_unknown", "candidates": int(summary.gate_status.eq("unknown").sum())},
            {"stage": "hard_unconfigured", "candidates": int(summary.gate_status.eq("unconfigured").sum())},
            {"stage": "complete_soft_scores", "candidates": int(summary.diagnostic_preference_score.notna().sum())},
            {"stage": "recommended_top_k", "candidates": len(top)},
        ])
        stage_counts.to_csv(run.path("pipeline_stage_counts.csv"), index=False)
        report = {"mode": config["policy"]["mode"], "candidates": len(candidates),
            "pipeline_stages": ["verified_evidence", "eligibility", "scoring", "recommendations", "inspection"],
            "gate_statuses": summary.gate_status.value_counts().to_dict(),
            "diagnostic_ranked_candidates": int(summary.diagnostic_preference_score.notna().sum()),
            "top_k_returned": len(top), "operational_suitability_assessed": bool(operational_checks.margin.notna().any()),
            "preliminary_model_only": True, "certified_suitability": False,
            "stage3_statuses": operational.stage3_status.value_counts().to_dict(),
            "stage3_top_k_returned": len(operational_top),
            "mission_profile_supplied": args.mission_profile is not None,
            "golden_target": "outline Stage 3: mission/equipment adequacy, operating margins, failed and uncertain requirements",
            "holds": ["Purposive EDA components, not CNN patch identities or validated base footprints",
                      "Candidate selection already used proxy solar/Earth/slope conditions: not independent validation",
                      "Fixed-common phase summaries are not chronological extremes or equipment response",
                      "Mean visibility is not dated power/contact continuity",
                      "Image/CPR context, missingness and source support are not scoring rewards",
                      "No trained environmental CNN, suitability labels, calibrated weights or safe-site claim"]}
        atomic_text(run.path("report.json"), json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    print("Outputs:", run.directory)
    return run.directory


if __name__ == "__main__":
    main()
