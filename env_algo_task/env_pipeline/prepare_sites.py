"""Offline, reproducible fixtures from native LOLA products; NEVER reads sites.csv.

Preparation needs numpy/rasterio/PyYAML. The standalone scorer does not import this.
Run --sample first; it writes to a separate directory, never over the main fixtures.
"""
import argparse
from contextlib import ExitStack
import csv
import hashlib
import json
import math
from pathlib import Path

import numpy as np
import rasterio
from rasterio.windows import Window, from_bounds
import yaml


HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[1]
DATA = ROOT / "env_algo_task/data"
NASA_2022 = "https://www.nasa.gov/news-release/nasa-identifies-candidate-regions-for-landing-next-americans-on-moon/"
PRODUCTS = {
    "sun": "solar_illumination/AVGVISIB_85S_060M_201608.TIF",
    "earth": "earth_visibility/AVGVISIB_85S_060M_201608_EARTH.TIF",
    "shadow": "permanent_shadow/LPSR_85S_060M_201608.TIF",
    "sky": "sky_visibility/SKYV_65S_240M.TIF",
}


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def native_values(dataset, bounds):
    """Mask fills before scaling; include native pixel centres in half-open bounds."""
    left, bottom, right, top = bounds
    raw_window = from_bounds(*bounds, dataset.transform)
    col, row = math.floor(raw_window.col_off), math.floor(raw_window.row_off)
    stop_col = math.ceil(raw_window.col_off + raw_window.width)
    stop_row = math.ceil(raw_window.row_off + raw_window.height)
    if col < 0 or row < 0 or stop_col > dataset.width or stop_row > dataset.height:
        raise ValueError(f"Footprint outside source raster: {bounds}")
    window = Window(col, row, stop_col-col, stop_row-row)
    raw = dataset.read(1, window=window, masked=True)
    transform = dataset.window_transform(window)
    x = transform.c + (np.arange(raw.shape[1]) + .5) * transform.a
    y = transform.f + (np.arange(raw.shape[0]) + .5) * transform.e
    inside = (y[:, None] >= bottom) & (y[:, None] < top) & (x[None, :] >= left) & (x[None, :] < right)
    valid = inside & ~np.ma.getmaskarray(raw)
    values = raw.data.astype(float) * dataset.scales[0] + dataset.offsets[0]
    valid &= np.isfinite(values)
    return values, valid, int(inside.sum())


def profile(datasets, bounds):
    arrays = {name: native_values(dataset, bounds) for name, dataset in datasets.items()}
    sun, earth, shadow = (arrays[n] for n in ("sun", "earth", "shadow"))
    joint = sun[1] & earth[1] & shadow[1]
    count = int(joint.sum())
    if not count:
        raise ValueError(f"No co-supported source pixels: {bounds}")
    for values, _, _ in (sun, earth, shadow):
        if np.any((values[joint] < 0) | (values[joint] > 1)):
            raise ValueError("Decoded fraction outside [0, 1]")
    if not np.isin(shadow[0][joint], [0.0, 1.0]).all():
        raise ValueError("Permanent-shadow product is not binary after label scaling")
    sky, sky_valid, _ = arrays["sky"]
    if not sky_valid.any():
        raise ValueError("No native sky support")
    if np.any((sky[sky_valid] < 0) | (sky[sky_valid] > 4 * math.pi)):
        raise ValueError("Decoded sky solid angle outside [0, 4*pi]")
    result = {
        "median_sun_visibility_fraction": float(np.median(sun[0][joint])),
        "median_earth_visibility_fraction": float(np.median(earth[0][joint])),
        "permanently_shadowed_cell_fraction": float(np.mean(shadow[0][joint])),
        "median_visible_sky_fraction": float(np.median(sky[sky_valid]) / (4 * math.pi)),
    }
    support = dict(joint_60m_pixels=count, footprint_60m_centres=sun[2],
                   native_240m_sky_pixels=int(sky_valid.sum()))
    return result, support


