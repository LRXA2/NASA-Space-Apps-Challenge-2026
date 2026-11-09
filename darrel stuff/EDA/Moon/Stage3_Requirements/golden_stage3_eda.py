"""Required Stage 3 evidence audit and bounded, source-qualified follow-up EDA.

No invented mission profile, archive-completeness claim or operational threshold.
"""
from pathlib import Path
import json
import re
import sys

import numpy as np
import pandas as pd

LOCAL = Path(__file__).resolve().parents[3]
ROOT = LOCAL.parent
sys.path[:0] = [str(LOCAL / "EDA/shared"), str(LOCAL), str(ROOT)]
from data_maintenance import resolve_data_path
from decision_eda import accepted_input, sampled_condition_runs
from environment_workflow import LocalRun

PINS = {
    "thermal": ("dar_001_temperature_local_time", "20261106T082643415392Z_4e6a0b"),
    "paired": ("dar_002_temperature_environment", "20261106T082929336242Z_623f9f"),
    "joint": ("dar_012_joint_environment", "20261106T134155791814Z_c6f9ab"),
    "geometry": ("dar_010_research_geometry", "20261106T093511302492Z_634df5"),
    "conditional": ("dar_025_conditional_terrain_thermal", "20261107T145837258343Z_fcfe52"),
    "battery": ("dar_015_battery_reference", "20261106T180201347294Z_6782cd"),
    "soil": ("dar_016_apollo_soil_reference", "20261106T160018461511Z_ac6ed4"),
    "radiation": ("dar_005_research_radiation", "20261107T160219935579Z_f7779c"),
}
GOLDEN = {
    "selected_site_and_operating_period": ("D01 D02 D03 D04 D05 D06 D19 D20 D38", "Dar_001/002/010/012/023/025/030", "phase/static evidence and dated reference geometry; no selected operating period"),
    "mission_duration_and_activities": ("M04 M07", "Dar_029/031", "project input absent; crew-day and time-window sensitivity are not a selected mission"),
    "crew_requirements_and_consumables": ("M02 M10 S01 S02", "Dar_029/031", "published nominal load reference available; crew, stocks, recovery and approved limits absent"),
    "equipment_capabilities_and_thermal_control": ("M01 M04 D21 D28 R01", "Dar_004/015/029/031", "historical/laboratory references only; selected hardware and local thermal response absent"),
    "power_and_reserves": ("D02 M07 R01", "Dar_015/030/031", "mean sunlight and laboratory cell response cannot establish mission energy reserve"),
    "communications": ("D03 D19 M08", "Dar_010/030/031", "reference-sphere geometry lacks terrain/relay/link model and required contact schedule"),
    "radiation_and_protection": ("D07 D08 D31 M06 S02 S03", "Dar_005/029/031", "scenario-qualified shielding reference; no applicable crew dose/transport/limits"),
    "dust_and_physical_surface_hazards": ("D10 M03 D13 D14 D23 D15 D33 M05 M13", "Dar_007/008/016/029/031", "quality/reference findings exist; local wear/hazard/strength response and requirements absent"),
    "requirements_margins_and_uncertainty": ("M04 M09 M14 C01 S02", "Dar_022/029/031 and Pipeline_Proto", "passed/failed/unknown framework; no approved complete requirements inventory or mission profile"),
}


def read_accepted(run, key, name):
    stage, identifier = PINS[key]
    folder = LOCAL / "data/processed/analysis" / stage / identifier
    return pd.read_csv(accepted_input(run, folder, name))


def latest_selections(data, run=None):
    """Timestamped selection evidence, not CSV's historical acquisition statuses."""
    records = {}
    paths = set((data / "manifests/eda_datasets").glob("*/inventory.json"))
    paths.update((data / "manifests/eda_datasets").glob("*/download.json"))
    for path in sorted(paths, key=lambda p: (p.parent.name, p.name == "download.json")):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        for item in record.get("datasets", []):
            key = item["id"]
            outcome = record.get("dataset_outcomes", {}).get(key, {})
            records[key] = (path, item, outcome, [f for f in record.get("files", []) if f["dataset"] == key])
    if run:
        for path in {r[0] for r in records.values()}:
            run.input(path)
        journal = data / "manifests/file_relocations.json"
        if journal.exists(): run.input(journal)
    return records


