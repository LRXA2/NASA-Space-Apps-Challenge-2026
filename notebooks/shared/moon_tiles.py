"""Shared lunar tile identity for joining terrain similarity and operability outputs.

Both pipelines cut 960 m windows from the same 32-cell lattice but name them
differently: similarity patches use centre row/column and a view
(`<region>:<view>:<centre row>:<centre col>:960`), operability predictions use
the top-left row/column (`<region>:960:<row>:<col>`), and the two may come
from different lunar processing runs. A tile is therefore identified by its
centre in the common lunar polar stereographic CRS, snapped to one lattice per
region: `<region>:<centre x m>:<centre y m>`.

Sources whose windows do not sit on the same 960 m lattice are refused rather
than matched to the nearest tile. No terrain values are compared or changed.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from pyproj import CRS, Transformer

from notebooks.shared.inspection import check_input, verify_run
from notebooks.shared.processing import MOON_CRS, Run

TILE_SIZE_M = 960
LATTICE_TOLERANCE_M = 1.0


def tile_id(region: str, center_x: float, center_y: float) -> str:
    """Name a tile by region and its centre in metres in the common lunar CRS."""
    if not region or not np.isfinite(center_x) or not np.isfinite(center_y):
        raise ValueError('A tile needs a region and a finite centre')
    return f'{region}:{int(np.rint(center_x))}:{int(np.rint(center_y))}'


def to_moon_crs(x: np.ndarray, y: np.ndarray, crs_wkt: str) -> tuple[np.ndarray, np.ndarray]:
    """Project centres from a source CRS into the common lunar polar stereographic CRS."""
    source, target = CRS.from_user_input(crs_wkt), CRS.from_user_input(MOON_CRS)
    if source == target:
        return np.asarray(x, dtype=np.float64), np.asarray(y, dtype=np.float64)
    transformer = Transformer.from_crs(source, target, always_xy=True)
    projected_x, projected_y = transformer.transform(np.asarray(x, dtype=np.float64),
                                                     np.asarray(y, dtype=np.float64))
    return np.asarray(projected_x), np.asarray(projected_y)


def _project_groups(frame: pd.DataFrame, x: pd.Series, y: pd.Series) -> pd.DataFrame:
    """Project each CRS group separately; regions may carry their own WKT."""
    result = pd.DataFrame(index=frame.index, columns=['center_x', 'center_y'], dtype=np.float64)
    for crs_wkt, rows in frame.groupby('crs_wkt').groups.items():
        result.loc[rows, 'center_x'], result.loc[rows, 'center_y'] = to_moon_crs(
            x.loc[rows].to_numpy(), y.loc[rows].to_numpy(), crs_wkt)
    return result


def _require(frame: pd.DataFrame, columns: list[str], name: str) -> None:
    missing = [column for column in columns if column not in frame.columns]
    if missing:
        raise ValueError(f'{name} is missing columns: {missing}')
    if frame.empty or frame['patch_id'].duplicated().any():
        raise ValueError(f'{name} needs unique patch IDs')


def similarity_tiles(patches: pd.DataFrame) -> pd.DataFrame:
    """Lunar centres from a terrain-similarity `patches.csv` (tile bounds per view)."""
    _require(patches, ['patch_id', 'body', 'region', 'view', 'size_m',
                       'left', 'right', 'bottom', 'top', 'crs_wkt'], 'Similarity patches')
    moon = patches.loc[patches['body'] == 'moon']
    if moon.empty or (moon['size_m'] != TILE_SIZE_M).any():
        raise ValueError(f'Similarity patches need {TILE_SIZE_M} m lunar tiles')
    centres = _project_groups(moon, (moon['left'] + moon['right']) / 2, (moon['bottom'] + moon['top']) / 2)
    return pd.concat([moon[['patch_id', 'region', 'view']], centres], axis=1).reset_index(drop=True)


def operability_tiles(predictions: pd.DataFrame) -> pd.DataFrame:
    """Lunar centres from an operability or walkability `predictions.csv`."""
    _require(predictions, ['patch_id', 'region', 'size_m', 'center_x', 'center_y', 'crs_wkt'],
             'Operability predictions')
    if (predictions['size_m'] != TILE_SIZE_M).any():
        raise ValueError(f'Operability predictions need {TILE_SIZE_M} m lunar tiles')
    centres = _project_groups(predictions, predictions['center_x'], predictions['center_y'])
    return pd.concat([predictions[['patch_id', 'region']], centres], axis=1).reset_index(drop=True)


def _snap(sources: dict[str, pd.DataFrame]) -> dict[str, pd.DataFrame]:
    """Snap every source onto the first source's lattice per region, or refuse."""
    origins: dict[str, tuple[float, float]] = {}
    snapped: dict[str, pd.DataFrame] = {}
    for name, tiles in sources.items():
        frame = tiles.copy()
        for region, rows in frame.groupby('region').groups.items():
            first = frame.loc[rows].iloc[0]
            origin_x, origin_y = origins.setdefault(region, (first['center_x'], first['center_y']))
            steps_x = np.rint((frame.loc[rows, 'center_x'] - origin_x) / TILE_SIZE_M)
            steps_y = np.rint((frame.loc[rows, 'center_y'] - origin_y) / TILE_SIZE_M)
            snapped_x, snapped_y = origin_x + steps_x * TILE_SIZE_M, origin_y + steps_y * TILE_SIZE_M
            offset = np.hypot(frame.loc[rows, 'center_x'] - snapped_x, frame.loc[rows, 'center_y'] - snapped_y)
            if offset.max() > LATTICE_TOLERANCE_M:
                raise ValueError(f'{name} tiles in {region} are off the shared 960 m lattice by up to '
                                 f'{offset.max():.1f} m; rebuild them from the same lunar grid')
            frame.loc[rows, 'center_x'], frame.loc[rows, 'center_y'] = snapped_x, snapped_y
        frame['tile_id'] = [tile_id(r, x, y) for r, x, y in
                            zip(frame['region'], frame['center_x'], frame['center_y'], strict=True)]
        snapped[name] = frame
    return snapped


