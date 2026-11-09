"""Additive Stage 3/P1 acquisitions; the original downloader is imported read-only.

No arguments: live inventory (metadata only). --dry-run: offline, writes nothing.
--download: transfer the pinned selection. --sample: deliberately incomplete test.
All new payloads, evidence, partials and logs default to D:\\projects\\NASA Dataset.
"""
from __future__ import annotations

import argparse
import calendar
from collections import deque
from concurrent.futures import ThreadPoolExecutor, as_completed
import csv
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import sys
import threading
from urllib.parse import unquote, urlencode, urljoin, urlsplit
import xml.etree.ElementTree as ET

HERE = Path(__file__).resolve().parent
LOCAL = HERE.parent
sys.dont_write_bytecode = True  # Reused helpers stay read-only, including caches.
sys.path.insert(0, str(LOCAL / "download_script"))
import download_environmental as base

DEFAULT_OUTPUT = Path(r"D:\projects\NASA Dataset")
ORIGINAL_SHA256 = "89597c766babd4ccecd7914a5800282c91f6981abcbcde14277f7443df17fb5a"
REQUESTED_STOP = "2026-11-01T00:00:00.000"  # Exclusive; through October 2026.
MILLISECOND = timedelta(milliseconds=1)
RADIUS_M = 1737400.0
DIVINER_SAMPLE = {"bbox": [29.0, -85.6, 29.2, -85.4], "start": "2023-11-01", "stop_exclusive": "2023-11-08"}
REGIONS = {
    "A3CLR22_10_Leibnitz_Beta_Plateau": [65000, 110000, 81000, 126000],
    "A3CLR22_11_Malapert_Massif": [-11000, 111000, 10000, 132000],
    "A3CLR22_12_deGerlache_Kocher_Massif": [-123400, -66100, -103400, -46100],
    "A3CLR22_2_Haworth": [-52900, 75600, -23100, 105400],
    "A3CLR22_3_Faustini_Rim_A": [54000, -10000, 74000, 10000],
    "A3CLR22_4_deGerlache_Rim_2": [-58500, 13000, -38500, 33000],
    "A3CLR22_5_Connecting_Ridge_Extension": [-38700, -16100, -18700, 3900],
}
SOURCES = {
    "D20": "https://oderest.rsl.wustl.edu/livegds/",
    "D07": "https://pds-ppi.igpp.ucla.edu/data/lro-crater/",
    "D08": "https://data.ngdc.noaa.gov/platforms/solar-space-observing-satellites/goes/",
    "D11": "https://spdf.gsfc.nasa.gov/pub/data/themis/thb/l2/merged/cdf/",
    "D14": "https://pds-geosciences.wustl.edu/lunar/urn-nasa-pds-apollo_pse/data/xa/metadata/",
    "D15": "https://oderest.rsl.wustl.edu/live2/",
    "D26": "https://oderest.rsl.wustl.edu/live2/",
    "D27": "https://oderest.rsl.wustl.edu/live2/",
}
NOTES = {
    "D20": "Regional channel 3-9 brightness temperature/radiance, UTC/local time and flags; not component temperature, dose or plasma.",
    "D07": "CRaTER daily derived secondary and sparse monthly primary-detector days; not crew surface dose or shielding adequacy.",
    "D08": "GOES-16 and GOES-19 SGPS proton context, separate platforms and calibration; not local lunar flux/dose.",
    "D11": "ARTEMIS THB/P1 merged ion density, thermal speed/flow, field and spacecraft position; plasma context, not a local ionisation rate, regolith charging or dose.",
    "D14": "Historical Apollo StationXML response/epoch metadata for waveform interpretation; not recent polar seismic measurements.",
    "D15": "Bounded dated NAC calibrated science imagery and labels intersecting study geographic bounding boxes; exact terrain-footprint validation remains EDA work.",
    "D26": "Bounded study-overlapping Kaguya v2 DTM tiles and detached labels; historical/static, no invented recent acquisition dates.",
    "D27": "Bounded dated ShadowCam unstretched 32-bit calibrated radiance map COGs and labels; not an illumination continuity history.",
}
TERMINAL = {"downloaded", "verified_existing", "referenced_existing", "no_observations"}
FAILURES = (base.requests.RequestException, OSError, ValueError, RuntimeError, ET.ParseError)


def digest(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(",", ":")).encode()).hexdigest()[:24]


def parse_time(value):
    result = datetime.fromisoformat(value.replace("Z", "+00:00"))
    return result.replace(tzinfo=timezone.utc) if result.tzinfo is None else result.astimezone(timezone.utc)


def wire(value):
    """GDS requires UTC milliseconds without a trailing Z."""
    return value.astimezone(timezone.utc).replace(tzinfo=None).isoformat(timespec="milliseconds")


def years_before(value, years):
    return value.replace(year=value.year-years,
                         day=min(value.day, calendar.monthrange(value.year-years, value.month)[1]))


def resolve_window(latest_exclusive, requested_stop=REQUESTED_STOP, years=3):
    stop = min(parse_time(requested_stop), latest_exclusive)
    return {"start": wire(years_before(stop, years)), "stop_exclusive": wire(stop),
            "requested_stop_exclusive": requested_stop, "years": years}


def months(start, stop):
    while start < stop:
        end = (start.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
               + timedelta(days=32)).replace(day=1)
        end = min(end, stop)
        yield start, end
        start = end


def xy_to_geo(x, y):
    return math.degrees(math.atan2(x, y)) % 360, math.degrees(2*math.atan(math.hypot(x, y)/(2*RADIUS_M))-math.pi/2)


