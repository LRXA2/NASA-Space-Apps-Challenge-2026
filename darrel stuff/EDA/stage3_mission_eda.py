"""Moon-only Step 3 EDA. No adopted gates, rankings, mission defaults or downloads."""
from pathlib import Path
import json
import re
import sys

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

LOCAL = Path(__file__).resolve().parents[1]
ROOT = LOCAL.parent
sys.path[:0] = [str(LOCAL), str(ROOT)]
from data_maintenance import checked_path
from decision_eda import accepted_input
from environment_workflow import LocalRun
from research_p1_readers import read_pds4
from notebooks.shared.inspection import file_hash
from notebooks.shared.processing import MOON_CRS, MOON_GEOGRAPHIC

CONFIG = Path(__file__).with_name("stage3_eda_config.json")


def load_config():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported EDA configuration")
    return config


def accepted_csv(run, folder, name):
    return pd.read_csv(accepted_input(run, folder, name))


def external_input(run, config, item):
    """Add a verified external input without changing LocalRun's existing contract."""
    root = Path(config["external_root"]).resolve()
    path = checked_path(root, item["relative_path"])
    receipt = checked_path(root, item["receipt"])
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    if path.name.endswith(".part") or not path.is_file() or path.stat().st_size != item["size_bytes"]:
        raise ValueError(f"Incomplete external source: {path}")
    digest = file_hash(path)
    if digest != item["sha256"] or saved["sha256"] != digest or saved["source"]["url"] != item["url"]:
        raise ValueError(f"External source/receipt changed: {path}")
    for p in [path, receipt]:
        key = "external_data/" + p.relative_to(root).as_posix()
        run.record["inputs"][key] = {"path": str(p), "bytes": p.stat().st_size,
                                    "sha256": digest if p == path else file_hash(p)}
    return path


def resource_changes(frame):
    """Historical changes; retain source redlines and do not return operational gates."""
    result = frame.copy()
    if result.duplicated(["mission", "eva", "crew_role", "resource"]).any():
        raise ValueError("Repeated primary resource identity")
    fields = ["actual_initial", "actual_consumed", "actual_remaining", "predicted_consumed",
              "predicted_remaining", "reported_actual_redline"]
    if not np.isfinite(result[fields].to_numpy(float)).all() or result[fields].lt(0).any().any():
        raise ValueError("Invalid primary resource values")
    if not np.allclose(result.actual_initial-result.actual_consumed, result.actual_remaining, atol=.011, rtol=0):
        raise ValueError("Primary resource balance changed")
    result["consumed_minus_predicted"] = result.actual_consumed-result.predicted_consumed
    result["consumption_ratio_actual_to_predicted"] = result.actual_consumed.div(result.predicted_consumed.where(result.predicted_consumed.gt(0)))
    result["historical_remaining_minus_source_redline"] = result.actual_remaining-result.reported_actual_redline
    result["assessment_scope"] = "historical Apollo configuration only; not present-site or modern equipment eligibility"
    return result


def percentage_changes(frame):
    result = frame.copy()
    if result.duplicated(["mission", "eva", "crew_role", "resource"]).any():
        raise ValueError("Repeated reconstruction identity")
    for column in ["actual_remaining_percent", "predicted_remaining_percent"]:
        known = result[column].dropna()
        if not np.isfinite(known).all() or not known.between(0, 100).all():
            raise ValueError("Invalid percent remaining")
    result["actual_minus_predicted_remaining_pp"] = result.actual_remaining_percent-result.predicted_remaining_percent
    result["prediction_supported"] = result.predicted_remaining_percent.notna()
    return result


def reference_exposures(frame, days=(1, 7, 30, 90)):
    """Explicit steady-rate sensitivity, not a dated forecast or exposure-limit test."""
    if (not np.isfinite(frame.effective_dose_cSv_year).all() or frame.effective_dose_cSv_year.lt(0).any()
            or any(isinstance(d, bool) or not np.isfinite(d) or d <= 0 for d in days)):
        raise ValueError("Invalid reference dose/duration")
    outputs = []
    for day in days:
        piece = frame.copy()
        piece["illustrative_days"] = day
        # 1 cSv = 10 mSv. Annual rate is assumed constant for this sensitivity only.
        piece["reference_mSv"] = piece.effective_dose_cSv_year*10*day/365.25
        piece["basis"] = "published scenario; assumed steady annual rate; not SPE worst case, crew dose or selected mission"
        outputs.append(piece)
    return pd.concat(outputs, ignore_index=True)


