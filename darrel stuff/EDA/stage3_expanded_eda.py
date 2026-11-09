"""Additional Moon-only Step 3 diagnostics; no suitability gates or defaults."""
from pathlib import Path
import json

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import rasterio
from pyproj import Geod, Transformer
from rasterio.windows import Window

from stage3_mission_eda import ROOT, LOCAL, external_input, goes_observations, save_figure
from environment_workflow import LocalRun
from research_p1_readers import pilot_files, pin_source
from notebooks.shared.processing import MOON_CRS, MOON_GEOGRAPHIC

CONFIG = Path(__file__).with_name("stage3_expanded_config.json")


def load_config():
    config = json.loads(CONFIG.read_text(encoding="utf-8"))
    if config["schema"] != 1:
        raise ValueError("Unsupported expansion configuration")
    return config


def cartesian(lon_deg, lat_deg, radius_m):
    lon, lat = np.deg2rad(lon_deg), np.deg2rad(lat_deg)
    return np.stack([radius_m*np.cos(lat)*np.cos(lon),
                     radius_m*np.cos(lat)*np.sin(lon), radius_m*np.sin(lat)], axis=-1)


def local_basis(lon_deg, lat_deg):
    lon, lat = np.deg2rad(lon_deg), np.deg2rad(lat_deg)
    east = np.array([-np.sin(lon), np.cos(lon), 0.])
    up = cartesian(lon_deg, lat_deg, 1.)
    north = np.cross(up, east)
    return east, north, up


def angles(vectors, basis):
    east, north, up = basis
    vectors = np.asarray(vectors)
    az = np.rad2deg(np.arctan2(vectors@east, vectors@north)) % 360
    elevation = np.rad2deg(np.arctan2(vectors@up,
                                    np.hypot(vectors@east, vectors@north)))
    return az, elevation


def indexed_values(source, x, y):
    """Nearest native cells in one bounded read, retaining missing/outside values."""
    rows, cols = rasterio.transform.rowcol(source.transform, x.ravel(), y.ravel())
    rows, cols = np.asarray(rows), np.asarray(cols)
    inside = (rows >= 0)&(rows < source.height)&(cols >= 0)&(cols < source.width)
    values = np.full(len(rows), np.nan)
    if inside.any():
        r0, r1 = rows[inside].min(), rows[inside].max()+1
        c0, c1 = cols[inside].min(), cols[inside].max()+1
        array = source.read(1, window=Window(c0, r0, c1-c0, r1-r0), masked=True)
        array = array.astype(float).filled(np.nan)*source.scales[0]+source.offsets[0]
        values[inside] = array[rows[inside]-r0, cols[inside]-c0]
    return values.reshape(x.shape)


def horizon_profile(lon, lat, elevation_m, height_m, azimuths, distances,
                    dem, error, effective, radius_m):
    """Finite-range sampled terrain skyline, not a certified unobstructed horizon."""
    aa, dd = np.meshgrid(azimuths, distances, indexing="ij")
    geod = Geod(a=radius_m, b=radius_m)
    lon2, lat2, _ = geod.fwd(np.full(aa.shape, lon), np.full(aa.shape, lat), aa, dd)
    x, y = Transformer.from_crs(MOON_GEOGRAPHIC, MOON_CRS, always_xy=True).transform(lon2, lat2)
    z = indexed_values(dem, x, y)
    observer = cartesian(lon, lat, radius_m+elevation_m+height_m)
    vectors = cartesian(lon2, lat2, radius_m+z)-observer
    _, elevation = angles(vectors, local_basis(lon, lat))
    valid = np.isfinite(elevation)
    index = np.argmax(np.where(valid, elevation, -np.inf), axis=1)
    axis = np.arange(len(azimuths))
    peak_x, peak_y = x[axis, index], y[axis, index]
    peak = elevation[axis, index]
    peak[~valid.any(axis=1)] = np.nan
    return pd.DataFrame({"azimuth_deg": azimuths, "horizon_deg": peak,
                         "controlling_distance_m": distances[index],
                         "sampled_valid_fraction": valid.mean(axis=1),
                         "controlling_dem_error_m": indexed_values(error, peak_x, peak_y),
                         "controlling_effective_resolution_m": indexed_values(effective, peak_x, peak_y)})