def in_region(lon, lat, bounds):
    rho = 2*RADIUS_M*math.tan((math.pi/2+math.radians(lat))/2)
    x, y = rho*math.sin(math.radians(lon)), rho*math.cos(math.radians(lon))
    return bounds[0] <= x <= bounds[2] and bounds[1] <= y <= bounds[3]


def region_boxes(bounds):
    """Conservative sphere south-polar stereographic envelope; split at 0 E."""
    x0, y0, x1, y1 = bounds
    corners = [xy_to_geo(x, y) for x in (x0, x1) for y in (y0, y1)]
    lons = sorted(c[0] for c in corners)
    gaps = [(lons[(i+1) % 4] + (360 if i == 3 else 0)-lons[i], i) for i in range(4)]
    _, i = max(gaps)
    west, east = lons[(i+1) % 4], lons[i]
    near_x = 0 if x0 <= 0 <= x1 else min(abs(x0), abs(x1))
    near_y = 0 if y0 <= 0 <= y1 else min(abs(y0), abs(y1))
    south = xy_to_geo(near_x, near_y)[1]
    north = max(c[1] for c in corners)
    intervals = [(west, east)] if west <= east else [(west, 360.0), (0.0, east)]
    return [[w, south, e, north] for w, e in intervals if e > w]


def tiles(box, channels):
    # GDS synchronous estimate is area x channels x ~1 million; stay below 7M.
    west, south, east, north = box
    max_area = 5.0 / len(channels)
    ny = max(1, math.ceil((north-south)/0.5))
    dy = (north-south)/ny
    nx = max(1, math.ceil((east-west)*dy/max_area))
    for iy in range(ny):
        for ix in range(nx):
            yield [west+(east-west)*ix/nx, south+dy*iy,
                   west+(east-west)*(ix+1)/nx, south+dy*(iy+1)]


def make_session(args):
    client = base.session(args.cookies)
    if args.ca_bundle:
        client.verify = str(args.ca_bundle)
    return client


def retry(args, label, operation):
    return base.retry_connections(operation, label, base.LOG, args.connection_retries, base.STOP)


def fetch(args, url, evidence=None):
    def once():
        base.LOG.info('Metadata request %s', url)
        with make_session(args) as client:
            raw, final = base.metadata(client, url, args.timeout)
        if evidence:
            evidence.parent.mkdir(parents=True, exist_ok=True)
            evidence.write_bytes(raw)
        base.LOG.info('Metadata received %s bytes=%s', final, len(raw))
        return raw, final
    return retry(args, url, once)


def links(args, url, evidence_dir):
    raw, final = fetch(args, url, evidence_dir / (digest(url)+".html"))
    from bs4 import BeautifulSoup
    result = set()
    for node in BeautifulSoup(raw, "html.parser").find_all("a", href=True):
        target = urljoin(final, node["href"])
        if target.startswith(url) and not urlsplit(target).query and target != url:
            result.add(base.safe_url(target))
    return sorted(result)


def newest_versions(urls, pattern):
    """Select one publisher version per dated science product, never labels alone."""
    result = {}
    for url in urls:
        match = re.fullmatch(pattern, unquote(urlsplit(url).path.rsplit("/", 1)[-1]), re.I)
        if match:
            key, version = match.group("date"), tuple(int(v) for v in re.findall(r"\d+", match.group("version")))
            if key not in result or version > result[key][0]:
                result[key] = version, url
    return [result[key][1] for key in sorted(result)]


def date_of(url):
    name = urlsplit(url).path.rsplit("/", 1)[-1]
    if name.upper().startswith("CRAT_"):
        return datetime.strptime(re.search(r"_(\d{7})_", name)[1], "%Y%j").replace(tzinfo=timezone.utc)
    return parse_time(re.search(r"(?:_d|merged_)(\d{8})_", name)[1][:4]+"-"+
                      re.search(r"(?:_d|merged_)(\d{8})_", name)[1][4:6]+"-"+
                      re.search(r"(?:_d|merged_)(\d{8})_", name)[1][6:8])