def save_figure(run, fig, name):
    fig.savefig(run.path(name+".png"), dpi=140, bbox_inches="tight")
    plt.close(fig)


def hazard_evidence():
    rows = [
        ("Radiation / solar-particle exposure", "D07/D08 instrument context; D31 published shielding scenarios", "Excess applicable exposure or inadequate protection is a potential mandatory failure, not a preference trade-off", "Orbital counters/proton flux are not local shielded crew dose; actual field, transport, duration and applicable limit remain needed"),
        ("Thermal extremes", "D01/D20 surface radiometry; historical equipment records", "Equipment/crew thermal demand outside supported operating response requires a failed or unresolved mandatory assessment", "Surface brightness is not component temperature; limited temporal/footprint support is not a mission envelope"),
        ("Darkness / power loss", "D02 mean visibility; D19 reference geometry; R01 cell tests", "Life-critical power shortfall cannot be offset by high average illumination", "Terrain-aware dated generation/load, storage, efficiencies and reserves are missing"),
        ("Seismic / structural events", "D13 catalogs; D14 historical waveform and response metadata", "Applicable structural loads exceeding capacity are mandatory risk concerns", "Sparse historical samples do not establish local recurrence, shaking or structural response"),
        ("Impact / plume / ejecta", "D33 selected new-crater catalog; historical deployment records", "Unacceptable impact/ejecta loads on occupied or critical assets cannot be treated as soft costs", "Observation effort, event dates, local probability, plume geometry and protection response are not established"),
        ("Dust / wear / contamination", "D10 orbital dust; documented Apollo visor, glove, fender and radiator effects", "Loss of required cooling, sealing or visibility is a mandatory concern when applicable", "Orbital dust does not quantify local wear or indoor loading; hardware-specific exposure/response is missing"),
        ("Vacuum / atmosphere / life support", "C01 vacuum baseline; S01-S03 references; LM/EMU historical configuration", "Pressure, oxygen, CO2 removal and essential supplies cannot be compensated by site preferences", "Exterior conditions do not prove protected-system capability or internal air/water quality"),
        ("Ground / foundations / mobility", "D05/D06 terrain; R02 historical soil tests", "Unsupported loads or failed required return/mobility capability are mandatory concerns", "Slope and historical probe stress do not supply local bearing capacity, traction or vehicle response"),
        ("Communications loss", "D03 mean Earth visibility; D19 geometry; historical conditional return rules", "Outages exceeding mission-critical communication capability require explicit handling", "Mean visibility is not a working link or contact schedule; Apollo exceptions must not become universal cutoffs"),
        ("Plasma / charging / electronics", "D11 near-lunar ion/plasma context; D22 access gap", "Electrical discharge or electronic damage affecting essential systems is a potential mandatory concern", "Environmental plasma is not a qualified surface charging/discharge or hardware-damage rate"),
        ("Resources / sample chemistry", "D16 spectra; D29/D30/D34 indirect context", "Unverified resources cannot be credited as essential consumable supply", "Local extractability, processing, containment and exposure are unverified"),
        ("Crew workload / contingency", "Apollo plans, primary resource tables and later EVA reconstruction", "Insufficient return, reserve or workload support cannot be hidden by an overall score", "Historical loads and redlines are not an approved new mission/equipment profile"),
    ]
    return pd.DataFrame(rows, columns=["hazard", "available_evidence", "risk_principle_not_implemented_rule", "essential_limitations"]).assign(
        current_site_operational_status="Unknown; no complete applicable mission/equipment/requirement assessment", risk_weight_or_threshold="not adopted")


