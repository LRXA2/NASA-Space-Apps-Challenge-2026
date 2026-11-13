"""Science-aware, unweighted preference fronts alongside the existing baseline."""
from pathlib import Path
import json

import numpy as np
import pandas as pd

from decision_eda import accepted_input
from data_maintenance import atomic_text

LOCAL = Path(__file__).resolve().parents[2]
PREFIX = "evidence_context/science/"


def align_profiles(candidates, source):
    """Exact IDs only. Other candidate sets receive explicit unsupported rows."""
    if candidates.candidate_id.duplicated().any() or source.candidate_id.duplicated().any():
        raise ValueError("Ambiguous science candidate identity")
    shared = candidates[["candidate_id","region"]].merge(source[["candidate_id","region"]],on="candidate_id",suffixes=("_live","_source"),validate="one_to_one")
    if not shared.region_live.eq(shared.region_source).all():
        raise ValueError("Science candidate regions do not match the live candidates")
    aligned = candidates[["candidate_id","region"]].merge(source.drop(columns="region"),on="candidate_id",how="left",validate="one_to_one")
    aligned["science_profile_status"] = np.where(aligned.candidate_id.isin(source.candidate_id),"Matched_source_profile","Unknown_no_associated_source_profile")
    return aligned


def pareto_fronts(frame, objectives):
    """Complete rows only; ties stay together and IDs are not preference weights."""
    metrics = [x["metric"] for x in objectives]
    if not metrics or len(metrics) != len(set(metrics)) or frame.candidate_id.duplicated().any():
        raise ValueError("Unique candidate identities and objective metrics required")
    if any(x["direction"] not in {"higher", "lower"} for x in objectives):
        raise ValueError("Explicit objective direction required")
    matrix = frame[metrics].to_numpy(dtype=float)
    if not np.isfinite(matrix).all():
        raise ValueError("Unknown objectives cannot enter a preference front")
    signs = np.array([1 if x["direction"] == "lower" else -1 for x in objectives])
    values = matrix*signs
    dominates = np.all(values[:,None,:] <= values[None,:,:],axis=2) & np.any(values[:,None,:] < values[None,:,:],axis=2)
    remaining = set(range(len(frame)))
    fronts = {}
    level = 1
    while remaining:
        current = [i for i in sorted(remaining) if not any(dominates[j,i] for j in remaining)]
        if not current:
            raise ValueError("Inconsistent dominance relation")
        for i in current:
            fronts[frame.iloc[i].candidate_id] = level
        remaining.difference_update(current)
        level += 1
    pairs = [{"dominant_candidate_id": frame.iloc[i].candidate_id, "dominated_candidate_id": frame.iloc[j].candidate_id}
             for i,j in zip(*np.where(dominates))]
    return fronts, pd.DataFrame(pairs,columns=["dominant_candidate_id","dominated_candidate_id"])


