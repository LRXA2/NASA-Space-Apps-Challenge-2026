#!/usr/bin/env python3
"""Inventory and (optionally) download the South Polar NASA Diviner PCP files.

Dependencies: pip install requests beautifulsoup4

The default behavior is INVENTORY ONLY. It reads three public NASA PDS directory
pages, writes a CSV manifest including advertised file sizes, and prints totals.
Nothing large is downloaded unless --download is provided.

Examples (Windows PowerShell):
  python download_diviner_south_polar.py --output 'D:\\NASA\\Moon\\Diviner'
  python download_diviner_south_polar.py --download --output 'D:\\NASA\\Moon\\Diviner'
  python download_diviner_south_polar.py --collections seasonal --match 'ls030_slon01' --download
  python download_diviner_south_polar.py --collections seasonal --metadata-only --download

Source: NASA PDS Geosciences Node /lro/urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/
Note: This intentionally does NOT recursively crawl the entire lunar archive.
"""

from __future__ import annotations

import argparse
import csv
import os
import re
import shutil
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urljoin, urlparse

import requests
from bs4 import BeautifulSoup
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

ROOT = (
    'https://pds-geosciences.wustl.edu/lro/'
    'urn-nasa-pds-lro_diviner_derived1/data_derived_pcp/'
)
COLLECTIONS = {
    'seasonal': 'seasonal/slon/pols/',
    'local_time': 'diurnal/ltim/pols/',
    'subsolar_longitude': 'diurnal/slon/pols/',
}
EXTENSIONS = {'.tab', '.xml', '.lbl'}
CHUNK_SIZE = 4 * 1024 * 1024


@dataclass(frozen=True)
class RemoteFile:
    collection: str
    filename: str
    url: str
    bytes_expected: int | None


def gib(byte_count: int) -> str:
    return f'{byte_count / (1024 ** 3):,.2f} GiB'


def make_session() -> requests.Session:
    session = requests.Session()
    session.headers.update({
        'User-Agent': 'LunarDivinerAcademicDownloader/1.0 (NASA public PDS archive)',
        'Accept-Encoding': 'identity',
    })
    retry = Retry(
        total=5,
        connect=5,
        read=3,
        backoff_factor=1.5,
        status_forcelist=(429, 500, 502, 503, 504),
        allowed_methods=frozenset({'GET', 'HEAD'}),
        respect_retry_after_header=True,
    )
    adapter = HTTPAdapter(max_retries=retry)
    session.mount('https://', adapter)
    return session


def parse_advertised_size(link) -> int | None:
    """Parse IIS-style directory listings; use HEAD later if a listing differs."""
    previous = link.previous_sibling
    if isinstance(previous, str):
        match = re.search(r'(?<!\d)([\d,]+)\s*$', previous)
        if match:
            try:
                return int(match.group(1).replace(',', ''))
            except ValueError:
                pass
    # Alternative common directory layouts: filenames and sizes in table cells.
    row = link.find_parent('tr')
    if row:
        for cell in reversed(row.find_all(['td', 'th'])):
            text = cell.get_text(' ', strip=True).replace(',', '')
            if re.fullmatch(r'\d+', text):
                return int(text)
    return None


def fetch_inventory(session: requests.Session, collection: str,
                    timeout: int) -> list[RemoteFile]:
    base = urljoin(ROOT, COLLECTIONS[collection])
    print(f'Checking {collection}: {base}', flush=True)
    response = session.get(base, timeout=timeout)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    found = []
    seen = set()
    for link in soup.select('a[href]'):
        url = urljoin(base, link['href'])
        parsed = urlparse(url)
        if parsed.netloc.lower() != urlparse(base).netloc.lower():
            continue
        if not parsed.path.startswith(urlparse(base).path):
            continue
        filename = unquote(parsed.path.rsplit('/', 1)[-1])
        if filename in seen or not filename or Path(filename).suffix.lower() not in EXTENSIONS:
            continue
        if '/' in filename or '\\' in filename or filename in {'.', '..'}:
            continue
        seen.add(filename)
        size = parse_advertised_size(link)
        found.append(RemoteFile(collection, filename, url, size))
    if not found:
        raise RuntimeError(f'No matching product links on {base}; the archive layout may have changed.')
    return sorted(found, key=lambda f: f.filename)