def resources(run, config):
    folder = LOCAL/"data/processed/analysis"/config["evidence_run"]
    primary = resource_changes(accepted_csv(run, folder, "apollo17_emu_resources.csv"))
    reconstruction = percentage_changes(accepted_csv(run, folder, "eva_percent_remaining.csv"))
    lm = accepted_csv(run, folder, "apollo17_lm_resource_totals.csv")
    narrative = accepted_csv(run, folder, "mission_equipment_evidence.csv")
    primary.to_csv(run.path("primary_resource_changes.csv"), index=False)
    reconstruction.to_csv(run.path("reconstructed_remaining_changes.csv"), index=False)
    summary = reconstruction.groupby("resource").agg(rows=("resource", "size"), paired_rows=("prediction_supported", "sum"),
        minimum_remaining_change_pp=("actual_minus_predicted_remaining_pp", "min"), median_remaining_change_pp=("actual_minus_predicted_remaining_pp", "median"),
        maximum_remaining_change_pp=("actual_minus_predicted_remaining_pp", "max")).reset_index()
    summary.to_csv(run.path("remaining_prediction_summary.csv"), index=False)
    durations = primary.groupby(["mission", "eva", "crew_role"])[["actual_duration_min", "planned_duration_min"]].nunique()
    if not durations.eq(1).all().all():
        raise ValueError("Inconsistent duration across repeated resource rows")
    durations = primary[["mission", "eva", "crew_role", "actual_duration_min", "planned_duration_min"]].drop_duplicates()
    durations["actual_minus_planned_minutes"] = durations.actual_duration_min-durations.planned_duration_min
    durations.to_csv(run.path("historical_eva_durations.csv"), index=False)
    cross = primary.assign(resource=primary.resource.replace({"Battery charge": "Power"})).merge(
        reconstruction.loc[reconstruction.mission.eq("Apollo 17")], on=["mission", "eva", "crew_role", "resource"], validate="one_to_one", suffixes=("_primary", "_reconstruction"))
    cross["percent_from_rounded_primary_initial"] = 100*cross.actual_remaining/cross.actual_initial
    cross["reconstruction_minus_primary_pp"] = cross.actual_remaining_percent-cross.percent_from_rounded_primary_initial
    cross.to_csv(run.path("related_source_consistency.csv"), index=False)
    lm["actual_minus_predicted"] = lm.actual-lm.predicted
    lm.to_csv(run.path("lm_aggregate_changes.csv"), index=False)
    narrative.loc[narrative.topic.isin(["thermal operation", "consumable reserve", "duration", "communications", "return capability"])].to_csv(run.path("historical_context_not_adopted_limits.csv"), index=False)
    hazard_evidence().to_csv(run.path("hazard_evidence_boundaries.csv"), index=False)
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    for ax, resource in zip(axes, ["Oxygen", "Feedwater", "Power"]):
        for mission, group in reconstruction.loc[reconstruction.resource.eq(resource)].groupby("mission"):
            ax.scatter(group.predicted_remaining_percent, group.actual_remaining_percent, label=mission, s=28)
        ax.plot([0, 60], [0, 60], "k--", lw=.8)
        ax.set(title=resource, xlabel="Predicted remaining (%)", ylabel="Actual remaining (%)")
    axes[-1].legend(fontsize=7)
    fig.suptitle("Related historical EVA records, not independent missions or safety labels")
    save_figure(run, fig, "planned_actual_remaining")
    fig, axes = plt.subplots(1, 3, figsize=(13, 4), layout="constrained")
    for ax, resource in zip(axes, primary.resource.unique()):
        for crew, group in primary.loc[primary.resource.eq(resource)].groupby("crew_role"):
            ax.plot(group.eva, group.historical_remaining_minus_source_redline, marker="o", label=crew)
        ax.axhline(0, color="k", ls="--", lw=.8)
        ax.set(title=resource, xlabel="Apollo 17 EVA", ylabel="Remaining minus historical redline ("+primary.loc[primary.resource.eq(resource), "unit"].iloc[0]+")", xticks=[1,2,3])
    axes[-1].legend()
    fig.suptitle("Historical source reserves only; not modern equipment or lunar-site eligibility")
    save_figure(run, fig, "historical_resource_headroom")
    return {"primary_resource_rows": len(primary), "reconstruction_rows": len(reconstruction),
            "paired_reconstruction_rows": int(reconstruction.prediction_supported.sum()),
            "primary_consumption_over_prediction_rows": int(primary.consumed_minus_predicted.gt(0).sum()),
            "minimum_source_redline_headroom_by_resource": primary.groupby("resource").historical_remaining_minus_source_redline.min().to_dict(),
            "eva_duration_overruns_min": durations.groupby("eva").actual_minus_planned_minutes.first().to_dict(),
            "related_source_maximum_absolute_difference_pp": float(cross.reconstruction_minus_primary_pp.abs().max()),
            "holds": ["Historical redlines/configurations not adopted", "Primary and reconstructed tables are related sources", "No EDA-derived hard gates or preference weights", "Reported real-time duration exceeds preflight plan; not automatic retrospective violation"]}