def compare(profiles, ranking, views):
    if (profiles.candidate_id.duplicated().any() or ranking.candidate_id.duplicated().any()
            or set(profiles.candidate_id) != set(ranking.candidate_id)):
        raise ValueError("Science profiles must match the live candidate set")
    rows, pairs = [], []
    joined = profiles.merge(ranking[["candidate_id","context_filter_status","environmental_score"]],on="candidate_id",validate="one_to_one")
    if not joined.context_filter_status.isin({"pass","fail","unknown","unconfigured"}).all():
        raise ValueError("Unknown context-filter state")
    for view in views:
        objectives = view["objectives"]
        metrics = [x["metric"] for x in objectives]
        # UV and Sun visibility are the same input. They cannot be independent
        # weighted benefits/penalties or opposing duplicates in one Pareto view.
        solar_family = {"solar_opportunity_fraction_median","uv_sun_visibility_opportunity_proxy","photoemission_opportunity_proxy","shadow_opportunity_proxy"}
        if len(set(metrics)&solar_family) > 1 or any("weight" in x for x in objectives):
            raise ValueError("Do not double-count solar-family proxies or invent hazard weights")
        if "photoemission_opportunity_proxy" in metrics or "shadow_opportunity_proxy" in metrics or any("plasma" in m or "dose" in m for m in metrics):
            raise ValueError("No monotonic plasma score or candidate dose is supported")
        supported = {"sky_visible_fraction_4pi","uv_sun_visibility_opportunity_proxy","earth_visibility_fraction_median","thermal_phase_median_span_K"}
        if not set(metrics) <= supported:
            raise ValueError("Objective has no supported preference meaning in this science comparison")
        passed = joined.context_filter_status.eq("pass")
        complete = np.isfinite(joined[metrics].to_numpy(dtype=float)).all(axis=1)
        selected = joined.loc[passed & complete]
        fronts, dominance = (pareto_fronts(selected,objectives) if len(selected) >= 2 else
                              ({},pd.DataFrame(columns=["dominant_candidate_id","dominated_candidate_id"])))
        for item in joined.to_dict("records"):
            cid = item["candidate_id"]
            missing = [m for m in metrics if not np.isfinite(item[m])]
            if item["context_filter_status"] == "fail":
                status, reason = "excluded_by_current_context_filters", "Current context filter state: "+item["context_filter_status"]
            elif item["context_filter_status"] != "pass":
                status, reason = "withheld_unknown_context_filters", "Context requirements have not all passed; no preference comparison"
            elif missing:
                status, reason = "Unknown", "Missing comparable objectives: "+"; ".join(missing)+"; no imputation or weight renormalization"
            elif len(selected) < 2:
                status, reason = "insufficient_comparable_candidates", "Only one complete candidate passes the current filters; do not turn missing competitors into a preference winner"
            else:
                status, reason = "compared_context_only", view["meaning"]
            rows.append({"candidate_id":cid,"region":item["region"],"view":view["id"],
                         "preference_status":status,"pareto_front":fronts.get(cid,np.nan),
                         "baseline_visibility_score":item["environmental_score"],
                         **{m:item[m] for m in metrics},"reason":reason,
                         "weighting":"none_Pareto_not_a_composite_risk_score",
                         "operational_suitability":"Unknown"})
        if not dominance.empty:
            pairs.extend(dominance.assign(view=view["id"]).to_dict("records"))
    return pd.DataFrame(rows), pd.DataFrame(pairs,columns=["dominant_candidate_id","dominated_candidate_id","view"])


def operational_unknowns(profiles):
    requirements = [
        ("radiation_protection", "Radiation", "GCR_GEOMETRY; REDMOON", "Applicable exposure period, particle field, transport/protection and adopted dose limit; sky openness is not dose"),
        ("ultraviolet_exposure", "UV", "LOLA_POLAR; UV_SCIENCE", "Spectral/incidence/reflection exposure model, relevant exposure quantity and applicable limit; Sun visibility is not UV dose"),
        ("plasma_charging", "Plasma / charging", "CHARGING_MODEL; PSR_CHARGING", "Electron/ion and material/photoemission/grounding response and applicable limits; illumination alone is not surface voltage"),
    ]
    return pd.DataFrame([{"candidate_id":item.candidate_id,"region":item.region,"requirement":id,"category":category,
                          "status":"Unknown","limit_state":"not_adopted","margin":np.nan,
                          "source_ids":source,"reason":reason,"assessment_domain":"operational_NOT_Pareto_preference"}
                         for item in profiles.itertuples() for id,category,source,reason in requirements])


