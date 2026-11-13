"""Addon contracts, without changing or weakening the original downloader tests."""
import argparse
from datetime import timedelta
import hashlib
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'download_script_addons.py'
spec = importlib.util.spec_from_file_location('environmental_addons', SCRIPT)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


class AddonTests(unittest.TestCase):
    def args(self, *extra):
        result = a.parser().parse_args(list(extra))
        result.attempts = 1
        return result

    def test_original_unchanged(self):
        self.assertEqual(hashlib.sha256(Path(a.base.__file__).read_bytes()).hexdigest(), a.ORIGINAL_SHA256)

    def test_default_destination(self):
        self.assertEqual(str(self.args().output), r'D:\projects\NASA Dataset')

    def test_default_scope_channels_retries(self):
        args = self.args()
        self.assertEqual(args.channels, list(range(3, 10)))
        self.assertEqual(args.connection_retries, 3)
        self.assertEqual(args.quality_max, [0, 12, 0])
        self.assertIn('D07', args.datasets)
        self.assertIn('D08', args.datasets)
        self.assertIn('D11', args.datasets)

    def test_coverage_all_p1_preserves_priority(self):
        rows = a.coverage_table()
        self.assertEqual(len([r for r in rows if r['priority'].startswith('P1')]), 34)
        self.assertEqual(next(r for r in rows if r['id'] == 'D21')['status'], 'login_required')
        self.assertEqual(next(r for r in rows if r['id'] == 'M04')['status'], 'project_inputs_required')
        self.assertIn('original P2', next(r for r in rows if r['id'] == 'D11')['priority'])

    def test_three_year_availability_cap(self):
        window = a.resolve_window(a.parse_time('2026-06-15T23:59:59.973Z')+a.MILLISECOND)
        self.assertEqual(window['start'], '2023-06-15T23:59:59.974')
        self.assertEqual(window['stop_exclusive'], '2026-06-15T23:59:59.974')

    def test_requested_end_cap(self):
        self.assertEqual(a.resolve_window(a.parse_time('2027-01-01'))['stop_exclusive'], a.REQUESTED_STOP)

    def test_leap_year(self):
        self.assertEqual(a.years_before(a.parse_time('2024-02-29'), 3), a.parse_time('2021-02-28'))

    def test_months_contiguous_partial(self):
        start, stop = a.parse_time('2023-06-15'), a.parse_time('2026-06-15')
        windows = list(a.months(start, stop))
        self.assertEqual(len(windows), 37)
        self.assertEqual(windows[0][0], start)
        self.assertEqual(windows[-1][1], stop)
        self.assertTrue(all(windows[i][1] == windows[i+1][0] for i in range(len(windows)-1)))

    def test_wire_no_z(self):
        self.assertEqual(a.wire(a.parse_time('2025-01-01T01:00:00+01:00')), '2025-01-01T00:00:00.000')

    def test_seven_regions_and_zero_split(self):
        self.assertEqual(len(a.REGIONS), 7)
        boxes = a.region_boxes(a.REGIONS['A3CLR22_11_Malapert_Massif'])
        self.assertEqual(len(boxes), 2)
        self.assertEqual(boxes[0][2], 360)
        self.assertEqual(boxes[1][0], 0)

    def test_envelopes_contain_projected_grid(self):
        for bounds in a.REGIONS.values():
            boxes = a.region_boxes(bounds)
            for ix in range(11):
                for iy in range(11):
                    lon, lat = a.xy_to_geo(bounds[0]+(bounds[2]-bounds[0])*ix/10,
                                           bounds[1]+(bounds[3]-bounds[1])*iy/10)
                    self.assertTrue(any(b[0]-1e-9 <= lon <= b[2]+1e-9 and b[1]-1e-9 <= lat <= b[3]+1e-9 for b in boxes))

    def test_inverse_region_membership(self):
        for b in a.REGIONS.values():
            lon, lat = a.xy_to_geo((b[0]+b[2])/2, (b[1]+b[3])/2)
            self.assertTrue(a.in_region(lon, lat, b))
        self.assertFalse(a.in_region(180, 0, next(iter(a.REGIONS.values()))))

    def test_tiles_area_and_union(self):
        for b in a.REGIONS.values():
            for box in a.region_boxes(b):
                pieces = list(a.tiles(box, list(range(3, 10))))
                area = sum((t[2]-t[0])*(t[3]-t[1]) for t in pieces)
                self.assertAlmostEqual(area, (box[2]-box[0])*(box[3]-box[1]))
                self.assertTrue(all((t[2]-t[0])*(t[3]-t[1])*7 <= 5.000001 for t in pieces))

    def test_flags_channels_and_exclusive_end(self):
        p = a.diviner_params([29, -85.6, 29.2, -85.4], a.parse_time('2025-11-01'), a.parse_time('2025-12-01'), self.args())
        self.assertEqual(p['channel'], 'ffttttttt')
        self.assertEqual(p['maxobtime'], '2025-11-30T23:59:59.999')
        self.assertEqual(p['maxgeometry'], 12)

    def test_newest_version(self):
        urls = ['https://example.org/thb_l2_merged_20260101_v01.cdf', 'https://example.org/thb_l2_merged_20260101_v02.cdf']
        selected = a.newest_versions(urls, r'thb_l2_merged_(?P<date>\d{8})_v(?P<version>\d+)\.cdf')
        self.assertEqual(selected, urls[1:])

    def test_native_dates(self):
        self.assertEqual(a.date_of('https://example.org/CRAT_L2_SEC_2026181_V01.TAB'), a.parse_time('2026-06-30'))
        self.assertEqual(a.date_of('https://example.org/sci_sgps-l2-avg5m_g19_d20260930_v3-0-3.nc'), a.parse_time('2026-09-30'))
        self.assertEqual(a.date_of('https://example.org/thb_l2_merged_20260901_v01.cdf'), a.parse_time('2026-09-01'))

    def test_shadowcam_science_not_browse(self):
        files = [{'URL': 'https://example.org/A_map_raw.'+ext, 'Type': 'Referenced'} for ext in ('tif', 'xml')]
        files.append({'URL': 'https://example.org/A_map_stretched.tif', 'Type': 'Browse'})
        entries = a.ode_product_entries('D27', {'pdsid': 'a', 'Product_files': {'Product_file': files}})
        self.assertEqual(len(entries), 2)
        self.assertTrue(all('_map_raw.' in e['url'] for e in entries))

    def test_missing_label_rejected(self):
        with self.assertRaises(ValueError):
            a.ode_product_entries('D15', {'Product_files': {'Product_file': {'URL': 'https://example.org/A.img', 'Type': 'Product'}}})

    def test_ode_zero_products_string_is_valid_empty(self):
        self.assertEqual(a.product_records({'Status': 'Success', 'Count': '0', 'Products': ''}), [])

    def test_ode_incomplete_or_error_not_empty(self):
        for value in ({}, {'Status': 'Error', 'Count': '0'}, {'Count': '1', 'Products': ''},
                      {'Count': '2', 'Products': {'Product': {}}}):
            with self.assertRaises(ValueError):
                a.product_records(value)

    def test_ode_single_product(self):
        self.assertEqual(a.product_records({'Count': '1', 'Products': {'Product': {'pdsid': 'a'}}}), [{'pdsid': 'a'}])

    def test_baseline_reference_requires_sha(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp)/'original.tab'
            p.write_bytes(b'abc')
            item = dict(url='https://example.org/original.tab', size_bytes=3, relative_path='datasets/D07/a.tab')
            receipt = dict(source=item, sha256=hashlib.sha256(b'abc').hexdigest())
            p.with_name(p.name+'.json').write_text(json.dumps(receipt))
            index = a.scan_receipts([Path(temp)])
            ref = a.existing_reference(item, index)
            self.assertEqual(ref['path'], str(p.resolve()))
            p.write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'checksum changed'):
                a.existing_reference(item, index)

    def test_same_name_different_source_not_reused(self):
        self.assertIsNone(a.existing_reference(dict(url='https://different.org/a.tab'), {'https://example.org/a.tab': []}))

    def test_job_cache_revalidates_payload(self):
        record = dict(status='downloaded', files=[dict(relative_path='a.tab', size_bytes=1)])
        with patch.object(a.base, 'verify_existing', return_value=None):
            self.assertFalse(a.verified_job(record, Path('.')))
        with patch.object(a.base, 'verify_existing', return_value='a'*64):
            self.assertTrue(a.verified_job(record, Path('.')))

    def test_empty_job_cache_does_not_claim_measurements(self):
        self.assertTrue(a.verified_job({'status': 'no_observations'}, Path('.')))
        self.assertFalse(a.verified_job({'status': 'inventoried', 'files': []}, Path('.')))

    def test_dry_run_offline_no_writes(self):
        with patch.object(a, 'fetch', side_effect=AssertionError('network')), patch.object(Path, 'mkdir', side_effect=AssertionError('write')), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(a.main(['--dry-run']), 0)
            self.assertEqual(json.loads(out.getvalue())['output'], r'D:\projects\NASA Dataset')

    def test_invalid_limits(self):
        for flags in (['--workers', '0'], ['--connection-retries', '-1'], ['--channels', '1'], ['--quality-max', '0', '256', '0']):
            with patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit) as error:
                a.main(['--dry-run']+flags)
            self.assertEqual(error.exception.code, 2)

    def test_retry_single_outer_budget(self):
        args = self.args()
        operation = lambda: 123
        with patch.object(a.base, 'retry_connections', return_value=123) as retry:
            self.assertEqual(a.retry(args, 'test', operation), 123)
            retry.assert_called_once_with(operation, 'test', a.base.LOG, 3, a.base.STOP)

    def test_plan_cache_avoids_regeneration(self):
        args = self.args('--datasets', 'D20')
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            path = root/'manifests/addons/plans'/(a.digest(a.settings(args))+'.json')
            path.parent.mkdir(parents=True)
            plan = dict(settings=a.settings(args), jobs=[], id='frozen')
            path.write_text(json.dumps(plan))
            with patch.object(a, 'diviner_jobs', side_effect=AssertionError('regenerated')):
                self.assertEqual(a.build_plan(args, root), plan)

    def test_discovery_error_continues_to_other_source(self):
        args = self.args('--datasets', 'D20', 'D14')
        with tempfile.TemporaryDirectory() as temp, patch.object(a, 'diviner_jobs', side_effect=ValueError('source unavailable')):
            with patch.object(a.base.LOG, 'exception'):
                plan = a.build_plan(args, Path(temp))
            self.assertEqual(plan['gaps'][0]['key'], 'D20')
            self.assertEqual(plan['jobs'][0]['key'], 'D14')

    def test_error_is_logged_and_next_job_continues(self):
        jobs = [{'id': 'bad', 'key': 'D07', 'entries': [{'url': 'https://example.org/bad.tab'}]},
                {'id': 'good', 'key': 'D14', 'entries': []}]
        def run(args, job, *rest):
            if job['id'] == 'bad':
                raise a.base.requests.ConnectionError('connection still down after retries')
            return {'id': job['id'], 'key': job['key'], 'status': 'downloaded'}
        with tempfile.TemporaryDirectory() as temp, patch.object(a, 'build_plan', return_value={'id': 'test', 'jobs': jobs, 'gaps': []}), patch.object(a, 'scan_receipts', return_value={}), patch.object(a, 'process_job', side_effect=run), patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(a.main(['--output', temp, '--datasets', 'D07', 'D14', '--download', '--workers', '2']), 1)
            report = json.loads(next(Path(temp).glob('manifests/addons/runs/*/summary.json')).read_text())
            self.assertEqual({r['status'] for r in report['results']}, {'error', 'downloaded'})
            self.assertFalse(report['selection_complete'])
            self.assertIn('https://example.org/bad.tab', (Path(temp)/'error_log.txt').read_text())

    def test_diviner_plan_covers_all_seven_and_three_years(self):
        args = self.args('--datasets', 'D20')
        response = b'<GDSResults><Status>Success</Status><Global_Parameters><GlobalMaxUTC>2026-06-15T23:59:59.973Z</GlobalMaxUTC></Global_Parameters></GDSResults>'
        with patch.object(a, 'fetch', return_value=(response, 'https://example.org')):
            jobs, info = a.diviner_jobs(args, Path('.'))
        self.assertEqual({j['region'] for j in jobs}, set(a.REGIONS))
        self.assertEqual(info['window']['years'], 3)
        self.assertEqual(min(j['params']['minobtime'] for j in jobs), '2023-06-15T23:59:59.974')
        self.assertEqual(max(j['params']['maxobtime'] for j in jobs), '2026-06-15T23:59:59.973')

    def test_diviner_batches_single_channel_without_dropping_any(self):
        args = self.args('--datasets', 'D20', '--sample')
        response = b'<GDSResults><Status>Success</Status><Global_Parameters><GlobalMaxUTC>2026-06-15T23:59:59.973Z</GlobalMaxUTC></Global_Parameters></GDSResults>'
        with patch.object(a, 'fetch', return_value=(response, 'https://example.org')):
            jobs, _ = a.diviner_jobs(args, Path('.'))
        self.assertEqual(len(jobs), 7)
        self.assertTrue(all(j['params']['channel'].count('t') == 1 for j in jobs))
        self.assertEqual({j['params']['channel'].index('t')+1 for j in jobs}, set(range(3, 10)))

    def test_crater_primary_is_monthly_bounded_not_whole_archive(self):
        args = self.args('--datasets', 'D07')
        def archive(args, url, evidence):
            if url.endswith('data-der-sec/') or url.endswith('data-der-pri/'):
                return [url+'2026/']
            stem = 'SEC' if 'data-der-sec/' in url else 'PRI'
            return [url+f'CRAT_L2_{stem}_{date}_V01.TAB' for date in ['2026001', '2026002', '2026032', '2026033']]
        with patch.object(a, 'links', side_effect=archive):
            entries, info = a.dated_listing(args, 'D07', Path('.'))
        self.assertEqual(len([e for e in entries if '_SEC_' in e['url'] and not e.get('metadata')]), 4)
        primary = [e['url'] for e in entries if '_PRI_' in e['url'] and not e.get('metadata')]
        self.assertEqual(len(primary), 2)
        self.assertTrue(primary[0].endswith('2026002_V01.TAB'))
        self.assertTrue(primary[1].endswith('2026033_V01.TAB'))

    def test_shared_goes_window_does_not_extend_retired_satellite_backwards(self):
        args = self.args('--datasets', 'D08')
        def archive(args, url, evidence):
            if url.endswith('sgps-l2-avg5m/'):
                return [url+str(y)+'/' for y in [2022, 2023, 2025, 2026]]
            if re_match := __import__('re').search(r'/20\d{2}/$', url):
                return [url+'10/']
            date = url[-8:-4]+url[-3:-1]+'01'
            satellite = '16' if 'goes16/' in url else '19'
            if satellite == '16' and date > '20251001':
                return []
            return [url+f'sci_sgps-l2-avg5m_g{satellite}_d{date}_v3-0-3.nc']
        with patch.object(a, 'links', side_effect=archive):
            entries, info = a.dated_listing(args, 'D08', Path('.'))
        self.assertEqual(info['windows']['16'], info['windows']['19'])
        self.assertTrue(all(a.date_of(e['url']) >= a.parse_time('2023-10-02') for e in entries))

    def test_inventory_checkpoint_is_reused_for_transfer_without_head(self):
        args = self.args('--datasets', 'D14', '--download')
        job = {'id': 'pinned', 'key': 'D14', 'entries': []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root/'manifests/addons/jobs/pinned/inventory.json'
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(json.dumps({'job': job, 'status': 'inventoried', 'files': [
                {'url': 'https://example.org/a.xml', 'relative_path': 'datasets/D14/a.xml', 'dataset': 'D14', 'metadata': True, 'size_bytes': 1}]}))
            with patch.object(a, 'pin_entries', side_effect=AssertionError('repinned')), patch.object(a.base, 'transfer_with_connection_retries', return_value='downloaded'):
                record = a.process_job(args, job, root, {}, {'bytes': 0, 'reserved': 0}, __import__('threading').Lock())
            self.assertEqual(record['status'], 'downloaded')
            self.assertFalse((checkpoint.parent/'active.lock').exists())

    def test_lowered_file_cap_applies_to_cached_inventory(self):
        args = self.args('--datasets', 'D14', '--download', '--max-file-mib', '1')
        job = {'id': 'large', 'key': 'D14', 'entries': []}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root/'manifests/addons/jobs/large/inventory.json'
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(json.dumps({'job': job, 'status': 'inventoried', 'files': [
                {'url': 'https://example.org/a.xml', 'relative_path': 'datasets/D14/a.xml', 'dataset': 'D14', 'metadata': True, 'size_bytes': 2*1024**2}]}))
            with patch.object(a.base, 'transfer_with_connection_retries', side_effect=AssertionError('must not download')):
                with self.assertRaisesRegex(ValueError, 'current --max-file-mib'):
                    a.process_job(args, job, root, {}, {'bytes': 0, 'reserved': 0}, __import__('threading').Lock())

    def test_cached_empty_job_keeps_no_observations_status(self):
        args = self.args('--datasets', 'D20', '--download')
        job = {'id': 'empty', 'key': 'D20', 'params': {}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            checkpoint = root/'manifests/addons/jobs/empty/inventory.json'
            checkpoint.parent.mkdir(parents=True)
            checkpoint.write_text(json.dumps({'job': job, 'status': 'no_observations'}))
            with patch.object(a.base, 'discover_ode_diviner', side_effect=AssertionError('must not regenerate')):
                result = a.process_job(args, job, root, {}, {'bytes': 0, 'reserved': 0}, __import__('threading').Lock())
            self.assertEqual(result['status'], 'no_observations')

    def test_exact_original_query_referenced_without_new_urls(self):
        params = {'query': 'divinerrdr', 'channel': 'fffffffft'}
        original = {'dataset': 'D20', 'url': 'https://example.org/old.tab', 'size_bytes': 3, 'relative_path': 'old.tab'}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp)
            (root/'old.tab').write_bytes(b'abc')
            saved = {'source': original, 'sha256': hashlib.sha256(b'abc').hexdigest()}
            (root/'old.tab.json').write_text(json.dumps(saved))
            index = a.scan_receipts([root])
            index['__ode_queries__'] = [(params, root, [original])]
            result = a.existing_query({'params': params}, index)
            self.assertEqual(result[0]['reference']['path'], str((root/'old.tab').resolve()))
            self.assertIsNone(a.existing_query({'params': {**params, 'channel': 'ffffffftf'}}, index))

    def test_shadowcam_publisher_window_not_old_index_window(self):
        args = self.args('--datasets', 'D27')
        index = {'ODEResults': {'IIPTSets': {'IIPTSet': {
            'ODEMetaDB': 'Moon', 'IHID': 'KPLO', 'IID': 'ShadowCam', 'PT': 'CAL',
            'MaxObservationTime': '2024-09-30T23:41:58.531Z'}}}}
        def metadata(args, url, evidence):
            if 'query=iipt' in url:
                return json.dumps(index).encode(), url
            if url.endswith('data-calibrated.xml'):
                return b'<Product_Collection><stop_date_time>2025-09-30T23:29:46.494Z</stop_date_time></Product_Collection>', url
            return b'{"ODEResults":{"Status":"Success","Count":"0","Products":""}}', url
        with patch.object(a, 'fetch', side_effect=metadata):
            entries, info = a.imagery_listing(args, 'D27', Path('.'))
        self.assertEqual(entries, [])
        self.assertEqual(info['window']['start'], '2022-09-30T23:29:46.495')
        self.assertEqual(info['coverage_warnings'][0]['status'], 'provider_index_lag')
        self.assertTrue(any(r['year'] == 2025 and r['status'] == 'not_indexed' for r in info['selections']))

    def test_queue_interleaves_sources_without_losing_or_reordering_their_jobs(self):
        jobs = [{'id': str(i), 'key': 'D20'} for i in range(5)]
        jobs += [{'id': 'radiation', 'key': 'D07'}, {'id': 'plasma', 'key': 'D11'}]
        scheduled = a.interleave_sources(jobs)
        self.assertEqual([j['key'] for j in scheduled[:3]], ['D20', 'D07', 'D11'])
        self.assertEqual([j['id'] for j in scheduled if j['key'] == 'D20'], [str(i) for i in range(5)])
        self.assertEqual({j['id'] for j in scheduled}, {j['id'] for j in jobs})


if __name__ == '__main__':
    unittest.main()
