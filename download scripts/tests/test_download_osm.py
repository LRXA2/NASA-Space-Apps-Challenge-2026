"""Verify publisher-checksum enforcement and safe resumable transfers."""
import hashlib
import importlib.util
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SPEC = importlib.util.spec_from_file_location("osm", Path(__file__).parents[1] / "download_osm.py")
assert SPEC is not None and SPEC.loader is not None
osm = importlib.util.module_from_spec(SPEC)
sys.modules[SPEC.name] = osm
SPEC.loader.exec_module(osm)


class DownloadTests(unittest.TestCase):
    def test_bounded_ranges_resume_and_verify_the_complete_payload(self):
        source = {'url': 'https://download.geofabrik.de/sample.osm.pbf',
                  'filename': 'sample.osm.pbf', 'size_bytes': 5,
                  'md5': 'ab56b4d92b40713acc5af89985d4b786'}  # Known MD5 for b'abcde'.
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'sample.osm.pbf.part').write_bytes(b'a')
            session = MagicMock()
            responses = []
            for content_range, body in [('bytes 1-2/5', b'bc'), ('bytes 3-4/5', b'de')]:
                response = MagicMock()
                response.status_code = 206
                response.headers = {'Content-Range': content_range}
                response.iter_content.return_value = [body]
                context = MagicMock()
                context.__enter__.return_value = response
                responses.append(context)
            session.get.side_effect = responses
            self.assertEqual(osm.download(session, source, output, 10, 1, chunk_bytes=2), 'downloaded')
            self.assertEqual((output / 'sample.osm.pbf').read_bytes(), b'abcde')
            self.assertEqual([call.kwargs['headers']['Range'] for call in session.get.call_args_list], ['bytes=1-2', 'bytes=3-4'])

    def test_expansion_regions_are_explicit_and_original_project_selection_is_preserved(self):
        cases = [
            (['--project-areas'], ['arizona', 'canary-islands', 'chile', 'bolivia']),
            (['--regions', 'northern-california', 'jordan', '--date', '261025'], ['northern-california', 'jordan']),
        ]
        for arguments, expected in cases:
            with self.subTest(arguments=arguments), tempfile.TemporaryDirectory() as directory:
                def head(url, **kwargs):
                    response = MagicMock()
                    response.url = url.replace('-latest.osm.pbf', '-261025.osm.pbf')
                    response.headers = {'Content-Length': '3', 'Last-Modified': 'Mon, 26 Oct 2026 03:00:00 GMT'}
                    context = MagicMock()
                    context.__enter__.return_value = response
                    return context

                def get(url, **kwargs):
                    response = MagicMock()
                    filename = url.rsplit('/', 1)[-1].removesuffix('.md5')
                    response.text = '900150983cd24fb0d6963f7d28e17f72  ' + filename
                    return response

                session = MagicMock()
                session.head.side_effect = head
                session.get.side_effect = get
                with patch.object(sys, 'argv', ['download_osm.py', *arguments, '--output', directory]), patch.object(osm.requests, 'Session') as factory:
                    factory.return_value.__enter__.return_value = session
                    self.assertEqual(osm.main(), 0)
                selection = json.loads((Path(directory) / 'manifests/selection.json').read_text())
                self.assertEqual(selection['regions'], expected)
                self.assertEqual([source['region'] for source in selection['sources']], expected)
                if 'northern-california' in expected:
                    self.assertEqual(selection['sources'][0]['url'], 'https://download.geofabrik.de/north-america/us/california/norcal-261025.osm.pbf')
                    self.assertEqual(session.head.call_args_list[0].args[0], 'https://download.geofabrik.de/north-america/us/california/norcal-261025.osm.pbf')

    def test_complete_partial_is_promoted_without_network(self):
        source = {'url': 'https://download.geofabrik.de/sample.osm.pbf',
                  'filename': 'sample.osm.pbf', 'size_bytes': 3,
                  'md5': '900150983cd24fb0d6963f7d28e17f72'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'sample.osm.pbf.part').write_bytes(b'abc')
            session = MagicMock()
            session.get.side_effect = AssertionError('Complete valid partial must not download again')
            self.assertEqual(osm.download(session, source, output, 10, 1), 'downloaded')
            self.assertEqual((output / 'sample.osm.pbf').read_bytes(), b'abc')
            self.assertTrue((output / 'sample.osm.pbf.json').exists())
            session.get.assert_not_called()

    def test_checksum_parser_rejects_wrong_filename(self):
        self.assertEqual(osm.parse_checksum('900150983cd24fb0d6963f7d28e17f72  sample.osm.pbf\n', 'sample.osm.pbf'),
                         '900150983cd24fb0d6963f7d28e17f72')
        with self.assertRaises(ValueError):
            osm.parse_checksum('900150983cd24fb0d6963f7d28e17f72  different.osm.pbf', 'sample.osm.pbf')

    def test_ignored_range_restarts_and_corrupt_completed_file_is_preserved(self):
        body = b'abc'
        source = {'url': 'https://download.geofabrik.de/sample.osm.pbf',
                  'filename': 'sample.osm.pbf', 'size_bytes': 3,
                  'md5': '900150983cd24fb0d6963f7d28e17f72'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / 'sample.osm.pbf.part').write_bytes(b'a')
            session = MagicMock()
            response = session.get.return_value.__enter__.return_value
            response.status_code = 200
            response.iter_content.return_value = [body]
            osm.download(session, source, output, 10, 1)
            self.assertEqual((output / 'sample.osm.pbf').read_bytes(), body)
            (output / 'sample.osm.pbf').write_bytes(b'bad')
            with self.assertRaisesRegex(ValueError, 'preserved'):
                osm.download(session, source, output, 10, 1)
            self.assertEqual((output / 'sample.osm.pbf').read_bytes(), b'bad')

    def test_bad_checksum_never_promotes_and_wrong_range_never_appends(self):
        source = {'url': 'https://download.geofabrik.de/sample.osm.pbf',
                  'filename': 'sample.osm.pbf', 'size_bytes': 3,
                  'md5': '900150983cd24fb0d6963f7d28e17f72'}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            session = MagicMock()
            response = session.get.return_value.__enter__.return_value
            response.status_code = 200
            response.iter_content.return_value = [b'bad']
            with self.assertRaisesRegex(RuntimeError, 'MD5 mismatch'):
                osm.download(session, source, output, 10, 1)
            self.assertFalse((output / 'sample.osm.pbf').exists())
            self.assertFalse((output / 'sample.osm.pbf.json').exists())
            partial = output / 'sample.osm.pbf.part'
            partial.write_bytes(b'a')
            response.status_code = 206
            response.headers = {'Content-Range': 'bytes 0-2/3'}
            with self.assertRaisesRegex(RuntimeError, 'Content-Range'):
                osm.download(session, source, output, 10, 1)
            self.assertEqual(partial.read_bytes(), b'a')

    def test_resume_then_verify_existing_without_network(self):
        body = b"independent synthetic transfer payload"
        source = {"url": "https://download.geofabrik.de/test-261025.osm.pbf",
                  "filename": "test-261025.osm.pbf", "size_bytes": len(body),
                  "md5": hashlib.md5(body).hexdigest()}
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory)
            (output / (source["filename"] + ".part")).write_bytes(body[:7])
            session = MagicMock()
            response = session.get.return_value.__enter__.return_value
            response.status_code = 206
            response.headers = {"Content-Range": f"bytes 7-{len(body)-1}/{len(body)}"}
            response.iter_content.return_value = [body[7:]]
            self.assertEqual(osm.download(session, source, output, 10, 1), "downloaded")
            self.assertEqual((output / source["filename"]).read_bytes(), body)
            self.assertEqual(session.get.call_args.kwargs["headers"]["Range"], "bytes=7-")
            self.assertEqual(osm.download(session, source, output, 10, 1), "verified_existing")
            self.assertEqual(session.get.call_count, 1)


if __name__ == "__main__":
    unittest.main()
