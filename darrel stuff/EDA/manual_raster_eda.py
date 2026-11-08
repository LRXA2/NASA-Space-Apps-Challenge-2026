"""Bounded, label-driven readers for the manually supplied D27/D30 products."""
from contextlib import contextmanager
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from pyproj import Transformer
import rasterio
from rasterio.windows import Window

from notebooks.shared.processing import MOON_GEOGRAPHIC
from research_p1_readers import NS, pds3_number, pin_source
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from data_maintenance import resolve_data_path

ISIS_SOURCE = "https://isis.astrogeology.usgs.gov/7.2.0/Object/Developer/_special_pixel_8h_source.html"
SHADOW_SOURCE = "https://pds.shadowcam.im-ldi.com/document/archsis.pdf"
RADAR_SOURCE = "https://pds-geosciences.wustl.edu/lro/lro-l-mrflro-5-global-mosaic-v1/lromrf_1001/document/userguide.txt"
# Explicit category names survive ordinary CSV readers: bare "NULL" would be
# silently parsed as a missing string by pandas rather than a known pixel class.
SPECIAL_BITS = {"isis_null": 0xFF7FFFFB, "isis_lrs": 0xFF7FFFFC, "isis_lis": 0xFF7FFFFD,
                "isis_his": 0xFF7FFFFE, "isis_hrs": 0xFF7FFFFF}
CONTEXT_FIELDS = ["solar_visibility", "earth_visibility", "sky_view_sr", "elevation_m", "slope_deg"]


def local_value(root, name):
    matches = [e for e in root.iter() if e.tag.split("}")[-1] == name]
    if len(matches) != 1:
        raise ValueError(f"Missing/ambiguous XML {name}")
    return matches[0].text.strip()


def classify_pixels(values, nodata=None):
    """Decode exact ISIS float32 bit patterns; keep ordinary signed measurements."""
    a = np.asarray(values, dtype="<f4")
    result = np.full(a.shape, "valid", dtype="U12")
    bits = a.view("<u4")
    for name, number in SPECIAL_BITS.items():
        result[bits == number] = name
    result[~np.isfinite(a)] = "nonfinite"
    if nodata is not None and np.isfinite(nodata):
        declared = np.float32(nodata)
        result[(a == declared) & (result == "valid")] = "declared_nd"
    return result


def distribution(values):
    a = np.asarray(values, dtype=float)
    a = a[np.isfinite(a)]
    result = {"count": len(a), "minimum": np.nan, "q10": np.nan, "median": np.nan,
              "q90": np.nan, "maximum": np.nan}
    if len(a):
        result.update(zip(["minimum", "q10", "median", "q90", "maximum"],
                          np.quantile(a, [0, .1, .5, .9, 1]).tolist()))
    return result


def shadow_definition(label, image):
    root = ET.parse(label).getroot()
    if not local_value(root, "logical_identifier").endswith(":m013049982s_map_raw"):
        raise ValueError("Unexpected ShadowCam manual product identity")
    if local_value(root, "file_name").casefold() != image.name.casefold():
        raise ValueError("ShadowCam label names another image")
    if int(local_value(root, "file_size")) != image.stat().st_size:
        raise ValueError("ShadowCam TIFF byte count disagrees with its label")
    with rasterio.open(image) as src:
        if src.dtypes != ("float32",) or src.count != 1 or src.crs is None:
            raise ValueError("Expected one georeferenced float32 ShadowCam band")
        expected = [float(local_value(root, name)) for name in
                    ["upperleft_corner_x", "pixel_resolution_x", "upperleft_corner_y", "pixel_resolution_y"]]
        if not np.allclose([src.transform.c, src.transform.a, src.transform.f, -src.transform.e], expected,
                           rtol=0, atol=1e-7) or src.transform.b or src.transform.d:
            raise ValueError("TIFF geotransform differs from the XML")
        if not np.isclose(float(local_value(root, "a_axis_radius")), 1737400):
            raise ValueError("Unexpected lunar radius")
        projection = src.crs.to_dict()
        # The XML calls this latitude an origin; the actual TIFF is variant B:
        # pole at -90, standard parallel -88.12. Preserve the native TIFF CRS.
        if (projection.get("proj") != "stere" or projection.get("lat_0") != -90
                or not np.isclose(projection.get("lat_ts", np.nan), float(local_value(root, "latitude_of_projection_origin")))
                or not np.isclose(projection.get("lon_0", np.nan), float(local_value(root, "longitude_of_central_meridian")))):
            raise ValueError("TIFF polar stereographic parameters disagree with the supplied map label")
        return {"shape": list(src.shape), "dtype": src.dtypes[0], "crs": src.crs.to_wkt(),
                "transform": list(src.transform)[:6], "resolution_m": list(src.res), "nodata": src.nodata,
                "unit": "W m^-2 sr^-1 um^-1", "unit_basis": "ShadowCam archive SIS calibrated map definition; TIFF band unit absent",
                "projection_note": "Native TIFF variant B used unchanged: XML origin-latitude value corresponds to its standard parallel, not its pole",
                "label_suffix": label.suffix, "special_pixel_policy": ISIS_SOURCE,
                "geometric_control": "Map projected, but no fine-tuned control network/physical co-registration established"}