def review_evidence(external_root):
    """Cross-check inference choices against distinct completed EDA studies.

    No values from these studies are inserted into site measurement cells.
    Pins deliberately avoid silently switching to a new run on a later rebuild.
    """
    pins = {
        "dar_020_candidate_environment": "20261109T142736412889Z_04ccd0",
        "dar_021_preference_influence": "20261109T142749542712Z_8afae4",
        "dar_022_rule_influence": "20261109T142752187951Z_6b8993",
        "subject_terrain_time": "20261110T210226961886Z_f00b81",
        "subject_polar_thermal": "20261110T233730894536Z_e98b6f",
        "subject_radiation_time": "20261110T233725005604Z_72515a",
        "subject_plasma": "20261110T231619494574Z_f61cb6",
    }
    review = []
    for stage, run_id in pins.items():
        folder = DATA / "processed/analysis" / stage / run_id
        record = json.loads((folder / "provenance.json").read_text())
        if record["status"] != "complete":
            raise ValueError(f"Reviewed EDA run is not complete: {folder}")
        findings = json.loads((folder / "findings.json").read_text())
        review.append(dict(stage=stage, run=run_id,
                           findings_sha256=sha256(folder / "findings.json"),
                           conclusion=findings.get("base_conclusion", findings.get("limits"))))
    terrain = DATA / "processed/analysis/subject_terrain_time" / pins["subject_terrain_time"] / "static_vs_point_context.csv"
    with terrain.open(newline="") as handle:
        comparisons = list(csv.DictReader(handle))
    if len(comparisons) != 14 or any(r["substitutable_for_static_candidate_profile"] != "False" for r in comparisons):
        raise ValueError("Reviewed regional-to-candidate non-substitution contract changed")
    # Direct source check in the OTHER dataset folder: static PRP has no applicable chronology.
    label = external_root / "datasets/D20_PRP/dlre_prp_south.lbl"
    text = label.read_text()
    if "START_TIME                   = 'N/A'" not in text or "STOP_TIME                    = 'N/A'" not in text:
        raise ValueError("PRP time-applicability label changed; review before rebuilding")
    review.append(dict(source=str(label), sha256=sha256(label),
                       conclusion="Native START_TIME/STOP_TIME are N/A, agreeing with Dar050. Do not fill candidate-window thermal profiles with static annual PRP quantities."))
    return dict(reviewed_sources=review,
                crosscheck=dict(terrain_reference_vs_candidate_rows=14,
                                all_reference_substitutions_rejected=True,
                                terrain_table_sha256=sha256(terrain)),
                policy="Dar020 support/cohort limits + Dar021 normalization sensitivity + Dar022 gate-first Unknown semantics + Dar054 temporal/footprint limits + Dar050/native PRP time applicability + Dar049/046 nonlocal hazard limitations. No single EDA source sets safety thresholds.")


