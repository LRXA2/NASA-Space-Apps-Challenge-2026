"""Historical UTC monthly/quarterly context; never a lunar-season or safety forecast."""
from pathlib import Path
import argparse
import json
import sys
import zipfile

sys.path[:0] = [str(Path(__file__).resolve().parents[2] / "shared"),
               str(Path(__file__).resolve().parents[3]), str(Path(__file__).resolve().parents[4])]

import cdflib
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from decision_eda import accepted_input
from environment_workflow import LocalRun
from stage3_mission_eda import ROOT, LOCAL, external_input, save_figure

CONFIG = Path(__file__).with_name("stage3_temporal_config.json")
NOTEBOOK = "Moon/Stage3_Requirements/Dar_043_temporal_environment.ipynb"
UV_COLUMNS = ["nominal_date", "jdn", "low_nm", "high_nm", "mode", "version",
              "irradiance", "uncertainty", "quality"]
VALUE_COLUMNS = ["daily_median", "daily_p95", "daily_max"]


def uv_days(frame, band):
    """Integrate only complete, quality=0, fixed 1-nm daily spectra; no partial sums."""
    low, high = {"FUV": (115, 180), "MUV": (180, 310)}[band]
    f = frame.copy()
    if not f["mode"].eq({"FUV": 11, "MUV": 9}[band]).all():
        raise ValueError("UV instrument mode does not match the selected spectral band")
    f["date"] = pd.to_datetime(np.floor(f.nominal_date).astype("int64").astype(str), format="%Y%m%d", utc=True)
    if f.duplicated(["date", "mode", "version", "low_nm", "high_nm"]).any():
        raise ValueError("Duplicate UV wavelength/date/mode/version")
    if not f.quality.isin([0, 1, 2, 3]).all():
        raise ValueError("Unknown SOLSTICE quality flag; review publisher semantics")
    rows = []
    for (date, mode, version), g in f.groupby(["date", "mode", "version"], sort=True):
        g = g.sort_values("low_nm")
        structure = (len(g) == high-low and np.array_equal(g.low_nm.to_numpy(), np.arange(low, high))
                     and np.array_equal(g.high_nm.to_numpy(), np.arange(low+1, high+1)))
        good = (g.quality.eq(0) & np.isfinite(g.irradiance) & g.irradiance.ge(0)
                & np.isfinite(g.uncertainty) & g.uncertainty.ge(0))
        value = float(g.irradiance.sum()) if structure and good.all() else np.nan
        rows.append({"series_id": f"UV_SOLSTICE_{band}_mode{int(mode)}_v{int(version)}",
                     "date": date, "daily_median": value, "daily_p95": np.nan, "daily_max": value,
                     "recorded_samples": len(g), "valid_samples": int(good.sum()), "valid_seconds": np.nan,
                     "complete_spectrum": bool(structure and good.all())})
    return pd.DataFrame(rows)


def read_uv(path, band, sample=False):
    """Bounded chunks with a carried final day; never cut a spectrum at chunk boundaries."""
    rows, carry = [], pd.DataFrame()
    last_date = None
    with zipfile.ZipFile(path) as package:
        if len(package.namelist()) != 1 or not package.namelist()[0].endswith(".txt"):
            raise ValueError("Expected a single SOLSTICE ASCII member")
        with package.open(package.namelist()[0]) as stream:
            for chunk in pd.read_csv(stream, sep=r"\s+", comment=";", names=UV_COLUMNS,
                                     chunksize=32760, encoding="latin-1"):
                if chunk.isna().any().any() or not chunk.nominal_date.is_monotonic_increasing:
                    raise ValueError("Invalid or unordered SOLSTICE records")
                if last_date is not None and chunk.nominal_date.iloc[0] < last_date:
                    raise ValueError("Unordered SOLSTICE chunks")
                last_date = chunk.nominal_date.iloc[-1]
                batch = pd.concat([carry, chunk], ignore_index=True)
                last = np.floor(batch.nominal_date.iloc[-1])
                keep = np.floor(batch.nominal_date).eq(last)
                ready, carry = batch.loc[~keep], batch.loc[keep].copy()
                if not ready.empty:
                    rows.append(uv_days(ready, band))
                if sample:
                    break
    if not carry.empty:
        rows.append(uv_days(carry, band))
    result = pd.concat(rows, ignore_index=True)
    if result.duplicated(["series_id", "date"]).any():
        raise ValueError("Repeated daily UV identity")
    return result


