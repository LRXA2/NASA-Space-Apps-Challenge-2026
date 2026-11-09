"""Step 4/5 evidence-use rules and explanations, separate from site eligibility.

No mission defaults, physical safety thresholds or new ranking factors.
"""
from pathlib import Path
import json

import numpy as np
import pandas as pd

from decision_eda import accepted_input
from data_maintenance import atomic_text

PIPELINE = Path(__file__).resolve().parent
LOCAL = PIPELINE.parent
ROLES = {"evidence_guard", "conditional_requirement", "historical_reference", "planetary_baseline"}


def local_file(relative):
    path = (PIPELINE / relative).resolve()
    if not path.is_relative_to(LOCAL.resolve()):
        raise ValueError("Evidence-rule configuration escapes Darrel's workspace")
    return path


def validate_register(register):
    if register.get("schema") != 1 or not register.get("rules"):
        raise ValueError("Expected a nonempty schema-1 evidence register")
    seen = set()
    fields = ["id", "title", "research_ids", "source", "applicability", "required_inputs", "effect", "evaluator", "authority"]
    for row in register["rules"]:
        if any(not isinstance(row.get(k), str) or not row[k].strip() for k in fields):
            raise ValueError("Rule lacks identity, provenance, applicability or explanation")
        if row["id"] in seen or row.get("role") not in ROLES:
            raise ValueError("Duplicate rule or unsupported classification")
        if row.get("limit_state") != "not_adopted" or "limit" in row or "weight" in row:
            raise ValueError("This register cannot invent physical limits or preference weights")
        seen.add(row["id"])


def compile_register(register, policy, policy_source):
    """Compile the actual configured comparison settings, including overrides."""
    validate_register(register)
    rows = [dict(row, metric="not_configured", operator="not_applicable", limit="not_adopted",
                 weight="not_applicable", lower="not_applicable", upper="not_applicable",
                 unit="requirement_specific", scope="see_applicability")
            for row in register["rules"]]
    for kind, field in [("comparison_filter", "hard_rules"), ("comparison_preference", "soft_preferences")]:
        for item in policy[field]:
            metric = item.get("metric")
            role = kind if metric is not None else "optional_requirement_placeholder"
            rows.append({"id": kind+"::"+item["id"], "title": item["id"], "role": role,
                "research_ids": "D02 D03 D05 D06" if metric else "mission_specific",
                "source": str(policy_source), "applicability": item.get("scope", "not_configured"),
                "required_inputs": metric or "; ".join(item["missing_inputs"]), "effect": item["reason"],
                "evaluator": "existing_run_eligibility" if kind == "comparison_filter" else "existing_run_scoring",
                "limit_state": "illustrative_not_operational" if metric else "not_adopted",
                "authority": "active exploratory policy, NOT a NASA operational requirement",
                "metric": metric or "not_configured", "unit": item.get("unit", "not_configured"),
                "scope": item.get("scope", "not_configured"), "operator": item.get("operator", item.get("direction", "not_applicable")),
                "limit": item.get("limit", "not_applicable"), "weight": item.get("weight", "not_applicable"),
                "lower": item.get("lower", "not_applicable"), "upper": item.get("upper", "not_applicable")})
    return pd.DataFrame(rows)


def load_bundle(run, manifest_name):
    manifest_path = local_file(manifest_name)
    run.input(Path(__file__))
    run.input(manifest_path)
    for source_document in [LOCAL/"research/Research_Notes.md", LOCAL/"research/environmental_data.csv",
                            LOCAL.parent/"outline.md"]:
        run.input(source_document)
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != 1:
        raise ValueError("Unsupported evidence-rule manifest")
    register_path = local_file(manifest["register"])
    run.input(register_path)
    register = json.loads(register_path.read_text(encoding="utf-8"))
    validate_register(register)
    frames, catalog = {}, []
    root = (LOCAL/"data/processed/analysis").resolve()
    for key, source in manifest["sources"].items():
        scope_fields = ["basis", "spatial_scope", "temporal_scope", "quantity_class"]
        if any(not isinstance(source.get(field), str) or not source[field].strip() for field in scope_fields):
            raise ValueError("Source lacks explicit observed/modelled, spatial, temporal or quantity meaning")
        folder = (root/source["run"]).resolve()
        if not folder.is_relative_to(root):
            raise ValueError("Evidence source escapes accepted analysis root")
        for name in source["files"]:
            identity = key+"/"+name
            if identity in frames:
                raise ValueError("Repeated evidence source identity")
            path = accepted_input(run, folder, name)
            frame = pd.read_csv(path)
            frames[identity] = frame
            catalog.append({"source_id": identity, "run": source["run"], "rows": len(frame),
                "path": str(path.relative_to(LOCAL)),
                "sha256": run.record["inputs"][str(path.relative_to(run.project_root))]["sha256"],
                **{field: source[field] for field in scope_fields},
                "permitted_use": "declared_context_only_not_candidate_operation"})
    return register, frames, pd.DataFrame(catalog)


