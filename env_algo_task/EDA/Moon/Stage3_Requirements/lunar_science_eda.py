"""Moon science indicators: geometry/proxies and separate reference scenarios."""
from pathlib import Path
import argparse
import json
import sys

sys.path[:0] = [str(Path(__file__).resolve().parents[2] / "shared"), str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[4])]
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from environment_workflow import LocalRun
from decision_eda import accepted_input
from stage3_mission_eda import ROOT, LOCAL, save_figure

CONFIG = LOCAL/"research/lunar_science_models.json"
NOTEBOOK = "Moon/Stage3_Requirements/Dar_042_lunar_science_indicators.ipynb"


def derive_profiles(candidates, static, thermal, support):
    """Keep measured summaries, source models and unavailable quantities distinct."""
    if candidates.candidate_id.duplicated().any() or candidates.candidate_id.isna().any():
        raise ValueError("Expected unique candidate identities")
    if static.duplicated(["candidate_id", "variable"]).any():
        raise ValueError("Ambiguous static profiles")
    fixed = thermal.loc[thermal.cohort.eq("fixed_common")].merge(
        support[["candidate_id", "expected_common_products"]], on="candidate_id", validate="one_to_one")
    if set(fixed.candidate_id) != set(candidates.candidate_id):
        raise ValueError("Missing fixed-cohort candidate records")
    frame = candidates[["candidate_id", "region"]].copy().set_index("candidate_id")
    specs = [("solar_visibility", "fraction", "median", "solar_opportunity_fraction_median", 1),
             ("earth_visibility", "fraction", "median", "earth_visibility_fraction_median", 1),
             ("sky_view_sr", "steradian", "median", "sky_visible_sr_median", 4*np.pi),
             ("permanent_shadow", "binary", "mean", "psr_fraction_cells", 1)]
    for variable, unit, statistic, name, maximum in specs:
        part = static.loc[static.variable.eq(variable)].set_index("candidate_id")
        if set(part.index) != set(frame.index):
            raise ValueError("Required source profile records disappeared: "+variable)
        if (not part.unit.eq(unit).all() or part.finite_cells.lt(0).any()
                or part.cells.le(0).any() or (part.finite_cells > part.cells).any()):
            raise ValueError("Source unit/count mismatch: "+variable)
        finite = np.isfinite(part[statistic])
        if ((part.loc[finite, statistic] < 0) | (part.loc[finite, statistic] > maximum)).any():
            raise ValueError("Source outside physical quantity domain: "+variable)
        complete = part.finite_cells.eq(part.cells) & finite
        frame[name] = part[statistic].where(complete)
        frame[name+"_support"] = part.finite_cells
    # 4*pi, not 2*pi: the product is visible solid angle, and values above a
    # planar hemisphere can occur. This is NOT a dose/shielding-efficiency factor.
    frame["sky_visible_fraction_4pi"] = frame.sky_visible_sr_median/(4*np.pi)
    frame["uv_sun_visibility_opportunity_proxy"] = frame.solar_opportunity_fraction_median
    frame["photoemission_opportunity_proxy"] = frame.solar_opportunity_fraction_median
    frame["shadow_opportunity_proxy"] = 1-frame.solar_opportunity_fraction_median
    fixed = fixed.set_index("candidate_id")
    cols = ["minimum_product_median_K", "maximum_product_median_K", "span_of_product_medians_K"]
    complete = (fixed.expected_common_products.gt(0)
                &fixed.supported_products.eq(fixed.expected_common_products)
                &fixed.minimum_centers_per_product.gt(0)&np.isfinite(fixed[cols]).all(axis=1))
    selected = fixed.loc[complete]
    if (selected.minimum_product_median_K.lt(0).any()
            or not np.allclose(selected.maximum_product_median_K-selected.minimum_product_median_K,
                               selected.span_of_product_medians_K, rtol=1e-10, atol=1e-8)):
        raise ValueError("Thermal cohort range is inconsistent")
    for source, target in zip(cols, ["thermal_phase_median_min_K", "thermal_phase_median_max_K", "thermal_phase_median_span_K"]):
        frame[target] = fixed[source].where(complete)
    frame["thermal_common_products"] = fixed.supported_products
    frame["thermal_minimum_centers"] = fixed.minimum_centers_per_product
    return frame.reset_index()