def radar_definition(label, detached, image):
    root = ET.parse(label).getroot()
    if not local_value(root, "logical_identifier").endswith(":global_cpr_128ppd_simp_0c"):
        raise ValueError("Unexpected radar product identity")
    array = root.find("p:File_Area_Observational/p:Array_2D_Image", NS)
    if array is None or array.findtext("p:Element_Array/p:data_type", namespaces=NS) != "IEEE754LSBSingle":
        raise ValueError("Expected a little-endian float32 CPR array")
    names = root.findall("p:File_Area_Observational/p:File/p:file_name", NS)
    if len(names) != 1 or names[0].text.casefold() != image.name.casefold():
        raise ValueError("Radar label image identity mismatch")
    axes = {a.findtext("p:axis_name", namespaces=NS): int(a.findtext("p:elements", namespaces=NS))
            for a in array.findall("p:Axis_Array", NS)}
    rows, cols = axes["Line"], axes["Sample"]
    offset = int(array.findtext("p:offset", namespaces=NS))
    text = detached.read_text(encoding="ascii")
    if (pds3_number(text, "LINES"), pds3_number(text, "LINE_SAMPLES"), pds3_number(text, "SAMPLE_BITS")) != (rows, cols, 32):
        raise ValueError("PDS3 and PDS4 radar dimensions/types disagree")
    if pds3_number(text, "BANDS") != 1:
        raise ValueError("Expected a single CPR band")
    if not re.search(r'^\s*SAMPLE_TYPE\s*=\s*PC_REAL\s*$', text, re.M) or pds3_number(text, "SCALING_FACTOR") != 1 or pds3_number(text, "OFFSET") != 0:
        raise ValueError("Unexpected detached CPR type/scaling")
    if image.stat().st_size != offset + rows * cols * 4:
        raise ValueError("Radar binary size disagrees with declared dimensions")
    ppd = float(local_value(root, "pixel_scale_x"))
    if ppd != float(local_value(root, "pixel_scale_y")) or ppd != pds3_number(text, "MAP_RESOLUTION"):
        raise ValueError("Radar angular pixel scales disagree")
    if (rows, cols) != (int(180 * ppd), int(360 * ppd)):
        raise ValueError("Expected full simple-cylindrical angular grid")
    for field, expected in [("west_bounding_coordinate", -180), ("east_bounding_coordinate", 180),
                            ("north_bounding_coordinate", 90), ("south_bounding_coordinate", -90)]:
        if float(local_value(root, field)) != expected:
            raise ValueError("Unexpected radar bounds")
    radius = float(local_value(root, "a_axis_radius")) * 1000
    scale = float(local_value(root, "pixel_resolution_x"))
    if not np.isclose(scale, float(local_value(root, "pixel_resolution_y")), rtol=0, atol=1e-12):
        raise ValueError("Radar x/y map scales disagree")
    if not np.isclose(scale, radius * np.pi / 180 / ppd, rtol=1e-12):
        raise ValueError("Radar sphere/degree/metre scales disagree")
    if not np.allclose([float(local_value(root, "upperleft_corner_x")), float(local_value(root, "upperleft_corner_y"))],
                       [-radius * np.pi, radius * np.pi / 2], rtol=0, atol=1e-6):
        raise ValueError("Radar origin disagrees with angular bounds")
    missing = float(array.findtext("p:Special_Constants/p:missing_constant", namespaces=NS))
    return {"shape": [rows, cols], "offset": offset, "ppd": ppd, "radius_m": radius,
            "unit": "dimensionless CPR", "map_pixel_scale_m": scale, "label_missing_constant": missing,
            "label_missing_representable_float32": bool(abs(missing) <= float(np.finfo("float32").max)),
            "special_pixel_policy": ISIS_SOURCE,
            "geometry_hold": "Uncontrolled, unorthorectified multi-acquisition mosaic; viewing geometries are mixed"}