def dated_listing(args, key, evidence):
    """Inspect four requested years, resolve true latest file date, then three years."""
    stop = parse_time(args.stop)
    years = range(stop.year-args.years-1, stop.year+1)
    streams = ([('secondary', SOURCES[key]+"data-der-sec/", r"CRAT_L2_SEC_(?P<date>\d{7})_V(?P<version>\d+)\.TAB"),
                ('primary', SOURCES[key]+"data-der-pri/", r"CRAT_L2_PRI_(?P<date>\d{7})_V(?P<version>\d+)\.TAB")]
               if key == "D07" else
               [("thb", SOURCES[key], r"thb_l2_merged_(?P<date>\d{8})_v(?P<version>\d+)\.cdf")]
               if key == "D11" else
               [(sat, SOURCES[key]+f"goes{sat}/l2/data/sgps-l2-avg5m/",
                 rf"sci_sgps-l2-avg5m_g{sat}_d(?P<date>\d{{8}})_v(?P<version>[\d-]+)\.nc") for sat in ("16", "19")])
    selected, windows, gaps, stream_files = [], {}, [], []
    for stream, root, pattern in streams:
        files = []
        available = set(links(args, root, evidence))
        for year in years:
            year_url = root+str(year)+"/"
            if year_url not in available:
                continue
            children = links(args, year_url, evidence)
            if key == "D08":
                for month in children:
                    if re.fullmatch(r"\d{2}/", month[len(year_url):]):
                        if parse_time(f"{year}-{month[-3:-1]}-01") < stop:
                            files.extend(links(args, month, evidence))
            else:
                files.extend(children)
        files = newest_versions(files, pattern)
        files = [u for u in files if date_of(u) < stop]
        stream_files.append((stream, root, files))
    # One family window: GOES-16 bridges earlier dates, not an extra rolling
    # three years before its retirement on top of the GOES-19 window.
    latest_dates = [date_of(files[-1]) for _, _, files in stream_files if files]
    if not latest_dates:
        return [], {"windows": {}, "coverage": [{"status": "no_observations", "url": SOURCES[key]}]}
    latest = max(latest_dates)
    latest_stop = next(months(latest, latest+timedelta(days=32)))[1] if key == "D11" else latest+timedelta(days=1)
    window = resolve_window(latest_stop, args.stop, args.years)
    for stream, root, files in stream_files:
        if not files:
            gaps.append({"stream": stream, "status": "no_observations", "url": root})
            continue
        windows[stream] = window
        start, end = parse_time(window["start"]), parse_time(window["stop_exclusive"])
        selected_stream = []
        for url in files:
            day = date_of(url)
            file_stop = next(months(day, day+timedelta(days=32)))[1] if key == "D11" else day+timedelta(days=1)
            if day < end and file_stop > start:
                selected_stream.append(url)
        available_dates = [wire(date_of(u)) for u in selected_stream]
        if key == 'D07' and stream == 'primary':
            by_month = {}
            for url in selected_stream:
                by_month.setdefault(date_of(url).strftime('%Y-%m'), []).append(url)
            selected_stream = [url for urls in by_month.values() for url in urls[-args.primary_days_per_month:]]
        if args.sample:
            selected_stream = selected_stream[-1:]
        for url in selected_stream:
            name = urlsplit(url).path.rsplit("/", 1)[-1]
            prefix = f"datasets/{key}/{stream}/{date_of(url).year}/"
            selected.append({"url": url, "relative_path": prefix+name})
            if key == "D07":
                label = url.rsplit(".", 1)[0]+".xml"
                selected.append({"url": label, "relative_path": prefix+label.rsplit("/", 1)[-1], "metadata": True})
        dates = sorted({wire(date_of(u)) for u in selected_stream})
        gaps.append({"stream": stream, "status": "file_date_inventory", "selected_file_dates": dates,
                     "available_file_dates_in_window": available_dates,
                     "selection": f"Last {args.primary_days_per_month} available day(s) per month; sparse primary pilot, NOT event-complete" if key == 'D07' and stream == 'primary' else "All available file dates in window, unless sample active",
                     "warning": "File dates do not prove within-file sampling, quality or uninterrupted coverage."})
    return selected, {"windows": windows, "coverage": gaps}


def diviner_params(box, start, stop, args):
    west, south, east, north = box
    cal, geom, misc = args.quality_max
    return {"query": "divinerrdr", "output": "XML", "results": "v",
            "westernlon": west, "easternlon": east, "minlat": south, "maxlat": north,
            "minobtime": wire(start), "maxobtime": wire(stop-MILLISECOND),
            "channel": "".join("t" if i in args.channels else "f" for i in range(1, 10)),
            "mincalibration": 0, "maxcalibration": cal, "mingeometry": 0, "maxgeometry": geom,
            "minmisc": 0, "maxmisc": misc}


def diviner_jobs(args, evidence):
    raw, _ = fetch(args, SOURCES['D20']+"?query=gdivinerrdr&output=XML", evidence/"coverage.xml")
    root = ET.fromstring(raw)
    latest = root.findtext(".//GlobalMaxUTC")
    if root.findtext("Status", "").upper() != "SUCCESS" or not latest:
        raise ValueError("Diviner global coverage response lacks a successful dated maximum")
    window = resolve_window(parse_time(latest)+MILLISECOND, args.stop, args.years)
    jobs = []
    for name, bounds in REGIONS.items():
        for channel in args.channels:
            channel_args = argparse.Namespace(**{**vars(args), 'channels': [channel]})
            for box in region_boxes(bounds):
                for tile in tiles(box, [channel]):
                    for start, stop in months(parse_time(window["start"]), parse_time(window["stop_exclusive"])):
                        params = diviner_params(tile, start, stop, channel_args)
                        jobs.append({"key": "D20", "region": name, "params": params, "id": digest(params)})
    if args.sample:
        # Explicit one-week test inside the study envelope; never a full-scope fallback.
        start, stop = parse_time(DIVINER_SAMPLE['start']), parse_time(DIVINER_SAMPLE['stop_exclusive'])
        if not (parse_time(window['start']) <= start < stop <= parse_time(window['stop_exclusive'])):
            raise ValueError("Fixed small sample lies outside resolved archive window")
        jobs = []
        for channel in args.channels:
            channel_args = argparse.Namespace(**{**vars(args), 'channels': [channel]})
            params = diviner_params(DIVINER_SAMPLE['bbox'], start, stop, channel_args)
            jobs.append({"key": "D20", "region": next(iter(REGIONS)), "params": params, "id": digest(params)})
    return jobs, {"window": window, "roi_bounds_m": REGIONS,
                  "projection": "Sphere R=1737400m; polar stereographic lat_0=-90, lat_ts=-90, lon_0=0",
                  "selection": "Conservative geographic envelopes; retain flags and clip observation centres with in_region before site EDA. Shared tile boundaries can repeat observations: deduplicate native records during EDA, not by temperature."}


def listify(value):
    return [] if value is None else value if isinstance(value, list) else [value]