def audit_data(run):
    data = LOCAL / "data"
    register = LOCAL / "research/environmental_data.csv"
    run.input(register)
    frame = pd.read_csv(register)
    selected = latest_selections(data, run)
    # Do not let the newest tiny research pilot hide the already acquired core.
    # Union completed research selections + completed core records + the latest
    # explicit Moon-support inventory (whose metadata write can fail independently).
    union = {}
    for path in sorted((data / "manifests").glob("eda_datasets/*/download.json")) + sorted((data / "manifests").glob("core/*/*/download.json")):
        record = json.loads(path.read_text(encoding="utf-8-sig"))
        if record.get("status") != "complete": continue
        run.input(path)
        for item in record.get("files", []):
            key = item["dataset"]
            rel = item["relative_path"]
            if key == "lunar-temperature": key = "D01"
            elif key == "lunar-illumination":
                key = "D03" if "earth_visibility" in rel else "D04" if "sky_visibility" in rel else "D02"
            union.setdefault(key, {})[str(resolve_data_path(data, rel))] = item
    support_records = sorted((data / "manifests/moon_support").glob("*/run.json"))
    if support_records:
        p = support_records[-1]; run.input(p)
        for item in json.loads(p.read_text()).get("files", []):
            rel = item["relative_path"]
            key = "D05" if "sdem" in rel else "D06" if "lola_product90" in rel else "D02"
            union.setdefault(key, {})[str(resolve_data_path(data, rel))] = item
    rows, file_checks = [], []
    for item in frame.to_dict("records"):
        key = re.search(r"[DMC]\d{2}", item["Priority ID"])[0]
        priorities = item["Priority ID"].split("-")[0]
        facts = {"dataset_id": key, "research_priority": priorities, "dataset": item["Dataset"],
                 "group": item["Environmental Group"], "source_url": item["Source"],
                 "golden_categories": ";".join(k for k, v in GOLDEN.items() if key in v[0].split())}
        files, missing, wrong, receipts = [], [], [], 0
        if key.startswith("M"):
            status, reason = "project_input_missing", "Not a downloadable universal dataset; selected mission/equipment/test/model inputs required"
        elif key == "C01":
            status, reason = "configuration_baseline", "Moon scope/body applicability, not an empirical time-varying dataset"
        elif key not in selected:
            status, reason = "not_in_current_download_selection", "No selected manifest; source/access/scope must be checked before adding"
        else:
            path, entry, outcome, files = selected[key]
            current = dict(union.get(key, {}))
            current.update({str(resolve_data_path(data, f["relative_path"])): f for f in files})
            files = list(current.values())
            status = outcome.get("status", entry.get("status", "unknown"))
            reason = "Bounded selection only; archive-wide/site/time coverage is NOT implied"
            for f in files:
                p = resolve_data_path(data, f["relative_path"])
                if not p.is_file(): missing.append(f["relative_path"])
                elif f.get("size_bytes") is not None and p.stat().st_size != f["size_bytes"]: wrong.append(f["relative_path"])
                elif p.with_name(p.name + ".json").is_file(): receipts += 1
                file_checks.append({"dataset_id": key, "path": p.relative_to(data).as_posix(), "source_url": f["url"],
                    "expected_bytes": f.get("size_bytes"), "actual_bytes": p.stat().st_size if p.is_file() else None,
                    "present_expected_size": p.is_file() and p.stat().st_size == f.get("size_bytes"),
                    "receipt_present": p.with_name(p.name + ".json").is_file()})
            if missing or wrong: status = "missing_or_wrong_size"
            elif files and status in {"complete", "planned", "partial_selection"}: status = "selected_subset_present"
            facts["selection_manifest"] = path.relative_to(data).as_posix()
        rows.append({**facts, "local_status": status, "selected_files": len(files),
            "missing_files": len(missing), "wrong_size_files": len(wrong), "receipt_files": receipts, "reason": reason})
    audit = pd.DataFrame(rows)
    pd.DataFrame(file_checks).to_csv(run.path("selected_file_presence_audit.csv"), index=False)
    audit.to_csv(run.path("all_research_dataset_audit.csv"), index=False)
    audit.loc[audit.research_priority.eq("P1")].to_csv(run.path("p1_dataset_audit.csv"), index=False)
    golden = pd.DataFrame([{"golden_category": key, "datasets": value[0], "notebooks": value[1],
        "evidence_status": value[2], "operational_status": "Unknown without applicable mission/configuration/evidence"} for key, value in GOLDEN.items()])
    golden.to_csv(run.path("golden_input_coverage.csv"), index=False)
    # All eleven P1 M-rows are assessed for missing fields, not fabricated numeric EDA.
    fields = {
        "M01": "component identity; calibrated thermal response; operating/survival limits; test environment/time",
        "M02": "crew; internal pressure/composition; atmosphere telemetry; life-support capacity",
        "M04": "mission body/site/start/stop/activities; selected equipment; requirement provenance/limits/reserves",
        "M05": "local ground properties; selected vehicle/structure loads; bearing/sinkage/stability response",
        "M06": "exposure scenario; material/geometry; transported quantity/unit; uncertainty; applicable limits",
        "M07": "dated terrain-aware generation/load/storage; heat balance; initial states/reserves; completeness",
        "M08": "dated terrain/relay/link evidence; contact schedule; outage budget",
        "M09": "sample identity; containment/release test conditions; calibration; exposure requirements",
        "M10": "air/water/surface monitoring analyte/unit/time/quality; applicable limits",
        "M13": "lander/plume/structure geometry; loads; validated vulnerability model",
        "M14": "failure/repair/return scenarios; exposure; reliability/medical applicability",
    }
    pd.DataFrame([{"dataset_id": key, "required_fields": value, "available_project_records": 0,
        "eda_result": "input schema/availability assessed; numeric measurement analysis unavailable", "action": "supply project evidence, not another broad lunar archive"}
        for key, value in fields.items()]).to_csv(run.path("p1_project_input_contracts.csv"), index=False)
    result = {"research_rows": len(audit), "p1_rows": int(audit.research_priority.eq("P1").sum()),
        "status_counts": audit.local_status.value_counts().to_dict(), "golden_categories_assessed": len(golden),
        "missing_selected_files": int(audit.missing_files.sum()), "wrong_size_selected_files": int(audit.wrong_size_files.sum()),
        "verification_scope": "Latest bounded selections plus completed core/research selections and latest Moon support: local presence/size and receipt existence, NOT full checksum/whole-archive verification",
        "reference_additions": "S01 BVAD Rev2 curated source extract; full PDF local transport 403. S02 NASA-STD-3001 V2 F and S03 V1 C acquired separately; none is a mission profile."}
    return result