def manual_selection(data_root, inventory, key, run=None):
    root = Path(data_root).resolve()
    inventory = Path(inventory).resolve()
    if not inventory.is_relative_to(root):
        raise ValueError("Manual inventory must be local")
    record = json.loads(inventory.read_text(encoding="utf-8"))
    items = [item for item in record["files"] if item["dataset"] == key]
    if not items:
        raise FileNotFoundError(f"No manually registered {key} files")
    paths = {}
    for item in items:
        path = resolve_data_path(root, item["relative_path"])
        if not path.is_relative_to(root) or not path.is_file():
            raise FileNotFoundError(f"Missing/unsafe manual input: {path}")
        saved = json.loads(path.with_name(path.name + ".json").read_text(encoding="utf-8"))
        if saved["source"]["url"] != item["url"] or path.stat().st_size != item["size_bytes"]:
            raise ValueError("Manual receipt/inventory size or source differs")
        paths[item["role"]] = path
        if run is not None:
            pin_source(run, path)
    if run is not None:
        run.input(inventory)
        journal = root / "manifests/file_relocations.json"
        if journal.is_file():
            run.input(journal)
            run.input(Path(resolve_data_path.__code__.co_filename))
    return paths


@contextmanager
def radar_array(image, meta):
    data = np.memmap(image, mode="r", dtype="<f4", offset=meta["offset"], shape=tuple(meta["shape"]))
    try:
        yield data
    finally:
        data._mmap.close()


def radar_indices(longitude, latitude, ppd):
    lon, lat = np.broadcast_arrays(np.asarray(longitude, float), np.asarray(latitude, float))
    valid = np.isfinite(lon) & np.isfinite(lat) & (lat > -90) & (lat < 90)
    # Both seam longitudes address the same western edge; poles have no unique longitude.
    normalized = ((np.where(valid, lon, 0) + 180) % 360) - 180
    rows = np.floor((90 - np.where(valid, lat, 0)) * ppd).astype(int)
    cols = np.floor((normalized + 180) * ppd).astype(int)
    return rows, cols, valid


def sample_radar(image, meta, longitude, latitude):
    rows, cols, valid = radar_indices(longitude, latitude, meta["ppd"])
    values = np.full(rows.shape, np.nan, dtype="float32")
    with radar_array(image, meta) as data:
        values[valid] = data[rows[valid], cols[valid]]
    return values, rows, cols, valid