def sampled_runs(times, blocked):
    """First-to-last sample spans; do not extrapolate transitions or bridge gaps."""
    times = pd.DatetimeIndex(times)
    blocked = np.asarray(blocked, dtype=bool)
    if len(times) != len(blocked) or not times.is_monotonic_increasing or times.has_duplicates:
        raise ValueError("Invalid time/visibility alignment")
    if len(times) < 2:
        raise ValueError("Insufficient cadence support")
    gaps = np.diff(times.asi8)
    if not np.all(gaps == gaps[0]):
        raise ValueError("Irregular cadence cannot be bridged")
    rows = []
    i = 0
    while i < len(times):
        if not blocked[i]:
            i += 1
            continue
        j = i
        while j+1 < len(times) and blocked[j+1]:
            j += 1
        rows.append({"first_blocked_sample": times[i], "last_blocked_sample": times[j],
                     "blocked_samples": j-i+1, "sample_span_hours": (times[j]-times[i]).total_seconds()/3600,
                     "left_censored": i == 0, "right_censored": j == len(times)-1})
        i = j+1
    return rows


def lookup_horizon(profile, azimuths):
    """Nearest sampled bearing; no azimuth interpolation or visibility guarantee."""
    angles_ = profile.azimuth_deg.to_numpy()
    if len(angles_) < 2 or not np.allclose(np.diff(angles_), np.diff(angles_)[0]):
        raise ValueError("Expected a uniform cyclic azimuth grid")
    step = angles_[1]-angles_[0]
    if angles_[0] != 0 or not np.isclose(len(angles_)*step, 360):
        raise ValueError("Incomplete azimuth grid")
    indices = (np.floor((np.asarray(azimuths) % 360)/step+.5).astype(int)) % len(angles_)
    return profile.horizon_deg.to_numpy()[indices]


