"""Decision-facing descriptive EDA, without inventing mission/equipment limits."""
from itertools import combinations
import re

import numpy as np
import pandas as pd

from notebooks.shared.inspection import check_input, verify_run

CONTEXT = ["solar_visibility", "earth_visibility", "permanent_shadow", "sky_view_sr",
           "elevation_m", "slope_deg", "elevation_error_m", "effective_resolution_m", "spot_count"]
PREDICTORS = [name for name in CONTEXT if name != "permanent_shadow"]
BLOCK_KEYS = ["region", "block_x", "block_y"]


def accepted_input(run, folder, relative):
    folder = folder.resolve()
    path = (folder / relative).resolve()
    if not path.is_relative_to(folder):
        raise ValueError("Input escapes the accepted run")
    check_input(path, verify_run(folder), {})
    run.input(folder / "provenance.json")
    run.input(path)
    return path


def assign_blocks(frame, width_m):
    if not isinstance(width_m, (int, float)) or width_m <= 0 or not np.isfinite(width_m):
        raise ValueError("Block width must be finite and positive")
    if not np.isfinite(frame[["x_m", "y_m"]].to_numpy(dtype=float)).all():
        raise ValueError("Unknown projected native-center coordinates")
    result = frame.copy()
    result["block_x"] = np.floor(result.x_m / width_m).astype("int64")
    result["block_y"] = np.floor(result.y_m / width_m).astype("int64")
    return result


def spatial_blocks(footprints, width_m):
    if not np.isfinite(width_m) or width_m <= 0:
        raise ValueError("Positive block width required")
    rows = []
    for region, info in footprints.items():
        west, south, east, north = info["bounds_m"]
        if not np.isfinite([west, south, east, north]).all() or west >= east or south >= north:
            raise ValueError("Invalid region footprint")
        for x in range(int(np.floor(west / width_m)), int(np.ceil(east / width_m))):
            for y in range(int(np.floor(south / width_m)), int(np.ceil(north / width_m))):
                left, right = max(west, x * width_m), min(east, (x + 1) * width_m)
                bottom, top = max(south, y * width_m), min(north, (y + 1) * width_m)
                rows.append({"region": region, "block_x": x, "block_y": y, "left_m": left, "right_m": right,
                             "bottom_m": bottom, "top_m": top, "block_mid_x_m": (left + right) / 2,
                             "block_mid_y_m": (bottom + top) / 2})
    return pd.DataFrame(rows)


def validate_observations(frame):
    required = ["region", "source_product", "clon", "clat", "x_m", "y_m", "tbol", "local_time_h",
                "usable", "valid_temperature", "complete_common_cohort", *CONTEXT]
    if set(required) - set(frame):
        raise ValueError(f"Missing fields: {set(required) - set(frame)}")
    for field in ["usable", "valid_temperature", "complete_common_cohort"]:
        if frame[field].dtype != bool:
            raise ValueError(f"Invalid boolean encoding: {field}")
    if frame[["region", "source_product", "clon", "clat"]].isna().any().any():
        raise ValueError("Missing native-center identity")
    if frame.duplicated(["region", "source_product", "clon", "clat"]).any():
        raise ValueError("Duplicate native center within a source product")
    usable = frame.loc[frame.usable]
    if (not usable.valid_temperature.all() or not usable.tbol.gt(0).all()
            or not np.isfinite(usable.tbol).all() or not usable.local_time_h.between(0, 24, inclusive="left").all()):
        raise ValueError("Usable flags contradict temperature/local-time validity")


def distinct_context(frame):
    columns = ["region", "clon", "clat", "x_m", "y_m", "complete_common_cohort", *CONTEXT]
    result = frame[columns].drop_duplicates().copy()
    if result.duplicated(["region", "clon", "clat"]).any():
        raise ValueError("A source center has inconsistent static context or cohort flags")
    return result


def context_features(centers, keys):
    """Equal weight per observed center, never per repeated phase observation."""
    f = centers.copy()
    f["joint_context_available"] = np.isfinite(f[CONTEXT].to_numpy()).all(axis=1)
    f["zero_spots"] = f.spot_count.eq(0)
    f["finite_spots"] = np.isfinite(f.spot_count)
    result = f.groupby(keys, observed=True, sort=True).agg(
        observed_center_union=("clon", "size"), fixed_common_centers=("complete_common_cohort", "sum"),
        joint_context_centers=("joint_context_available", "sum"),
        x_center_m=("x_m", "mean"), y_center_m=("y_m", "mean"),
        context_mean_solar_fraction=("solar_visibility", "mean"),
        context_mean_earth_fraction=("earth_visibility", "mean"),
        context_psr_fraction=("permanent_shadow", "mean"), context_median_sky_sr=("sky_view_sr", "median"),
        context_median_elevation_m=("elevation_m", "median"), context_median_slope_deg=("slope_deg", "median"),
        context_median_height_error_m=("elevation_error_m", "median"),
        context_median_effective_resolution_m=("effective_resolution_m", "median"),
        context_zero_spot_centers=("zero_spots", "sum"), context_finite_spot_centers=("finite_spots", "sum")).reset_index()
    result["context_zero_spot_fraction"] = (result.context_zero_spot_centers
                                            / result.context_finite_spot_centers.replace(0, np.nan))
    result["context_complete_fraction"] = result.joint_context_centers / result.observed_center_union
    return result


