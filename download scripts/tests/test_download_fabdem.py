"""Selection and transfer contracts; no requests to external data servers."""

import sys
import unittest
from pathlib import Path
import io
import tempfile
import threading
import zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_fabdem import Archive, archive_bounds, select_archives, download_archive, parse_catalog


class SelectionTests(unittest.TestCase):
    def test_official_listing_format_ignores_external_archive_links(self):
        filename = "N00E000-N10E010_FABDEM_V1-2.zip"
        html = f'<table><tr><td></td><td><a href="{filename}">{filename}</a></td><td>2022-12-12T17:15:15Z</td><td>1146164795</td></tr><tr><td><a href="https://example.org/N00E010-N10E020_FABDEM_V1-2.zip">other</a></td><td>200</td></tr></table>'
        entries = parse_catalog(html)
        self.assertEqual(len(entries), 1)
        self.assertEqual(entries[0].size_bytes, 1146164795)
        self.assertEqual(entries[0].url, "https://data.bris.ac.uk/datasets/s5hqmjcdj8yo2ibzi9b4ew3sn/" + filename)

    def test_signed_coordinates_and_dateline_archive(self):
        self.assertEqual(archive_bounds("S30W070-S20W060_FABDEM_V1-2.zip"), (-70, -30, -60, -20))
        self.assertEqual(archive_bounds("N00E170-N10W180_FABDEM_V1-2.zip"), (170, 0, 180, 10))

    def test_union_excludes_edge_touch_and_deduplicates(self):
        west = Archive("west.zip", "https://example.org/west.zip", 100, (-70, -30, -60, -20))
        east = Archive("east.zip", "https://example.org/east.zip", 100, (-60, -30, -50, -20))
        boxes = [(-69, -24, -60, -23), (-68, -25, -67, -24)]
        self.assertEqual(select_archives([west, east], boxes), [west])


class TransferTests(unittest.TestCase):
    def setUp(self):
        content = io.BytesIO()
        with zipfile.ZipFile(content, "w") as archive:
            archive.writestr("sample.tif", b"known test payload" * 100)
        self.body = content.getvalue()
        self.mode = "resume"
        self.requests_seen = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requested = self.headers.get("Range")
                owner.requests_seen.append(requested)
                start = int(requested.removeprefix("bytes=").removesuffix("-")) if requested else 0
                if requested and owner.mode != "ignore":
                    self.send_response(206)
                    advertised_start = start + 1 if owner.mode == "wrong" else start
                    self.send_header("Content-Range", f"bytes {advertised_start}-{len(owner.body)-1}/{len(owner.body)}")
                else:
                    start = 0
                    self.send_response(200)
                payload = owner.body[start:]
                self.send_header("Content-Length", str(len(payload)))
                self.end_headers()
                self.wfile.write(payload)

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.session = requests.Session()
        self.archive = Archive("sample.zip", f"http://127.0.0.1:{self.server.server_port}/sample.zip", len(self.body), (0, 0, 10, 10))

    def tearDown(self):
        self.session.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def test_resume_and_range_ignored_both_produce_original_bytes(self):
        for mode in ("resume", "ignore"):
            with self.subTest(mode=mode):
                self.mode = mode
                destination = self.folder / "sample.zip"
                destination.unlink(missing_ok=True)
                (self.folder / "sample.zip.part").write_bytes(self.body[:37])
                result = download_archive(self.session, self.archive, self.folder, attempts=1)
                self.assertEqual(result.read_bytes(), self.body)
                self.assertEqual(self.requests_seen[-1], "bytes=37-")
                self.assertFalse((self.folder / "sample.zip.part").exists())

    def test_wrong_range_rejected_without_changing_partial(self):
        self.mode = "wrong"
        partial = self.folder / "sample.zip.part"
        partial.write_bytes(self.body[:37])
        with self.assertRaisesRegex(RuntimeError, "Content-Range"):
            download_archive(self.session, self.archive, self.folder, attempts=1)
        self.assertEqual(partial.read_bytes(), self.body[:37])
        self.assertFalse((self.folder / "sample.zip").exists())

    def test_existing_corrupt_file_is_preserved_and_rejected(self):
        final = self.folder / "sample.zip"
        corrupted = b"X" * len(self.body)
        final.write_bytes(corrupted)
        with self.assertRaisesRegex(RuntimeError, "Invalid ZIP"):
            download_archive(self.session, self.archive, self.folder, attempts=1)
        self.assertEqual(final.read_bytes(), corrupted)
        self.assertEqual(self.requests_seen, [])

    def test_complete_partial_promoted_without_network(self):
        (self.folder / "sample.zip.part").write_bytes(self.body)
        result = download_archive(self.session, self.archive, self.folder, attempts=1)
        self.assertEqual(result.read_bytes(), self.body)
        self.assertEqual(self.requests_seen, [])


if __name__ == "__main__":
    unittest.main()