def products(run, declaration, candidates, ranking):
    root = (LOCAL/"data/processed/analysis").resolve()
    folder = (root/declaration["run"]).resolve()
    config = (LOCAL/declaration["config"]).resolve()
    if not folder.is_relative_to(root) or not config.is_relative_to(LOCAL.resolve()):
        raise ValueError("Science declaration escapes Darrel's workspace")
    run.input(Path(__file__));run.input(config)
    settings = json.loads(config.read_text(encoding="utf-8"))
    if settings["schema"] != 1 or settings["body"] != "Moon" or any(settings["reference_policy"].values()):
        raise ValueError("Invalid science scope or unsupported candidate-dose/limit substitution")
    frames = {name:pd.read_csv(accepted_input(run,folder,name),low_memory=False) for name in declaration["files"]}
    saved = json.loads((folder/"provenance.json").read_text(encoding="utf-8"))["config"]
    for key in ["schema","body","candidate_run","radiation_reference_run","reference_policy","sources"]:
        if saved[key] != settings[key]:
            raise ValueError("Science source/model configuration changed; regenerate the pinned EDA before use")
    source_profiles = frames["candidate_science_profiles.csv"]
    contract = frames["indicator_contract.csv"]
    reference = frames["radiation_reference_scenarios.csv"]
    if (source_profiles.candidate_id.duplicated().any() or "candidate_id" in reference
            or not reference.evidence_basis.eq("Reference").all()):
        raise ValueError("Common scenarios cannot become candidate measurements")
    profiles = align_profiles(candidates,source_profiles)
    if (not np.allclose(profiles.sky_visible_fraction_4pi,profiles.sky_visible_sr_median/(4*np.pi),equal_nan=True)
            or not np.allclose(profiles.uv_sun_visibility_opportunity_proxy,profiles.solar_opportunity_fraction_median,equal_nan=True)):
        raise ValueError("Derived proxy meaning changed")
    if not frames["candidate_science_indicators.csv"].basis.isin({"Observed","Modelled","Reference","Unknown"}).all():
        raise ValueError("Unsupported science evidence basis")
    compared, dominated = compare(profiles,ranking,settings["comparison_views"])
    details = []
    for view in settings["comparison_views"]:
        ids = compared.loc[compared.view.eq(view["id"]) & compared.preference_status.eq("compared_context_only"), "candidate_id"]
        subset = profiles.loc[profiles.candidate_id.isin(ids)]
        for objective in view["objectives"]:
            metric = objective["metric"]
            positions = subset[metric].rank(method="min", ascending=objective["direction"] == "lower")
            for index,item in subset.iterrows():
                rule = contract.set_index("metric").loc[metric]
                details.append({"view":view["id"],"candidate_id":item.candidate_id,"metric":metric,
                                "value":item[metric],"direction":objective["direction"],
                                "relative_preference_rank":int(positions.loc[index]),"unit":rule.unit,"basis":rule.basis,
                                "meaning":"Relative position within this comparable cohort, NOT safety or a risk probability"})
    detail_frame = pd.DataFrame(details,columns=["view","candidate_id","metric","value","direction","relative_preference_rank","unit","basis","meaning"])
    checks = operational_unknowns(profiles)
    plasma = profiles[["candidate_id","region","photoemission_opportunity_proxy","shadow_opportunity_proxy","psr_fraction_cells"]].copy()
    plasma["surface_potential_V"] = np.nan
    plasma["status"] = "Unknown"
    plasma["reason"] = "Sunlit photoemission and dark/plasma-poor charging both require assessment; no monotonic risk score, inferred volts or safe-by-shadow assumption"
    plasma["source_ids"] = "CHARGING_MODEL; PSR_CHARGING"
    source_catalog = pd.DataFrame([{"file":name,"run":declaration["run"],"rows":len(frame),
                                    "source_path":str((folder/name).relative_to(LOCAL)),
                                    "sha256":run.record["inputs"][str((folder/name).resolve().relative_to(run.project_root))]["sha256"],
                                    "scope":"science indicator or common reference; not operational qualification"}
                                   for name,frame in frames.items()])
    model_checks = pd.DataFrame([
        {"rule_id":"E13","check":"common_references_not_candidate_doses","status":"Passed","domain":"evidence_handling_NOT_safety"},
        {"rule_id":"E13","check":"proxy_definitions_and_live_candidate_regions_preserved","status":"Passed","domain":"evidence_handling_NOT_safety"},
        {"rule_id":"E13","check":"no_duplicate_solar_weights_or_monotonic_plasma_score","status":"Passed","domain":"preference_configuration_NOT_safety"},
    ]).assign(candidate_operational_conclusion="Unknown")
    tables = [(PREFIX+name,"Science source: "+name,frame,"No supported source rows; explicit limits retained") for name,frame in frames.items()]
    tables += [(PREFIX+"science_preference_fronts.csv","Unweighted exploratory science tradeoffs, NOT operational eligibility",compared,"No comparable science preferences"),
               (PREFIX+"science_dominance_pairs.csv","Within-view dominance proof, not physical safety",dominated,"No dominance among comparable candidates"),
               (PREFIX+"science_preference_details.csv","Per-factor lower/higher relative positions, not safety ranks",detail_frame,"No comparable objective values"),
               (PREFIX+"science_operational_requirements.csv","Radiation/UV/plasma applicability and limit holds",checks,"No candidate requirement rows"),
               (PREFIX+"science_source_catalog.csv","Pinned science input tables and original source hashes",source_catalog,"No science input tables"),
               (PREFIX+"science_model_checks.csv","Model-contract handling checks, NOT site safety",model_checks,"No science model checks"),
               (PREFIX+"candidate_plasma_context.csv","Illumination context and unqualified charging response",plasma,"No candidate plasma context")]
    tables += [(PREFIX+"aligned_candidate_science_profiles.csv","Exact-ID science evidence; unsupported candidates remain Unknown",profiles,"No candidate rows")]
    lines = ["# Lunar science-based environmental comparison","",
             "**This extends the environmental comparison, not operational approval.** The baseline visibility score remains separate. No actual mission/equipment configuration is required for these reference/proxy comparisons.","",
             "## What is included","",
             "- Radiation: candidate terrain-modelled visible solid angle divided by **4*pi**. Geometric primary-particle openness only, not a dose or shielding-efficiency percentage. Values above 2*pi are retained correctly.",
             "- UV: long-period direct-Sun visibility opportunity, not spectral irradiance, biological dose or a zero-UV guarantee in shadow.",
             "- Plasma: sourced sunlit/terminator/dark charging regimes and candidate illumination/PSR context. Local voltage, discharge risk and monotonic desirability remain Unknown.",
             "- Thermal: complete fixed-common surface phase-median profiles, not actual extremes or equipment temperatures.","",
             "## How preferences work","",
             "Candidates must first pass the **live** illustrative context filters. Separate Pareto views compare geometric exposure/UV opportunity/Earth visibility, optionally adding qualified phase-temperature stability. No invented hazard weights or composite risk score. One candidate dominates another only if it is no worse on every included objective and strictly better on at least one; ties share a front.",
             "Sunlight and the UV proxy share the same input. The exposure view deliberately does not count sunlight again as an opposing independent benefit. Solar visibility is still constrained by the current context filter; the existing power/access-oriented baseline remains available alongside it. Switching views is an explicit project preference, not a NASA prescription.",
             "Missing objectives withhold that view; they are never filled or dropped to produce a score. **Front 1 is not a declaration of safety.** Source spatial support and uncalibrated uncertainty limit fine distinctions.","",
             "## Current views","",
             "| View | Compared | Missing comparable data after filters | First-front candidates |","| --- | ---: | ---: | ---: |"]
    summaries, view_notes = [], []
    for view,part in compared.groupby("view",sort=False):
        summary = {"view":view,"compared":int(part.preference_status.eq("compared_context_only").sum()),
                   "unknown":int(part.preference_status.eq("Unknown").sum()),"front_one":int(part.pareto_front.eq(1).sum()),
                   "insufficient_comparators":int(part.preference_status.eq("insufficient_comparable_candidates").sum())}
        summaries.append(summary)
        lines.append(f"| {view} | {summary['compared']} | {summary['unknown']} | {summary['front_one']} |")
        if summary["insufficient_comparators"]:
            view_notes += ["",f"{view}: {summary['insufficient_comparators']} complete eligible candidate, but fewer than two comparators. No preference front or per-factor winning rank is issued.",""]
    lines += view_notes
    lines += ["","[Candidate indicators](candidate_science_indicators.csv) | [Preference fronts](science_preference_fronts.csv) | [Dominance proof](science_dominance_pairs.csv) | [Operational holds](science_operational_requirements.csv)","",
              "## First-front options",""]
    for view,part in compared.loc[compared.pareto_front.eq(1)].groupby("view",sort=False):
        lines += ["### "+view,""]+["- `"+cid+"`" for cid in sorted(part.candidate_id)]+[""]
    lines += ["## Common scenarios, not fabricated site readings","",
              f"The {len(reference)} checked REDMoon dose-duration scenarios retain their original solar/shielding/depth assumptions and steady-rate extrapolation. They are **not multiplied by the sky proxy**, assigned to candidate doses, or used as adopted limits. Primary terrain geometry does not account for whole-field secondary-particle transport.",
              "Published charging mechanisms are retained as reference regimes, not invented local plasma density or volts. The current northern LAMP samples are not substituted for south-polar UV coverage.","",
              "All radiation/UV/plasma operational requirements remain Unknown until their quantity, applicability, response and limits are supplied. An applicable mandatory failure cannot be offset by preference benefits.","","## Science sources",""]
    for source in settings["sources"]:
        lines.append(f"- [{source['id']}: {source['citation']}]({source['url']}) — {source['limitation']}")
    atomic_text(run.path(PREFIX+"SCIENCE_COMPARISON.md"),"\n".join(lines)+"\n")
    return tables, {"candidates":len(profiles),"unsupported_candidate_profiles":int(profiles.science_profile_status.ne("Matched_source_profile").sum()),
                    "reference_scenarios":len(reference),"views":summaries,"consumed_tables":len(frames),
                    "operational_unknowns":len(checks),"new_operational_passes":0,
                    "baseline_score_changed":False,"method":"explicit_unweighted_Pareto_context_views",
                    "entry_point":PREFIX+"SCIENCE_COMPARISON.md"}