def thermal_features(frame, keys, common_products):
    """Observed phase summaries and matched-phase contextual values, no mission maxima."""
    base = frame.groupby(keys, observed=True, sort=True).agg(
        observed_rows=("tbol", "size"), valid_temperature_rows=("valid_temperature", "sum")).reset_index()
    fields = list(dict.fromkeys([*keys, "source_product", "tbol", "local_time_h", "complete_common_cohort", *CONTEXT]))
    valid = frame.loc[frame.usable, fields].copy()
    if valid.empty:
        for name in ["usable_rows", "joint_temperature_context_rows", "fixed_common_rows"]:
            base[name] = 0
        for name in ["paired_mean_solar_fraction", "paired_mean_earth_fraction", "paired_psr_fraction",
                     "paired_median_sky_sr", "paired_median_elevation_m", "paired_median_slope_deg",
                     "local_time_resultant", "circular_mean_local_hour", "tbol_q10_K", "tbol_median_K",
                     "tbol_q90_K", "fixed_common_tbol_median_K"]:
            base[name] = np.nan
        return base
    valid["time_sin"] = np.sin(valid.local_time_h * np.pi / 12)
    valid["time_cos"] = np.cos(valid.local_time_h * np.pi / 12)
    valid["joint_context"] = np.isfinite(valid[CONTEXT].to_numpy()).all(axis=1)
    grouped = valid.groupby(keys, observed=True, sort=True)
    counts = grouped.agg(usable_rows=("tbol", "size"), joint_temperature_context_rows=("joint_context", "sum"),
        paired_mean_solar_fraction=("solar_visibility", "mean"), paired_mean_earth_fraction=("earth_visibility", "mean"),
        paired_psr_fraction=("permanent_shadow", "mean"), paired_median_sky_sr=("sky_view_sr", "median"),
        paired_median_elevation_m=("elevation_m", "median"), paired_median_slope_deg=("slope_deg", "median"),
        time_sin=("time_sin", "mean"), time_cos=("time_cos", "mean")).reset_index()
    quantiles = grouped.tbol.quantile([.1, .5, .9]).unstack().rename(
        columns={.1: "tbol_q10_K", .5: "tbol_median_K", .9: "tbol_q90_K"}).reset_index()
    counts["local_time_resultant"] = np.hypot(counts.time_sin, counts.time_cos)
    counts["circular_mean_local_hour"] = np.mod(np.arctan2(counts.time_sin, counts.time_cos) * 12 / np.pi, 24)
    counts.loc[np.isclose(counts.circular_mean_local_hour, 24, atol=1e-12, rtol=0), "circular_mean_local_hour"] = 0.
    counts.loc[counts.local_time_resultant < 1e-12, "circular_mean_local_hour"] = np.nan
    counts = counts.drop(columns=["time_sin", "time_cos"])
    result = base.merge(counts, on=keys, how="left", validate="one_to_one").merge(
        quantiles, on=keys, how="left", validate="one_to_one")
    fixed = valid.loc[valid.complete_common_cohort & valid.source_product.isin(common_products)]
    fixed_summary = fixed.groupby(keys, observed=True).agg(
        fixed_common_rows=("tbol", "size"), fixed_common_tbol_median_K=("tbol", "median")).reset_index()
    result = result.merge(fixed_summary, on=keys, how="left", validate="one_to_one")
    for name in ["usable_rows", "joint_temperature_context_rows", "fixed_common_rows"]:
        result[name] = result[name].fillna(0).astype("int64")
    return result


def phase_metadata(products):
    rows = []
    for product in products:
        match = re.search(r"_ls(\d+)_slon(\d+)_", product)
        if match is None:
            raise ValueError(f"Unknown solar-phase identity: {product}")
        rows.append({"source_product": product, "seasonal_ls_bin": int(match[1]),
                     "subsolar_longitude_bin": int(match[2])})
    return pd.DataFrame(rows)