def cdf_values(cdf, name):
    """Honor publisher fill and validity ranges, including vector component bounds."""
    attrs = cdf.varattsget(name)
    values = np.asarray(cdf.varget(name), dtype=float)
    good = np.isfinite(values)
    for field, op in [("VALIDMIN", np.greater_equal), ("VALIDMAX", np.less_equal)]:
        if field not in attrs:
            raise ValueError(f"Missing CDF {field}: {name}")
        good &= op(values, attrs[field])
    if "FILLVAL" not in attrs:
        raise ValueError(f"Missing CDF fill value: {name}")
    good &= values != attrs["FILLVAL"]
    return np.where(good, values, np.nan), attrs


def position_groups(xyz, edges=(1, 5, 20)):
    """Descriptive SSE geometry only, NOT a solar-wind/magnetotail classification."""
    if list(edges) != [1, 5, 20]:
        raise ValueError("Review changed descriptive position bins explicitly")
    radius = np.linalg.norm(xyz, axis=1)
    usable = np.isfinite(xyz).all(axis=1) & (radius >= 1)
    labels = np.full(len(radius), "unknown_position", dtype=object)
    for i, label in enumerate(["1to5Rm", "5to20Rm", "ge20Rm"]):
        selected = usable & (radius >= edges[i])
        if i+1 < len(edges):
            selected &= radius < edges[i+1]
        labels[selected & (xyz[:, 0] >= 0)] = "SSE_x_nonnegative_"+label
        labels[selected & (xyz[:, 0] < 0)] = "SSE_x_negative_"+label
    return labels, radius


def plasma_file(path, edges):
    cdf = cdflib.CDF(str(path))
    epoch = np.asarray(cdf.varget("Epoch"))
    if not np.isfinite(epoch).all() or (epoch == cdf.varattsget("Epoch")["FILLVAL"]).any():
        raise ValueError("Invalid plasma epochs")
    times = pd.DatetimeIndex(pd.to_datetime(cdflib.cdfepoch.to_datetime(epoch), utc=True))
    if times.hasnans or times.has_duplicates or not times.is_monotonic_increasing:
        raise ValueError("Duplicate, missing or unordered plasma timestamps")
    expected_month = pd.to_datetime(path.name.split("_")[3], format="%Y%m%d").strftime("%Y-%m")
    if not (times.strftime("%Y-%m") == expected_month).all():
        raise ValueError("CDF timestamp/month identity mismatch")
    xyz, attributes = cdf_values(cdf, "XYZ_SSE")
    if attributes["UNITS"] != "Rm" or len(xyz) != len(times):
        raise ValueError("Unrecognised plasma position units/alignment")
    groups, radius = position_groups(xyz, edges)
    version = path.stem.rsplit("_", 1)[1]
    variables = {"thb_peif_densityQ": "n/cc", "thb_peif_vthermalQ": "km/s",
                 "thb_peif_vflowspeedQ": "km/s", "thb_fgs_btotal": "1/N SUM |B|, nT"}
    rows, catalog = [], []
    for name, units in variables.items():
        value, attrs = cdf_values(cdf, name)
        if attrs["UNITS"] != units or attrs["DEPEND_0"] != "Epoch" or len(value) != len(times):
            raise ValueError("Changed plasma quantity/epoch/units")
        f = pd.DataFrame({"date": times.floor("D"), "value": value, "position": groups})
        for position in ["all_positions", *sorted(set(groups))]:
            part = f if position == "all_positions" else f.loc[f.position.eq(position)]
            sid = f"PLASMA_THB_{version}_{name}_{position}"
            daily = part.groupby("date").value.agg(recorded_samples="size", valid_samples="count",
                                                   daily_median="median", daily_max="max")
            daily["daily_p95"] = part.groupby("date").value.quantile(.95)
            daily["series_id"], daily["valid_seconds"] = sid, np.nan
            rows.append(daily.reset_index())
            catalog.append({"series_id": sid, "environment": "plasma", "instrument": "ARTEMIS_THB",
                "version": version, "channel": name, "unit": units, "position_group": position,
                "daily_statistic": "record-weighted median; measured variable cadence, NOT time-weighted",
                "validity_basis": "publisher good-Q plasma selection plus CDF FILLVAL/VALIDMIN/VALIDMAX; FGM range-screened",
                "spatial_scope": "spacecraft position, NOT candidate surface potential or discharge risk"})
    delta = np.diff(times.asi8)/1e9
    info = {"file": path.name, "version": version, "records": len(times),
        "first_utc": times.min().isoformat(), "last_utc": times.max().isoformat(),
        "cadence_96s_pairs": int(np.isclose(delta, 96, atol=1).sum()),
        "cadence_384s_pairs": int(np.isclose(delta, 384, atol=1).sum()),
        "observed_delta_p10_seconds": float(np.quantile(delta, .1)),
        "observed_delta_median_seconds": float(np.median(delta)),
        "observed_delta_p90_seconds": float(np.quantile(delta, .9)),
        "gaps_over_600s": int((delta > 600).sum()), "maximum_gap_seconds": float(delta.max()),
        "unknown_position_records": int((groups == "unknown_position").sum()),
        "radius_min_Rm": float(np.nanmin(radius)), "radius_max_Rm": float(np.nanmax(radius)),
        "scope": "cadence diagnostics, not integrated valid observation time; 600s is not a safety limit"}
    metadata = {"file": path.name, "global": cdf.globalattsget(),
                "variables": {v: cdf.varattsget(v) for v in ["Epoch", "XYZ_SSE", *variables]}}
    return pd.concat(rows, ignore_index=True), pd.DataFrame(catalog), info, metadata


