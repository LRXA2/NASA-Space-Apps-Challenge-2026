"""Consume historical calendar EDA without turning temporal contrasts into site safety."""
from pathlib import Path

import numpy as np
import pandas as pd

from data_maintenance import atomic_text

PREFIX = "temporal/"


def validate(frames):
    """Verify handoff semantics/counts; older manifests without this extension still work."""
    if not any(key.startswith(PREFIX) for key in frames):
        return []
    catalog = frames[PREFIX+"series_catalog.csv"]
    support = frames[PREFIX+"temporal_support.csv"]
    daily = frames[PREFIX+"daily_context.csv"]
    monthly = frames[PREFIX+"monthly_context.csv"]
    quarterly = frames[PREFIX+"quarterly_context.csv"]
    overlap = frames[PREFIX+"cross_dataset_overlap.csv"]
    for key, f in frames.items():
        if key.startswith(PREFIX) and "candidate_id" in f:
            raise ValueError("Historical temporal context cannot be relabelled candidate measurements")
    if catalog.series_id.duplicated().any() or support.series_id.duplicated().any():
        raise ValueError("Repeated temporal series identity")
    if set(catalog.series_id) != set(support.series_id) or set(daily.series_id) != set(catalog.series_id):
        raise ValueError("Temporal series catalog/support mismatch")
    if catalog[["instrument", "version", "channel", "unit", "position_group", "validity_basis"]].isna().any().any():
        raise ValueError("Missing temporal instrument/quantity/position meaning")
    if daily.duplicated(["series_id", "date"]).any():
        raise ValueError("Repeated temporal daily identity")
    if (daily.valid_samples.lt(0).any() or daily.valid_samples.gt(daily.recorded_samples).any()
            or daily.loc[daily.valid_samples.eq(0), "daily_median"].notna().any()):
        raise ValueError("Invalid temporal daily support")
    if not support.candidate_operational_conclusion.eq("Unknown").all():
        raise ValueError("Historical context cannot establish operational suitability")
    for f, frequency, kind in [(monthly, "M", "calendar_month"), (quarterly, "Q", "calendar_quarter")]:
        if f.duplicated(["series_id", "period"]).any() or not f.period_kind.eq(kind).all():
            raise ValueError("Repeated or non-calendar temporal period")
        if set(f.series_id) != set(catalog.series_id):
            raise ValueError("Period summary lacks a declared series")
        periods = pd.PeriodIndex(f.period, freq=frequency)
        expected = ((periods+1).start_time-periods.start_time).days
        start = pd.to_datetime(f.period_start_utc, utc=True)
        stop = pd.to_datetime(f.period_stop_exclusive_utc, utc=True)
        if (not np.array_equal(expected, f.expected_calendar_days)
                or not np.array_equal(periods.year, f.year)
                or not np.array_equal(start.to_numpy(), periods.start_time.tz_localize("UTC").to_numpy())
                or not np.array_equal(stop.to_numpy(), (periods+1).start_time.tz_localize("UTC").to_numpy())):
            raise ValueError("Calendar support/window meaning changed")
        counts = f[["recorded_days", "valid_days", "recorded_samples", "valid_samples"]]
        if (not np.isfinite(counts).all().all() or counts.lt(0).any().any()
                or counts.mod(1).ne(0).any().any() or f.valid_days.gt(f.recorded_days).any()
                or f.recorded_days.gt(f.expected_calendar_days).any()
                or f.valid_samples.gt(f.recorded_samples).any()
                or not np.allclose(f.valid_day_fraction, f.valid_days/f.expected_calendar_days)):
            raise ValueError("Invalid temporal support counts/fractions")
        empty = f.valid_days.eq(0)
        if f.loc[empty, "median_of_daily_medians"].notna().any() or f.loc[~empty, "median_of_daily_medians"].isna().any():
            raise ValueError("Unsupported periods have fabricated levels or valid periods lack levels")
        totals = f.groupby("series_id")[["recorded_samples", "valid_samples", "recorded_days", "valid_days"]].sum().sort_index()
        expected_totals = support.set_index("series_id")[["recorded_samples", "valid_samples", "recorded_dates", "valid_dates"]].sort_index()
        if not np.array_equal(totals.to_numpy(), expected_totals.to_numpy()):
            raise ValueError("Period totals disagree with temporal source support")
        source = daily.copy()
        source["period"] = pd.to_datetime(source.date, utc=True).dt.tz_localize(None).dt.to_period(frequency).astype(str)
        derived = source.groupby(["series_id", "period"]).agg(
            recorded_days=("date", "size"), valid_days=("daily_median", "count"),
            recorded_samples=("recorded_samples", "sum"), valid_samples=("valid_samples", "sum"),
            median_of_daily_medians=("daily_median", "median"),
            maximum_observed_value=("daily_max", "max"))
        derived["p95_of_daily_medians"] = source.groupby(["series_id", "period"]).daily_median.quantile(.95)
        derived["valid_seconds"] = source.groupby(["series_id", "period"]).valid_seconds.sum(min_count=1)
        index = f.set_index(["series_id", "period"])
        expected_rows = derived.reindex(index.index)
        count_fields = ["recorded_days", "valid_days", "recorded_samples", "valid_samples"]
        expected_rows[count_fields] = expected_rows[count_fields].fillna(0)
        if not np.allclose(index[derived.columns].to_numpy(float), expected_rows.to_numpy(float), equal_nan=True, rtol=1e-12, atol=1e-12):
            raise ValueError("Temporal period statistics disagree with the consumed daily evidence")
        seconds = f.valid_seconds.notna()
        if (f.loc[seconds, "valid_seconds"].lt(0).any() or
                not np.allclose(f.loc[seconds, "valid_time_fraction"],
                                f.loc[seconds, "valid_seconds"]/(f.loc[seconds, "expected_calendar_days"]*86400))):
            raise ValueError("Qualified time fraction differs from actual valid seconds")
        non_goes = catalog.loc[~catalog.instrument.str.startswith("GOES"), "series_id"]
        if f.loc[f.series_id.isin(non_goes), ["valid_seconds", "valid_time_fraction"]].notna().any().any():
            raise ValueError("Sample support cannot be fabricated into continuous valid time")
        if f.loc[seconds, "valid_time_fraction"].gt(1).any():
            raise ValueError("Qualified time exceeds calendar support")
    if not overlap.simultaneous_correlation_performed.eq(False).all():
        raise ValueError("This handoff does not support simultaneous cross-instrument correlations")
    uv_pairs = overlap.loc[overlap.left.eq("UV")]
    if len(uv_pairs) != 2 or not uv_pairs.span_overlap_days.eq(0).all():
        raise ValueError("Historical UV and recent plasma/radiation overlap assumptions changed; review explicitly")
    return [
        ("E14", "calendar_period_and_coverage_handling", "Passed", f"{len(monthly)} months / {len(quarterly)} quarters", "separate series-period rows",
         "UTC calendar windows, separate identities and support totals agree; daily statistics are not pooled raw-record quantiles",
         "temporal", "Historical context only; no lunar-season claim, future forecast or new score"),
        ("E15", "nonoverlapping_UV_to_simultaneous_correlation", "Failed", "0 overlapping days", "UV versus recent plasma/radiation spans",
         "Month labels do not make different years simultaneous observations",
         "temporal", "Withhold simultaneous UV/plasma/radiation correlation and mission-window exposure inference"),
        ("E16", "spacecraft_temporal_plasma_to_surface_charging", "Unknown", "position-stratified, variable cadence", "ARTEMIS spacecraft, not candidate surface",
         "SSE position strata are not certified plasma regimes; local potential, hardware response and applicable limits remain absent",
         "temporal", "No lower-density-is-safer preference or operational protection pass"),
    ]


