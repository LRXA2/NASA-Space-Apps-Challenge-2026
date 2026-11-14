"""One row per lunar tile: terrain operability, with an optional environment join.

Reads an operability or walkability `predictions.csv`, keys it by the shared
`tile_id` from `notebooks.shared.moon_tiles`, and keeps the rover class, the
human-terrain class (when present), crossing directions and slope figures.
Operations and survival scores from the environment pipeline's compact output
join per tile when its IDs are tile IDs (scorer input built by
`integration.tile_environment`, `env_scope` = "tile"). Otherwise they join by
region: baselines `eda_001`-`eda_007` each summarise one of the seven terrain
regions, so every tile in a region carries that region's scores
(`env_scope` = "region"), and other rows (further NASA names, synthetic, dummy
and Apollo scenarios) are skipped.

This joins existing outputs only. It adds no new score, threshold or claim:
terrain classes remain Earth-trained proxies and environment scores keep the
assumptions of the policy that produced them.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd

from notebooks.shared.inspection import check_input, verify_run
from notebooks.shared.moon_tiles import build_tile_table
from notebooks.shared.processing import Run

DIRECTIONS = ('north_south', 'east_west', 'northwest_southeast', 'northeast_southwest')
# The rover-only inference run uses the older, unprefixed class column names.
ROVER_ONLY_NAMES = {
    'predicted_class': 'predicted_rover_class',
    'predicted_class_probability': 'predicted_rover_probability',
    'probability_operable': 'rover_probability_operable',
    'probability_marginal': 'rover_probability_marginal',
    'probability_non_operable': 'rover_probability_non_operable',
}
TERRAIN_COLUMNS = [
    'slope_median_deg', 'slope_p90_deg', 'relative_relief_m',
    'predicted_rover_class', 'predicted_rover_probability',
    'rover_probability_operable', 'rover_probability_marginal', 'rover_probability_non_operable',
    *[f'predicted_{name}' for name in DIRECTIONS],
]
HUMAN_COLUMNS = [
    'predicted_human_terrain_class', 'predicted_human_terrain_probability',
    'human_probability_easy', 'human_probability_caution', 'human_probability_unsuitable',
    'direct_human_terrain_rule', 'cnn_agrees_with_direct_human_rule',
]
# Environment pipeline baselines that summarise each terrain region (env_pipeline/README.md).
REGION_ENVIRONMENT_IDS = {
    'eda_001': 'A3CLR22_10_Leibnitz_Beta_Plateau',
    'eda_002': 'A3CLR22_11_Malapert_Massif',
    'eda_003': 'A3CLR22_12_deGerlache_Kocher_Massif',
    'eda_004': 'A3CLR22_2_Haworth',
    'eda_005': 'A3CLR22_3_Faustini_Rim_A',
    'eda_006': 'A3CLR22_4_deGerlache_Rim_2',
    'eda_007': 'A3CLR22_5_Connecting_Ridge_Extension',
}
ENVIRONMENT_REQUIRED = ['ID', 'operations_score', 'survival_score', 'operations_status', 'survival_status',
                        'operations_fail_reason', 'survival_fail_reason']


def terrain_sites(predictions: pd.DataFrame) -> pd.DataFrame:
    """Per-tile terrain table from an operability or walkability `predictions.csv`."""
    frame = predictions.rename(columns=ROVER_ONLY_NAMES)
    missing = [name for name in TERRAIN_COLUMNS if name not in frame.columns]
    if missing:
        raise ValueError(f'Terrain predictions are missing columns: {missing}')
    _, mapping = build_tile_table(operability={'terrain': frame})
    tiles = mapping.set_index('patch_id')['tile_id']
    human = [name for name in HUMAN_COLUMNS if name in frame.columns]
    result = frame[['patch_id', 'region', 'center_x', 'center_y', *TERRAIN_COLUMNS, *human]].rename(
        columns={'patch_id': 'terrain_patch_id'})
    result.insert(0, 'tile_id', frame['patch_id'].map(tiles))
    crossings = result[[f'predicted_{name}' for name in DIRECTIONS]].astype(bool)
    result.insert(result.columns.get_loc('predicted_rover_probability') + 1,
                  'predicted_crossing_count', crossings.sum(axis=1))
    return result


def environment_scores(results: pd.DataFrame) -> tuple[pd.DataFrame, list[str], str]:
    """Compact output renamed to `env_*`; returns (scores, skipped IDs, scope).

    Scope is `tile` when every ID is a tile ID (per-tile scorer input from
    `integration.tile_environment`), otherwise `region`: rows `eda_001`-`eda_007`
    are kept and every other row is skipped.
    """
    missing = [name for name in ENVIRONMENT_REQUIRED if name not in results.columns]
    if missing:
        raise ValueError(f'Environment results are missing columns: {missing}; '
                         'supply the environment pipeline compact (Operations/Survival) output')
    ids = results['ID'].astype(str)
    if results['ID'].isna().any() or ids.duplicated().any():
        raise ValueError('Environment results need one row per unique ID')
    scores = results.rename(columns=lambda name: 'env_id' if name == 'ID' else f'env_{name}')
    tiles = ids.str.count(':') == 2
    if tiles.any():
        if not tiles.all():
            raise ValueError('Environment results mix tile IDs with other IDs, e.g. '
                             f'{", ".join(ids[~tiles][:3])}')
        scores.insert(0, 'tile_id', ids)
        scores.insert(1, 'env_scope', 'tile')
        return scores.reset_index(drop=True), [], 'tile'
    regional = ids.isin(REGION_ENVIRONMENT_IDS)
    if not regional.any():
        raise ValueError(f'Environment results hold neither tile IDs nor the region baselines '
                         f'{", ".join(REGION_ENVIRONMENT_IDS)}')
    scores = scores.loc[regional]
    scores.insert(0, 'region', ids[regional].map(REGION_ENVIRONMENT_IDS))
    scores.insert(1, 'env_scope', 'region')
    return scores.reset_index(drop=True), sorted(ids[~regional]), 'region'


def build_moon_sites(predictions: pd.DataFrame,
                     environment: pd.DataFrame | None = None) -> pd.DataFrame:
    """Join terrain predictions and, optionally, per-tile or region-level environment scores."""
    sites = terrain_sites(predictions)
    if environment is None:
        sites['env_assessed'] = False
    else:
        scores, _, scope = environment_scores(environment)
        key = 'tile_id' if scope == 'tile' else 'region'
        unknown = sorted(set(scores[key]) - set(sites[key])) if scope == 'tile' else []
        if unknown:
            raise ValueError(f'{len(unknown)} environment tile IDs are not in these predictions, '
                             f'e.g. {", ".join(unknown[:3])}')
        sites = sites.merge(scores, on=key, how='left',
                            validate='one_to_one' if scope == 'tile' else 'many_to_one')
        sites['env_assessed'] = sites[key].isin(scores[key])
    return sites.sort_values(['region', 'center_y', 'center_x'], ascending=[True, False, True],
                             ignore_index=True)


def summary_by_region(sites: pd.DataFrame) -> pd.DataFrame:
    """Tile counts per region by rover class, human class and environment status."""
    groups = sites.groupby('region')
    parts = [groups.size().rename('tiles'),
             pd.crosstab(sites['region'], sites['predicted_rover_class']).add_prefix('rover_')]
    if 'predicted_human_terrain_class' in sites.columns:
        parts.append(pd.crosstab(sites['region'], sites['predicted_human_terrain_class']).add_prefix('human_'))
    parts.append(groups['env_assessed'].sum().rename('env_assessed'))
    for assessment in ('operations', 'survival'):
        if f'env_{assessment}_status' in sites.columns:
            parts.append((sites[f'env_{assessment}_status'] == 'Pass').groupby(sites['region']).sum()
                         .rename(f'env_{assessment}_pass'))
    summary = pd.concat(parts, axis=1).fillna(0).astype(int)
    if 'env_operations_score' in sites.columns:
        summary = summary.join(groups[['env_operations_score', 'env_survival_score']].median()
                               .add_prefix('median_'))
    return summary.reset_index()


def build(root: Path, terrain_run: Path, environment_csv: Path | None = None) -> Path:
    """Write `moon_sites.csv` and a per-region summary as a new versioned run."""
    root = root.resolve()
    predictions_path = (root / terrain_run).resolve() / 'predictions.csv'
    config = {'terrain_run': str(predictions_path.parent.relative_to(root)),
              'environment_csv': None if environment_csv is None
              else str((root / environment_csv).resolve().relative_to(root))}
    with Run(root, 'moon_sites', config, '../integration/moon_sites.py') as run:
        check_input(predictions_path, verify_run(predictions_path.parent), {})
        run.input(predictions_path)
        environment, skipped = None, []
        if environment_csv is not None:
            environment_path = (root / environment_csv).resolve()
            run.input(environment_path)
            environment = pd.read_csv(environment_path)
            skipped = environment_scores(environment)[1]
        sites = build_moon_sites(pd.read_csv(predictions_path), environment)
        sites.to_csv(run.path('moon_sites.csv'), index=False)
        summary = summary_by_region(sites)
        summary.to_csv(run.path('summary_by_region.csv'), index=False)
        run.record['result'] = {'tiles': int(len(sites)), 'env_assessed': int(sites['env_assessed'].sum()),
                                'regions': sorted(sites['region'].unique()),
                                'env_ids_without_tiles': skipped}
    return run.directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path('.'))
    parser.add_argument('--terrain-run', type=Path, required=True,
                        help='Lunar operability or walkability inference run holding predictions.csv')
    parser.add_argument('--environment-csv', type=Path,
                        help='Environment pipeline compact output keyed by tile IDs, or eda_001-eda_007 by region')
    args = parser.parse_args()
    print(json.dumps({'run': str(build(args.root, args.terrain_run, args.environment_csv))}))


if __name__ == '__main__':
    main()