def goes_observations(path):
    import netCDF4 as nc
    with nc.Dataset(path) as source:
        tv = source["time"]
        times = pd.to_datetime(nc.num2date(tv[:], tv.units, only_use_cftime_datetimes=False), utc=True)
        values = lambda key: np.ma.asarray(source[key][:]).astype(float).filled(np.nan)
        flux, samples = values("AvgDiffProtonFlux"), values("DiffValidL1bSamplesInAvg")
        flags = [values(key) for key in ["DiffDQFdtcSum", "DiffDQFoobSum", "DiffDQFerrSum"]]
        lut = int(source["ExpectedLUTNotFound"][...])
        if source["AvgDiffProtonFlux"].units != "protons/(cm^2 sr keV s)":
            raise ValueError("Changed GOES flux units")
        low, high = values("DiffProtonLowerEnergy"), values("DiffProtonUpperEnergy")
        rows = []
        for sensor in range(flux.shape[1]):
            for channel in range(flux.shape[2]):
                finite = np.isfinite(flux[:,sensor,channel]) & (flux[:,sensor,channel] >= 0)
                good = finite & (samples[:,sensor,channel] >= 300) & (lut == 1)
                for flag in flags:
                    good &= flag[:,sensor,channel] == 0
                rows.append(pd.DataFrame({"timestamp": times, "sensor": sensor, "channel": channel,
                    "lower_energy_keV": low[sensor,channel], "upper_energy_keV": high[sensor,channel],
                    "flux": flux[:,sensor,channel], "strict_quality": good, "finite_nonnegative": finite,
                    "lookup_tables_matched": lut == 1, "error_flag_sum": flags[2][:,sensor,channel]}))
    return pd.concat(rows, ignore_index=True)