def ode_product_entries(key, product):
    files = listify(product.get("Product_files", {}).get("Product_file"))
    chosen = []
    for entry in files:
        url = entry.get("URL", "")
        ext = Path(urlsplit(url).path).suffix.lower()
        if key == "D27":
            accept = bool(re.search(r"_map_raw\.(tif|xml)$", url, re.I))
        else:
            accept = entry.get("Type") == "Product" and ext in {".img", ".lbl", ".xml"}
        if accept:
            base.safe_url(url)
            chosen.append({"url": url, "metadata": ext in {".lbl", ".xml"}})
    if not any(not e["metadata"] for e in chosen) or not any(e["metadata"] for e in chosen):
        raise ValueError(f"{key} product lacks a science payload and companion label")
    prefix = f"datasets/{key}/{digest(product.get('pdsid', chosen))}/"
    return [{**e, "relative_path": prefix+unquote(urlsplit(e["url"]).path.rsplit("/", 1)[-1])} for e in chosen]


def imagery_listing(args, key, evidence):
    ih, instrument, pt = {"D15": ("LRO", "LROC", "CDRNAC4"),
                           "D26": ("SLN", "TC", "TCDTMM"), "D27": ("KPLO", "ShadowCam", "CAL")}[key]
    entries, selections = {}, []
    period = None
    coverage_notes, indexed_stop = [], None
    if key != 'D26':
        raw, _ = fetch(args, SOURCES[key]+"?query=iipt&output=JSON", evidence/'iipt.json')
        records = listify(json.loads(raw)['ODEResults']['IIPTSets']['IIPTSet'])
        matched = [r for r in records if r.get('ODEMetaDB', '').lower() == 'moon'
                   and r.get('IHID') == ih and r.get('IID') == instrument and r.get('PT') == pt]
        if len(matched) != 1 or not matched[0].get('MaxObservationTime'):
            raise ValueError(f"{key}: unique dated official archive coverage unavailable")
        indexed_stop = parse_time(matched[0]['MaxObservationTime'])+MILLISECOND
        archive_stop = indexed_stop
        if key == 'D27':
            # ODE can lag the publisher. Never label index age as archive age.
            collection_url = 'https://pds.shadowcam.im-ldi.com/observation/collection_kplo-shadowcam_data-calibrated.xml'
            raw, _ = fetch(args, collection_url, evidence/'publisher_collection.xml')
            label = ET.fromstring(raw)
            stops = [n.text for n in label.iter() if n.tag.rsplit('}', 1)[-1] == 'stop_date_time' and n.text]
            if len(stops) != 1:
                raise ValueError('ShadowCam publisher temporal coverage is ambiguous/missing')
            archive_stop = parse_time(stops[0])+MILLISECOND
            if indexed_stop < min(archive_stop, parse_time(args.stop)):
                coverage_notes.append({'status': 'provider_index_lag', 'indexed_stop_exclusive': wire(indexed_stop),
                                       'publisher_stop_exclusive': wire(archive_stop), 'url': collection_url,
                                       'reason': 'Newer publisher products lack verified spatial-query selections here; ODE pilots are partial, not full recent coverage. Do not infer no observations from an unindexed year.'})
        period = resolve_window(archive_stop, args.stop, args.years)
    regions = list(REGIONS.items())[:1] if args.sample else REGIONS.items()
    # Small per-year pilots, not an attempt to download entire image archives.
    years = [None] if key == "D26" else list(range(parse_time(period["start"]).year, parse_time(period['stop_exclusive']).year+1))
    if args.sample:
        years = [min(years[-1], (indexed_stop-MILLISECOND).year)] if indexed_stop else years[-1:]
    for name, bounds in regions:
        for box in region_boxes(bounds):
            for year in years:
                west, south, east, north = box
                params = dict(query="products", target="moon", ihid=ih, iid=instrument, pt=pt,
                              output="JSON", results="copmf", loc="b", westernlon=west,
                              easternlon=east, minlat=south, maxlat=north,
                              limit=args.products_per_region, offset=0)
                if year is not None:
                    start = max(parse_time(period["start"]), parse_time(f"{year}-01-01"))
                    stop = min(parse_time(period['stop_exclusive']), parse_time(f"{year+1}-01-01"))
                    if start >= stop:
                        continue
                    if start >= indexed_stop:
                        selections.append({"region": name, "year": year, "status": "not_indexed",
                                           "url": SOURCES[key], "reason": "Publisher window exceeds indexed spatial coverage; not evidence of no observations"})
                        continue
                    params.update(minobtime=wire(start), maxobtime=wire(stop-MILLISECOND))
                url = SOURCES[key]+"?"+urlencode(params)
                raw, _ = fetch(args, url, evidence/(digest(params)+".json"))
                result = json.loads(raw)["ODEResults"]
                products = product_records(result)
                selections.append({"region": name, "year": year, "query_url": url,
                                   "products_returned": len(products), "selection_cap": args.products_per_region,
                                   "status": "bounded_pilot" if products else "no_observations"})
                for product in products:
                    for entry in ode_product_entries(key, product):
                        entries[entry["url"]] = entry
    return list(entries.values()), {"selections": selections, "window": period if key != "D26" else "historical/static",
                                   "coverage_warnings": coverage_notes,
                                   "warning": "Bounding-box overlap is not verified full study footprint support. Bounded image pilots are NOT three-year continuous histories; inspect labels before EDA."}


def product_records(result):
    """ODE legitimately represents Products as an empty string when Count is zero."""
    if (not isinstance(result, dict) or result.get('Error')
            or result.get('Status', 'SUCCESS').upper() not in {'SUCCESS', 'FINISHED'}
            or not str(result.get('Count', '')).isdigit()):
        raise ValueError(f"Invalid/failed ODE product result: {str(result)[:500]}")
    if int(result['Count']) == 0:
        return []
    container = result.get('Products')
    if not isinstance(container, dict):
        raise ValueError('ODE nonzero count lacks a product container')
    products = listify(container.get('Product'))
    if len(products) != int(result['Count']) or not all(isinstance(p, dict) for p in products):
        raise ValueError('ODE product count/records disagree')
    return products