def radiation_daily(run, config):
    rows, catalog = [], []
    for kind, folder in config["radiation_sources"].items():
        name = "goes_daily_directional_support.csv" if kind == "radiation_goes" else "crater_daily_context.csv"
        f = pd.read_csv(accepted_input(run, LOCAL/"data/processed/analysis"/folder, name), low_memory=False)
        if kind == "radiation_goes":
            keys = ["platform", "version", "sensor", "channel", "lower_energy_keV", "upper_energy_keV"]
            for identity, g in f.groupby(keys, dropna=False):
                platform, version, sensor, channel, low, high = identity
                sid = f"RAD_GOES{platform}_{version}_s{sensor}_c{channel}_{low}-{high}keV"
                r = g.rename(columns={"qualified_median_flux": "daily_median", "qualified_max_flux": "daily_max",
                    "recorded_bins": "recorded_samples", "qualified_bins": "valid_samples", "qualified_seconds": "valid_seconds"}).copy()
                r["series_id"], r["daily_p95"] = sid, np.nan
                rows.append(r)
                catalog.append({"series_id": sid, "environment": "radiation", "instrument": f"GOES{platform}",
                    "version": version, "channel": f"sensor{sensor}/channel{channel}/{low}-{high}keV",
                    "unit": "protons/(cm2 s sr keV)", "position_group": "geostationary_spacecraft",
                    "daily_statistic": "median of qualified 5-minute directional flux bins",
                    "validity_basis": "existing Dar_041 strict quality and energy lookup checks",
                    "spatial_scope": "GOES, NOT local lunar flux or transported dose"})
        else:
            sid = "RAD_CRATER_SEC_selected_state"
            r = f.rename(columns={"selected_state_good_median": "daily_median", "selected_state_good_p95": "daily_p95",
                "selected_state_good_max": "daily_max", "records": "recorded_samples",
                "supported_nonnegative_counter_records": "valid_samples"}).copy()
            r["series_id"], r["valid_seconds"] = sid, np.nan
            rows.append(r)
            catalog.append({"series_id": sid, "environment": "radiation", "instrument": "LRO_CRATER_SEC",
                "version": config["crater_product_version"], "channel": "GOOD_counter_selected_state", "unit": "counts/SEC record",
                "position_group": "LRO_orbit", "daily_statistic": "median of supported selected-state counters",
                "validity_basis": "existing Dar_041 selected instrument state and nonnegative counter checks",
                "spatial_scope": "orbital counters, NOT crew dose or a calibrated event catalogue"})
    return pd.concat(rows, ignore_index=True), pd.DataFrame(catalog)


