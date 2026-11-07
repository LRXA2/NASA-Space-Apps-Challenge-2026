"""Small, explicit readers shared by Darrel's P1 Moon EDA notebooks.

Reuse the original PDS reader and lunar coordinate definitions. No downloads,
archive extraction, missing-value imputation or suitability scoring occurs here.
"""
from pathlib import Path
import re
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd
from pyproj import Transformer
import rasterio
from rasterio.crs import CRS
from rasterio.windows import Window, from_bounds

from notebooks.shared.processing import MOON_CRS, MOON_GEOGRAPHIC, diviner_chunks


REGIONS = (
    "A3CLR22_10_Leibnitz_Beta_Plateau", "A3CLR22_11_Malapert_Massif",
    "A3CLR22_12_deGerlache_Kocher_Massif", "A3CLR22_2_Haworth",
    "A3CLR22_3_Faustini_Rim_A", "A3CLR22_4_deGerlache_Rim_2",
    "A3CLR22_5_Connecting_Ridge_Extension",
)


def region_footprints(data_root):
    """Read only DEM headers from the original seven ZIPs; never extract them."""
    result = {}
    for name in REGIONS:
        archive = data_root / "moon/sdem/archives" / (name + ".zip")
        with zipfile.ZipFile(archive) as package:
            members = [n for n in package.namelist() if n.endswith("_GLDELEV_005.tif")]
            if len(members) != 1:
                raise ValueError(f"Missing/ambiguous region DEM in {archive}")
        uri = f"/vsizip/{archive.resolve().as_posix()}/{members[0]}"
        with rasterio.open(uri) as src:
            if src.crs != CRS.from_user_input(MOON_CRS):
                raise ValueError(f"Unexpected region coordinate system: {archive}")
            result[name] = {"archive": archive, "member": members[0], "bounds": tuple(src.bounds)}
    return result


def local_time_hours(values):
    """Normalize the exact 24-hour endpoint to midnight; reject other invalids."""
    array = np.asarray(values, dtype=float)
    valid = np.isfinite(array) & (array >= 0) & (array <= 24)
    return np.where(valid, np.where(array == 24, 0., array), np.nan)


def prepare_regional_diviner(labels, regions, run, chunk_rows=250_000):
    """Equivalent selection/validity rules to 06, without a terrain-run dependency."""
    project = Transformer.from_crs(MOON_GEOGRAPHIC, MOON_CRS, always_xy=True)
    collected = {name: [] for name in regions}
    coverage = []
    ns = {"p": "http://pds.nasa.gov/pds4/pds/v1"}
    for number, label in enumerate(labels, 1):
        root = ET.parse(label).getroot()
        units = {field.findtext("p:name", namespaces=ns): field.findtext("p:unit", namespaces=ns)
                 for field in root.findall(".//p:Field_Character", ns)}
        if units.get("ltim") != "hours" or units.get("tbol") != "K":
            raise ValueError(f"Unconfirmed local-time/temperature units in {label}")
        match = re.search(r"ls(\d+)_slon(\d+)", label.stem)
        if match is None:
            raise ValueError(f"Missing phase identity: {label}")
        run.input(label)
        run.input(label.with_suffix(".tab"))
        selected = {name: [] for name in regions}
        for chunk in diviner_chunks(label, chunk_rows):
            valid_coordinates = (np.isfinite(chunk.clon) & np.isfinite(chunk.clat)
                                 & chunk.clon.between(-180, 180) & chunk.clat.between(-90, -79))
            chunk = chunk.loc[valid_coordinates].copy()
            x, y = project.transform(chunk.clon.to_numpy(), chunk.clat.to_numpy())
            chunk["x_m"], chunk["y_m"] = x, y
            chunk["valid_temperature"] = np.isfinite(chunk.tbol) & (chunk.tbol > 0)
            chunk.loc[~chunk.valid_temperature, "tbol"] = np.nan
            chunk["local_time_h"] = local_time_hours(chunk.ltim)
            for name, info in regions.items():
                west, south, east, north = info["bounds"]
                inside = (x >= west) & (x < east) & (y >= south) & (y < north)
                if inside.any():
                    selected[name].append(chunk.loc[inside, ["clon", "clat", "x_m", "y_m", "ltim",
                        "local_time_h", "tbol", "valid_temperature"]].copy())
        for name, parts in selected.items():
            columns = ["clon", "clat", "x_m", "y_m", "ltim", "local_time_h", "tbol", "valid_temperature"]
            frame = pd.concat(parts, ignore_index=True) if parts else pd.DataFrame(columns=columns)
            if frame.duplicated(["clon", "clat"]).any():
                raise ValueError(f"Duplicate native cell in {name}, {label.stem}")
            frame["region"] = name
            frame["source_product"] = label.stem
            frame["seasonal_ls_bin"] = int(match[1])
            frame["subsolar_longitude_bin"] = int(match[2])
            coverage.append({"region": name, "source_product": label.stem,
                "selected_rows": len(frame), "valid_temperature_rows": int(frame.valid_temperature.sum()),
                "valid_local_time_rows": int(frame.local_time_h.notna().sum()),
                "usable_rows": int((frame.valid_temperature & frame.local_time_h.notna()).sum())})
            if len(frame):
                collected[name].append(frame)
        print(f"{number}/{len(labels)}: {label.stem}")
    combined = []
    for name, frames in collected.items():
        if not frames:
            raise ValueError(f"No observed source centers for required region {name}")
        combined.append(pd.concat(frames, ignore_index=True))
    return pd.concat(combined, ignore_index=True), pd.DataFrame(coverage)