def radiation(run, config):
    rows, hourly, coverage = [], [], []
    for sample in config["radiation_days"]:
        crater = [external_input(run, config, f) for f in sample["D07"]["files"]]
        label = next(p for p in crater if p.suffix.lower()==".xml")
        frame = read_pds4(label)
        frame["timestamp"] = pd.to_datetime(frame.TIME, utc=True)
        normal = frame.BIASCMD.eq(1)&frame.CALLOW.eq(0)&frame.CALHIGH.eq(0)&frame[[f"PROCDFLAG {i}" for i in range(1,7)]].eq(1).all(axis=1)
        gaps = frame.timestamp.diff().dt.total_seconds()
        coverage.append({"date":sample["date"],"dataset":"D07","rows":len(frame),"strict_rows":int(normal.sum()),
                         "cadence_gap_count":int(gaps.gt(1.01).sum()),"quantity":"per-record counters, not local dose"})
        h=frame.loc[normal].set_index("timestamp")[["GOOD","REJECT","TOTAL"]].resample("1h").median().reset_index()
        h["sample_date"]=sample["date"];hourly.append(h)
        path=external_input(run,config,sample["D08"]["files"][0])
        obs=goes_observations(path);obs["sample_date"]=sample["date"]
        rows.append(obs)
        coverage.append({"date":sample["date"],"dataset":"D08","rows":len(obs),"strict_rows":int(obs.strict_quality.sum()),
                         "cadence_gap_count":int(obs.timestamp.drop_duplicates().sort_values().diff().dt.total_seconds().gt(300.01).sum()),
                         "quantity":"Earth-orbit directional differential proton flux; not lunar dose"})
    observations=pd.concat(rows,ignore_index=True)
    hour=pd.concat(hourly,ignore_index=True)
    groups=[]
    for key, part in observations.groupby(["sample_date","sensor","channel","lower_energy_keV","upper_energy_keV"]):
        accepted=part.loc[part.strict_quality,"flux"]
        groups.append(dict(zip(["sample_date","sensor","channel","lower_energy_keV","upper_energy_keV"],key),
            recorded_rows=len(part),accepted_rows=len(accepted),diagnostic_unqualified_median_flux=part.loc[part.finite_nonnegative,"flux"].median(),
            qualified_median_flux=accepted.median(), observed_qualified_bin_integral=accepted.sum()*300 if len(accepted) else np.nan,
            integral_scope="Only supported 300-second bins; not event-total fluence or dose; no bridging gaps"))
    pd.DataFrame(groups).to_csv(run.path("goes_quality_and_supported_integrals.csv"),index=False)
    pd.DataFrame(coverage).to_csv(run.path("radiation_sample_coverage.csv"),index=False)
    hour.to_csv(run.path("crater_hourly_counter_context.csv"),index=False)
    observations.groupby(["sample_date","lookup_tables_matched","error_flag_sum","strict_quality"],dropna=False).size().rename("rows").reset_index().to_csv(run.path("goes_quality_states.csv"),index=False)
    folder=LOCAL/"data/processed/analysis"/config["radiation_reference_run"]
    dose=accepted_csv(run,folder,"published_dose_depth_scenarios.csv")
    selected=dose.loc[dose.particles.eq("all") & dose.depth_cm.isin([0,10,100])].copy()
    if selected.empty:raise ValueError("No requested published scenario support")
    exposure=reference_exposures(selected)
    exposure.to_csv(run.path("reference_radiation_duration_sensitivity.csv"),index=False)
    paired=dose.merge(dose.loc[dose.al_g_cm2.eq(dose.al_g_cm2.min()),["solar_scenario","particles","depth_cm","effective_dose_cSv_year"]].rename(columns={"effective_dose_cSv_year":"minimum_Al_reference_rate"}),on=["solar_scenario","particles","depth_cm"],validate="many_to_one")
    paired["rate_minus_minimum_Al_reference"]=paired.effective_dose_cSv_year-paired.minimum_Al_reference_rate
    paired.to_csv(run.path("shielding_component_direction_sensitivity.csv"),index=False)
    hazard_evidence().to_csv(run.path("hazard_evidence_boundaries.csv"),index=False)
    seismic=accepted_csv(run,LOCAL/"data/processed/analysis"/config["seismic_run"],"catalog_class_counts.csv")
    impact=accepted_csv(run,LOCAL/"data/processed/analysis"/config["impact_run"],"new_crater_catalog.csv")
    seismic.assign(interpretation="catalog entries, not independent events or local recurrence").to_csv(run.path("seismic_evidence_context.csv"),index=False)
    impact[[c for c in ["lat","lon","diam_m","before_img","after_img"] if c in impact]].assign(interpretation="selected detections; no observation-effort/time-normalized site probability").to_csv(run.path("impact_evidence_context.csv"),index=False)
    fig,axes=plt.subplots(1,2,figsize=(13,4),layout="constrained")
    for date, part in hour.groupby("sample_date"):
        axes[0].plot(part.timestamp.dt.hour,part.GOOD,label=date)
    axes[0].set(xlabel="UTC hour",ylabel="Median GOOD counter / SEC record",title="Different sampled days; not surface dose");axes[0].legend(fontsize=7)
    for scenario,part in selected.loc[selected.depth_cm.eq(0)].groupby("solar_scenario"):
        axes[1].plot(part.al_g_cm2,part.effective_dose_cSv_year,marker="o",label=scenario)
    axes[1].set(xlabel="Published Al areal density (g/cm²)",ylabel="Published effective dose (cSv/year)",title="Surface scenario, not candidate protection adequacy");axes[1].legend(fontsize=7)
    save_figure(run,fig,"radiation_context_and_reference_shielding")
    return {"sample_dates":[x["date"] for x in config["radiation_days"]],"goes_channel_time_rows":len(observations),
            "qualified_goes_rows":int(observations.strict_quality.sum()),"crater_seconds":sum(x["rows"] for x in coverage if x["dataset"]=="D07"),
            "published_duration_scenarios":len(exposure),"seismic_catalog_entries":int(seismic.catalog_entries.sum()),"selected_impact_entries":len(impact),
            "published_components_with_rate_increase_over_minimum_Al":int(paired.rate_minus_minimum_Al_reference.gt(0).sum()),
            "holds":["No numeric local radiation safety cutoff adopted", "Unqualified flux is not zero exposure", "Steady reference scaling does not bound solar events", "Catalog entries cannot certify low disaster risk"]}


