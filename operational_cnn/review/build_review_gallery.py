"""Create deterministic visual-review galleries from a completed EDA run."""
from __future__ import annotations

import argparse
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from notebooks.shared.inspection import verify_run
from notebooks.shared.processing import Run


CLASSES = ('operable', 'marginal', 'non_operable')


def select_examples(patches: pd.DataFrame) -> pd.DataFrame:
    """Select the patch nearest each region/class median P90 slope."""
    rows = []
    primary = patches.loc[patches['size_m'] == 960].copy()
    for (region, label_class), group in primary.groupby(['region', 'label_class'], sort=True):
        target = group['slope_p90_deg'].median()
        selected = group.assign(distance=(group['slope_p90_deg'] - target).abs()).sort_values(
            ['distance', 'patch_id']).iloc[0]
        rows.append(selected.drop(labels='distance'))
    return pd.DataFrame(rows).sort_values(['region', 'label_class']).reset_index(drop=True)


def build(root: Path, source_relative: Path) -> Path:
    root = root.resolve()
    source = (root / source_relative).resolve()
    processed = (root / 'data/processed').resolve()
    if not source.is_relative_to(processed):
        raise ValueError('Source must be a completed processed run')
    verify_run(source)
    patches_path = source / 'patches.csv'
    patches = pd.read_csv(patches_path)
    selected = select_examples(patches)
    config = {
        'source_run': str(source.relative_to(root)),
        'size_m': 960,
        'selection': 'nearest region/class median P90 slope; stable patch-ID ties',
        'display_only': True,
    }
    with Run(root, 'terrain_operability_review', config,
             '../operational_cnn/notebooks/37_operational_terrain_eda.ipynb') as run:
        run.input(Path(__file__))
        run.input(source / 'provenance.json')
        run.input(patches_path)
        selected.to_csv(run.path('selected_samples.csv'), index=False)
        for region in sorted(selected['region'].unique()):
            shard = source / f'tensors/{region}_960m.npz'
            run.input(shard)
            with np.load(shard) as archive:
                tensors = archive['physical']
            region_rows = selected.loc[selected['region'] == region].set_index('label_class')
            figure, axes = plt.subplots(3, 4, figsize=(13, 10), constrained_layout=True)
            for row_index, label_class in enumerate(CLASSES):
                if label_class not in region_rows.index:
                    for axis in axes[row_index]:
                        axis.axis('off')
                    axes[row_index, 0].text(.5, .5, f'{label_class}\nno eligible sample',
                                            ha='center', va='center', transform=axes[row_index, 0].transAxes)
                    continue
                record = region_rows.loc[label_class]
                tensor = tensors[int(record['tensor_index'])]
                elevation, slope, rough90 = tensor[:3]
                displays = (
                    (elevation, 'relative elevation (m)', 'terrain'),
                    (slope, 'slope (deg)', 'magma'),
                    (rough90, '90 m roughness (m)', 'viridis'),
                    (slope <= 15., 'nominal passable (≤15°)', 'gray'),
                )
                for axis, (values, title, cmap) in zip(axes[row_index], displays, strict=True):
                    options = {'vmin': 0, 'vmax': 1} if title == 'nominal passable (≤15°)' else {}
                    image = axis.imshow(values, cmap=cmap, origin='upper', **options)
                    axis.set_title(title)
                    axis.set_xticks([])
                    axis.set_yticks([])
                    if title != 'nominal passable (≤15°)':
                        figure.colorbar(image, ax=axis, shrink=.72)
                axes[row_index, 0].set_ylabel(
                    f"{label_class}\nP90 slope {record['slope_p90_deg']:.1f}°\n"
                    f"nominal crossings {int(record['nominal_crossing_count'])}")
            figure.suptitle(f'{region}: provisional 960 m label review')
            figure.savefig(run.path(f'{region}_gallery.png'), dpi=160)
            plt.close(figure)
        run.record['result'] = {
            'selected_samples': int(len(selected)),
            'regions': sorted(selected['region'].unique()),
            'trained_model': False,
            'purpose': 'visual review of provisional labels',
        }
    return run.directory


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--root', type=Path, default=Path(__file__).resolve().parents[2])
    parser.add_argument('--source-run', type=Path, required=True)
    arguments = parser.parse_args()
    print(build(arguments.root, arguments.source_run))