def build_tile_table(similarity: pd.DataFrame | None = None,
                     operability: dict[str, pd.DataFrame] | None = None) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Return one row per lunar tile and a long `tile_id` to source patch map.

    `similarity` is a similarity `patches.csv`; `operability` maps a source name
    (for example `rover` or `walkability`) to its `predictions.csv`.
    """
    sources: dict[str, pd.DataFrame] = {}
    if similarity is not None:
        tiles = similarity_tiles(similarity)
        for view, rows in tiles.groupby('view'):
            sources[f'similarity_{view}'] = rows.drop(columns='view')
    for name, predictions in (operability or {}).items():
        sources[name] = operability_tiles(predictions)
    if not sources:
        raise ValueError('Supply at least one similarity or operability source')
    snapped = _snap(sources)

    links = []
    for name, frame in snapped.items():
        if frame['tile_id'].duplicated().any():
            raise ValueError(f'{name} has more than one patch per tile')
        links.append(frame[['tile_id', 'patch_id']].assign(source=name))
    mapping = pd.concat(links, ignore_index=True)[['tile_id', 'source', 'patch_id']]

    centres = pd.concat([frame[['tile_id', 'region', 'center_x', 'center_y']] for frame in snapped.values()])
    table = centres.drop_duplicates('tile_id').set_index('tile_id')
    half = TILE_SIZE_M / 2
    table['xmin'], table['xmax'] = table['center_x'] - half, table['center_x'] + half
    table['ymin'], table['ymax'] = table['center_y'] - half, table['center_y'] + half
    wide = mapping.pivot(index='tile_id', columns='source', values='patch_id')
    for name in snapped:
        table[f'{name}_patch_id'] = wide[name]
        table[f'in_{name}'] = table[f'{name}_patch_id'].notna()
    table = table.reset_index().sort_values(['region', 'center_y', 'center_x'],
                                            ascending=[True, False, True], ignore_index=True)
    return table, mapping.sort_values(['tile_id', 'source'], ignore_index=True)


def coverage_summary(table: pd.DataFrame) -> pd.DataFrame:
    """Tiles per region found by each source and by all of them."""
    flags = [column for column in table.columns if column.startswith('in_')]
    summary = table.groupby('region')[flags].sum()
    summary.insert(0, 'tiles', table.groupby('region').size())
    summary['in_all_sources'] = table[flags].all(axis=1).groupby(table['region']).sum()
    return summary.reset_index()


def build(root: Path, similarity_run: Path | None, operability_runs: dict[str, Path]) -> Path:
    """Write `moon_tiles.csv`, `tile_sources.csv` and a coverage summary as a new run."""
    root = root.resolve()
    inputs: dict[str, Path] = {}
    if similarity_run is not None:
        inputs['similarity'] = (root / similarity_run).resolve() / 'patches.csv'
    for name, folder in operability_runs.items():
        inputs[name] = (root / folder).resolve() / 'predictions.csv'
    config = {'tile_size_m': TILE_SIZE_M, 'crs': MOON_CRS, 'lattice_tolerance_m': LATTICE_TOLERANCE_M,
              'inputs': {name: str(path.parent.relative_to(root)) for name, path in inputs.items()}}
    with Run(root, 'moon_tiles', config, 'shared/moon_tiles.py') as run:
        evidence: dict[str, str] = {}
        frames = {}
        for name, path in inputs.items():
            check_input(path, verify_run(path.parent), evidence)
            run.input(path)
            frames[name] = pd.read_csv(path)
        similarity = frames.pop('similarity', None)
        table, mapping = build_tile_table(similarity, frames)
        table.to_csv(run.path('moon_tiles.csv'), index=False)
        mapping.to_csv(run.path('tile_sources.csv'), index=False)
        summary = coverage_summary(table)
        summary.to_csv(run.path('coverage_by_region.csv'), index=False)
        run.record['result'] = {'tiles': int(len(table)), 'sources': sorted(mapping['source'].unique()),
                                'regions': sorted(table['region'].unique())}
    return run.directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--similarity-run', type=Path,
                        help='terrain_learning_readiness run holding patches.csv')
    parser.add_argument('--operability-run', action='append', default=[], metavar='NAME=RUN',
                        help='Lunar inference run holding predictions.csv, e.g. rover=data/processed/...')
    args = parser.parse_args()
    runs = {}
    for item in args.operability_run:
        name, _, folder = item.partition('=')
        if not name or not folder or name in runs or name == 'similarity':
            raise SystemExit(f'Expected a unique NAME=RUN pair, got {item!r}')
        runs[name] = Path(folder)
    print(json.dumps({'run': str(build(args.root, args.similarity_run, runs))}))


if __name__ == '__main__':
    main()