def evidence_use_checks(frames):
    """Tri-state checks about evidence USE, never physical site safety verdicts."""
    thermal = frames["dated_thermal/dated_thermal_support.csv"]
    apollo = frames["apollo/primary_resource_changes.csv"]
    observer = frames["geometry/reference_observers.csv"]
    geometry = frames["geometry/terrain_geometry_summary.csv"]
    if observer.region.duplicated().any() or not set(geometry.region) <= set(observer.region):
        raise ValueError("Ambiguous or missing reference observer identity")
    if "candidate_id" in observer or "candidate_id" in geometry:
        raise ValueError("Reference-point geometry must not be relabelled candidate measurements")
    if not np.allclose(apollo.actual_remaining-apollo.reported_actual_redline,
                       apollo.historical_remaining_minus_source_redline, atol=1e-10, rtol=0):
        raise ValueError("Historical headroom arithmetic disagrees with accepted source")
    strict = int(thermal.strict_rows.sum())
    rows = [
        ("E03", "qualified_dated_thermal_history", "Failed" if strict == 0 else "Unknown", str(strict), "strict observations",
         "No strict observations in this frozen cohort" if strict == 0 else "Some strict observations alone do not establish footprint/period/response coverage",
         "dated_thermal", "Withhold candidate thermal adequacy; preserve flagged diagnostics separately"),
        ("E02", "surface_phase_to_component_response", "Failed", "surface/phase temperature", "quantity/scope",
         "No component thermal-response measurement or applicable operating window supplied by these sources",
         "existing_candidate_thermal", "Keep existing phase profiles as context, not equipment limits"),
        ("E04", "orbital_data_to_shielded_dose", "Failed", "SEC counters / directional proton flux", "quantity/scope",
         "Orbital quantities and published scenarios are not local transported crew/electronics exposure",
         "annual_radiation", "Do not infer a radiation safety threshold or candidate score"),
        ("E05", "reference_point_to_component_history", "Failed", "ROI-center target-center geometry", "spatial/model scope",
         "Finite range, declared 2020 windows and reference points are not validated component power/contact histories",
         "geometry", "Retain regional reference coordinates and sensitivity; do not promote to candidate measurements"),
        ("E06", "historical_reserve_arithmetic", "Passed", str(len(apollo)), "historical records",
         "Remaining minus source redline reproduces accepted history in original lb/Ah; not current equipment adequacy",
         "apollo", "Historical comparison only; zero at source rounding is not robust positive reserve"),
        ("E06", "historical_limit_to_new_configuration", "Failed", "Apollo configuration only", "applicability",
         "No applicable modern mission/equipment identity established; Ah is not Wh",
         "apollo", "Do not adopt historical redlines, stocks or crew as defaults"),
        ("E08", "catalog_to_local_event_probability", "Failed", "related catalogs / selected crater detections", "event support",
         "Independence, observation effort, dates and local vulnerability are not established",
         "events", "Keep seismic/impact concerns unresolved, not zero-risk estimates"),
        ("E09", "indirect_indicator_to_resources_or_strength", "Failed", "terrain/image/radar/reference context", "quantity/scope",
         "No verified local extractability, stocks, bearing capacity or traction follows from these proxies",
         "existing_candidate_context", "Do not credit essential supplies or load/mobility capacity"),
    ]
    result = pd.DataFrame(rows, columns=["rule_id", "check_id", "data_use_status", "observed_basis", "unit_or_scope",
                                         "reason", "source_group", "consequence"])
    result["assessment_domain"] = "evidence_use_NOT_site_safety"
    result["candidate_operational_conclusion_from_these_sources"] = "Unknown"
    return result