def read_diviner_query(table, label):
    text=Path(label).read_text(encoding="utf-8")
    header=re.search(r'\^TABLE\s*=\s*\("([^"\n]+)",\s*(\d+)\)',text)
    record_bytes=int(re.search(r"^RECORD_BYTES\s*=\s*(\d+)",text,re.M)[1])
    file_records=int(re.search(r"^FILE_RECORDS\s*=\s*(\d+)",text,re.M)[1])
    if not header or Path(table).name!=header[1] or Path(table).stat().st_size!=record_bytes*file_records:
        raise ValueError("Diviner label/file size or identity mismatch")
    # ODE's supplied label misspells the opening of column 17 as COLUM.
    # Accept only that documented spelling variant; require all numbered fields.
    columns=re.findall(r"^OBJECT\s*=\s*COLUM(?:N)?\b(.*?)^END_OBJECT\s*=\s*COLUMN",text,re.S|re.M)
    names=[re.search(r"\bNAME\s*=\s*(\w+)",block)[1] for block in columns]
    numbers=[int(re.search(r"COLUMN_NUMBER\s*=\s*(\d+)",block)[1]) for block in columns]
    if len(names)!=33 or len(set(names))!=33 or numbers!=list(range(1,34)):
        raise ValueError("Unexpected Diviner schema")
    skip=int(header[2])-1
    frame=pd.read_csv(table,skiprows=skip,header=None,names=names,skipinitialspace=True)
    if len(frame)!=file_records-skip:raise ValueError("Diviner row count mismatch")
    for name in set(names)-{"date","utc"}:frame[name]=pd.to_numeric(frame[name],errors="raise")
    frame["timestamp"]=pd.to_datetime(frame.date.str.strip().str.strip('"')+" "+frame.utc.str.strip().str.strip('"'),format="%d-%b-%Y %H:%M:%S.%f",utc=True)
    frame.attrs["source_label_COLUM_openings"]=len(re.findall(r"^OBJECT\s*=\s*COLUM\s*$",text,re.M))
    return frame


def thermal_quality(frame, bounds):
    from pyproj import Transformer
    f=frame.copy()
    valid_coordinates=f.clon.between(-360,360)&f.clat.between(-90,90)
    x,y=Transformer.from_crs(MOON_GEOGRAPHIC,MOON_CRS,always_xy=True).transform(f.clon.where(valid_coordinates),f.clat.where(valid_coordinates))
    west,south,east,north=bounds
    f["in_region"]=valid_coordinates & (x>=west)&(x<=east)&(y>=south)&(y<=north)
    f["physical_temperature"]=np.isfinite(f.tb)&f.tb.gt(0)
    f["strict_quality"]=f.in_region&f.physical_temperature&f.qca.eq(0)&f.qge.eq(0)&f.qmi.eq(0)
    f["download_policy_diagnostic"]=f.in_region&f.physical_temperature&f.qca.eq(0)&f.qge.between(0,12)&f.qmi.eq(0)
    f["local_hour"]=np.floor(f.cloctime.where(f.cloctime.between(0,24))%24)
    return f