def seasonal_design(table):
    hour = table.local_time_bin_h.to_numpy(float) * 2 * np.pi / 24
    phase = np.deg2rad(table.seasonal_ls_bin.to_numpy(float))
    return np.column_stack([np.ones(len(table)), np.sin(hour), np.cos(hour), np.sin(phase), np.cos(phase)])


def cyclic_validation(table):
    """Hold out a whole Ls group; no treating observed aggregate bins as independent trials."""
    rows = []
    for (region, cohort), part in table.groupby(["region", "cohort"]):
        f = part.loc[part.median_K.notna() & part.rows.gt(0)]
        for held in sorted(part.seasonal_ls_bin.unique()):
            train, test = f.loc[f.seasonal_ls_bin.ne(held)], f.loc[f.seasonal_ls_bin.eq(held)]
            x = seasonal_design(train)
            known = len(train) >= 10 and len(test) > 0 and np.linalg.matrix_rank(x) == 5
            model_mae = baseline_mae = np.nan
            if known:
                beta = np.linalg.lstsq(x, train.median_K.to_numpy(), rcond=None)[0]
                model_mae = np.mean(abs(seasonal_design(test) @ beta - test.median_K))
                baseline_mae = np.mean(abs(train.median_K.mean() - test.median_K))
            rows.append({"region": region, "cohort": cohort, "held_out_ls": held, "train_bins": len(train),
                "test_bins": len(test), "cyclic_mae_K": model_mae, "training_mean_baseline_mae_K": baseline_mae,
                "status": "aggregate_diagnostic" if known else "insufficient_support"})
    return pd.DataFrame(rows)