def terrain(run, config, sample=False):
    import spiceypy as spice
    paths = {k: ROOT/config[k] for k in ["dem", "dem_error", "effective_resolution"]}
    for path in paths.values():
        pin_source(run, path)
        run.input(path.with_name(path.name+".json"))
    kernels = [p for suffix in [".tls", ".tpc", ".bsp", ".bpc", ".tf"]
               for p in pilot_files(LOCAL/"data", "D19", suffix)]
    for p in kernels:
        pin_source(run, p)
        run.input(p.with_name(p.name+".json"))
    times = pd.DatetimeIndex([t for window in config["windows"] for t in pd.date_range(
        window, periods=config["window_days"]*24+1, freq="1h", tz="UTC")])
    window_labels = np.repeat(config["windows"], config["window_days"]*24+1)
    profiles, observers, geometry, intervals, checks = [], [], [], [], []
    spice.kclear()
    try:
        for p in kernels:
            spice.furnsh(str(p))
        targets = {target: np.array([spice.spkpos(target, spice.str2et(t.strftime("%Y-%m-%dT%H:%M:%S")),
            "MOON_ME", "NONE", "MOON")[0] for t in times])*1000 for target in ["SUN", "EARTH"]}
        with rasterio.open(paths["dem"]) as dem, rasterio.open(paths["dem_error"]) as error, rasterio.open(paths["effective_resolution"]) as effective:
            for source in [dem, error, effective]:
                if not source.crs == rasterio.crs.CRS.from_string(MOON_CRS):
                    raise ValueError("Unexpected lunar source CRS")
            for region, bounds in config["region_bounds_m"].items():
                if sample and region != config["convergence_region"]:
                    continue
                x, y = (bounds[0]+bounds[2])/2, (bounds[1]+bounds[3])/2
                row, col = dem.index(x, y)
                x, y = dem.xy(row, col)
                lon, lat = Transformer.from_crs(MOON_CRS, MOON_GEOGRAPHIC, always_xy=True).transform(x, y)
                z = float(indexed_values(dem, np.array([x]), np.array([y]))[0])
                if not np.isfinite(z):
                    raise ValueError("Missing reference observer elevation")
                observers.append({"region": region, "x_m": x, "y_m": y, "longitude_deg": lon,
                    "latitude_deg": lat, "surface_elevation_m": z, "selection": "nearest native cell to ROI center, not recommended site"})
                for height in config["observer_heights_m"]:
                    observer = cartesian(lon, lat, config["radius_m"]+z+height)
                    for radius in config["horizon_radii_m"]:
                        profile = horizon_profile(lon, lat, z, height,
                            np.arange(0, 360, config["azimuth_step_deg"]),
                            np.arange(config["radial_step_m"], radius+.01, config["radial_step_m"]),
                            dem, error, effective, config["radius_m"])
                        identity={"region": region, "height_m": height, "radius_m": radius}
                        profiles.append(profile.assign(**identity))
                        if region == config["convergence_region"] and height == config["observer_heights_m"][0] and radius == max(config["horizon_radii_m"]):
                            refined = horizon_profile(lon, lat, z, height, np.arange(0, 360, 1.),
                                np.arange(40., radius+.01, 40.), dem, error, effective, config["radius_m"])
                            # Exact common bearings isolate radial sampling differences.
                            common = profile.merge(refined, on="azimuth_deg", suffixes=("_base", "_refined"), validate="one_to_one")
                            common["refined_minus_base_horizon_deg"] = common.horizon_deg_refined-common.horizon_deg_base
                            common.assign(**identity).to_csv(run.path("horizon_sampling_convergence.csv"), index=False)
                        for target, positions in targets.items():
                            az, alt = angles(positions-observer, local_basis(lon, lat))
                            horizon = lookup_horizon(profile, az)
                            if not np.isfinite(horizon).all():
                                raise ValueError("Unsupported horizon bearings; cannot classify samples")
                            part = pd.DataFrame({"utc": times, "window": window_labels, "azimuth_deg": az,
                                "target_center_elevation_deg": alt, "sampled_horizon_deg": horizon,
                                "center_blocked_by_sampled_terrain": alt <= horizon,
                                "center_below_local_horizontal": alt <= 0,
                                "clearance_deg": alt-horizon}).assign(**identity, target=target)
                            geometry.append(part)
                            for window, group in part.groupby("window"):
                                for entry in sampled_runs(group.utc, group.center_blocked_by_sampled_terrain):
                                    intervals.append({**identity, "target": target, "window": window, **entry})
                            if region == config["convergence_region"] and height == config["observer_heights_m"][0] and radius == max(config["horizon_radii_m"]):
                                fine_times = pd.DatetimeIndex([t for w in config["windows"] for t in pd.date_range(w,
                                    periods=config["window_days"]*48+1, freq="30min", tz="UTC")])
                                fine_pos = np.array([spice.spkpos(target, spice.str2et(t.strftime("%Y-%m-%dT%H:%M:%S")),
                                    "MOON_ME", "NONE", "MOON")[0] for t in fine_times])*1000
                                fine_az, fine_alt = angles(fine_pos-observer, local_basis(lon, lat))
                                fine = pd.DataFrame({"utc": fine_times, "window": np.repeat(config["windows"], config["window_days"]*48+1),
                                    "blocked": fine_alt <= lookup_horizon(refined, fine_az)})
                                for window, g in fine.groupby("window"):
                                    rs=sampled_runs(g.utc, g.blocked)
                                    checks.append({**identity, "target": target, "window": window,
                                        "refined_azimuth_step_deg": 1, "refined_radial_step_m": 40, "refined_cadence_min": 30,
                                        "refined_blocked_fraction": g.blocked.iloc[:-1].mean(),
                                        "refined_longest_sample_span_hours": max((r["sample_span_hours"] for r in rs), default=0.)})
                print("Terrain diagnostic completed:", region, flush=True)
    finally:
        spice.kclear()
    profile = pd.concat(profiles, ignore_index=True)
    obs = pd.DataFrame(observers)
    frame = pd.concat(geometry, ignore_index=True)
    profile.to_csv(run.path("sampled_horizon_profiles.csv"), index=False)
    obs.to_csv(run.path("reference_observers.csv"), index=False)
    frame.to_csv(run.path("terrain_target_center_geometry.csv.gz"), index=False, compression="gzip")
    pd.DataFrame(intervals).to_csv(run.path("sampled_blocked_intervals.csv"), index=False)
    pd.DataFrame(checks).to_csv(run.path("geometry_resolution_convergence.csv"), index=False)
    # Exclude the final endpoint for equal-length sample-fraction comparisons.
    summary = frame.groupby(["region", "height_m", "radius_m", "target", "window"]).apply(
        lambda g: pd.Series({"samples": len(g), "sampled_blocked_fraction": g.center_blocked_by_sampled_terrain.iloc[:-1].mean(),
            "below_local_horizontal_fraction": g.center_below_local_horizontal.iloc[:-1].mean(),
            "near_sampled_horizon_samples_within_0_25deg": g.clearance_deg.abs().le(.25).sum()}), include_groups=False).reset_index()
    summary.to_csv(run.path("terrain_geometry_summary.csv"), index=False)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout="constrained")
    for region, g in profile.loc[profile.height_m.eq(2)&profile.radius_m.eq(20000)].groupby("region"):
        axes[0].plot(g.azimuth_deg, g.horizon_deg, label=region.split("_", 2)[-1])
    axes[0].set(xlabel="Local north-clockwise bearing (degrees)", ylabel="Sampled horizon (degrees)", title="Finite 20 km skyline at 2 m; unmodelled blockers remain possible")
    axes[0].legend(fontsize=6, ncol=3)
    g=summary.loc[summary.target.eq("SUN")&summary.height_m.eq(2)&summary.radius_m.eq(20000)]
    for window, part in g.groupby("window"):
        axes[1].scatter(part.region.str.split("_", n=2).str[-1], part.sampled_blocked_fraction, label=window)
    axes[1].set(ylabel="Sampled solar-center blocked fraction", title="Two explicit 30-day diagnostic windows, not solar power or mission darkness")
    axes[1].tick_params(axis="x", labelsize=6);axes[1].legend()
    save_figure(run, fig, "terrain_horizon_and_solar_center_support")
    return {"reference_points": len(obs), "target_center_samples": len(frame),
        "horizon_bearings": len(profile), "rays_with_missing_samples": int(profile.sampled_valid_fraction.lt(1).sum()),
        "solar_sampled_blocked_fraction_range_2m_20km": [float(g.sampled_blocked_fraction.min()), float(g.sampled_blocked_fraction.max())],
        "holds": ["Finite radius and discrete bearings/distances can miss blockers; not a proven clear horizon",
            "Only target centers: solar disk, panel attitude, link budgets, loads and storage are absent",
            "No continuous-darkness or power-endurance claim; interval boundaries are sampled/censored",
            "DEM error and effective resolution retained at controlling sampled terrain; not independent accuracy validation",
            "Two 2020 windows and ROI-center points are declared diagnostics, not intended mission/sites"]}


