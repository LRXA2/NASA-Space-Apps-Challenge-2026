"""Label-driven readers for the bounded P1 research notebooks (no downloads)."""
from pathlib import Path
from contextlib import contextmanager
import io
import json
import re
import zipfile
import xml.etree.ElementTree as ET

import numpy as np
import pandas as pd

NS = {"p": "http://pds.nasa.gov/pds4/pds/v1"}
INVENTORY = "manifests/eda_datasets/20261106T053410890901Z/inventory.json"


def pilot_files(data_root, dataset, suffix):
    record = json.loads((data_root / INVENTORY).read_text(encoding="utf-8"))
    items = [item for item in record["files"]
             if item["dataset"] == dataset and Path(item["relative_path"]).suffix.lower() == suffix.lower()]
    if not items:
        raise FileNotFoundError(f"No selected {dataset} {suffix} products in pinned inventory")
    paths = []
    for item in items:
        path = (data_root / item["relative_path"]).resolve()
        if not path.is_relative_to(data_root.resolve()):
            raise ValueError("Pilot inventory path escapes the local data root")
        if not path.is_file():
            raise FileNotFoundError(f"Missing selected {dataset} input: {path}")
        receipt = json.loads(path.with_name(path.name + ".json").read_text(encoding="utf-8"))
        if (path.stat().st_size != item["size_bytes"]
                or receipt.get("source", {}).get("url") != item["url"]):
            raise ValueError(f"Pinned size/source differs from the local pilot: {path}")
        paths.append(path)
    return paths


def pin_source(run, path):
    """Reuse Run's hash, verifying the existing download receipt without rehashing."""
    path = path.resolve()
    receipt = path.with_name(path.name + ".json")
    saved = json.loads(receipt.read_text(encoding="utf-8"))
    if saved.get("source", {}).get("size_bytes") != path.stat().st_size:
        raise ValueError(f"Source size/receipt mismatch: {path}")
    run.input(path)
    key = str(path.relative_to(run.project_root))
    if run.record["inputs"][key]["sha256"] != saved.get("sha256"):
        raise ValueError(f"Source SHA256/receipt mismatch: {path}")
    run.input(receipt)
    return path


def pds4_definition(label):
    root = ET.parse(label).getroot()
    tables = [t for t in root.findall(".//p:Table_Character", NS) + root.findall(".//p:Table_Delimited", NS)
              if int(t.findtext("p:records", namespaces=NS) or 0) > 1]
    if len(tables) != 1:
        raise ValueError(f"Expected one data table, found {len(tables)} in {label}")
    table = tables[0]
    fields = table.findall(".//p:Field_Character", NS) + table.findall(".//p:Field_Delimited", NS)
    names = [f.findtext("p:name", namespaces=NS) for f in fields]
    if not fields or None in names or len(names) != len(set(names)):
        raise ValueError(f"Missing/duplicate fields in {label}")
    return root, table, fields


@contextmanager
def table_stream(label, archive=None):
    root, selected_table, _ = pds4_definition(label)
    areas = [area for area in root if selected_table in list(area)]
    if len(areas) != 1:
        raise ValueError(f"Ambiguous file area for selected table: {label}")
    # A product can also declare a supplemental .txt header. Only the file area
    # containing this data table defines the byte stream we must decode.
    names = [n.text for n in areas[0].findall("p:File/p:file_name", NS)]
    if archive is not None:
        with zipfile.ZipFile(archive) as package:
            matches = [i for i in package.infolist() if i.filename.lower() in {n.lower() for n in names}]
            if len(matches) != 1:
                raise ValueError(f"Missing/ambiguous declared table in {archive}")
            with package.open(matches[0]) as stream:
                yield stream, matches[0].file_size
    else:
        paths = [label.parent / n for n in names if Path(n).name == n and (label.parent / n).is_file()
                 and Path(n).suffix.lower() in {".csv", ".tab", ".txt"}]
        if len(paths) != 1:
            raise ValueError(f"Missing/ambiguous declared table beside {label}")
        with paths[0].open("rb") as stream:
            yield stream, paths[0].stat().st_size