def period_summary(daily, frequency):
    """Equal weight per valid day; never call quantiles of daily medians raw-record quantiles."""
    if frequency not in {"M", "Q"}:
        raise ValueError("Use calendar months or quarters")
    if daily.duplicated(["series_id", "date"]).any():
        raise ValueError("Duplicate series/date")
    rows = []
    for sid, g in daily.groupby("series_id", sort=True):
        g = g.copy()
        date = pd.to_datetime(g.date, utc=True).dt.tz_localize(None)
        g["period"] = date.dt.to_period(frequency)
        for period in pd.period_range(g.period.min(), g.period.max(), freq=frequency):
            f = g.loc[g.period.eq(period)]
            valid = f.daily_median.dropna()
            expected = (period.end_time.normalize()-period.start_time).days+1
            seconds = f.valid_seconds.sum(min_count=1)
            rows.append({"series_id": sid, "period": str(period), "year": period.year,
                "period_kind": "calendar_month" if frequency == "M" else "calendar_quarter",
                "period_start_utc": period.start_time.tz_localize("UTC").isoformat(),
                "period_stop_exclusive_utc": (period+1).start_time.tz_localize("UTC").isoformat(),
                "expected_calendar_days": expected, "recorded_days": len(f), "valid_days": len(valid),
                "valid_day_fraction": len(valid)/expected, "recorded_samples": int(f.recorded_samples.sum()),
                "valid_samples": int(f.valid_samples.sum()), "valid_seconds": seconds,
                "valid_time_fraction": seconds/(expected*86400) if pd.notna(seconds) else np.nan,
                "median_of_daily_medians": valid.median(), "p95_of_daily_medians": valid.quantile(.95),
                "maximum_observed_value": f.daily_max.max(),
                "maximum_daily_p95": f.daily_p95.max(),
                "comparison_scope": "historical same-series descriptive levels; NOT safety, forecast or lunar season"})
    return pd.DataFrame(rows)


def within_year_comparison(periods):
    """Describe contrasts only; retain sparse cells rather than announcing a safest month."""
    f = periods.copy()
    keys = ["series_id", "year"]
    f["observed_level_order_within_year"] = f.groupby(keys).median_of_daily_medians.rank(method="min")
    f["comparable_nonempty_periods"] = f.groupby(keys).median_of_daily_medians.transform("count")
    f["coverage_note"] = "Check valid days/time and position/cadence; ranks are NOT risk or seasonal significance"
    return f


def support_table(daily, catalog):
    rows = []
    for sid, g in daily.groupby("series_id", sort=True):
        times = pd.to_datetime(g.date, utc=True)
        rows.append({"series_id": sid, "start_utc": times.min().isoformat(),
            "stop_exclusive_utc": (times.max()+pd.Timedelta(days=1)).isoformat(),
            "recorded_dates": len(g), "valid_dates": int(g.daily_median.notna().sum()),
            "valid_samples": int(g.valid_samples.sum()), "recorded_samples": int(g.recorded_samples.sum()),
            "valid_seconds": g.valid_seconds.sum(min_count=1),
            "candidate_operational_conclusion": "Unknown"})
    return pd.DataFrame(rows).merge(catalog, on="series_id", validate="one_to_one")


def overlap_table(support):
    rows = []
    for a, b in [("UV", "plasma"), ("UV", "radiation"), ("plasma", "radiation")]:
        left, right = support.loc[support.environment.eq(a)], support.loc[support.environment.eq(b)]
        start = max(pd.to_datetime(left.start_utc, utc=True).min(), pd.to_datetime(right.start_utc, utc=True).min())
        stop = min(pd.to_datetime(left.stop_exclusive_utc, utc=True).max(), pd.to_datetime(right.stop_exclusive_utc, utc=True).max())
        rows.append({"left": a, "right": b, "span_overlap_days": max(0., (stop-start).total_seconds()/86400),
                     "simultaneous_correlation_performed": False,
                     "reason": "Span overlap is not matched qualified timestamps or co-located measurements"})
    return pd.DataFrame(rows)


