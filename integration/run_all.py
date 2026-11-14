"""Run the stitched Moon pipeline: tiles, environment, per-tile sites and Earth matches.

One command, one config (`run_all.json`). It needs processed outputs only (the
walkability inference run, the similarity model, dataset and orientation
runs), not raw downloads. Each stage still writes its own versioned run; this
script records them and copies the files the app export reads into one
`data/processed/moon_pipeline/<run>/` folder:

- `moon_tiles.csv`: one row per 960 m lunar tile and which sources cover it
- `moon_sites.csv`: terrain classes plus region-level environment scores
- `earth_matches.csv`: top-k Earth patches per tile for every Earth site
- `physical_comparison.csv`: the five physical checks behind every match
- `environment.csv`: the environment scorer's compact output, when configured
- `environment_detailed.csv`: the same scoring with `--detailed` (adds each hard gate's value, threshold and verdict)
- `environment_sites.csv` and `tile_support.csv`: the per-tile scorer input and
  which tiles had their map columns measured (`environment_scope` = "tile")
- `summary.json`: per-region counts, best-matching Earth sites and stage runs

Every tile is matched; nothing is shortlisted or combined into one score.
Terrain, environment and similarity stay separate, as `outline.md` asks.
"""
from __future__ import annotations

import argparse
import json
import shutil
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

import pandas as pd

from integration import moon_sites
from integration.tile_environment import build_tile_sites, map_paths
from notebooks.modeling.terrain_similarity.pipeline.artifacts import ArtifactConfig
from notebooks.modeling.terrain_similarity.pipeline.main import run_tile_matching
from notebooks.shared import moon_tiles
from notebooks.shared.processing import Run

DEFAULT_CONFIG = Path(__file__).with_name('run_all.json')
ENVIRONMENT_SCORER = 'env_algo_task/env_pipeline/env_pipeline.py'
CAVEAT_TERRAIN = 'Terrain classes are Earth-trained proxies.'
CAVEAT_ENVIRONMENT = {
    'tile': ('Environment scores use per-tile LOLA Sun, Earth, shadow and sky values where measured; every other '
             "environment input is the region baseline's test fixture value."),
    'region': ("Environment scores are the region baseline's (eda_001-eda_007), shared by every tile in a region; "
               'most of its inputs are test fixture values.'),
    None: 'No environment scores were computed.',
}
CAVEAT_SIMILARITY = 'Cosine is not a percentage or validated suitability.'
SCOPES = ('tile', 'region')


def caveat(environment_scope: str | None) -> str:
    """The run's caveat, worded for the environment scope that was actually used."""
    return ' '.join((CAVEAT_TERRAIN, CAVEAT_ENVIRONMENT[environment_scope], CAVEAT_SIMILARITY))


@dataclass(frozen=True)
class PipelineConfig:
    terrain_run: str
    similarity_config: str = 'notebooks/modeling/terrain_similarity/pipeline/config.json'
    environment_input: str | None = None
    environment_config: str | None = None
    environment_scope: str = 'tile'
    top_k_per_site: int = 3
    regions: tuple[str, ...] | None = None

    def __post_init__(self):
        if type(self.top_k_per_site) is not int or self.top_k_per_site < 1:
            raise ValueError('top_k_per_site must be a positive integer')
        if self.environment_scope not in SCOPES:
            raise ValueError(f'environment_scope must be one of {SCOPES}')
        if self.environment_config and not self.environment_input:
            raise ValueError('environment_config needs environment_input')


def load_config(path: Path, **overrides) -> PipelineConfig:
    """Read `run_all.json`; non-None keyword overrides replace its values."""
    values = json.loads(path.read_text(encoding='utf-8'))
    values.update({key: value for key, value in overrides.items() if value is not None})
    if values.get('regions') is not None:
        values['regions'] = tuple(values['regions'])
    return PipelineConfig(**values)


def select_regions(available: list[str], wanted: tuple[str, ...] | None) -> list[str]:
    """Full region IDs for names such as `Haworth` or `A3CLR22_2_Haworth`."""
    if wanted is None:
        return sorted(available)
    chosen = []
    for name in wanted:
        hits = [region for region in available if region == name or region.lower().endswith('_' + name.lower())]
        if len(hits) != 1:
            raise ValueError(f'Region {name!r} matches {hits or "nothing"}; choose from {sorted(available)}')
        chosen.append(hits[0])
    return sorted(set(chosen))


def score_environment(root: Path, config: PipelineConfig, output: Path, sites: Path | None = None,
                      *, detailed: bool = False) -> Path | None:
    """Run the environment scorer's compact (or detailed) export into `output`, if configured.

    `sites` replaces the configured input, e.g. with per-tile rows.
    """
    if config.environment_input is None:
        return None
    command = [sys.executable, str(root / ENVIRONMENT_SCORER), '--input', str(sites or root / config.environment_input),
               '--output', str(output), '--detailed' if detailed else '--compact', '--overwrite']
    if config.environment_config:
        command += ['--config', str(root / config.environment_config)]
    result = subprocess.run(command, cwd=root, capture_output=True, text=True)
    if result.returncode != 0:
        raise RuntimeError(f'Environment scorer failed:\n{result.stderr.strip() or result.stdout.strip()}')
    return output