def goes_daily(observations):
    """Keep energy/direction and qualified duration separate, without gap filling."""
    rows=[]
    for key, g in observations.groupby(["sensor", "channel", "lower_energy_keV", "upper_energy_keV"]):
        if g.timestamp.duplicated().any():
            raise ValueError("Duplicate channel-time identity")
        if not g.timestamp.sort_values().diff().dropna().eq(pd.Timedelta(minutes=5)).all():
            raise ValueError("Unexpected GOES cadence")
        accepted = g.loc[g.strict_quality]
        best = accepted.sort_values(["flux", "timestamp"], ascending=[False, True]).head(1)
        rows.append(dict(zip(["sensor", "channel", "lower_energy_keV", "upper_energy_keV"], key),
            recorded_bins=len(g), qualified_bins=len(accepted), qualified_seconds=len(accepted)*300,
            qualified_max_flux=accepted.flux.max(), qualified_median_flux=accepted.flux.median(),
            qualified_peak_utc=best.timestamp.iloc[0] if len(best) else pd.NaT,
            supported_bin_integral=accepted.flux.sum()*300 if len(accepted) else np.nan,
            raw_finite_median_not_quality_approved=g.loc[g.finite_nonnegative,"flux"].median(),
            lookup_tables_matched=bool(g.lookup_tables_matched.all())))
    return pd.DataFrame(rows)