def plots(run, daily, monthly, quarterly, catalog):
    # Fixed identities, not selected because they happen to look quiet or extreme.
    chosen = catalog.loc[(catalog.instrument.eq("LRO_CRATER_SEC")) | catalog.environment.eq("UV")
        | (catalog.environment.eq("plasma") & catalog.channel.eq("thb_peif_densityQ")
           & catalog.position_group.eq("all_positions"))]
    goes = catalog.loc[catalog.instrument.str.startswith("GOES")].groupby("instrument", sort=True).head(1)
    chosen = pd.concat([chosen, goes]).drop_duplicates("series_id")
    for item in chosen.to_dict("records"):
        sid = item["series_id"]
        f = monthly.loc[monthly.series_id.eq(sid)].copy()
        f["month"] = f.period.str[-2:].astype(int)
        fig, axes = plt.subplots(1, 2, figsize=(12, 5), layout="constrained")
        for ax, field, title in zip(axes, ["median_of_daily_medians", "valid_day_fraction"],
                                   ["Median of valid daily values", "Valid-day fraction (NOT time coverage)"]):
            grid = f.pivot(index="year", columns="month", values=field).reindex(columns=range(1, 13))
            im = ax.imshow(grid.to_numpy(float), aspect="auto", interpolation="nearest")
            ax.set(xticks=range(12), xticklabels=range(1, 13), yticks=range(len(grid)),
                   yticklabels=grid.index, xlabel="UTC calendar month", title=title)
            fig.colorbar(im, ax=ax)
        fig.suptitle(sid+"\n"+item["unit"]+"; historical context, NOT site safety", fontsize=9)
        save_figure(run, fig, "monthly_"+sid)
        part = daily.loc[daily.series_id.eq(sid)]
        fig, ax = plt.subplots(figsize=(12, 3), layout="constrained")
        ax.scatter(pd.to_datetime(part.date, utc=True), part.daily_median, s=2, label="Daily median / UV daily band integral")
        ax.scatter(pd.to_datetime(part.date, utc=True), part.daily_max, s=2, alpha=.4, label="Observed daily maximum (cadence-limited)")
        ax.set(ylabel=item["unit"], title=sid+"; short peaks retained, gaps not filled")
        ax.legend(fontsize=7)
        save_figure(run, fig, "daily_"+sid)
        q = quarterly.loc[quarterly.series_id.eq(sid)]
        fig, axes = plt.subplots(2, 1, figsize=(12, 5), sharex=True, layout="constrained")
        axes[0].scatter(pd.to_datetime(q.period_start_utc, utc=True), q.median_of_daily_medians, s=15)
        axes[0].set(ylabel=item["unit"], title=sid+"; UTC quarters by year, NOT lunar seasons")
        axes[1].scatter(pd.to_datetime(q.period_start_utc, utc=True), q.valid_day_fraction, s=15)
        axes[1].set(ylabel="Valid-day fraction", xlabel="Quarter start UTC", ylim=(-.05, 1.05))
        save_figure(run, fig, "quarterly_"+sid)