def pds4_chunks(label, archive=None, columns=None, chunk_rows=100_000):
    """Fixed-width or delimited PDS4 tables; offsets, types and constants from XML."""
    _, table, fields = pds4_definition(label)
    names = [f.findtext("p:name", namespaces=NS) for f in fields]
    chosen = set(names if columns is None else columns)
    if chosen - set(names):
        raise ValueError(f"Unknown requested columns: {chosen - set(names)}")
    records = int(table.findtext("p:records", namespaces=NS))
    offset = int(table.findtext("p:offset", namespaces=NS))
    length = table.findtext(".//p:record_length", namespaces=NS)
    with table_stream(label, archive) as (stream, size):
        stream.seek(offset)
        if table.tag.endswith("Table_Character"):
            length = int(length)
            if size != offset + records * length:
                raise ValueError(f"Table byte count disagrees with label: {label}")
            iterator = range(0, records, chunk_rows)
        else:
            delimiter = table.findtext("p:field_delimiter", namespaces=NS)
            if delimiter != "Comma":
                raise ValueError(f"Unsupported delimiter {delimiter}")
            iterator = pd.read_csv(stream, names=names, header=None, sep=",", skipinitialspace=True,
                                   dtype=str, keep_default_na=False, chunksize=chunk_rows)
        read = 0
        for part in iterator:
            if length is not None:
                count = min(chunk_rows, records - part)
                block = stream.read(count * length)
                if len(block) != count * length:
                    raise ValueError("Truncated fixed-width table")
                frame = {}
                for field, name in zip(fields, names):
                    if name not in chosen:
                        continue
                    start = int(field.findtext("p:field_location", namespaces=NS)) - 1
                    width = int(field.findtext("p:field_length", namespaces=NS))
                    frame[name] = np.ndarray((count,), dtype=f"S{width}", buffer=block,
                                             offset=start, strides=(length,)).astype(str)
                frame = pd.DataFrame(frame)
            else:
                frame = part.loc[:, [name for name in names if name in chosen]].copy()
                count = len(frame)
            for field, name in zip(fields, names):
                if name not in chosen:
                    continue
                dtype = field.findtext("p:data_type", namespaces=NS)
                text = frame[name].str.strip().str.strip('"')
                if dtype in {"ASCII_Real", "ASCII_Integer", "ASCII_NonNegative_Integer"}:
                    numeric = pd.to_numeric(text.replace("", np.nan), errors="raise")
                    for constant in field.findall("p:Special_Constants/*", NS):
                        if constant.tag.split("}")[-1].endswith("constant"):
                            numeric = numeric.mask(numeric == float(constant.text))
                    frame[name] = numeric
                else:
                    frame[name] = text
            read += count
            yield frame
        if read != records:
            raise ValueError(f"Record count mismatch: {read} != {records} in {label}")


def read_pds4(label, **kwargs):
    return pd.concat(pds4_chunks(label, **kwargs), ignore_index=True)


def pds3_number(text, field):
    values = re.findall(r"^\s*" + re.escape(field) + r"\s*=\s*([-+\d.eE]+)(?:\s|$)", text, re.M)
    if len(values) != 1:
        raise ValueError(f"Missing/ambiguous PDS3 field: {field}")
    return float(values[0])


def pds4_image(label, path, stride=8):
    """Systematic native-pixel sample of a labeled signed 16-bit NAC CDR."""
    root = ET.parse(label).getroot()
    array = root.find(".//p:Array_2D_Image", NS)
    if array is None or array.findtext("p:Element_Array/p:data_type", namespaces=NS) != "SignedLSB2":
        raise ValueError("Expected signed LSB 16-bit CDR array")
    axes = {a.findtext("p:axis_name", namespaces=NS): int(a.findtext("p:elements", namespaces=NS))
            for a in array.findall("p:Axis_Array", NS)}
    offset = int(array.findtext("p:offset", namespaces=NS))
    shape = (axes["Line"], axes["Sample"])
    if path.stat().st_size != offset + np.prod(shape) * 2:
        raise ValueError("NAC image bytes disagree with label")
    raw = np.memmap(path, mode="r", dtype="<i2", offset=offset, shape=shape)[::stride, ::stride].astype(float)
    valid = np.isfinite(raw)
    for constant in array.findall("p:Special_Constants/*", NS):
        name = constant.tag.split("}")[-1]
        value = float(constant.text)
        valid &= raw >= value if name == "valid_minimum" else raw <= value if name == "valid_maximum" else raw != value
    scale = float(array.findtext("p:Element_Array/p:scaling_factor", namespaces=NS) or 1)
    offset = float(array.findtext("p:Element_Array/p:value_offset", namespaces=NS) or 0)
    values = np.where(valid, raw * scale + offset, np.nan)
    return values, {"native_shape": shape, "stride": stride, "scale": scale, "offset": offset,
                    "unit": array.findtext("p:Element_Array/p:unit", namespaces=NS),
                    "sampled_pixels": raw.size, "valid_sampled_pixels": int(valid.sum())}