def sample_shadow(image, longitude, latitude):
    lon, lat = np.broadcast_arrays(np.asarray(longitude, float), np.asarray(latitude, float))
    values = np.full(lon.shape, np.nan, dtype="float32")
    with rasterio.Env(GDAL_CACHEMAX=16 * 1024**2), rasterio.open(image) as src:
        x, y = Transformer.from_crs(MOON_GEOGRAPHIC, src.crs, always_xy=True).transform(lon, lat)
        finite = np.isfinite(x) & np.isfinite(y)
        rows, cols = rasterio.transform.rowcol(src.transform, np.where(finite, x, 0), np.where(finite, y, 0))
        rows, cols = np.asarray(rows), np.asarray(cols)
        inside = finite & (rows >= 0) & (cols >= 0) & (rows < src.height) & (cols < src.width)
        bh, bw = src.block_shapes[0]
        groups = pd.DataFrame({"index": np.flatnonzero(inside), "br": rows[inside] // bh, "bc": cols[inside] // bw})
        for (br, bc), part in groups.groupby(["br", "bc"], sort=True):
            top, left = int(br * bh), int(bc * bw)
            block = src.read(1, window=Window(left, top, min(bw, src.width-left), min(bh, src.height-top)))
            indices = part["index"].to_numpy()
            values[indices] = block[rows[indices]-top, cols[indices]-left]
        nodata = src.nodata
    return values, rows, cols, inside, nodata


def attach_pixels(context, values, rows, cols, inside, *, nodata=None, nonnegative=False):
    frame = context.copy()
    frame["raw_value"] = values
    frame["source_row"], frame["source_col"] = rows, cols
    frame["inside_source_grid"] = inside
    status = classify_pixels(values, nodata)
    status[~inside] = "outside"
    frame["pixel_status"] = status
    frame["ordinary_pixel"] = inside & (status == "valid")
    frame["nonnegative_screen"] = frame.ordinary_pixel & (frame.raw_value >= 0)
    use = frame.nonnegative_screen if nonnegative else frame.ordinary_pixel
    frame["analysis_value"] = frame.raw_value.where(use)
    frame["analysis_cohort"] = "ordinary_nonnegative_CPR" if nonnegative else "ordinary_signed_radiance"
    return frame


def regional_summary(frame):
    rows = []
    for region, part in frame.groupby("region", sort=True):
        valid = part.analysis_value.notna()
        rows.append({"region": region, "context_centres": len(part), "inside_source_grid": int(part.inside_source_grid.sum()),
                     "ordinary_pixels": int(part.ordinary_pixel.sum()), "negative_ordinary_pixels": int((part.ordinary_pixel & part.raw_value.lt(0)).sum()),
                     "analysis_centres": int(valid.sum()), "distinct_analysis_source_pixels": len(part.loc[valid, ["source_row", "source_col"]].drop_duplicates()),
                     "support_fraction_of_context_centres": float(valid.mean()), **distribution(part.analysis_value)})
    return pd.DataFrame(rows)


def relationship_tables(frame, minimum=20):
    """Per-region native-source-pixel medians avoid repeated-source-pixel weighting."""
    eligible = frame.loc[frame.analysis_value.notna()]
    keys = ["region", "source_row", "source_col"]
    unique = eligible.groupby(keys, as_index=False)[["analysis_value", *CONTEXT_FIELDS]].median()
    masks = eligible.groupby(keys).permanent_shadow.agg(["min", "max", "count", "size"]).reset_index()
    masks["permanent_shadow"] = np.where((masks["min"] == masks["max"]) & (masks["count"] == masks["size"]),
                                         masks["min"], np.nan)
    unique = unique.merge(masks[keys + ["permanent_shadow"]], on=keys, validate="one_to_one")
    rows, contrasts = [], []
    for region in sorted(frame.region.unique()):
        part = unique.loc[unique.region.eq(region)]
        for field in CONTEXT_FIELDS:
            paired = part[["analysis_value", field]].dropna()
            status, rho = "descriptive", np.nan
            if len(paired) < minimum:
                status = "insufficient_rows"
            elif paired.nunique().min() < 2:
                status = "constant_variable"
            else:
                rho = paired.rank().corr(method="pearson").iloc[0, 1]
            rows.append({"region": region, "predictor": field, "distinct_source_pixels": len(paired),
                         "status": status, "spearman_rho": rho})
        # Mixed parent-mask assignments are kept separate, not majority-voted.
        for category, mask in [("no_shadow_at_sampled_centres", part.permanent_shadow.eq(0)),
                               ("shadow_at_sampled_centres", part.permanent_shadow.eq(1)),
                               ("mixed_or_unknown_parent_mask", ~part.permanent_shadow.isin([0, 1]))]:
            contrasts.append({"region": region, "parent_shadow_context": category, **distribution(part.loc[mask, "analysis_value"])})
    return unique, pd.DataFrame(rows), pd.DataFrame(contrasts)


def radar_preview(image, meta, stride=128):
    if stride < 1:
        raise ValueError("Stride must be positive")
    with radar_array(image, meta) as data:
        # Copy the small native sample; release the map before plotting.
        return np.array(data[::stride, ::stride], copy=True)


def shadow_patch_sample(image, grid=8, side=64):
    """Fixed patch grid; not a whole-scene histogram or a random sample."""
    values, records = [], []
    with rasterio.Env(GDAL_CACHEMAX=16 * 1024**2), rasterio.open(image) as src:
        for row in np.linspace(0, src.height-side, grid, dtype=int):
            for col in np.linspace(0, src.width-side, grid, dtype=int):
                a = src.read(1, window=Window(int(col), int(row), side, side))
                status = classify_pixels(a, src.nodata)
                values.append(a.ravel())
                records.append({"row": int(row), "col": int(col), "pixels": a.size,
                                **{name: int((status == name).sum()) for name in ["valid", *SPECIAL_BITS, "nonfinite", "declared_nd"]},
                                **{"ordinary_"+k: v for k, v in distribution(a[status == "valid"]).items()}})
    return np.concatenate(values), pd.DataFrame(records)