def indicator_contract():
    rows = [
        ("sky_visible_fraction_4pi", "Radiation", "Modelled", "fraction of 4*pi solid angle", "LOLA_POLAR; GCR_GEOMETRY", "sky_geometry",
         "Visible sky / (4*pi); lower is an explicit geometric preference, NOT lower total transported dose", "static terrain-modelled component cell-summary median"),
        ("uv_sun_visibility_opportunity_proxy", "UV", "Modelled", "fraction", "LOLA_POLAR; UV_SCIENCE", "solar_visibility",
         "Long-period Sun visibility opportunity only; no spectral, incidence-weighted, reflected or biological UV dose", "median of long-period modelled solar visibility over component cells"),
        ("earth_visibility_fraction_median", "Communications context", "Modelled", "fraction", "LOLA_POLAR", "earth_visibility",
         "Geometric visibility only, not a link budget or communications service", "static component cell-summary median"),
        ("photoemission_opportunity_proxy", "Plasma / charging", "Modelled", "fraction", "UV_SCIENCE; CHARGING_MODEL", "solar_visibility",
         "Shares the UV/Sun input; no independent score, current density, local potential or discharge rate", "Sun-visibility opportunity, not mean equilibrium charging"),
        ("shadow_opportunity_proxy", "Plasma / charging", "Modelled", "fraction", "CHARGING_MODEL; PSR_CHARGING", "solar_visibility",
         "Complement of Sun visibility, not a dark-interval duration or plasma density; darkness is not universally safer", "long-period opportunity complement"),
        ("psr_fraction_cells", "Plasma / charging", "Modelled", "fraction", "LOLA_POLAR; PSR_CHARGING", "permanent_shadow",
         "Mapped PSR cell fraction; a zero does not certify no shadow, plasma or charging hazard", "source component-cell map summary"),
    ]
    for suffix in ["min", "max", "span"]:
        rows.append((f"thermal_phase_median_{suffix}_K", "Thermal", "Observed", "K", "existing Dar_020 fixed-common Diviner EDA", "fixed_thermal_cohort",
                     "Observation-derived phase-product medians at matched centers; not actual extremes, a full footprint or equipment response",
                     "complete fixed-common remote-observation cohort only"))
    return pd.DataFrame(rows, columns=["metric", "category", "basis", "unit", "source_ids", "shared_input_family", "meaning_and_limits", "scope"])


def long_indicators(profiles):
    rows = []
    for item in profiles.to_dict("records"):
        for rule in indicator_contract().to_dict("records"):
            value = item[rule["metric"]]
            rows.append({"candidate_id": item["candidate_id"], "region": item["region"], **rule,
                         "value": value, "basis": rule["basis"] if np.isfinite(value) else "Unknown",
                         "indicator_status": "Available" if np.isfinite(value) else "Unknown",
                         "candidate_operational_conclusion": "Unknown"})
    return pd.DataFrame(rows)


def plasma_reference_cases():
    return pd.DataFrame([
        {"regime": "sunlit_surface", "mechanism": "Solar photoemission and collection of plasma electrons/ions",
         "source_ids": "CHARGING_MODEL; UV_SCIENCE", "inference_limit": "Mean solar visibility does not determine voltage or equipment effects"},
        {"regime": "near_terminator_or_shadow_boundary", "mechanism": "Changing illumination and plasma-current balance",
         "source_ids": "CHARGING_MODEL", "inference_limit": "Source model domain and electron/material inputs must be established; no transition count from averages"},
        {"regime": "dark_plasma_poor_polar_terrain", "mechanism": "Limited charge dissipation and possible triboelectric charging",
         "source_ids": "PSR_CHARGING", "inference_limit": "Dark or plasma-poor does not imply electrically benign; grounding/material/operation response remains needed"},
    ]).assign(basis="Reference", local_surface_potential_V=np.nan, operational_status="Unknown")


