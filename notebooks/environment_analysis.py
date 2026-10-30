"""Native environmental coverage rules, independent of file and plotting operations."""

import numpy as np
import pandas as pd


def diviner_cell_matrix(observations: pd.DataFrame, products: list[str]) -> pd.DataFrame:
    """Keep the union of observed source centers and every declared phase product.

    Coordinates are the source's exact exported longitude/latitude, not a rounded
    projected grid. An absent row or invalid temperature remains NaN. The union
    cannot describe native cells absent from every source product.
    """
    keys = ['clon', 'clat', 'source_product']
    required = {*keys, 'tbol', 'valid_temperature'}
    if not required.issubset(observations.columns):
        raise ValueError('Missing Diviner observation columns')
    if not products or len(products) != len(set(products)):
        raise ValueError('Products must be nonempty and unique')
    if observations.duplicated(keys).any():
        raise ValueError('Duplicate source cell/product records')
    if not observations.source_product.isin(products).all():
        raise ValueError('Undeclared source product')
    coordinates = observations[['clon', 'clat']].to_numpy(dtype=float)
    if not np.isfinite(coordinates).all():
        raise ValueError('Cell coordinates must be finite')
    if not observations.clon.between(-180, 180).all() or not observations.clat.between(-90, 90).all():
        raise ValueError('Cell coordinates outside longitude/latitude bounds')
    values = observations.tbol.to_numpy(dtype=float)
    flags = observations.valid_temperature
    if flags.dtype != np.dtype(bool) or flags.isna().any():
        raise ValueError('Validity must contain explicit booleans')
    if not np.array_equal(flags.to_numpy(), np.isfinite(values) & (values > 0)):
        raise ValueError('Validity flag disagrees with positive finite temperature')
    clean = observations[keys].copy()
    clean['tbol'] = np.where(flags, values, np.nan)
    return clean.pivot(index=['clon', 'clat'], columns='source_product', values='tbol').reindex(columns=products).sort_index()
