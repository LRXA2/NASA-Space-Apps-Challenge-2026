"""Appended sources preserve dates, native products, labels and existing contracts."""
from datetime import timedelta
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import threading
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'download_script_addons.py'
spec = importlib.util.spec_from_file_location('native_addons', SCRIPT)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def args(*flags):
    result = a.parser().parse_args(list(flags))
    result.attempts = 1
    return result


class NativeAdditionTests(unittest.TestCase):
    def test_default_scope_appended_and_d20_removed(self):
        x = args()
        self.assertTrue(set(a.ADDITIONS) <= set(x.datasets))
        self.assertNotIn('D20', x.datasets)
        self.assertEqual(str(x.output), r'D:\projects\NASA Dataset')

    def test_cli_fixed_start_and_exclusive_stop_are_offline(self):
        with patch.object(a, 'fetch', side_effect=AssertionError('network')), patch.object(Path, 'mkdir', side_effect=AssertionError('write')), patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(a.main(['--dry-run']), 0)
        s = json.loads(out.getvalue())['settings']
        self.assertEqual(s['start'], '2023-06-01T00:00:00.000')
        self.assertEqual(s['stop'], '2026-11-01T00:00:00.000')
        self.assertIn('D20', s['disabled_datasets'])

    def test_explicit_d20_cannot_start_a_download(self):
        with patch.object(a, 'fetch', side_effect=AssertionError('network')), patch.object(Path, 'mkdir', side_effect=AssertionError('write')), patch('sys.stderr', new_callable=io.StringIO):
            with self.assertRaises(SystemExit): a.main(['--datasets', 'D20', '--download'])

    def test_d20_is_disabled_not_failed_physical_requirement(self):
        row = next(r for r in a.coverage_table() if r['id'] == 'D20')
        self.assertEqual(row['status'], 'disabled_by_request')
        self.assertIn('preserved', row['note'])

    def test_native_prp_not_blocked_with_d20(self):
        self.assertIn('D20_PRP', args().datasets)
        self.assertNotIn('D20_PRP', a.DISABLED)

    def test_fixed_start_does_not_slide_with_archive_end(self):
        x = args('--start', '2023-06-01')
        w = a.selection_window(x, a.parse_time('2026-06-15'))
        self.assertEqual(w['start'], '2023-06-01T00:00:00.000')
        self.assertEqual(w['stop_exclusive'], '2026-06-15T00:00:00.000')

    def test_explicit_rolling_mode_retained(self):
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(a.main(['--dry-run', '--rolling-window', '--years', '2']), 0)
        s = json.loads(out.getvalue())['settings']
        self.assertIsNone(s['start'])
        self.assertEqual(s['years'], 2)

    def test_inverted_or_invalid_dates_fail_before_writes(self):
        for start in ['not-a-date', '2027-01-01']:
            with patch.object(Path, 'mkdir', side_effect=AssertionError('write')), patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
                a.main(['--start', start, '--dry-run'])

    def test_archive_before_requested_start_is_not_substituted(self):
        with self.assertRaises(ValueError):
            a.selection_window(args('--start', '2023-06-01'), a.parse_time('2020-01-01'))

    def test_see_and_esa_date_decoding(self):
        self.assertEqual(a.date_of('https://example.org/see__L3_2024366_012_03.ncdf'), a.parse_time('2024-12-31'))
        self.assertEqual(a.date_of('https://example.org/thb_l2_esa_20240601_v01.cdf'), a.parse_time('2024-06-01'))
        with self.assertRaises(ValueError): a.date_of('https://example.org/latest.ncdf')

    def test_see_selects_latest_revision_not_duplicate_day(self):
        urls = ['https://example.org/see__L3_2024001_012_01.ncdf', 'https://example.org/see__L3_2024001_012_03.ncdf']
        selected = a.newest_versions(urls, r'see__L3_(?P<date>\d{7})_(?P<version>\d{3}_\d{2})\.ncdf')
        self.assertEqual(selected, urls[1:])

    def test_see_listing_retains_only_requested_dates(self):
        x = args('--datasets', 'D09_SEE', '--start', '2023-06-01', '--stop', '2023-06-03')
        root = a.SOURCES['D09_SEE']
        def listing(args, url, evidence):
            if url == root: return [root+'2023/']
            return [url+f'see__L3_2023{day:03d}_012_01.ncdf' for day in [151, 152, 153, 154]]
        with patch.object(a, 'links', side_effect=listing): entries, info = a.dated_listing(x, 'D09_SEE', Path('.'))
        self.assertEqual([a.date_of(e['url']) for e in entries], [a.parse_time('2023-06-01'), a.parse_time('2023-06-02')])

    def test_detached_products_require_published_labels(self):
        root = 'https://example.org/'
        with self.assertRaises(ValueError): a.paired_entries([root+'a.tab'], 'unit', r'a\.tab', root)
        entries = a.paired_entries([root+'a.tab', root+'a.xml'], 'unit', r'a\.tab', root)
        self.assertEqual([e['metadata'] for e in entries], [False, True])
        self.assertEqual(entries[0]['relative_path'], 'datasets/unit/a.tab')

    def test_prp_small_sample_labels_only_no_truncated_science(self):
        root = a.SOURCES['D20_PRP']
        urls = [root+'dlre_prp_south'+ext for ext in ['.tab', '.xml', '.lbl']]
        with patch.object(a, 'links', return_value=urls):
            entries, info = a.polar_prp_entries(args('--sample'), Path('.'))
            full, _ = a.polar_prp_entries(args(), Path('.'))
        self.assertTrue(all(e['metadata'] for e in entries))
        self.assertFalse(info['science_payload_in_sample'])
        self.assertTrue(any(not e['metadata'] for e in full))

    def test_south_lamp_complete_support_and_matching_version(self):
        root = a.SOURCES['D32']; categories = ['ALBEDO', 'BRIGHTNESS', 'DATA_QUALITY', 'ERROR', 'EXPOSURE']
        def listing(args, url, evidence):
            if url == root:return [root+c+'/' for c in categories]
            versions = [1] if 'ERROR/' in url else [1, 2]
            return [url+f'LAMP_80{pole}_240mpp_long_test_{version:02d}.{ext}'
                    for pole in ['n', 's'] for version in versions for ext in ['img', 'lbl']]
        with patch.object(a, 'links', side_effect=listing): entries, info = a.south_lamp_entries(args('--sample'), Path('.'))
        self.assertEqual(len(entries), 10)
        self.assertTrue(all('80s' in e['url'] and '_01.' in e['url'] for e in entries))
        self.assertEqual(info['common_versions'], {'long': 1})

    def test_lamp_missing_support_not_silently_ignored(self):
        with patch.object(a, 'links', return_value=[]), self.assertRaises(ValueError):
            a.south_lamp_entries(args('--sample'), Path('.'))

    def test_ldex_uses_historical_dates_despite_modern_start(self):
        root = a.SOURCES['D10']
        def listing(args, url, evidence):
            if url == root:return [root+'current/', root+'mass/']
            kind = url.rstrip('/').rsplit('/', 1)[-1]
            return [url+kind+'_13297_13304'+ext for ext in ['.tab', '.xml']]
        with patch.object(a, 'links', side_effect=listing): entries, info = a.historical_entries(args('--sample', '--start', '2023-06-01'), 'D10', Path('.'))
        self.assertEqual(len(entries), 4)
        self.assertIn('2013-2014', info['period'])

    def test_lend_never_substitutes_housekeeping_for_science(self):
        root = a.SOURCES['D29']
        def listing(args, url, evidence):
            if url == root:return [root+'2023/']
            if url.endswith('2023/'):return [url+'20230601/']
            return [url+'lend_rdr_chk_20230601'+ext for ext in ['.dat', '.xml']]
        with patch.object(a, 'links', side_effect=listing), self.assertRaisesRegex(ValueError, 'not substituted'):
            a.neutron_entries(args('--sample', '--start', '2023-06-01'), Path('.'))

    def test_d20_cached_inventory_cannot_trigger_retry(self):
        x = args('--download'); job = {'id': 'old', 'key': 'D20', 'params': {}}
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); p = root/'manifests/addons/jobs/old/inventory.json';p.parent.mkdir(parents=True)
            p.write_text(json.dumps({'job': job, 'status': 'inventoried', 'files': []}))
            with patch.object(a, 'pin_entries', side_effect=AssertionError('network')), self.assertRaisesRegex(ValueError, 'Disabled'):
                a.process_job(x, job, root, {}, {'bytes': 0, 'reserved': 0}, threading.Lock())

    def test_native_format_and_label_failures_are_not_hidden(self):
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp);(root/'bad.ncdf').write_text('not netCDF')
            with self.assertRaises(OSError):
                a.validate_addition_files([{'relative_path': 'bad.ncdf', 'metadata': False}], root)
            (root/'wrong.xml').write_text('<Product_Observational><file_name>wrong.tab</file_name></Product_Observational>')
            with self.assertRaisesRegex(ValueError, 'does not match'):
                a.validate_addition_files([{'relative_path': 'science.tab', 'metadata': False}, {'relative_path': 'wrong.xml', 'metadata': True}], root)

    def test_manual_holds_include_exact_file_urls(self):
        rows = a.manual_download_list(None, [{'key': 'D09_SEE', 'status': 'error',
            'file_urls': ['https://example.org/a.ncdf'], 'error': 'test failure'}])
        self.assertEqual(rows[-1]['file_urls'], ['https://example.org/a.ncdf'])
        self.assertEqual({r['key'] for r in rows[:-1]}, {'D21', 'D22', 'D23', 'D24'})


if __name__ == '__main__': unittest.main()
