"""Apollo acquisition contracts; existing downloader tests remain unchanged."""
import importlib.util
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1]/'download_script_addons.py'
spec = importlib.util.spec_from_file_location('apollo_addons', SCRIPT)
a = importlib.util.module_from_spec(spec)
spec.loader.exec_module(a)


def args(*flags):
    return a.parser().parse_args(list(flags))


def heat_listing(x, url, evidence):
    if url.endswith('/document/'):
        return [url+'bundle_documentation'+ext for ext in ['.md', '.xml']]
    mission = url.rstrip('/').rsplit('/', 1)[-1]
    return [url+f'{mission}{stem}{ext}' for stem in ['p1f1', '_1975p1f1', '_1975p2f1']
            for ext in ['.tab', '.xml']]+[url+'collection.xml']


def seismic_listing(x, url, evidence):
    root = a.SOURCES['D14_PSE']
    wave = root+'data/xa/continuous_waveform/'+x.apollo_station+'/'
    if url == wave:
        return [url+'1973/', url+'1974/']
    if url.endswith('/1973/') or url.endswith('/1974/'):
        return [url+'001/', url+'002/']
    if url.endswith('/metadata/'):
        return [url+name for name in ['dataless.xa.0.seed', 'dataless.xa.0.xml',
                                      'stationxml.xa.0.sxml', 'stationxml.xa.0.xml']]
    year, day = url.rstrip('/').split('/')[-2:]
    return [url+f'xa.{x.apollo_station}.{loc}.{ch}.{year}.{day}.{v}.{ext}'
            for ch in ['mh1', 'mh2', 'mhz', 'att'] for loc in (['00', '01'] if ch == 'mhz' else ['' if ch == 'att' else '00'])
            for v in [0, 1] for ext in ['mseed', 'xml', 'a.csv', 'a.xml']]