def response_entries():
    return [{"url": SOURCES['D14']+name, "relative_path": "datasets/D14/response/"+name, "metadata": True}
            for name in ("stationxml.xa.0.sxml", "stationxml.xa.0.xml")]


def coverage_table():
    rows = []
    with (LOCAL/"research/environmental_data.csv").open(encoding="utf-8-sig", newline="") as stream:
        for row in csv.DictReader(stream):
            if not row["Priority ID"].startswith("P1"):
                continue
            key = re.search(r"[DMC]\d{2}", row["Priority ID"])[0]
            status = ("addon_selection" if key in SOURCES else "login_required" if key in {"D21", "D23"}
                      else "project_inputs_required" if key.startswith("M") else "existing_reference_only")
            rows.append({"id": key, "priority": row["Priority ID"], "name": row["Dataset"],
                         "status": status, "source": row["Source"],
                         "note": NOTES.get(key, "No duplicate acquisition. Existing data still requires applicability/quality validation; reference presence is not a requirement pass.")})
    rows.append({"id": "D11", "priority": "Explicit plasma addition (original P2 retained)",
                 "status": "addon_selection", "source": SOURCES['D11'], "note": NOTES['D11']})
    rows.append({"id": "D22", "priority": "Explicit ionisation gap (original P2 retained)",
                 "status": "login_required", "source": "https://pradan.issdc.gov.in/ch3/",
                 "note": "RAMBHA Langmuir-probe surface plasma is distinct from orbital ARTEMIS; authorised access needed, no bypass."})
    return rows


def scan_receipts(roots):
    """Read original source receipts only; never migrate or modify baseline files."""
    index = {'__ode_queries__': []}
    for root in roots:
        if not root.is_dir():
            continue
        for receipt in root.rglob("*.json"):
            if receipt.is_symlink() or receipt.stat().st_size > 256*1024:
                continue
            try:
                saved = json.loads(receipt.read_text(encoding="utf-8"))
            except (OSError, ValueError):
                continue  # Most JSON files are not transfer receipts.
            if not isinstance(saved, dict):
                continue
            if receipt.name == 'selection.json' and 'files' in saved:
                for dataset in saved.get('datasets', []):
                    if dataset.get('id') == 'D20' and dataset.get('ode_params'):
                        files = [item for item in saved['files'] if item.get('dataset') == 'D20'
                                 and item.get('url') != base.DIVINER_RDR_SIS]
                        index['__ode_queries__'].append((dataset['ode_params'], root.resolve(), files))
            source = saved.get("source")
            path = receipt.with_name(receipt.name[:-5])
            if (isinstance(source, dict) and source.get("url") and saved.get("sha256")
                    and path.is_file() and path.resolve().is_relative_to(root.resolve())):
                index.setdefault(source['url'], []).append((path, saved))
    return index


def existing_query(job, index):
    """GDS URLs are generated afresh: deduplicate the exact scientific query first."""
    for params, root, files in index.get('__ode_queries__', []):
        if params != job['params'] or not files:
            continue
        pinned = []
        for original in files:
            path = base.safe_path(root, original['relative_path'])
            # Strictly read-only verification: require a source/hash receipt first.
            if not path.with_name(path.name+'.json').is_file():
                break
            ref = existing_reference(original, index)
            if not ref:
                break
            pinned.append({**original, 'reference': ref})
        else:
            return pinned
    return None


def existing_reference(item, index):
    for path, saved in index.get(item['url'], []):
        source = saved['source']
        if (source.get('size_bytes') != item['size_bytes'] or path.stat().st_size != item['size_bytes']
                or any(source.get(k) and source[k] != item.get(k) for k in ('etag', 'last_modified'))):
            continue
        with path.open('rb') as stream:
            sha = hashlib.file_digest(stream, 'sha256').hexdigest()
        if sha != saved['sha256'] or item.get('sha256') and sha != item['sha256']:
            raise ValueError(f"Original data checksum changed; preserved: {path}")
        if item.get('md5'):
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'md5').hexdigest() != item['md5']:
                    raise ValueError(f"Original publisher MD5 mismatch; preserved: {path}")
        return {"path": str(path.resolve()), "sha256": sha, "source": base.identity(item)}
    return None


def verified_job(record, output):
    if record.get('status') == 'no_observations':
        return True
    files = record.get('files', [])
    if not files or record.get('status') not in TERMINAL:
        return False
    for item in files:
        if item.get('reference'):
            ref = item['reference']
            path = Path(ref['path'])
            if not path.is_file() or path.stat().st_size != item['size_bytes']:
                return False
            with path.open('rb') as stream:
                if hashlib.file_digest(stream, 'sha256').hexdigest() != ref['sha256']:
                    raise ValueError(f"Referenced checksum changed: {path}")
        elif not base.verify_existing(base.safe_path(output, item['relative_path']), item, output):
            return False
    return True


def pin_entries(args, key, entries, output, index):
    pinned = []
    for entry in entries:
        def once():
            with make_session(args) as client:
                return base.file_item(client, entry, key, args.timeout)
        item = retry(args, entry['url'], once)
        if item['size_bytes'] > args.max_file_mib*1024**2:
            raise ValueError(f"File byte limit ({item['size_bytes']:,} bytes > {args.max_file_mib} MiB): {entry['url']}; increase --max-file-mib explicitly")
        reference = existing_reference(item, index)
        if reference:
            item['reference'] = reference
        pinned.append(item)
    return pinned


