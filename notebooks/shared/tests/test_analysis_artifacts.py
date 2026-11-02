"""Output ownership checks independent of the project datasets."""
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))
from notebooks.shared.analysis_artifacts import publish_analysis


class AnalysisArtifactTests(unittest.TestCase):
    def test_reports_are_disposable_and_links_follow_data(self):
        for schema in ('dict', 'list', 'outputs_sha256'):
            with self.subTest(schema=schema), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run = root / 'data/processed/analysis/example'
                run.mkdir(parents=True)
                payload = b'x,y\n1,2\n'
                (run / 'values.csv').write_bytes(payload)
                (run / 'plot.png').write_bytes(b'example image')
                (run / 'REPORT.md').write_text('[data](values.csv) ![plot](plot.png) [web](https://example.org)')
                (run / 'gallery.html').write_text('<img src="plot.png"><a href="values.csv#row">data</a>')
                outputs = {} if schema != 'list' else []
                key = 'outputs_sha256' if schema == 'outputs_sha256' else 'outputs'
                (run / 'provenance.json').write_text(json.dumps({'status': 'complete', key: outputs}))

                report = publish_analysis(root, run)
                self.assertEqual(report, root / 'reports/analysis/example')
                self.assertEqual((run / 'values.csv').read_bytes(), payload)
                self.assertFalse((run / 'plot.png').exists())
                self.assertEqual((report / 'REPORT.md').read_text(),
                                 '[data](../../../data/processed/analysis/example/values.csv) '
                                 '![plot](plot.png) [web](https://example.org)')
                self.assertIn('href="../../../data/processed/analysis/example/values.csv#row"',
                              (report / 'gallery.html').read_text())
                shutil.rmtree(report)
                record = json.loads((run / 'provenance.json').read_text())
                expected_hash = hashlib.sha256(payload).hexdigest()
                expected = ([{'path': 'values.csv', 'bytes': len(payload), 'sha256': expected_hash}]
                            if schema == 'list' else {'values.csv': expected_hash})
                self.assertEqual(record[key], expected)
                self.assertEqual(record['status'], 'complete')

    def test_collision_does_not_move_or_overwrite_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'data/processed/analysis/example'
            run.mkdir(parents=True)
            (run / 'plot.png').write_bytes(b'new')
            report = root / 'reports/analysis/example'
            report.mkdir(parents=True)
            (report / 'plot.png').write_bytes(b'old')
            with self.assertRaises(FileExistsError):
                publish_analysis(root, run)
            self.assertEqual((run / 'plot.png').read_bytes(), b'new')
            self.assertEqual((report / 'plot.png').read_bytes(), b'old')

    def test_refuses_a_directory_outside_analysis(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            with self.assertRaises(ValueError):
                publish_analysis(root, root / 'data/raw')

    def test_failed_report_publication_does_not_mark_data_complete(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            run = root / 'data/processed/analysis/example'
            run.mkdir(parents=True)
            (run / 'values.csv').write_text('x\n1\n')
            (run / 'provenance.json').write_text(json.dumps({'status': 'publishing'}))
            original_write = Path.write_text

            def fail_report_manifest(path, *args, **kwargs):
                if path == root / 'reports/analysis/example/provenance.json':
                    raise OSError('Simulated unavailable report destination')
                return original_write(path, *args, **kwargs)

            with patch.object(Path, 'write_text', fail_report_manifest), self.assertRaises(OSError):
                publish_analysis(root, run)
            self.assertEqual(json.loads((run / 'provenance.json').read_text())['status'], 'publishing')
            self.assertEqual((run / 'values.csv').read_text(), 'x\n1\n')

    def test_partial_runs_cannot_be_published(self):
        for status in (None, 'running', 'failed'):
            with self.subTest(status=status), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                run = root / 'data/processed/analysis/example'
                run.mkdir(parents=True)
                (run / 'plot.png').write_bytes(b'partial image')
                if status is not None:
                    (run / 'provenance.json').write_text(json.dumps({'status': status}))
                with self.assertRaises(ValueError):
                    publish_analysis(root, run)
                self.assertTrue((run / 'plot.png').exists())
                self.assertFalse((root / 'reports/analysis/example').exists())


if __name__ == '__main__':
    unittest.main()