class ApolloDownloadTests(unittest.TestCase):
    def test_defaults_preserve_d_drive_and_modern_dates(self):
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(a.main(['--dry-run']), 0)
        report = json.loads(out.getvalue())
        self.assertEqual(report['output'], r'D:\projects\NASA Dataset')
        self.assertEqual(report['settings']['start'], '2023-06-01T00:00:00.000')
        self.assertEqual(report['settings']['apollo_seismic']['start'], '1973-01-01')
        self.assertEqual(report['settings']['apollo_seismic']['stop_exclusive'], '1975-01-01')
        self.assertIn('D28', report['settings']['datasets'])
        self.assertIn('D14_PSE', report['settings']['datasets'])
        self.assertNotIn('D20', report['settings']['datasets'])

    def test_heat_full_selects_both_missions_and_paired_clean_tables(self):
        with patch.object(a, 'links', side_effect=heat_listing):
            entries, info = a.apollo_heat_entries(args(), Path('.'))
        self.assertEqual(sum(not e['metadata'] for e in entries), 6)
        self.assertEqual(len(entries), 14)
        self.assertTrue(all('data/clean/' in e['url'] for e in entries if not e['metadata']))
        self.assertIn('historical', info['period'])

    def test_heat_sample_has_science_from_each_mission(self):
        with patch.object(a, 'links', side_effect=heat_listing):
            entries, _ = a.apollo_heat_entries(args('--sample', '--start', '2023-06-01'), Path('.'))
        self.assertEqual(len(entries), 6)
        self.assertEqual(sum(not e['metadata'] for e in entries), 2)

    def test_heat_missing_label_or_documentation_fails(self):
        for mode in ['label', 'document']:
            def listing(x, url, evidence):
                entries = heat_listing(x, url, evidence)
                return [] if mode == 'document' and url.endswith('/document/') else [u for u in entries if mode != 'label' or not u.endswith('.xml')]
            with patch.object(a, 'links', side_effect=listing), self.assertRaises(ValueError):
                a.apollo_heat_entries(args(), Path('.'))

    def test_seismic_sample_retains_channels_timing_and_metadata_not_csv(self):
        with patch.object(a, 'links', side_effect=seismic_listing):
            entries, info = a.apollo_seismic_entries(args('--sample'), Path('.'))
        science = [e for e in entries if not e['metadata']]
        self.assertEqual(len(science), 5)  # Both MHZ location modes are retained.
        self.assertTrue(all(e['url'].endswith('.1.mseed') for e in science))
        self.assertEqual(info['selected_science_dates'], ['1973-01-01'])
        self.assertFalse(any(e['url'].endswith('.csv') for e in entries))
        self.assertTrue(all(e['metadata'] for e in entries if '/metadata/' in e['url']))
        self.assertEqual(len(entries), 14)

    def test_seismic_full_window_is_historical_and_stop_exclusive(self):
        x = args('--apollo-start', '1973-01-02', '--apollo-stop', '1974-01-02', '--start', '2023-06-01')
        with patch.object(a, 'links', side_effect=seismic_listing):
            _, info = a.apollo_seismic_entries(x, Path('.'))
        self.assertEqual(info['selected_science_dates'], ['1973-01-02', '1974-01-01'])
        self.assertEqual(len(info['coverage_warnings']), 1)
        self.assertEqual(info['window']['stop_exclusive'], '1974-01-02T00:00:00.000')

    def test_att_only_is_not_a_successful_ground_motion_selection(self):
        def listing(x, url, evidence):
            return [u for u in seismic_listing(x, url, evidence) if '.mh' not in u]
        with patch.object(a, 'links', side_effect=listing), self.assertRaisesRegex(ValueError, 'timing-only'):
            a.apollo_seismic_entries(args('--sample'), Path('.'))

    def test_missing_channel_is_reported_not_invented(self):
        def listing(x, url, evidence):
            return [u for u in seismic_listing(x, url, evidence) if '.mh2.' not in u]
        with patch.object(a, 'links', side_effect=listing):
            entries, info = a.apollo_seismic_entries(args('--sample'), Path('.'))
        self.assertFalse(any('.mh2.' in e['url'] for e in entries))
        self.assertTrue(any(w['status'] == 'missing_channels' and 'mh2' in w['reason'] for w in info['coverage_warnings']))

    def test_latest_revision_requires_its_own_label(self):
        def listing(x, url, evidence):
            return [u for u in seismic_listing(x, url, evidence) if not u.endswith('.1.xml')]
        with patch.object(a, 'links', side_effect=listing), self.assertRaisesRegex(ValueError, 'companion label'):
            a.apollo_seismic_entries(args('--sample'), Path('.'))

    def test_response_metadata_required(self):
        def listing(x, url, evidence):
            return [] if url.endswith('/metadata/') else seismic_listing(x, url, evidence)
        with patch.object(a, 'links', side_effect=listing), self.assertRaisesRegex(ValueError, 'response/epoch'):
            a.apollo_seismic_entries(args('--sample'), Path('.'))

    def test_plan_keeps_waves_with_labels_and_metadata_separate(self):
        x = args('--datasets', 'D28', 'D14_PSE', '--sample')
        def listing(x, url, evidence):
            return heat_listing(x, url, evidence) if 'hfe_concatenated' in url else seismic_listing(x, url, evidence)
        with tempfile.TemporaryDirectory() as temp, patch.object(a, 'links', side_effect=listing):
            plan = a.build_plan(x, Path(temp))
        self.assertFalse(plan['gaps'])
        waves = [j for j in plan['jobs'] if any(e['url'].endswith('.mseed') for e in j['entries'])]
        self.assertEqual(len(waves), 1)
        self.assertEqual(len(waves[0]['entries']), 10)
        self.assertTrue(any(all(e['metadata'] for e in j['entries']) for j in plan['jobs'] if j['key'] == 'D14_PSE'))

    def test_apollo_options_change_plan_identity(self):
        x = args('--datasets', 'D14_PSE')
        y = args('--datasets', 'D14_PSE', '--apollo-station', 's15')
        self.assertNotEqual(a.digest(a.settings(x)), a.digest(a.settings(y)))

    def test_invalid_apollo_dates_fail_before_writes(self):
        for start, stop in [('1975-01-01', '1973-01-01'), ('bad', '1975-01-01'), ('1973-01-01T12:00:00', '1975-01-01')]:
            with patch.object(Path, 'mkdir', side_effect=AssertionError('write')), patch('sys.stderr', new_callable=io.StringIO), self.assertRaises(SystemExit):
                a.main(['--apollo-start', start, '--apollo-stop', stop, '--dry-run'])

    def test_miniseed_decode_and_header_identity(self):
        import numpy as np
        from obspy import Stream, Trace, UTCDateTime
        with tempfile.TemporaryDirectory() as temp:
            root = Path(temp); name = 'xa.s12.00.mhz.1973.001.0.mseed'
            trace = Trace(np.arange(32, dtype=np.int32), header={'network': 'XA', 'station': 'S12', 'location': '00', 'channel': 'MHZ', 'starttime': UTCDateTime('1973-01-01'), 'sampling_rate': 6.625})
            Stream([trace]).write(str(root/name), format='MSEED')
            files = [{'relative_path': name, 'metadata': False}]
            a.validate_addition_files(files, root)
            trace.stats.channel = 'MH1'
            Stream([trace]).write(str(root/name), format='MSEED')
            with self.assertRaisesRegex(ValueError, 'identity mismatch'):
                a.validate_addition_files(files, root)


if __name__ == '__main__':
    unittest.main()