def annual_reference_geometry(run, template):
    import spiceypy as spice
    from research_p1_readers import pilot_files, pin_source
    files = [p for suffix in [".tls", ".tpc", ".bsp", ".bpc", ".tf"] for p in pilot_files(LOCAL / "data", "D19", suffix)]
    for p in files: pin_source(run, p)
    # First seven days of each 2020 month at six-hour cadence: not a full-year duty cycle.
    times = pd.DatetimeIndex([t for month in range(1, 13) for t in pd.date_range(
        f"2020-{month:02}-01", periods=28, freq="6h", tz="UTC")])
    coordinates = template[["region", "longitude_deg", "latitude_deg"]].drop_duplicates()
    if coordinates.region.duplicated().any(): raise ValueError("Ambiguous reference observer")
    rows = []
    spice.kclear()
    try:
        for p in files: spice.furnsh(str(p))
        epochs = [spice.str2et(t.strftime("%Y-%m-%dT%H:%M:%S")) for t in times]
        for item in coordinates.itertuples():
            observer = spice.latrec(1737.4, *np.deg2rad([item.longitude_deg, item.latitude_deg]))
            up = observer / np.linalg.norm(observer)
            for utc, et in zip(times, epochs):
                sun, _ = spice.spkpos("SUN", et, "MOON_ME", "NONE", "MOON")
                subsolar_lon = np.rad2deg(np.arctan2(sun[1], sun[0]))
                hour = ((item.longitude_deg - subsolar_lon) / 15 + 12) % 24
                for target in ["SUN", "EARTH"]:
                    pos, _ = spice.spkpos(target, et, "MOON_ME", "NONE", "MOON")
                    vector = np.asarray(pos) - observer
                    elevation = np.rad2deg(np.arcsin(np.clip(np.dot(vector / np.linalg.norm(vector), up), -1, 1)))
                    rows.append({"region": item.region, "target": target, "utc": utc, "month": utc.month,
                        "local_solar_hour": hour, "reference_elevation_deg": elevation,
                        "center_above_sphere_horizon": elevation > 0})
    finally:
        spice.kclear()
    return pd.DataFrame(rows)