def baseline_presence(roots):
    """A lightweight source-path inventory, explicitly not a full science audit."""
    rows = []
    core = {'D01': 'moon/diviner/seasonal', 'D02': 'moon/illumination_2016',
            'D03': 'moon/illumination_2016', 'D04': 'moon/illumination_2016',
            'D05': 'moon/sdem', 'D06': 'moon/lola_product90'}
    for row in coverage_table():
        if row['status'] != 'existing_reference_only':
            continue
        paths = []
        for root in roots:
            if row['id'].startswith('D'):
                candidate = root/core.get(row['id'], f"moon/eda_pilots/{row['id']}")
                if candidate.is_dir():
                    paths.append(str(candidate.resolve()))
        rows.append({"id": row['id'], "paths": paths, "status": "reference_paths_present" if paths else "baseline_unlocated",
                     "note": "Path presence only, not file integrity, complete spatial/temporal coverage or requirement applicability."})
    return rows


def process_job(args, job, output, index, budget, budget_lock):
    """One job worker owns its checkpoint; base transfers also lock each payload."""
    jobdir = output/"manifests/addons/jobs"/job['id']
    jobdir.mkdir(parents=True, exist_ok=True)
    lock = jobdir/"active.lock"
    descriptor = os.open(lock, os.O_CREAT | os.O_EXCL | os.O_WRONLY)
    try:
        os.close(descriptor)
        path = jobdir/"inventory.json"
        record = json.loads(path.read_text(encoding='utf-8')) if path.exists() else {"job": job}
        if record.get('job') != job:
            raise ValueError("Checkpoint job identity differs; not overwritten")
        if verified_job(record, output):
            status = 'no_observations' if record.get('status') == 'no_observations' else 'verified_existing'
            return {"id": job['id'], "key": job['key'], "status": status, "checkpoint": str(path)}
        if 'files' not in record:
            if job['key'] == 'D20':
                reused = existing_query(job, index)
                if reused:
                    record.update(files=reused, status='referenced_existing')
                    base.save_json(path, record)
                    return {"id": job['id'], "key": job['key'], "status": "referenced_existing", "checkpoint": str(path)}
                config = {"ode_params": job['params'], "ode_fingerprint": job['id'],
                          "ode_max_points": args.max_points, "note": NOTES['D20']}
                def discover():
                    with make_session(args) as client:
                        return base.discover_ode_diviner(client, config, args.timeout, jobdir)
                groups, info = retry(args, SOURCES['D20']+"?"+urlencode(job['params']), discover)
                entries = [e for group in groups for e in group if e['url'] != base.DIVINER_RDR_SIS]
                # The SIS is original baseline data, not a new copy per query.
                entries = [{**e, 'relative_path': 'datasets/D20/'+job['id']+'/'+Path(e['relative_path']).name} for e in entries]
                record['evidence'] = info
                if not entries:
                    record['status'] = 'no_observations'
                    base.save_json(path, record)
                    return {"id": job['id'], "key": job['key'], "status": "no_observations", "checkpoint": str(path)}
            else:
                entries = job['entries']
            record['files'] = pin_entries(args, job['key'], entries, output, index)
            record['status'] = 'inventoried'
            base.save_json(path, record)
        files = record['files']
        for item in files:
            if not item.get('reference') and item['size_bytes'] > args.max_file_mib*1024**2:
                raise ValueError(f"Pinned file exceeds current --max-file-mib: {item['url']}")
        if job['key'] == 'D20' and record.get('evidence', {}).get('ode_observation_count', 0) > args.max_points:
            raise ValueError('Pinned Diviner query exceeds current --max-points; checkpoint preserved')
        if not args.download:
            return {"id": job['id'], "key": job['key'], "status": "inventoried", "bytes": sum(i['size_bytes'] for i in files), "checkpoint": str(path)}
        needed = sum(i['size_bytes'] for i in files if not i.get('reference')
                     and not base.safe_path(output, i['relative_path']).exists())
        with budget_lock:
            if budget['bytes']+needed > args.max_total_mib*1024**2:
                raise ValueError("Run byte limit reached; checkpoint retained, other jobs continue")
            if shutil.disk_usage(output).free < needed+budget['reserved']+1024**3:
                raise OSError("Insufficient free disk space plus 1 GiB reserve")
            budget['bytes'] += needed
            budget['reserved'] += needed
        try:
            # Labels first, essential for Kaguya detached-image validation.
            for item in sorted(files, key=lambda i: (not i['metadata'], i['relative_path'])):
                if item.get('reference'):
                    item['result'] = 'referenced_existing'
                else:
                    item['result'] = base.transfer_with_connection_retries(item, output, args)
                    if item['result'] not in TERMINAL:
                        raise RuntimeError(f"Transfer incomplete: {item['result']}")
            record['status'] = 'downloaded'
            base.save_json(path, record)
        finally:
            with budget_lock:
                budget['reserved'] -= needed
        return {"id": job['id'], "key": job['key'], "status": "downloaded", "checkpoint": str(path)}
    finally:
        lock.unlink()


def settings(args):
    config = {"schema": 1, "stop": args.stop, "years": args.years, "channels": args.channels,
            "quality_max": args.quality_max, "regions": REGIONS, "datasets": sorted(args.datasets),
            "products_per_region": args.products_per_region, "primary_days_per_month": args.primary_days_per_month, "sample": args.sample,
            "diviner_sample": DIVINER_SAMPLE if args.sample else None,
            "diviner_batch_strategy": "one_channel_per_monthly_tile_v1",
            "sources": SOURCES}
    if 'D27' in args.datasets:
        config['shadowcam_coverage_policy'] = 'publisher_window_with_explicit_index_lag_v1'
    return config