def temperature_summary(frame, groups):
    """Descriptive observations, with native-center denominator; not independent trials."""
    valid = frame.loc[frame.valid_temperature & frame.local_time_h.notna()].copy()
    if valid.empty:
        return pd.DataFrame(columns=[*groups, "rows", "native_centers", "median_K", "q10_K", "q90_K"])
    valid["native_center"] = list(zip(valid.clon, valid.clat))
    return valid.groupby(groups, observed=True, dropna=False).agg(
        rows=("tbol", "size"), native_centers=("native_center", "nunique"),
        median_K=("tbol", "median"), q10_K=("tbol", lambda v: v.quantile(.1)),
        q90_K=("tbol", lambda v: v.quantile(.9))).reset_index()


def native_window(src, bounds):
    """Enclosing native window plus an exact inside-center mask (no resampling)."""
    window = from_bounds(*bounds, transform=src.transform)
    col, row = int(np.floor(window.col_off)), int(np.floor(window.row_off))
    right = int(np.ceil(window.col_off + window.width))
    bottom = int(np.ceil(window.row_off + window.height))
    window = Window(col, row, right - col, bottom - row).intersection(Window(0, 0, src.width, src.height))
    raw = src.read(1, window=window, masked=True).astype(float).filled(np.nan)
    values = raw * src.scales[0] + src.offsets[0]
    rows, cols = np.indices(values.shape)
    x, y = rasterio.transform.xy(src.window_transform(window), rows, cols, offset="center")
    x, y = np.asarray(x), np.asarray(y)
    inside = (x >= bounds[0]) & (x < bounds[2]) & (y >= bounds[1]) & (y < bounds[3])
    return window, values, inside.reshape(values.shape)


def documented_illumination(data_root):
    base = data_root / "moon/illumination_2016"
    definitions = {
        "solar_visibility": ("solar_illumination/AVGVISIB_85S_060M_201608.TIF", "fraction"),
        "earth_visibility": ("earth_visibility/AVGVISIB_85S_060M_201608_EARTH.TIF", "fraction"),
        "permanent_shadow": ("permanent_shadow/LPSR_85S_060M_201608.TIF", "binary"),
        "sky_view_sr": ("sky_visibility/SKYV_65S_240M.TIF", "steradian"),
    }
    result = {}
    for key, (relative, unit) in definitions.items():
        path = base / "geotiff/south" / relative
        label = base / "documentation/labels" / (path.stem.lower() + ".lbl")
        text = label.read_text(encoding="ascii")
        def numeric(field):
            found = re.findall(r"^\s*" + field + r"\s*=\s*([-+\d.eE]+)\s*$", text, re.M)
            if len(found) != 1:
                raise ValueError(f"Missing/ambiguous {field} in {label}")
            return float(found[0])
        with rasterio.open(path) as src:
            if src.crs != CRS.from_user_input(MOON_CRS):
                raise ValueError(f"Unexpected illumination CRS in {path}")
            if not np.allclose([src.scales[0], src.offsets[0]], [numeric("SCALING_FACTOR"), numeric("OFFSET")], rtol=0, atol=1e-12):
                raise ValueError(f"GeoTIFF/label scale disagreement in {path}")
        if unit == "steradian" and not re.search(r"^\s*UNIT\s*=\s*STERADIAN\s*$", text, re.M):
            raise ValueError(f"Unconfirmed solid-angle unit in {label}")
        if unit == "binary" and "permanent shadow" not in text.lower():
            raise ValueError(f"Unconfirmed shadow class in {label}")
        if unit == "fraction" and not re.search(r"between 0.*?and 1", text, re.S):
            raise ValueError(f"Unconfirmed visibility fraction in {label}")
        result[key] = {"path": path, "label": label, "unit": unit}
    return result


def sample_containing_pixels(path, centers, bounds):
    """Native containing pixel, decoded once; also expose source row/column IDs."""
    with rasterio.open(path) as src:
        if src.crs != CRS.from_user_input(MOON_CRS):
            raise ValueError(f"Unconfirmed grid/CRS: {path}")
        window, values, _ = native_window(src, bounds)
        row, col = rasterio.transform.rowcol(src.transform, centers.x_m.to_numpy(), centers.y_m.to_numpy())
        row, col = np.asarray(row), np.asarray(col)
        r, c = row - int(window.row_off), col - int(window.col_off)
        valid = (r >= 0) & (c >= 0) & (r < values.shape[0]) & (c < values.shape[1])
        samples = np.full(len(centers), np.nan)
        samples[valid] = values[r[valid], c[valid]]
        return samples, [f"{rr}:{cc}" if keep else None for rr, cc, keep in zip(row, col, valid)], src.res