def time_terrain(run):
    local = read_accepted(run, "thermal", "local_time_temperature.csv")
    coverage = local.groupby(["region", "cohort", "seasonal_ls_bin"]).agg(
        expected_hour_bins=("median_K", "size"), observed_hour_bins=("median_K", "count"),
        min_bin_median_K=("median_K", "min"), max_bin_median_K=("median_K", "max")).reset_index()
    coverage["span_of_observed_hour_bin_medians_K"] = coverage.max_bin_median_K - coverage.min_bin_median_K
    coverage.to_csv(run.path("local_hour_season_coverage.csv"), index=False)
    contrast = local.groupby(["region", "cohort", "local_time_bin_h"]).agg(
        observed_ls_groups=("median_K", "count"), minimum_bin_median_K=("median_K", "min"),
        maximum_bin_median_K=("median_K", "max"), minimum_bin_centres=("native_centers", "min"),
        maximum_bin_centres=("native_centers", "max")).reset_index()
    contrast["matched_hour_ls_span_K"] = (contrast.maximum_bin_median_K - contrast.minimum_bin_median_K).where(contrast.observed_ls_groups.ge(2))
    contrast.to_csv(run.path("matched_hour_seasonal_contrasts.csv"), index=False)
    cv = cyclic_validation(local)
    cv.to_csv(run.path("held_out_ls_cyclic_diagnostics.csv"), index=False)
    conditional = read_accepted(run, "conditional", "within_product_conditional_rank_relationships.csv")
    conditional["seasonal_ls_bin"] = conditional.source_product.str.extract(r"_ls(\d+)_").astype(int)
    conditional["negative"] = conditional.partial_rank_rho.lt(0).where(conditional.status.eq("descriptive"))
    terrain = conditional.groupby(["cohort", "predictor", "control_model", "seasonal_ls_bin"]).agg(
        comparisons=("status", "size"), supported=("partial_rank_rho", "count"),
        median_conditional_rho=("partial_rank_rho", "median"), minimum_rho=("partial_rank_rho", "min"),
        maximum_rho=("partial_rank_rho", "max"), negative_fraction_supported=("negative", "mean")).reset_index()
    terrain.to_csv(run.path("terrain_temperature_phase_sign_support.csv"), index=False)
    geometry = read_accepted(run, "geometry", "reference_sphere_sun_earth_geometry.csv")
    runs = []
    for (region, target), part in geometry.groupby(["region", "target"]):
        # These are sample spans, not physical continuous darkness/contact durations.
        intervals = sampled_condition_runs(part.utc, part.reference_sphere_center_elevation_deg.le(0), 3600)
        intervals["region"], intervals["target"] = region, target
        runs.append(intervals)
    intervals = pd.concat(runs, ignore_index=True)
    intervals.to_csv(run.path("november_reference_below_horizon_sample_spans.csv"), index=False)
    annual = annual_reference_geometry(run, geometry)
    annual.to_csv(run.path("monthly_reference_geometry.csv.gz"), index=False, compression="gzip")
    annual.groupby(["region", "target", "month"]).agg(samples=("reference_elevation_deg", "size"),
        minimum_elevation_deg=("reference_elevation_deg", "min"), maximum_elevation_deg=("reference_elevation_deg", "max"),
        above_sphere_horizon_fraction=("center_above_sphere_horizon", "mean")).reset_index().to_csv(run.path("monthly_reference_geometry_summary.csv"), index=False)
    usable = cv.loc[cv.status.eq("aggregate_diagnostic")]
    return {"local_hour_ls_rows": len(local), "supported_local_hour_ls_rows": int(local.median_K.notna().sum()),
        "matched_hour_contrasts_with_two_ls": int(contrast.observed_ls_groups.ge(2).sum()),
        "cyclic_supported_folds": len(usable), "cyclic_folds_better_than_training_mean": int((usable.cyclic_mae_K < usable.training_mean_baseline_mae_K).sum()),
        "terrain_phase_comparisons": len(conditional), "annual_reference_geometry_rows": len(annual),
        "below_reference_horizon_sample_spans": len(intervals),
        "holds": ["Ls and local solar hour are cyclic phase coordinates, not calendar-month temperature observations",
                  "Matched local-hour summaries do not guarantee identical sample centres across Ls",
                  "Aggregate-bin CV is a diagnostic, not independent site prediction or an equipment response model",
                  "Annual geometry samples only first seven days/month; terrain-free point-centre geometry, not terrain illumination/contact",
                  "November intervals are first-to-last sample spans with censoring, not measured continuous darkness"]}