def complete_phase_table(features, context, keys, products, common_products):
    """Explicitly retain missing block/products; zero counts are not zero temperatures."""
    index = context[keys].merge(pd.DataFrame({"source_product": products}), how="cross")
    result = index.merge(features, on=[*keys, "source_product"], how="left", validate="one_to_one")
    for field in ["observed_rows", "valid_temperature_rows", "usable_rows", "joint_temperature_context_rows", "fixed_common_rows"]:
        result[field] = result[field].fillna(0).astype("int64")
    result = result.merge(context, on=keys, how="left", validate="many_to_one").merge(
        phase_metadata(products), on="source_product", validate="many_to_one")
    result["observed_center_temperature_fraction"] = result.usable_rows / result.observed_center_union.replace(0, np.nan)
    result["common_product"] = result.source_product.isin(common_products)
    result["thermal_data_status"] = np.where(result.usable_rows.gt(0), "observed", "no_usable_thermal_rows")
    if result.loc[result.usable_rows.eq(0), "tbol_median_K"].notna().any():
        raise ValueError("A missing thermal group acquired a numeric temperature")
    return result


def block_coverage(phase_table, context, products, common_products):
    f = phase_table.copy()
    f["has_thermal"] = f.usable_rows.gt(0)
    result = f.groupby(BLOCK_KEYS, observed=True).agg(
        products_with_any_center=("has_thermal", "sum")).reset_index()
    common = f.loc[f.source_product.isin(common_products)].groupby(BLOCK_KEYS, observed=True).agg(
        common_products_with_any_center=("has_thermal", "sum")).reset_index()
    result = result.merge(common, on=BLOCK_KEYS, how="left", validate="one_to_one").merge(
        context[[*BLOCK_KEYS, "observed_center_union", "fixed_common_centers"]], on=BLOCK_KEYS, validate="one_to_one")
    result["selected_product_count"] = len(products)
    result["common_product_count"] = len(common_products)
    if common_products:
        result["all_common_products_have_some_center"] = result.common_products_with_any_center.eq(len(common_products))
        result["mixed_centers_only_completeness"] = (result.all_common_products_have_some_center
                                                      & result.fixed_common_centers.eq(0))
    else:
        result["all_common_products_have_some_center"] = pd.array([pd.NA] * len(result), dtype="boolean")
        result["mixed_centers_only_completeness"] = pd.array([pd.NA] * len(result), dtype="boolean")
    return result


def pairwise_spearman(frame, variables, groups):
    rows = []
    for group, part in frame.groupby(groups, observed=True, sort=True):
        group = group if isinstance(group, tuple) else (group,)
        for a, b in combinations(variables, 2):
            pairs = part[[a, b]].replace([np.inf, -np.inf], np.nan).dropna()
            valid = len(pairs) >= 3 and pairs.nunique().min() >= 2
            rows.append({**dict(zip(groups, group)), "variable_a": a, "variable_b": b,
                "pairs": len(pairs), "spearman_rho": pairs.corr(method="spearman").iloc[0, 1] if valid else np.nan,
                "status": "descriptive" if valid else "constant_or_insufficient"})
    return pd.DataFrame(rows)


def sampled_condition_runs(timestamps, condition, step_seconds=3600):
    """Runs of true samples, not continuous physical durations; preserve censoring/gaps."""
    times = pd.DatetimeIndex(pd.to_datetime(timestamps, utc=True))
    states = pd.array(condition, dtype="boolean")
    if len(times) != len(states) or not times.is_monotonic_increasing or times.has_duplicates:
        raise ValueError("Need equal-length ordered unique sample times and states")
    if not np.isfinite(step_seconds) or step_seconds <= 0:
        raise ValueError("Positive cadence required")
    expected = pd.Timedelta(seconds=step_seconds)
    rows, start = [], None
    for i in range(len(times) + 1):
        true = i < len(times) and not pd.isna(states[i]) and bool(states[i])
        adjacent = i > 0 and i < len(times) and times[i] - times[i - 1] == expected
        if start is not None and (not true or not adjacent):
            last = i - 1
            left_known = start > 0 and times[start] - times[start - 1] == expected and not pd.isna(states[start - 1])
            right_known = i < len(times) and adjacent and not pd.isna(states[i])
            rows.append({"first_sample_utc": times[start], "last_sample_utc": times[last],
                "sample_count": last - start + 1, "first_to_last_sample_span_hours": (times[last] - times[start]).total_seconds() / 3600,
                "left_censored": not left_known, "right_censored": not right_known})
            start = None
        if true and start is None:
            start = i
    return pd.DataFrame(rows, columns=["first_sample_utc", "last_sample_utc", "sample_count",
                                       "first_to_last_sample_span_hours", "left_censored", "right_censored"])