def build_plan(args, output):
    config = settings(args)
    plan_id = digest(config)
    path = output/"manifests/addons/plans"/(plan_id+".json")
    if path.exists() and not args.refresh_plan:
        plan = json.loads(path.read_text(encoding='utf-8'))
        if plan['settings'] != config:
            raise ValueError("Plan identity conflict")
        return plan
    evidence = output/"manifests/addons/discovery"/plan_id
    evidence.mkdir(parents=True, exist_ok=True)
    plan = {"id": plan_id, "settings": config, "jobs": [], "sources": {}, "gaps": []}
    # Discovery failures are isolated by source, not a reason to stop others.
    for key in args.datasets:
        try:
            print(f"Inventory {key}: {SOURCES[key]}", flush=True)
            source_dir = evidence/key
            source_dir.mkdir(exist_ok=True)
            if key == 'D20':
                jobs, info = diviner_jobs(args, source_dir)
            else:
                if key in {'D07', 'D08', 'D11'}:
                    entries, info = dated_listing(args, key, source_dir)
                elif key in {'D15', 'D26', 'D27'}:
                    entries, info = imagery_listing(args, key, source_dir)
                else:
                    entries, info = response_entries(), {"period": "historical response metadata, not recent measurements"}
                # Bundle companions beside their science payload; each group is a thread job.
                groups = {}
                for entry in entries:
                    groups.setdefault(entry['relative_path'].rsplit('/', 1)[0], []).append(entry)
                if key in {'D07', 'D08', 'D11'}:
                    groups = {}
                    for entry in entries:
                        stem = entry['url'].rsplit('.', 1)[0]
                        groups.setdefault(stem, []).append(entry)
                jobs = [{"key": key, "entries": group, "id": digest({"key": key, "entries": group})} for group in groups.values()]
            plan['jobs'].extend(jobs)
            plan['sources'][key] = {"note": NOTES[key], **info, "jobs": len(jobs)}
            base.LOG.info('Source inventory ready %s jobs=%s', key, len(jobs))
        except FAILURES as error:
            base.LOG.exception("Source discovery failed %s %s", key, SOURCES[key])
            plan['gaps'].append({"key": key, "url": SOURCES[key], "status": "inventory_failed", "error": str(error)})
    # Preserve a reproducible selection. Refresh is explicit; failed sources can be retried with it.
    plan['jobs'] = list({job['id']: job for job in plan['jobs']}.values())
    base.save_json(path, plan)
    return plan


def parser():
    result = argparse.ArgumentParser(description=__doc__)
    result.add_argument('--output', type=Path, default=DEFAULT_OUTPUT)
    result.add_argument('--baseline-root', type=Path, action='append', default=None)
    result.add_argument('--datasets', nargs='+', choices=list(SOURCES), default=list(SOURCES))
    result.add_argument('--download', action='store_true')
    result.add_argument('--dry-run', action='store_true')
    result.add_argument('--sample', action='store_true', help='Small, explicitly incomplete provider samples')
    result.add_argument('--refresh-plan', action='store_true', help='Recheck archive coverage and failed discovery; payloads preserved')
    result.add_argument('--workers', type=int, default=4)
    result.add_argument('--connection-retries', type=int, default=3)
    result.add_argument('--timeout', type=int, default=120)
    result.add_argument('--cookies', type=Path)
    result.add_argument('--ca-bundle', type=Path, help='Optional trusted PEM bundle; TLS verification stays enabled')
    result.add_argument('--stop', default=REQUESTED_STOP, help='Exclusive UTC stop, default through October 2026')
    result.add_argument('--years', type=int, default=3)
    result.add_argument('--channels', type=int, nargs='+', default=list(range(3, 10)))
    result.add_argument('--quality-max', type=int, nargs=3, default=[0, 12, 0], metavar=('CAL', 'GEOM', 'MISC'))
    result.add_argument('--max-points', type=int, default=5000000)
    result.add_argument('--max-file-mib', type=int, default=2048)
    result.add_argument('--max-total-mib', type=int, default=102400)
    result.add_argument('--products-per-region', type=int, default=2, help='Imagery products per ROI/meridian segment/year; static D26 per ROI segment')
    result.add_argument('--primary-days-per-month', type=int, default=1, help='Sparse CRaTER primary pilot: last N available days/month; secondary retains all available days')
    result.add_argument('--max-jobs', type=int, help='Limit this run only; remaining jobs explicitly reported incomplete')
    return result


def interleave_sources(jobs):
    """Do not queue thousands of thermal requests ahead of every other P1 source."""
    groups = {}
    for job in jobs:
        groups.setdefault(job['key'], deque()).append(job)
    result = []
    while groups:
        for key in list(groups):
            result.append(groups[key].popleft())
            if not groups[key]:
                del groups[key]
    return result