def space_weather(run, config, sample=False):
    rows=[]
    files = [config["goes_files"][0], config["goes_files"][-1]] if sample else config["goes_files"]
    for i, item in enumerate(files):
        path = external_input(run, config, item)
        obs = goes_observations(path)
        dates = obs.timestamp.dt.strftime("%Y-%m-%d").unique()
        if len(dates) != 1:
            raise ValueError("GOES source is not a single UTC day")
        if obs.sensor.nunique() != 2 or obs.channel.nunique() != 13 or len(obs) != 7488:
            raise ValueError("Changed GOES daily support")
        rows.append(goes_daily(obs).assign(date=dates[0], source_file=item["relative_path"]))
        if i % 50 == 0:
            print("GOES completed files:", i+1, "/", len(files), flush=True)
    frame = pd.concat(rows, ignore_index=True)
    if frame.duplicated(["date", "sensor", "channel"]).any():
        raise ValueError("Mixed satellites/versions need explicit grouping before combining")
    frame.to_csv(run.path("daily_directional_channel_support.csv"), index=False)
    energy = frame.groupby(["sensor", "channel", "lower_energy_keV", "upper_energy_keV"]).agg(
        recorded_days=("date", "size"), days_any_qualified=("qualified_bins", lambda x: x.gt(0).sum()),
        complete_qualified_days=("qualified_bins", lambda x: x.eq(288).sum()),
        qualified_bins=("qualified_bins", "sum"), recorded_bins=("recorded_bins", "sum"),
        largest_qualified_flux=("qualified_max_flux", "max")).reset_index()
    energy.to_csv(run.path("energy_direction_coverage.csv"), index=False)
    # Rank measured qualified peaks only within the same energy/direction.
    supported = frame.loc[frame.qualified_bins.gt(0)].copy()
    supported["peak_order_within_energy_direction"] = supported.groupby(["sensor", "channel"]).qualified_max_flux.rank(method="min", ascending=False)
    supported.loc[supported.peak_order_within_energy_direction.le(5)].to_csv(run.path("largest_qualified_observed_days.csv"), index=False)
    gaps=[]
    dates = pd.DatetimeIndex(sorted(frame.date.unique()))
    for a,b in zip(dates[:-1],dates[1:]):
        if (b-a).days > 1:
            gaps.append({"previous_completed_date":a,"next_completed_date":b,"unobserved_dates_between":(b-a).days-1})
    pd.DataFrame(gaps, columns=["previous_completed_date","next_completed_date","unobserved_dates_between"]).to_csv(run.path("completed_file_date_gaps.csv"),index=False)
    fig, axes = plt.subplots(2, 1, figsize=(12, 7), layout="constrained")
    daily=frame.groupby("date").qualified_bins.sum()/7488
    axes[0].scatter(pd.to_datetime(daily.index), daily, s=8)
    axes[0].set(ylabel="Qualified channel/time fraction", title="Frozen completed GOES-16 dates; gaps do not mean quiet conditions")
    for sensor, part in frame.loc[frame.channel.eq(0)].groupby("sensor"):
        axes[1].scatter(pd.to_datetime(part.date), part.qualified_max_flux.where(part.qualified_max_flux.gt(0)), s=8, label=f"sensor {sensor}")
    if frame.loc[frame.channel.eq(0), "qualified_max_flux"].gt(0).any():
        axes[1].set_yscale("log")
    else:
        axes[1].text(.5, .5, "No positive qualified channel 0 flux samples; missing is not zero",
                     transform=axes[1].transAxes, ha="center")
    axes[1].set(ylabel="Qualified observed maximum differential flux", xlabel="UTC date",
                title="Channel 0 only; protons/(cm2 sr keV s), not lunar dose or storm classification")
    axes[1].legend();save_figure(run, fig, "space_weather_coverage_and_qualified_peaks")
    return {"completed_files":len(files),"date_start":str(dates.min().date()),"date_end":str(dates.max().date()),
        "recorded_channel_bins":int(frame.recorded_bins.sum()), "qualified_channel_bins":int(frame.qualified_bins.sum()),
        "complete_qualified_direction_channel_days":int(frame.qualified_bins.eq(288).sum()),
        "days_without_any_qualified_bin":int(frame.groupby("date").qualified_bins.sum().eq(0).sum()),
        "calendar_gaps_between_completed_dates":len(gaps),
        "holds":["Completed-file selection is not a complete mission/event census", "Energy/direction retained; no raw-to-crew-dose conversion",
            "Ranked observed maxima are coverage-conditioned, not certified SPE events or worst cases",
            "Unqualified intervals are not zero exposure; partial integrals do not bridge them"]}


def execute(kind, notebook, sample=False):
    config = load_config()
    scope = "_sample" if sample else ""
    with LocalRun(ROOT, "analysis/stage3_expanded_"+kind+scope, config, notebook) as run:
        for path in [CONFIG, Path(__file__), ROOT/config["acquisition_snapshot"],
                     ROOT/"darrel stuff/EDA/stage3_mission_eda.py", ROOT/"outline.md"]:
            run.input(path)
        findings = {"terrain": terrain, "space_weather": space_weather}[kind](run, config, sample)
        run.path("findings.json").write_text(json.dumps(findings, indent=2, default=str), encoding="utf-8")
        print(json.dumps(findings, indent=2, default=str))
        folder = run.directory
    return folder, findings