def resolve_unknown_sizes(session: requests.Session, files: list[RemoteFile],
                          timeout: int) -> list[RemoteFile]:
    results = []
    for f in files:
        if f.bytes_expected is not None:
            results.append(f)
            continue
        print(f'  Checking HTTP content length: {f.filename}', flush=True)
        try:
            response = session.head(f.url, allow_redirects=True, timeout=timeout)
            response.raise_for_status()
            size = response.headers.get('Content-Length')
            size = int(size) if size and size.isdecimal() else None
        except requests.RequestException:
            size = None
        results.append(RemoteFile(f.collection, f.filename, f.url, size))
    return results


def write_manifest(path: Path, files: list[RemoteFile]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open('w', newline='', encoding='utf-8') as handle:
        writer = csv.writer(handle)
        writer.writerow(['collection', 'filename', 'size_bytes', 'size_gib', 'url'])
        for f in files:
            writer.writerow([
                f.collection,
                f.filename,
                '' if f.bytes_expected is None else f.bytes_expected,
                '' if f.bytes_expected is None else f'{f.bytes_expected / (1024**3):.6f}',
                f.url,
            ])


def validated_local_size(folder: Path, f: RemoteFile) -> int:
    path = folder / f.collection / f.filename
    if path.exists() and f.bytes_expected is not None and path.stat().st_size == f.bytes_expected:
        return f.bytes_expected
    return 0


def download_one(session: requests.Session, f: RemoteFile,
                 target_root: Path, timeout: int, attempts: int) -> bool:
    destination = target_root / f.collection / f.filename
    destination.parent.mkdir(parents=True, exist_ok=True)
    temp = destination.with_name(destination.name + '.part')
    expected = f.bytes_expected

    if destination.exists():
        if expected is not None and destination.stat().st_size == expected:
            print(f'  SKIP already verified {f.filename}')
            return True
        print(f'  Existing file size unexpected; moving to partial: {f.filename}')
        if temp.exists():
            destination.unlink()  # preserve the .part copy rather than overwrite it
        else:
            destination.rename(temp)

    for attempt in range(1, attempts + 1):
        try:
            start = temp.stat().st_size if temp.exists() else 0
            if expected is not None and start == expected:
                os.replace(temp, destination)
                print(f'  COMPLETE {f.filename} (previous partial verified)')
                return True
            if expected is not None and start > expected:
                raise RuntimeError(f'Partial file larger than listed size: {temp}')
            headers = {'Range': f'bytes={start}-'} if start else {}
            with session.get(f.url, stream=True, headers=headers, timeout=(timeout, timeout)) as response:
                if response.status_code == 416 and expected is not None and start == expected:
                    os.replace(temp, destination)
                    return True
                response.raise_for_status()
                if start and response.status_code == 206:
                    content_range = response.headers.get('Content-Range', '')
                    if not content_range.startswith(f'bytes {start}-'):
                        raise RuntimeError(f'Unexpected Content-Range: {content_range}')
                    mode = 'ab'
                elif start and response.status_code == 200:
                    # Server ignored Range: safely restart instead of appending duplicate data.
                    print(f'  Server ignored resume; restarting {f.filename}')
                    start = 0
                    mode = 'wb'
                else:
                    mode = 'wb'
                written = start
                next_report = (written // (64 * 1024 * 1024) + 1) * 64 * 1024 * 1024
                with temp.open(mode) as output:
                    for chunk in response.iter_content(chunk_size=CHUNK_SIZE):
                        if not chunk:
                            continue
                        output.write(chunk)
                        written += len(chunk)
                        if written >= next_report:
                            print(f'    {f.filename}: {written / (1024**2):,.0f} MiB', flush=True)
                            next_report += 64 * 1024 * 1024
            actual = temp.stat().st_size
            if expected is not None and actual != expected:
                raise IOError(f'Incomplete: {actual:,} of {expected:,} bytes')
            os.replace(temp, destination)
            print(f'  DONE {f.filename} ({gib(actual)})', flush=True)
            return True
        except (requests.RequestException, OSError, RuntimeError) as exc:
            print(f'  Attempt {attempt}/{attempts} failed for {f.filename}: {exc}', file=sys.stderr)
            if attempt < attempts:
                time.sleep(min(25, 2 ** attempt))
    print(f'  FAILED {f.filename}; partial file retained for later resumption.', file=sys.stderr)
    return False


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument('--output', type=Path, default=Path('data/raw/moon/diviner'))
    p.add_argument('--collections', nargs='+', choices=list(COLLECTIONS), default=list(COLLECTIONS),
                   help='Collection(s) to list or download (default: all three)')
    p.add_argument('--download', action='store_true', help='Download selected files; default just creates manifest')
    p.add_argument('--metadata-only', action='store_true', help='Select .lbl/.xml only, not large .tab files')
    p.add_argument('--match', default=None, help='Case-insensitive substring to restrict filenames')
    p.add_argument('--max-files', type=int, default=None, help='Download only first N matched files (test)')
    p.add_argument('--timeout', type=int, default=45, help='HTTP timeout in seconds')
    p.add_argument('--attempts', type=int, default=5, help='Attempts per download, with backoff')
    return p


def main() -> int:
    args = build_parser().parse_args()
    output = args.output.expanduser().resolve()
    output.mkdir(parents=True, exist_ok=True)
    session = make_session()
    all_files = []
    try:
        for collection in args.collections:
            all_files.extend(fetch_inventory(session, collection, args.timeout))
    except (requests.RequestException, RuntimeError) as exc:
        print(f'Unable to create inventory: {exc}', file=sys.stderr)
        return 1
    all_files = resolve_unknown_sizes(session, all_files, args.timeout)
    manifest = output / 'download_manifest.csv'
    write_manifest(manifest, all_files)
    print(f'\nComplete source inventory saved to: {manifest}')
    print('\nCollection totals (remote listed bytes):')
    for name in args.collections:
        section = [f for f in all_files if f.collection == name]
        tabs = sum(f.filename.endswith('.tab') for f in section)
        total_bytes = sum(f.bytes_expected or 0 for f in section)
        unknown = sum(f.bytes_expected is None for f in section)
        print(f'  {name:20} {len(section):4} files ({tabs:3} .tab), {gib(total_bytes)}'
              + (f' + {unknown} unknown sizes' if unknown else ''))
    full_bytes = sum(f.bytes_expected or 0 for f in all_files)
    print(f'  TOTAL                {len(all_files):4} files, {gib(full_bytes)}'
          + (' (known-size portion only)' if any(f.bytes_expected is None for f in all_files) else ''))

    selected = [f for f in all_files if (not args.metadata_only or f.filename.endswith(('.xml', '.lbl')))
                and (not args.match or args.match.lower() in f.filename.lower())]
    if args.max_files is not None:
        if args.max_files <= 0:
            print('--max-files must be positive', file=sys.stderr)
            return 2
        selected = selected[:args.max_files]
    if not selected:
        print('No files selected. Change --match, --collections, or --metadata-only.')
        return 2

    pending = sum(max(0, (f.bytes_expected or 0) - validated_local_size(output, f)) for f in selected)
    available = shutil.disk_usage(output).free
    print(f'\nSelected files: {len(selected)}, listed total {gib(sum(f.bytes_expected or 0 for f in selected))}')
    print(f'Known bytes not yet fully downloaded: {gib(pending)}')
    print(f'Free disk space in output volume: {gib(available)}')
    if not args.download:
        print('\nINVENTORY ONLY: No data downloaded. Rerun with --download to start.')
        return 0
    if pending > available:
        print('Not enough free disk space for the selected files; download not started.', file=sys.stderr)
        return 2

    print('\nDownloading sequentially (respecting NASA server resources). Ctrl+C to interrupt; rerun to resume.\n')
    successes = 0
    try:
        for i, f in enumerate(selected, 1):
            print(f'[{i}/{len(selected)}] {f.collection}/{f.filename}', flush=True)
            if download_one(session, f, output, args.timeout, args.attempts):
                successes += 1
            time.sleep(0.15)
    except KeyboardInterrupt:
        print('\nInterrupted. Existing .part files are preserved. Rerun the same command to resume.')
        return 130
    print(f'\nFinished: {successes}/{len(selected)} files verified against directory-listed sizes.')
    return 0 if successes == len(selected) else 1


if __name__ == '__main__':
    raise SystemExit(main())