def findings_table(frames):
    rows = []
    def add(id, value, unit, scope, effect, source):
        rows.append({"finding": id, "value": value, "unit": unit, "scope": scope, "decision_implication": effect, "source_id": source})
    apollo = frames["apollo/primary_resource_changes.csv"]
    add("actual_consumption_above_prediction", int(apollo.consumed_minus_predicted.gt(0).sum()), "of "+str(len(apollo))+" historical records",
        "Apollo 17 EMU Table 9-II only", "Prediction is not guaranteed adequacy; no modern limit adopted", "apollo/primary_resource_changes.csv")
    for resource, g in apollo.groupby("resource"):
        if g.unit.nunique() != 1:
            raise ValueError("Mixed units in historical resource")
        add("minimum_historical_headroom::"+resource, g.historical_remaining_minus_source_redline.min(), g.unit.iloc[0],
            "historical source remaining minus redline", "Not an actual configured mission margin", "apollo/primary_resource_changes.csv")
    thermal = frames["dated_thermal/dated_thermal_support.csv"]
    add("dated_thermal_strict_observations", int(thermal.strict_rows.sum()), "channel observations", "one regional frozen sample, channels 3/4",
        "No qualified mission temperature series inferred", "dated_thermal/dated_thermal_support.csv")
    crater = frames["annual_radiation/refreshed_crater_daily_context.csv"]
    goes = frames["annual_radiation/refreshed_goes_daily_directional_support.csv"]
    for name, f in [("CRaTER", crater), ("GOES16", goes)]:
        add(name+"_completed_dates", f.date.nunique(), "UTC dates", f.date.min()+" to "+f.date.max(),
            "Date span is not usable exposure coverage or a two-year event census", "annual_radiation")
    add("CRaTER_SEC_records", int(crater.records.sum()), "SEC records", "orbital counter context",
        "Counters are not surface/shielded crew dose", "annual_radiation/refreshed_crater_daily_context.csv")
    add("GOES_qualified_channel_time_fraction", goes.qualified_bins.sum()/goes.recorded_bins.sum(), "fraction", "two directions and thirteen separate energy bands",
        "No filling unqualified intervals; no crew-dose conversion", "annual_radiation/refreshed_goes_daily_directional_support.csv")
    for kind, name in [("CRaTER", "refreshed_crater_missing_dates.csv"), ("GOES16", "refreshed_goes_missing_dates.csv")]:
        add(kind+"_missing_dates", len(frames["annual_radiation/"+name]), "calendar dates", "between first and last completed dates",
            "Missing dates are not zero exposure", "annual_radiation/"+name)
    geo = frames["geometry/terrain_geometry_summary.csv"]
    add("reference_geometry_rows", len(geo), "reference scenario summaries", "ROI-center points; height/range/window/target axes",
        "Not candidate solar generation or communications service", "geometry/terrain_geometry_summary.csv")
    events = frames["events/seismic_evidence_context.csv"]
    add("seismic_catalog_entries", events.catalog_entries.sum(), "entries across related catalogs", "not independent events",
        "No local recurrence or structural risk probability", "events/seismic_evidence_context.csv")
    add("selected_new_crater_detections", len(frames["events/impact_evidence_context.csv"]), "selected detections", "no effort/time-normalized site rate",
        "No local impact probability or safe-site pass", "events/impact_evidence_context.csv")
    return pd.DataFrame(rows)


def candidate_limits(candidates, hazards):
    if candidates.candidate_id.duplicated().any() or hazards.hazard.duplicated().any():
        raise ValueError("Duplicate candidate/hazard identity")
    rows = []
    for item in candidates.itertuples():
        for hazard in hazards.itertuples():
            rows.append({"candidate_id": item.candidate_id, "region": item.region, "hazard": hazard.hazard,
                "evidence_scope": "bundled_context_not_candidate_validated_response", "candidate_specific_conclusion": "Unknown",
                "available_evidence": hazard.available_evidence, "limitation": hazard.essential_limitations,
                "use": "not_scored_not_an_operational_verdict", "risk_principle": hazard.risk_principle_not_implemented_rule})
    return pd.DataFrame(rows)


def explain_checks(checks):
    result = checks.copy()
    value = pd.to_numeric(result.value, errors="raise")
    limit = pd.to_numeric(result.limit, errors="raise")
    result["comparison_filter_distance"] = np.where(
        result.operator.eq("ge"), value-limit,
        np.where(result.operator.eq("le"), limit-value, np.nan))
    result["distance_kind"] = "exploratory_threshold_distance_NOT_operating_margin"
    result["assessment_domain"] = "exploratory_comparison_NOT_operational"
    result["register_id"] = "comparison_filter::"+result.rule_id
    return result