def execute(sample=False):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1 or config["body"] != "Moon" or any(config["reference_policy"].values()):
        raise ValueError("Expected Moon-only science indicators without adopted limits or reference-to-candidate dose substitution")
    with LocalRun(ROOT, "analysis/lunar_science_indicators"+("_sample" if sample else ""), config, NOTEBOOK) as run:
        for p in [CONFIG, Path(__file__), LOCAL/config["research_register"]]:
            run.input(p)
        folder = LOCAL/"data/processed/analysis"/config["candidate_run"]
        read = lambda n: pd.read_csv(accepted_input(run, folder, n))
        candidates = read("candidate_manifest.csv")
        static, thermal, support = read("candidate_static_profiles.csv"), read("candidate_thermal_summary.csv"), read("candidate_thermal_association_support.csv")
        if sample:
            # Include a >2*pi sky value and an available thermal cohort.
            ids = set(candidates.candidate_id.head(2)) | set(thermal.loc[thermal.cohort.eq("fixed_common")&thermal.supported_products.gt(0), "candidate_id"].head(1))
            candidates = candidates.loc[candidates.candidate_id.isin(ids)]
            static, thermal, support = [f.loc[f.candidate_id.isin(ids)] for f in [static, thermal, support]]
        profiles = derive_profiles(candidates, static, thermal, support)
        profiles.to_csv(run.path("candidate_science_profiles.csv"), index=False)
        long_indicators(profiles).to_csv(run.path("candidate_science_indicators.csv"), index=False)
        indicator_contract().to_csv(run.path("indicator_contract.csv"), index=False)
        references = pd.read_csv(accepted_input(run, LOCAL/"data/processed/analysis"/config["radiation_reference_run"], "reference_radiation_duration_sensitivity.csv"))
        if "candidate_id" in references or not references.particles.eq("all").all():
            raise ValueError("Expected common published all-particle scenario library, not candidate doses")
        expected = references.effective_dose_cSv_year*10*references.illustrative_days/365.25
        if not np.isfinite(expected).all() or not np.allclose(references.reference_mSv, expected, rtol=1e-12, atol=1e-12):
            raise ValueError("Reference-unit conversion disagrees with the checked EDA")
        references.assign(evidence_basis="Reference", source_ids="REDMOON", role="common_what_if_library_NOT_site_ranking_or_limit").to_csv(
            run.path("radiation_reference_scenarios.csv"), index=False)
        plasma_reference_cases().to_csv(run.path("plasma_reference_cases.csv"), index=False)
        pd.DataFrame(config["sources"]).to_csv(run.path("science_sources.csv"), index=False)
        fig, axes = plt.subplots(1,2,figsize=(12,4),layout="constrained")
        axes[0].scatter(profiles.uv_sun_visibility_opportunity_proxy, profiles.sky_visible_fraction_4pi)
        axes[0].set(xlabel="Sun/UV visibility opportunity proxy", ylabel="Visible sky / 4*pi", title="Separate geometric tradeoffs, not dose or safety")
        axes[1].scatter(profiles.solar_opportunity_fraction_median, profiles.uv_sun_visibility_opportunity_proxy)
        axes[1].set(xlabel="Existing sunlight input", ylabel="UV opportunity proxy", title="Same input: never double-count as independent weights")
        save_figure(run, fig, "science_proxy_tradeoffs")
        findings = {"sample": sample, "candidates": len(profiles), "sky_proxy_available": int(profiles.sky_visible_fraction_4pi.notna().sum()),
                    "uv_proxy_available": int(profiles.uv_sun_visibility_opportunity_proxy.notna().sum()),
                    "complete_thermal_candidates": int(profiles.thermal_phase_median_span_K.notna().sum()),
                    "sky_medians_above_2pi": int(profiles.sky_visible_sr_median.gt(2*np.pi).sum()),
                    "reference_scenarios": len(references), "charging_reference_regimes": 3,
                    "candidate_dose_or_voltage_invented": False, "operational_safety_limits_adopted": False,
                    "holds": ["No whole-component physical support or uncertainty calibration inferred", "UV proxy is not UV irradiance or dose", "Sky openness is not transported radiation dose", "Plasma response and all operational conclusions remain Unknown"]}
        run.path("findings.json").write_text(json.dumps(findings,indent=2),encoding="utf-8")
        result = run.directory
    print(json.dumps(findings,indent=2))
    return result, findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true")
    print(execute(parser.parse_args().sample)[0])