def products(run, frames):
    if PREFIX+"monthly_context.csv" not in frames:
        return None
    run.input(Path(__file__))
    catalog = frames[PREFIX+"series_catalog.csv"]
    support = frames[PREFIX+"temporal_support.csv"]
    monthly = frames[PREFIX+"monthly_context.csv"]
    quarterly = frames[PREFIX+"quarterly_context.csv"]
    lines = ["# Historical monthly and quarterly environmental context", "",
        "**Descriptive UTC calendar periods, not lunar seasons, safety rankings or future forecasts.**",
        "These observations remain separate from candidate measurements and mission/equipment qualification. No weights, physical limits or operational passes were added.", "",
        "## Read the tables", "",
        "- [Monthly levels and coverage](sources/temporal/monthly_context.csv) and [quarterly levels and coverage](sources/temporal/quarterly_context.csv). Years, instruments, channels, versions, UV modes and plasma position strata stay separate.",
        "- [Series meaning](sources/temporal/series_catalog.csv), [temporal support](sources/temporal/temporal_support.csv), [daily values/peaks](sources/temporal/daily_context.csv), [plasma cadence](sources/temporal/plasma_file_diagnostics.csv) and [cross-dataset overlap](sources/temporal/cross_dataset_overlap.csv).",
        "- Median/p95 fields explicitly describe daily medians, not pooled raw observations. Quarterly summaries are recomputed from days, not averaged monthly medians.",
        "- Full calendar denominators include partial edge periods. Missing/flagged data stays missing; valid-day fraction is not continuous-time coverage. Only GOES carries qualified 5-minute seconds.",
        "- Plasma statistics are record-weighted with measured variable cadence. SSE-x/radius strata describe spacecraft geometry, not confirmed solar-wind/magnetotail regimes or surface voltage.",
        "- SOLSTICE integrates complete quality=0 FUV/MUV daily spectra. Daily means do not resolve short flare peaks; solar-reference W/m2 is not candidate UV dose.",
        "- Historical UV ends in 2020, before these plasma/radiation cohorts. No simultaneous UV/plasma/radiation correlation is calculated.", "",
        "## Available historical support", "", "| Instrument | First date | Last date | Separate series |", "| --- | --- | --- | ---: |"]
    for instrument, g in support.groupby("instrument", sort=True):
        lines.append(f"| {instrument} | {g.start_utc.min()[:10]} | {(pd.Timestamp(g.stop_exclusive_utc.max())-pd.Timedelta(days=1)).date()} | {len(g)} |")
    lines += ["", "## Example within-year monthly contrasts", "",
        "Fixed illustrative series; latest year with all 12 populated months where available, otherwise latest year with at least two. Endpoints can have different coverage: these are **observed levels, not safest/riskiest months**. Consult the full tables, including quarterly contrasts.", "",
        "| Series | Year | Lowest monthly median of daily values (valid days) | Highest (valid days) | Unit |",
        "| --- | ---: | --- | --- | --- |"]
    examples = catalog.loc[catalog.environment.eq("UV") | catalog.instrument.eq("LRO_CRATER_SEC")
        | (catalog.environment.eq("plasma") & catalog.channel.eq("thb_peif_densityQ") & catalog.position_group.eq("all_positions"))]
    examples = pd.concat([examples, catalog.loc[catalog.instrument.str.startswith("GOES")].groupby("instrument", sort=True).head(1)])
    for item in examples.to_dict("records"):
        f = monthly.loc[monthly.series_id.eq(item["series_id"]) & monthly.median_of_daily_medians.notna()]
        years = f.groupby("year").size()
        if not years.ge(2).any():
            continue
        usable = years.loc[years.eq(12)] if years.eq(12).any() else years.loc[years.ge(2)]
        year = int(usable.index.max())
        f = f.loc[f.year.eq(year)]
        low = f.loc[f.median_of_daily_medians.idxmin()]
        high = f.loc[f.median_of_daily_medians.idxmax()]
        lines.append(f"| `{item['series_id']}` | {year} | {low.period}: {low.median_of_daily_medians:.6g} ({int(low.valid_days)}/{int(low.expected_calendar_days)}) | {high.period}: {high.median_of_daily_medians:.6g} ({int(high.valid_days)}/{int(high.expected_calendar_days)}) | {item['unit']} |")
    lines += ["", "**Operational conclusion: Unknown.** A quieter historical month does not establish a safe arrival window. Applicable mission dates, dated local environmental models, protection and equipment response remain necessary.", ""]
    atomic_text(run.path("evidence_context/TEMPORAL_CONTEXT.md"), "\n".join(lines))
    return {"series": len(catalog), "monthly_rows": len(monthly), "quarterly_rows": len(quarterly),
            "candidate_operational_conclusion": "Unknown", "new_scored_factors": 0,
            "entry_point": "evidence_context/TEMPORAL_CONTEXT.md"}