def execute(sample=False):
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config.get("schema") != 1:
        raise ValueError("Unsupported temporal EDA schema")
    stage = "analysis/stage3_temporal_environment"+("_sample" if sample else "")
    with LocalRun(ROOT, stage, config, NOTEBOOK) as run:
        for path in [CONFIG, Path(__file__), Path(__file__).with_name("stage3_mission_eda.py"),
                     LOCAL/"EDA/shared/decision_eda.py"]:
            run.input(path)
        run.record["packages"]["cdflib"] = cdflib.__version__
        daily, catalog = radiation_daily(run, config)
        if sample:
            daily = daily.groupby("series_id", sort=False).head(40)
        parts, cats = [daily], [catalog]
        for item in config["uv_files"]:
            path = external_input(run, {"external_root": str(LOCAL/"data")}, item)
            run.input(path); run.input(Path(str(path)+".json"))
            f = read_uv(path, item["band"], sample)
            parts.append(f)
            for sid in f.series_id.unique():
                cats.append(pd.DataFrame([{"series_id": sid, "environment": "UV", "instrument": "SORCE_SOLSTICE",
                    "version": sid.rsplit("_v", 1)[1], "channel": item["band"], "unit": "W/m2 at 1 AU",
                    "position_group": "solar_reference_not_lunar_surface",
                    "daily_statistic": "sum of complete contiguous 1-nm daily spectral bins; not subdaily peak",
                    "validity_basis": "SOLSTICE quality=0 plus finite nonnegative irradiance/uncertainty; no partial-band filling",
                    "spatial_scope": "solar reference; NOT terrain-adjusted candidate UV irradiance or dose"}]))
            print("UV parsed:", item["band"], len(f), "daily spectra", flush=True)
        diagnostics, metadata = [], []
        selected = config["plasma_files"]
        if sample:
            selected = [selected[0], selected[-1]]
        for item in selected:
            path = external_input(run, config, item)
            f, cat, info, attrs = plasma_file(path, config["plasma_distance_edges_Rm"])
            parts.append(f); cats.append(cat); diagnostics.append(info); metadata.append(attrs)
            print("Plasma parsed:", path.name, info["records"], flush=True)
        daily = pd.concat(parts, ignore_index=True)
        daily["date"] = pd.to_datetime(daily.date, utc=True)
        daily = daily[["series_id", "date", *VALUE_COLUMNS, "recorded_samples", "valid_samples", "valid_seconds"]].sort_values(["series_id", "date"])
        catalog = pd.concat(cats, ignore_index=True).drop_duplicates()
        if catalog.series_id.duplicated().any() or daily.duplicated(["series_id", "date"]).any():
            raise ValueError("Inconsistent source identities or overlapping daily files")
        if (daily.valid_samples > daily.recorded_samples).any() or (daily.valid_samples < 0).any():
            raise ValueError("Invalid sample support")
        monthly, quarterly = [within_year_comparison(period_summary(daily, frequency)) for frequency in ["M", "Q"]]
        support = support_table(daily, catalog)
        overlap = overlap_table(support)
        for name, frame in [("daily_context.csv", daily), ("series_catalog.csv", catalog),
                            ("monthly_context.csv", monthly), ("quarterly_context.csv", quarterly),
                            ("temporal_support.csv", support), ("cross_dataset_overlap.csv", overlap),
                            ("plasma_file_diagnostics.csv", pd.DataFrame(diagnostics))]:
            frame.to_csv(run.path(name), index=False)
        run.path("plasma_source_metadata.json").write_text(json.dumps(metadata, indent=2, default=lambda x: x.tolist() if hasattr(x, "tolist") else str(x)), encoding="utf-8")
        plots(run, daily, monthly, quarterly, catalog)
        findings = {"sample": sample, "series": len(catalog), "daily_rows": len(daily),
            "monthly_rows": len(monthly), "quarterly_rows": len(quarterly),
            "plasma_files": len(selected), "uv_valid_days": support.loc[support.environment.eq("UV"), ["channel", "valid_dates"]].to_dict("records"),
            "calendar_bins_are_lunar_seasons": False, "simultaneous_UV_plasma_analysis": False,
            "candidate_operational_conclusion": "Unknown", "new_safety_limits": False,
            "holds": ["Calendar contrasts are descriptive, not recurring seasonality or future forecasts",
                "UV does not overlap recent radiation/plasma; no simultaneous correlation",
                "GOES platforms/channels/versions stay separate; SEC counters are not dose",
                "Plasma strata describe spacecraft geometry, not certified plasma regimes or surface charging",
                "Plasma record-weighted statistics have mixed cadence; elapsed valid coverage remains unknown",
                "Full calendar denominators include partial edge periods; missing/flagged data is not zero",
                "UV daily means cannot resolve flare peaks; no local terrain or biological response applied",
                "No candidate measurements, existing preferences or operational passes created"]}
        run.path("findings.json").write_text(json.dumps(findings, indent=2), encoding="utf-8")
        folder = run.directory
    print(json.dumps(findings, indent=2), flush=True)
    return folder, findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true")
    args = parser.parse_args()
    print(execute(args.sample)[0])