def reference_margins(run):
    file = LOCAL / "data/reference/stage3/bvad_rev2/table3_31_curated.csv"
    run.input(file); run.input(file.with_suffix(".provenance.json"))
    rates = pd.read_csv(file)
    selections = latest_selections(LOCAL / "data", run)
    for key in ["S02", "S03"]:
        selection = selections.get(key)
        if selection:
            for item in selection[3]:
                run.input(resolve_data_path(LOCAL / "data", item["relative_path"]))
    pd.DataFrame([
        {"reference_id": "V2 6012", "factor": "internal cabin temperature/humidity envelope", "needed_mapping": "applicable crew environment/operating envelope, not lunar surface tbol"},
        {"reference_id": "V2 6017", "factor": "atmospheric control", "needed_mapping": "habitat pressure/composition controls, not external near-vacuum as cabin conditions; this requirement does not apply to spacesuits"},
        {"reference_id": "V2 6095", "factor": "radiation requirement allocation", "needed_mapping": "program-selected exposure/transport quantity and applicable Vol1 limits"},
    ]).assign(source="NASA-STD-3001 V2 Rev F (2026)", status="reference_review_not_adopted_project_limit").to_csv(run.path("human_system_requirement_reference_map.csv"), index=False)
    if rates.quantity.duplicated().any() or rates.nominal_value.le(0).any(): raise ValueError("Invalid published reference extract")
    rows = []
    for crew in [1, 2, 4]:
        for days in [1, 7, 30]:
            for item in rates.itertuples():
                rows.append({"illustrative_crew_count": crew, "illustrative_days": days, "crew_days": crew * days,
                    "quantity": item.quantity, "reference_total": item.nominal_value * crew * days,
                    "unit": item.unit.replace("/crew_day", ""), "source_table": item.source_table,
                    "status": "reference_sensitivity_not_selected_mission"})
    totals = pd.DataFrame(rows)
    totals.to_csv(run.path("crew_duration_reference_load_sensitivity.csv"), index=False)
    rates.assign(steady_equivalent_W=lambda f: np.where(f.unit.eq("MJ/crew_day"), f.nominal_value * 1e6 / 86400, np.nan)).to_csv(run.path("crew_reference_rates.csv"), index=False)
    battery = read_accepted(run, "battery", "cell_ambient_condition_summary.csv")
    # Conditioning groups, not a cross-cell causal ambient-temperature experiment.
    battery.groupby(["protocol_id", "ambient_temperature_C", "documented_stop_voltage_V"], dropna=False).agg(
        cell_condition_groups=("cell_id", "size"), total_discharge_records=("records", "sum"),
        minimum_group_median_energy_Wh=("median_observed_energy_Wh", "min"),
        maximum_group_median_energy_Wh=("median_observed_energy_Wh", "max")).reset_index().to_csv(run.path("protocol_ambient_battery_reference.csv"), index=False)
    dose = read_accepted(run, "radiation", "published_shielding_sensitivity.csv")
    dose.groupby(["solar_scenario", "particles", "depth_cm"]).agg(
        shielding_rows=("effective_dose_cSv_year", "size"), minimum_reference_dose=("effective_dose_cSv_year", "min"),
        maximum_reference_dose=("effective_dose_cSv_year", "max")).reset_index().to_csv(run.path("radiation_reference_scenario_envelope.csv"), index=False)
    soil = read_accepted(run, "soil", "algorithm_reference_features.csv")
    soil.groupby("geometry").agg(runs=("run", "size"), minimum_peak_stress_kPa=("maximum_stress_kPa", "min"),
        maximum_peak_stress_kPa=("maximum_stress_kPa", "max")).reset_index().to_csv(run.path("soil_geometry_reference_envelope.csv"), index=False)
    pd.DataFrame([{"comparison": name, "outcome": "Unknown", "missing": value}
        for name, value in {"consumable_stock_margin": "selected crew/duration, adopted rates, stock/recovery/reserve",
            "power_reserve": "dated terrain-aware generation/load, selected battery/efficiency/reserve",
            "thermal_control_margin": "applicable component/habitat response and limits",
            "communications_outage": "terrain/relay/link schedule and outage requirement",
            "radiation_margin": "applicable dose/transport quantity, exposure duration and limits",
            "foundation_mobility": "local ground properties and selected equipment/loads"}.items()
    ]).to_csv(run.path("operational_margin_input_readiness.csv"), index=False)
    return {"published_reference_rates": len(rates), "crew_duration_sensitivity_rows": len(totals),
        "nominal_oxygen_kg_per_crew_day": float(rates.set_index("quantity").loc["oxygen_consumed", "nominal_value"]),
        "reference_metabolic_heat_W_per_crew": float(rates.set_index("quantity").loc["metabolic_heat_total", "nominal_value"] * 1e6 / 86400),
        "battery_cell_condition_groups": len(battery), "shielding_reference_rows": len(dose), "historical_soil_runs": len(soil),
        "holds": ["All crew/duration combinations are declared sensitivity axes, not mission facts",
                  "Published nominal rates are not approved individual requirements or total logistics allowances",
                  "Battery/soil/radiation records remain protocol/site/scenario references, not local candidate measurements"]}


def execute(kind, notebook):
    functions = {"audit": audit_data, "time_terrain": time_terrain, "references": reference_margins}
    with LocalRun(ROOT, "analysis/stage3_required_" + kind, {"priority": "Stage 3 required work before research P1/P2/P3", "pins": PINS}, notebook) as run:
        run.input(Path(__file__)); run.input(ROOT / "outline.md")
        result = functions[kind](run)
        run.path("findings.json").write_text(json.dumps(result, indent=2, default=str) + "\n", encoding="utf-8")
    print(json.dumps(result, indent=2, default=str)); print("Completed:", run.directory)
    return run.directory