def write_explanations(run, ranking, evidence, checks, frames):
    lines = ["# Lunar conditions -> explained rules -> candidate comparisons", "",
        "**Mission/equipment inputs are optional.** These are existing-data context comparisons, not mission eligibility.",
        "The unchanged visibility/slope policy is exploratory. New global, historical and reference-point evidence is NOT added to scores or promoted into component measurements.", "",
        "## What the new evidence changes", "",
        "- Apollo prediction deviations/reserves motivate contingency/uncertainty handling, not modern defaults.",
        "- Year-plus CRaTER/GOES observations show coverage and variability; counters/flux are not candidate crew dose.",
        "- Zero strict dated thermal observations blocks using this cohort as a qualified operational thermal history.",
        "- Finite ROI-center Sun/Earth geometry demonstrates height/range/sampling sensitivity, not continuous darkness, power endurance or a working link.",
        "- Event/resource/soil proxies do not establish local probabilities, usable stocks or mechanical capability.", "",
        "[Rule register](rule_register.csv) | [Evidence-use checks](evidence_use_checks.csv) | [Measured findings](evidence_findings.csv) | [Source catalog](source_catalog.csv)", "",
        "Evidence-use Failed means **the proposed inference is unsupported**, not that the Moon site is physically unsafe. Unknown candidate conclusions cannot be converted to operational passes by a good context score.", "",
        "## Candidate explanations", ""]
    geo_regions = set(frames["geometry/reference_observers.csv"].region)
    for item in ranking.to_dict("records"):
        cid = item["candidate_id"]
        lines += ["### "+cid, "", "Region: `"+str(item["region"])+"`.",
            "Context result: **"+item["comparison_status"]+"**. "+item["reason"]]
        if pd.notna(item["environmental_score"]):
            lines.append(f"Declared context score: **{item['environmental_score']:.5f}**; rank **{int(item['environmental_rank'])}**. Not a safety probability.")
        known = evidence.loc[evidence.candidate_id.eq(cid)&evidence.status.eq("observed")]
        lines += ["", "Supported existing measurements:"]
        lines += [f"- `{r.metric}`: {r.value:.6g} {r.unit}; {r.scope}; support={int(r.support_count)}; source `{r.source_run}`."
                  for r in known.itertuples()]
        lines += ["", "Applied context filters:"]
        for r in checks.loc[checks.candidate_id.eq(cid)].to_dict("records"):
            value = f"{r['value']:.6g}" if pd.notna(r["value"]) else "not observed"
            lines.append(f"- `{r['rule_id']}`: {value}; {r.get('operator')} {r.get('limit')}; **{r['status']}**. {r['reason']}")
        lines += ["", "Additional evidence boundary:",
            ("- A separate ROI-center reference geometry exists for this region; it is NOT this component's measured/modelled operating history."
             if item["region"] in geo_regions else "- No bundled ROI-center geometry matches this region; no substitute is inserted."),
            "- All bundled hazard/reference conclusions remain **Unknown for this component's operational capability**; see [candidate inference limits](candidate_inference_limits.csv).",
            "- Mission/equipment qualification was not inferred. Optional operational checks, when requested, are reported separately.", ""]
    atomic_text(run.path("evidence_context/EVIDENCE_DECISIONS.md"), "\n".join(lines))


def products(run, manifest_name, candidates, evidence, policy, policy_source, checks, ranking):
    register, frames, catalog = load_bundle(run, manifest_name)
    compiled = compile_register(register, policy, policy_source)
    use_checks = evidence_use_checks(frames)
    findings = findings_table(frames)
    limits = candidate_limits(candidates, frames["hazards/hazard_evidence_boundaries.csv"])
    explained = explain_checks(checks)
    tables = []
    for name, title, frame in [
        ("rule_register.csv", "Scoped requirements, evidence guards and actual exploratory policy", compiled),
        ("evidence_use_checks.csv", "Checks on permitted evidence inference, not site safety", use_checks),
        ("evidence_findings.csv", "Measured historical/annual/regional findings and operational boundaries", findings),
        ("source_catalog.csv", "Pinned consumed EDA source identities and declared use", catalog),
        ("candidate_inference_limits.csv", "Per-component hazard inference limits, not operational verdicts", limits),
        ("explained_context_checks.csv", "Actual context filter values linked to the rule register", explained),
    ]:
        tables.append(("evidence_context/"+name, title, frame, "No applicable rows"))
    # Keep the exact source columns/identities: never add candidate_id to references.
    for identity, frame in frames.items():
        tables.append(("evidence_context/sources/"+identity, "Verified source: "+identity, frame, "No source rows; gap remains explicit"))
    write_explanations(run, ranking, evidence, checks, frames)
    return tables, {"register_rows": len(compiled), "static_rules": len(register["rules"]),
        "consumed_tables": len(catalog), "evidence_use_checks": len(use_checks),
        "candidate_hazard_boundaries": len(limits), "new_scored_factors": 0,
        "new_operational_passes": 0, "entry_point": "evidence_context/EVIDENCE_DECISIONS.md"}