def region_summary(sites: pd.DataFrame, matches: pd.DataFrame) -> pd.DataFrame:
    """Per region: terrain/environment counts plus each tile's best Earth site."""
    summary = moon_sites.summary_by_region(sites).set_index('region')
    best = matches.loc[matches['overall_rank'] == 1, ['tile_id', 'earth_region', 'cosine_similarity']]
    best = best.merge(sites[['tile_id', 'region']], on='tile_id')
    summary['tiles_matched'] = best.groupby('region').size()
    summary['median_best_cosine'] = best.groupby('region')['cosine_similarity'].median().round(4)
    counts = pd.crosstab(best['region'], best['earth_region']).add_prefix('best_site_')
    return summary.join(counts).fillna(0).reset_index()


def run_all(root: Path, config: PipelineConfig) -> Path:
    """Run every stage and write the combined output folder as a new versioned run."""
    root = root.resolve()
    similarity = ArtifactConfig(**json.loads((root / config.similarity_config).read_text(encoding='utf-8')))
    settings = {**asdict(config), 'similarity': asdict(similarity)}
    with Run(root, 'moon_pipeline', settings, '../integration/run_all.py') as run:
        stages: dict[str, Path] = {}
        stages['moon_tiles'] = moon_tiles.build(root, Path(similarity.dataset_run), {'walkability': Path(config.terrain_run)})
        sites_input = None
        if config.environment_input is not None and config.environment_scope == 'tile':
            covered = pd.read_csv(stages['moon_tiles'] / 'moon_tiles.csv')
            sites_input = build_tile_sites(root, covered[covered['in_walkability']],
                                           root / config.environment_input, run.path('environment_sites.csv'))
            for path in map_paths(root).values():
                run.input(path)
        environment = score_environment(root, config, run.path('environment.csv'), sites_input)
        # Same input and config: the app reads per-gate evidence from this one.
        score_environment(root, config, run.path('environment_detailed.csv'), sites_input, detailed=True)
        stages['moon_sites'] = moon_sites.build(
            root, Path(config.terrain_run), None if environment is None else environment.relative_to(root))

        tiles = pd.read_csv(stages['moon_tiles'] / 'moon_tiles.csv')
        sites = pd.read_csv(stages['moon_sites'] / 'moon_sites.csv')
        regions = select_regions(sorted(sites['region'].unique()), config.regions)
        tiles, sites = tiles[tiles['region'].isin(regions)], sites[sites['region'].isin(regions)]
        matchable = set(tiles.loc[tiles[f'in_similarity_{similarity.view}'], 'tile_id'])
        tile_ids = [tile for tile in sites['tile_id'] if tile in matchable]
        stages['earth_matches'] = run_tile_matching(root, similarity, tile_ids, top_k=config.top_k_per_site)
        matches = pd.read_csv(stages['earth_matches'] / 'earth_matches.csv')

        tiles.to_csv(run.path('moon_tiles.csv'), index=False)
        sites.to_csv(run.path('moon_sites.csv'), index=False)
        shutil.copyfile(stages['earth_matches'] / 'earth_matches.csv', run.path('earth_matches.csv'))
        shutil.copyfile(stages['earth_matches'] / 'physical_comparison.csv', run.path('physical_comparison.csv'))
        by_region = region_summary(sites, matches)
        by_region.to_csv(run.path('summary_by_region.csv'), index=False)
        environment_scope = config.environment_scope if environment is not None else None
        summary = {
            'regions': regions,
            'tiles': int(len(sites)),
            'tiles_matched': len(tile_ids),
            'tiles_without_similarity_patch': int(len(sites) - len(tile_ids)),
            'environment_assessed_tiles': int(sites['env_assessed'].sum()),
            'environment_scope': environment_scope,
            'earth_sites': sorted(matches['earth_region'].unique()),
            'top_k_per_site': config.top_k_per_site,
            'similarity_model': asdict(similarity),
            'stage_runs': {name: path.relative_to(root).as_posix() for name, path in stages.items()},
            'caveat': caveat(environment_scope),
        }
        run.path('summary.json').write_text(json.dumps(summary, indent=2), encoding='utf-8')
        run.record['result'] = summary
    return run.directory


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[1])
    parser.add_argument('--config', type=Path, default=DEFAULT_CONFIG)
    parser.add_argument('--region', action='append', help='Limit to a region, e.g. Haworth (repeatable)')
    parser.add_argument('--top-k', type=int, dest='top_k_per_site', help='Earth matches kept per site')
    parser.add_argument('--no-environment', action='store_true', help='Skip the environment scorer')
    parser.add_argument('--environment-scope', choices=SCOPES,
                        help='Score each tile from the illumination maps, or join region baselines')
    args = parser.parse_args()
    config = load_config(args.config, regions=args.region, top_k_per_site=args.top_k_per_site,
                         environment_scope=args.environment_scope)
    if args.no_environment:
        config = PipelineConfig(**{**asdict(config), 'environment_input': None, 'environment_config': None})
    print(json.dumps({'run': str(run_all(args.root, config))}))


if __name__ == '__main__':
    main()
