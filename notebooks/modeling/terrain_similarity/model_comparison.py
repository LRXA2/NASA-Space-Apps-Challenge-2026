"""Matched-location and equal-region contracts for the four-model comparison."""

import numpy as np
import pandas as pd


def align_common_locations(catalogues: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Return each catalogue in the same shared-location order, retaining patch IDs."""
    if len(catalogues) < 2:
        raise ValueError('At least two catalogues are required')
    identity = ['body', 'region', 'fold']
    required = ['patch_id', 'location_id', *identity]
    for name, frame in catalogues.items():
        if not set(required) <= set(frame.columns) or frame.empty:
            raise ValueError(f'Missing identity columns or empty catalogue: {name}')
        if (frame[required].isna().to_numpy().any() or frame.patch_id.duplicated().any()
                or frame.location_id.duplicated().any()):
            raise ValueError(f'Null or duplicate identity: {name}')
    locations = sorted(set.intersection(*(set(frame.location_id) for frame in catalogues.values())))
    if not locations:
        raise ValueError('Catalogues have no common locations')
    aligned = {name: frame.set_index('location_id').loc[locations].reset_index().copy()
               for name, frame in catalogues.items()}
    reference = next(iter(aligned.values()))[identity]
    for name, frame in aligned.items():
        if not frame[identity].equals(reference):
            raise ValueError(f'Common location identity or split disagrees: {name}')
    return aligned


def summarize_comparison(results: pd.DataFrame) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Average queries within each region, then weight regions equally."""
    groups = ['method', 'direction', 'case', 'threshold']
    rates = ['available', 'top1_hit', 'top5_hit']
    metrics = [*rates, 'top1_relief_error_m', 'top1_slope_error_deg', 'top1_local_sd_error_m']
    identity = [*groups, 'query_id']
    required = [*identity, 'query_region', *metrics]
    if results.empty or not set(required) <= set(results.columns):
        raise ValueError('Comparison requires query identities and physical metrics')
    if results[required].isna().to_numpy().any() or results.duplicated(identity).any():
        raise ValueError('Missing values or duplicate query results')
    values = results[metrics].to_numpy(dtype=float)
    if not np.isfinite(values).all() or (values < 0).any() or (results[rates].to_numpy() > 1).any():
        raise ValueError('Expected finite nonnegative errors and rates in [0, 1]')
    if ((results.top1_hit > results.top5_hit) | (results.top5_hit > results.available)).any():
        raise ValueError('Hits must agree with candidate availability')
    regional_groups = [*groups, 'query_region']
    regional = results.groupby(regional_groups, as_index=False)[metrics].mean()
    counts = pd.DataFrame(results.groupby(regional_groups, as_index=False).agg(query_count=('query_id', 'size')))
    regional = regional.merge(counts, on=regional_groups, validate='one_to_one')
    macro = regional.groupby(groups, as_index=False)[metrics].mean()
    counts = pd.DataFrame(regional.groupby(groups, as_index=False).agg(
        query_count=('query_count', 'sum'), query_region_count=('query_region', 'size')))
    return regional, macro.merge(counts, on=groups, validate='one_to_one')