def build(output, *, sample=False, external_root=Path("D:/projects/NASA Dataset")):
    config = yaml.safe_load((HERE / "config_nasa_reference.yml").read_text())
    evidence_review = review_evidence(external_root)
    fields = ["id", *config["metadata_columns"]]
    fields += [m["column"] for d in config["domains"].values() for m in d["metrics"]]
    fields = list(dict.fromkeys(fields))
    # Bounds are the documented SDEM product footprints, not invented site coordinates.
    bounds_path = ROOT / "env_algo_task/EDA/Moon/Stage3_Requirements/stage3_acquired_config.json"
    regions = json.loads(bounds_path.read_text())["region_bounds_m"]
    if sample:
        regions = dict(list(sorted(regions.items()))[:1])
    source_paths = {key: DATA / "moon/illumination_2016/geotiff/south" / value for key, value in PRODUCTS.items()}
    sources = []
    for key, path in source_paths.items():
        receipt = json.loads(path.with_suffix(path.suffix + ".json").read_text())
        digest = sha256(path)
        if digest != receipt["sha256"]:
            raise ValueError(f"Source hash disagrees with receipt: {path}")
        sources.append(dict(key=key, path=str(path.relative_to(ROOT)), sha256=digest,
                            url=receipt["source"]["url"]))
    rows, evidence, proposals = [], [], []
    with ExitStack() as stack:
        datasets = {key: stack.enter_context(rasterio.open(path)) for key, path in source_paths.items()}
        base = datasets["sun"]
        for key in ("earth", "shadow"):
            other = datasets[key]
            if (base.crs, base.transform, base.shape) != (other.crs, other.transform, other.shape):
                raise ValueError("Sun/Earth/shadow native grids must match")
        for index, (region, bounds) in enumerate(sorted(regions.items()), 1):
            elevations = list((DATA / "moon/sdem/regions" / region).glob("*GLDELEV_005.tif"))
            if len(elevations) != 1:
                raise ValueError(f"Need one native SDEM footprint source for {region}")
            with rasterio.open(elevations[0]) as elevation:
                # WKT datum labels differ (Moon 2015 vs Moon2000); the actual
                # stereographic projection/spherical radius/units must match.
                if elevation.crs.to_dict() != base.crs.to_dict() or not np.allclose(tuple(elevation.bounds), bounds, rtol=0, atol=1e-6):
                    raise ValueError(f"Configured bounds/CRS disagree with native SDEM product: {region}")
            sources.append(dict(key=f"footprint:{region}", path=str(elevations[0].relative_to(ROOT)),
                                sha256=sha256(elevations[0])))
            values, support = profile(datasets, bounds)
            row = dict(id=f"nasa_{index:03d}", candidate_id=region, sample_type="NASA",
                       comparison_scale="regional_product_footprint", region=region,
                       declaration_year="2022", declaration_source=NASA_2022,
                       footprint_bounds_m=json.dumps(bounds, separators=(",", ":")),
                       evidence_note="NASA-declared 2022 region; SDEM product-rectangle summary, not an approved base or exact landing footprint. Static LOLA model; mission-local hazards and chronology missing.", **values)
            rows.append(row)
            evidence.append(dict(id=row["id"], **support))
            # Nonoverlapping 1.2 km proposals. No claim that NASA selected these patches.
            left, bottom, right, top = bounds
            candidates = []
            for x in np.arange(left, right-1199, 1200):
                for y in np.arange(bottom, top-1199, 1200):
                    patch = [float(x), float(y), float(x+1200), float(y+1200)]
                    vals, sup = profile(datasets, patch)
                    if sup["joint_60m_pixels"] != sup["footprint_60m_centres"]:
                        continue
                    sun, earth = vals["median_sun_visibility_fraction"], vals["median_earth_visibility_fraction"]
                    candidates.append((min(sun, earth), (sun+earth)/2, patch, vals, sup))
            candidates.sort(key=lambda item: (-item[0], -item[1], item[2]))
            if len(candidates) < 2:
                raise ValueError(f"Insufficient fully supported proposal patches in {region}")
            proposals.append((region, candidates[:2]))
    # Round-robin regional coverage, then a second patch per region: 13 project proposals.
    chosen = [(region, candidates[k]) for k in range(2) for region, candidates in proposals]
    for index, (region, (_, _, bounds, values, support)) in enumerate(chosen[:2 if sample else 13], 1):
        row = dict(id=f"synthetic_{index:03d}", candidate_id=f"PROJECT_PROPOSAL:{region}:{index:03d}",
                   sample_type="Synthetic", comparison_scale="project_1.2km_patch", region=region,
                   footprint_bounds_m=json.dumps(bounds, separators=(",", ":")),
                   evidence_note="Hypothetical base footprint with freshly sampled real LOLA model values; NOT NASA-declared. Selected for balanced Sun/Earth access only; no buildability or safety claim.", **values)
        rows.append(row)
        evidence.append(dict(id=row["id"], **support))
    # Arbitrary fictional quantities, not empirical site measurements.
    dummy = [(.9,.9,156,3), (.8,.8,155.99,3), (.8,.8,156,0), (.8,.8,156,-.01),
             (1,1,None,3), (0,0,0,-5), (1,1,156,10), (None,.7,156,3),
             (.7,None,156,3), (.5,.5,156,None)]
    for index, (sun, earth, hours, link) in enumerate(dummy[:2 if sample else 10], 1):
        rows.append(dict(id=f"dummy_{index:03d}", candidate_id=f"FICTIONAL_TEST_{index:03d}",
                         sample_type="Dummy", comparison_scale="fictional_test",
                         start_utc="2030-01-01T00:00:00Z", stop_utc="2030-01-07T12:00:00Z",
                         evidence_note="Arbitrary software fixture. Dates, continuous sunlight and link margin are fictional; not a lunar site.",
                         median_sun_visibility_fraction=sun, median_earth_visibility_fraction=earth,
                         window_continuous_sunlight_hours=hours, window_minimum_link_margin_db=link))
    if not sample and (len(regions), len(rows)) != (7, 30):
        raise ValueError("Expected seven supported NASA region footprints and 30 total rows")
    output.mkdir(parents=True, exist_ok=True)
    with (output / "sites.csv").open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        writer.writerows(rows)
    template = output / "input_template.csv" if sample else HERE / "input_template.csv"
    with template.open("w", newline="", encoding="utf-8") as handle:
        csv.writer(handle, lineterminator="\n").writerow(fields)
    manifest = dict(schema=1, sample=sample, source_rule="Never read or reuse old sites.csv or its results",
                    preparation_script_sha256=sha256(Path(__file__)), bounds_source=str(bounds_path.relative_to(ROOT)),
                    bounds_source_sha256=sha256(bounds_path), sources=sources, support=evidence,
                    selection="13 disjoint 1.2km patches: regional round-robin, max min(sun median, Earth median), then equal mean, then bounds; access-only proposals",
                    missing_policy="No global/orbital/history-to-site substitution. Unsupported quantities and dates left blank.",
                    csv_sha256=sha256(output / "sites.csv"))
    manifest["evidence_review"] = evidence_review
    (output / "source_provenance.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps(dict(rows=len(rows), counts={kind:sum(r["sample_type"]==kind for r in rows)
                                               for kind in ("NASA", "Synthetic", "Dummy")}, output=str(output))))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--sample", action="store_true")
    parser.add_argument("--external-root", type=Path, default=Path("D:/projects/NASA Dataset"))
    args = parser.parse_args()
    build(HERE / ("outputs/verification/sample_check" if args.sample else "inputs"),
          sample=args.sample, external_root=args.external_root)