def dose_profiles(path):
    rows, scenario = [], None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("Al thickness"):
            match = re.fullmatch(r"Al thickness (\d+) g/cm2, (S\w+), particles (.+)", line)
            if not match:
                raise ValueError(f"Unknown dose scenario header: {line}")
            scenario = (int(match[1]), match[2], match[3])
        elif line.strip() and not line.lstrip().startswith("detpth"):
            if scenario is None:
                raise ValueError("Dose row before scenario header")
            depth, dose = map(float, line.split())
            rows.append({"al_g_cm2": scenario[0], "solar_scenario": scenario[1], "particles": scenario[2],
                         "depth_cm": depth, "effective_dose_cSv_year": dose})
    return pd.DataFrame(rows)


def nsp1_wavelengths(path):
    """Read only the two wavelength-mapping columns, not unused DN coefficients.

    The publisher's row 71 contains padding in a later coefficient column.
    Preserve the source unchanged and do not drop that pixel or invent a wavelength.
    """
    lines = path.read_text(encoding="ascii").splitlines()
    start = next((i for i, line in enumerate(lines) if line.startswith("Pixel\tWavelength(um)")), None)
    if start is None:
        raise ValueError("Missing NSP1 wavelength header")
    rows = []
    for line in lines[start + 1:]:
        if line.strip():
            parts = line.split("\t", 2)
            rows.append((int(parts[0]), float(parts[1])))
    frame = pd.DataFrame(rows, columns=["Pixel", "Wavelength(um)"])
    if (not np.array_equal(frame.Pixel, np.arange(len(frame)))
            or not np.isfinite(frame["Wavelength(um)"]).all()
            or not frame["Wavelength(um)"].gt(0).all()
            or not frame["Wavelength(um)"].diff().iloc[1:].gt(0).all()):
        raise ValueError("Invalid NSP1 pixel/wavelength mapping")
    return frame


def published_crater_tables(path):
    """Keep observed and modeled blocks separate; never skip a changed-width row."""
    lines = path.read_text(encoding="utf-8").splitlines()
    headers = [i for i, line in enumerate(lines) if line.startswith("Time, year\t")]
    if len(headers) != 2 or headers[0] != 0:
        raise ValueError("Expected two explicitly headed CRaTER study tables")
    observed = pd.read_csv(io.StringIO("\n".join(lines[:headers[1]])), sep="\t")
    modeled = pd.read_csv(io.StringIO("\n".join(lines[headers[1]:])), sep="\t")
    if (observed.shape[1] != 3 or modeled.shape[1] != 6
            or "CRaTER monthly averaged" not in observed.columns[1]
            or "GCR in Si detector" not in modeled.columns[1]):
        raise ValueError("Unrecognized observed/model CRaTER headers")
    observed.columns = ["decimal_year", "absorbed_rate_cGy_year", "std_cGy_year"]
    modeled.columns = ["decimal_year", "GCR_in_Si_cGy_year", "albedo_p_cGy_year", "albedo_n_cGy_year",
                       "albedo_gamma_cGy_year", "albedo_e_cGy_year"]
    for frame in (observed, modeled):
        if not np.isfinite(frame.to_numpy(dtype=float)).all() or frame.decimal_year.duplicated().any():
            raise ValueError("Invalid or duplicate study-month values")
    return observed, modeled