def thermal(run,config):
    summaries,flags,profiles=[],[],[]
    for product in config["thermal_products"]:
        paths=[external_input(run,config,f) for f in product["files"]]
        tab=next(p for p in paths if p.suffix.lower()==".tab");label=next(p for p in paths if p.suffix.lower()==".lbl")
        f=read_diviner_query(tab,label)
        if not f.c.eq(product["channel"]).all():raise ValueError("Channel differs from frozen selection")
        if f.duplicated(["sclk","c","det"]).any():
            raise ValueError("Repeated native observation identity; review before weighting")
        f=thermal_quality(f,config["region_bounds_m"][product["region"]])
        identity={"region":product["region"],"channel":product["channel"],"month":product["month"]}
        summaries.append({**identity,"source_label_COLUM_openings":f.attrs["source_label_COLUM_openings"],"rows":len(f),"in_region_rows":int(f.in_region.sum()),"nonpositive_or_missing_tb":int((~f.physical_temperature).sum()),
                          "strict_rows":int(f.strict_quality.sum()),"download_policy_diagnostic_rows":int(f.download_policy_diagnostic.sum()),
                          "observed_days":f.timestamp.dt.floor("D").nunique(),"timestamp_start":f.timestamp.min(),"timestamp_end":f.timestamp.max()})
        for key,n in f.groupby(["qca","qge","qmi"]).size().items():flags.append({**identity,"qca":key[0],"qge":key[1],"qmi":key[2],"rows":n})
        for cohort in ["strict_quality","download_policy_diagnostic"]:
            p=f.loc[f[cohort]].groupby("local_hour").tb.agg(["count","median","min","max"]).reset_index()
            for row in p.to_dict("records"):profiles.append({**identity,"cohort":cohort,**row})
    summary=pd.DataFrame(summaries);flag=pd.DataFrame(flags)
    profile=pd.DataFrame(profiles,columns=["region","channel","month","cohort","local_hour","count","median","min","max"])
    summary.to_csv(run.path("dated_thermal_support.csv"),index=False)
    flag.to_csv(run.path("dated_thermal_quality_flags.csv"),index=False)
    profile.to_csv(run.path("dated_thermal_local_hour_profiles.csv"),index=False)
    bits=[]
    for value,part in flag.groupby("qge"):
        bits.append({"qge":value,"set_bit_values":";".join(str(1<<i) for i in range(8) if int(value)&(1<<i)),"rows":int(part.rows.sum()),
                     "interpretation":"Nonzero geometry flags retained; bit semantics require applicable SIS review, not silently approved"})
    pd.DataFrame(bits).to_csv(run.path("geometry_flag_bit_patterns.csv"),index=False)
    fig,axes=plt.subplots(1,len(summary.channel.unique()),figsize=(12,4),layout="constrained",squeeze=False)
    for ax,channel in zip(axes[0],sorted(summary.channel.unique())):
        for month,part in profile.loc[profile.channel.eq(channel)&profile.cohort.eq("download_policy_diagnostic")].groupby("month"):
            ax.scatter(part.local_hour,part["median"],label=month)
        ax.set(xlabel="Lunar local solar hour",ylabel="Channel brightness temperature (K)",title=f"Channel {channel}: flagged diagnostic, not equipment response")
        if len(profile):ax.legend(fontsize=7)
    save_figure(run,fig,"dated_thermal_diagnostic_profiles")
    return {"products":len(summary),"regions":int(summary.region.nunique()),"channels":sorted(summary.channel.unique().tolist()),
            "observations":int(summary.rows.sum()),"in_region_observations":int(summary.in_region_rows.sum()),
            "strict_observations":int(summary.strict_rows.sum()),"nonpositive_or_missing_tb":int(summary.nonpositive_or_missing_tb.sum()),
            "diagnostic_observations":int(summary.download_policy_diagnostic_rows.sum()),
            "holds":["Not full seven-region acquisition or mission-temperature history", "Single-channel brightness is not bolometric/equipment temperature", "Nonzero quality flags remain qualified diagnostics", "Different month samples do not establish climate trend or mission extremes"]}


def execute(kind,notebook):
    config=load_config()
    functions={"resources":resources,"radiation":radiation,"thermal":thermal}
    with LocalRun(ROOT,"analysis/stage3_"+kind+"_eda",config,notebook) as run:
        run.input(CONFIG);run.input(Path(__file__))
        findings=functions[kind](run,config)
        run.path("findings.json").write_text(json.dumps(findings,indent=2,default=str),encoding="utf-8")
        print(json.dumps(findings,indent=2,default=str))
        folder=run.directory
    return folder,findings