def main(argv=None):
    command = parser()
    args = command.parse_args(argv)
    args.attempts = 1  # Exactly one initial attempt plus the outer connection retry budget.
    args.channels = sorted(set(args.channels))
    if (not args.channels or min(args.channels) < 3 or max(args.channels) > 9
            or any(q < 0 or q > 255 for q in args.quality_max)):
        command.error('Thermal channels must be 3..9; quality bounds must be 0..255')
    if (min(args.workers, args.timeout, args.years, args.max_points, args.max_file_mib,
            args.max_total_mib, args.products_per_region, args.primary_days_per_month) < 1 or args.connection_retries < 0):
        command.error('Limits must be positive; retries may be zero')
    # Separate check avoids accepting a silently empty truncated run.
    if args.max_jobs is not None and args.max_jobs < 1:
        command.error('--max-jobs must be positive')
    try:
        parse_time(args.stop)
    except ValueError as error:
        command.error(str(error))
    if args.dry_run:
        print(json.dumps({"output": str(args.output), "settings": settings(args), "scope": coverage_table(),
                          "mode": "offline; no directories or network requests; not an inventory/download"}, indent=2))
        return 0
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    run = output/"manifests/addons/runs"/datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    run.mkdir(parents=True, exist_ok=False)
    handlers = base.start_debug_log(run)
    base.STOP.clear()
    base.original_helpers()  # Initialise shared read-only imports before threads.
    old_bundle = os.environ.get('REQUESTS_CA_BUNDLE')
    if args.ca_bundle:
        os.environ['REQUESTS_CA_BUNDLE'] = str(args.ca_bundle.resolve())
    results, plan = [], None
    pool = None
    try:
        print(f"Addon data root: {output}\nWorkers={args.workers}; initial + {args.connection_retries} connection retries; TLS verified.", flush=True)
        plan = build_plan(args, output)
        base.save_json(run/'coverage.json', coverage_table())
        roots = args.baseline_root or [LOCAL/'data']
        index = scan_receipts([r.resolve() for r in roots])
        jobs = interleave_sources(plan['jobs'])
        if args.max_jobs:
            jobs = jobs[:args.max_jobs]
        print(f"Pinned jobs: {len(plan['jobs'])}; selected this run: {len(jobs)}; sample={args.sample}; download={args.download}", flush=True)
        budget, guard = {'bytes': 0, 'reserved': 0}, threading.Lock()
        pool = ThreadPoolExecutor(max_workers=args.workers)
        futures = {pool.submit(process_job, args, job, output, index, budget, guard): job for job in jobs}
        for future in as_completed(futures):
            job = futures[future]
            try:
                item = future.result()
            except FAILURES as error:
                base.LOG.exception('Job failed %s %s; continuing', job['key'], job['id'])
                checkpoint = output/'manifests/addons/jobs'/job['id']/'inventory.json'
                saved = json.loads(checkpoint.read_text(encoding='utf-8')) if checkpoint.is_file() else {}
                item = {"key": job['key'], "id": job['id'], "status": "error", "url": SOURCES[job['key']],
                        "file_urls": [f['url'] for f in saved.get('files', job.get('entries', []))],
                        "error": str(error), "checkpoint": str(checkpoint)}
            results.append(item)
            print(job['key'], item['status'], job['id'], flush=True)
            base.save_json(run/'results.json', results)
    except KeyboardInterrupt:
        base.STOP.set()
        print('Stopping; partials and checkpoints retained.', file=sys.stderr)
        return 130
    finally:
        if pool:
            pool.shutdown(wait=True, cancel_futures=True)
        gaps = (plan or {}).get('gaps', [])
        unresolved = [r for r in results if r['status'] not in TERMINAL | {'inventoried'}]
        report = {"mode": "sample_incomplete" if args.sample else "download" if args.download else "inventory_only",
                  "plan": (plan or {}).get('id'), "planned_jobs": len((plan or {}).get('jobs', [])),
                  "processed_jobs": len(results), "results": results, "source_gaps": gaps,
                  "scope": coverage_table(), "baseline_roots": [str(p) for p in (args.baseline_root or [LOCAL/'data'])],
                  "baseline_presence": baseline_presence(args.baseline_root or [LOCAL/'data'])}
        report['coverage_warnings'] = [{"key": key, **warning} for key, info in (plan or {}).get('sources', {}).items()
                                       for warning in info.get('coverage_warnings', [])]
        report['selection_complete'] = bool(plan) and args.download and not args.sample and not gaps and not unresolved and len(results) == len(plan['jobs'])
        base.save_json(run/'summary.json', report)
        text = [f"Addon run: {run}", f"Selected transfer completion: {report['selection_complete']}",
                'Completion refers to the bounded selection, NOT all Stage 3 inputs or uninterrupted measurements.']
        text += [f"{r.get('key')}: {r['status']} | {r.get('url')} | {r.get('error', '')}" for r in gaps+unresolved]
        text += [f"  File URL: {url}" for r in unresolved for url in r.get('file_urls', [])]
        text += [f"{r['key']}: {r['status']} | {r['url']} | {r['reason']}" for r in report['coverage_warnings']]
        text += [f"{r['key']}: no_observations (not downloaded measurements) | {SOURCES[r['key']]} | checkpoint {r.get('checkpoint')}"
                 for r in results if r['status'] == 'no_observations']
        text += [f"{key}: no selected products in source inventory | {SOURCES[key]}"
                 for key, info in (plan or {}).get('sources', {}).items() if not info.get('jobs')]
        text += [f"{r['id']}: baseline_unlocated; check relocated --baseline-root; not downloaded again automatically"
                 for r in report['baseline_presence'] if r['status'] == 'baseline_unlocated' and r['id'] != 'C01']
        text += [f"{r['id']}: {r['status']} | {r.get('source', '')}" for r in coverage_table() if r['status'] in {'login_required', 'project_inputs_required'}]
        if args.sample or args.max_jobs:
            text.append('Full scope NOT run: sample/job cap active. Repeat without those flags for full selected coverage.')
        base.atomic_text(run/'error_log.txt', '\n'.join(text)+'\n', logger=base.LOG)
        base.atomic_text(output/'error_log.txt', '\n'.join(text)+'\n', logger=base.LOG)
        if old_bundle is None:
            os.environ.pop('REQUESTS_CA_BUNDLE', None)
        else:
            os.environ['REQUESTS_CA_BUNDLE'] = old_bundle
        for handler in handlers:
            base.LOG.removeHandler(handler)
            handler.close()
    print(f"Summary: {run / 'summary.json'}\nMissing/errors: {output / 'error_log.txt'}", flush=True)
    return 1 if unresolved or gaps else 0


if __name__ == '__main__':
    raise SystemExit(main())
