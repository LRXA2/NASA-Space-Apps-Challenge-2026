"""Reproduce the frozen development sample; refuses to overwrite the original record."""
import hashlib
import json
from pathlib import Path

import pandas as pd
from pyproj import Transformer
from rasterio.crs import CRS


def main() -> None:
    root = next(p for p in (Path.cwd(), *Path.cwd().parents) if (p / 'outline.md').exists())
    prior = root / 'data/processed/analysis/candidate-inspection-20261029T132642335288Z'
    grids_path = root / 'data/processed/analysis/screening-eda-20261029T091841917085Z/site_grids.json'
    grids = json.loads(grids_path.read_text())
    uses = pd.read_csv(prior / 'arizona_candidate_uses.csv')
    native = pd.read_csv(prior / 'native_candidate_classes.csv').set_index('candidate_id')
    panels = pd.read_csv(prior / 'gallery_panels.csv')
    reasons: dict[str, list[str]] = {}
    for scenario in ['baseline', 'with_planarity']:
        group = uses.loc[uses['scenario'] == scenario].copy()
        group['center_row'] = group['candidate_id'].str.split(':').str[2].astype(int)
        group['center_col'] = group['candidate_id'].str.split(':').str[3].astype(int)
        for kind, selected in [
            ('high', group.sort_values(['query_uses', 'center_row', 'center_col'], ascending=[False, True, True]).head(2)),
            ('low', group.sort_values(['query_uses', 'center_row', 'center_col']).head(1)),
        ]:
            for candidate_id in selected['candidate_id']:
                reasons.setdefault(candidate_id, []).append(f'{scenario}_{kind}_reuse')
    for site, panel in [('atacama', 'Atacama baseline'), ('wadi', 'Wadi baseline')]:
        for gallery in [1, 8]:
            entry = panels.loc[(panels['gallery'] == gallery) & (panels['panel'] == panel)]
            assert len(entry) == 1
            reasons.setdefault(str(entry.iloc[0]['unit_id']), []).append(f'{site}_gallery_{gallery:02d}')
    records = []
    features = []
    for i, (candidate_id, selected_reasons) in enumerate(reasons.items(), 1):
        item = native.loc[candidate_id].to_dict()
        site = str(item['region'])
        crs = CRS.from_wkt(grids[site]['crs_wkt'])
        x, y = float(item['center_x_m']), float(item['center_y_m'])
        project = Transformer.from_crs(crs, 4326, always_xy=True)
        lon, lat = project.transform(x, y)
        bounds = [x - 300, y - 300, x + 300, y + 300]
        ring = [project.transform(xx, yy) for xx, yy in [(bounds[0], bounds[1]), (bounds[2], bounds[1]), (bounds[2], bounds[3]), (bounds[0], bounds[3]), (bounds[0], bounds[1])]]
        record = {'sample_id': f'S{i:02d}', 'candidate_id': candidate_id, 'region': site,
                  'selection_reason': ';'.join(selected_reasons), 'epsg': crs.to_epsg(),
                  'center_x_m': x, 'center_y_m': y, 'longitude': lon, 'latitude': lat,
                  'xmin': bounds[0], 'ymin': bounds[1], 'xmax': bounds[2], 'ymax': bounds[3],
                  'patch_row': int(item['row']), 'patch_col': int(item['col']),
                  'worldcover_tree_fraction': item['class_10_fraction'], 'worldcover_bare_fraction': item['class_60_fraction']}
        for scenario in ['baseline', 'with_planarity']:
            count = uses.loc[(uses['scenario'] == scenario) & (uses['candidate_id'] == candidate_id), 'query_uses']
            record[f'{scenario}_query_uses'] = int(count.iloc[0]) if len(count) else 0
        records.append(record)
        features.append({'type': 'Feature', 'properties': record, 'geometry': {'type': 'Polygon', 'coordinates': [ring]}})
    assert len(records) == 9 and len({r['candidate_id'] for r in records}) == 9
    destination = root / 'data/reference/source-check-sample-20261029'
    destination.mkdir(parents=True, exist_ok=False)
    pd.DataFrame(records).to_csv(destination / 'sample.csv', index=False)
    (destination / 'footprints.geojson').write_text(json.dumps({'type': 'FeatureCollection', 'features': features}, indent=2))
    paths = [prior / name for name in ['provenance.json', 'arizona_candidate_uses.csv', 'native_candidate_classes.csv', 'gallery_panels.csv']]
    paths += [grids_path, root / 'outline.md', Path(__file__)]
    manifest = {'selection_complete': True, 'inputs': {str(p.relative_to(root)): hashlib.sha256(p.read_bytes()).hexdigest() for p in paths},
                'outputs': {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in destination.iterdir()}}
    (destination / 'provenance.json').write_text(json.dumps(manifest, indent=2))
    print(pd.DataFrame(records)[['sample_id', 'candidate_id', 'selection_reason', 'longitude', 'latitude']].to_string(index=False))


if __name__ == '__main__':
    main()
