"""WorldCover catalog and resumable transfer contracts; local HTTP only."""

import sys
import unittest
from pathlib import Path
import json
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import requests

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from download_worldcover import Tile, parse_catalog_page, download_tile


class CatalogTests(unittest.TestCase):
    def test_s3_page_preserves_etag_and_continuation(self):
        # Object naming and fields follow ESA's public S3 ListObjectsV2 response.
        xml = '''<ListBucketResult xmlns="http://s3.amazonaws.com/doc/2006-03-01/">
        <IsTruncated>true</IsTruncated><NextContinuationToken>next+page==</NextContinuationToken>
        <Contents><Key>v200/2021/map/ESA_WorldCover_10m_2021_v200_S24W069_Map.tif</Key>
        <Size>12345</Size><ETag>"abcdef-2"</ETag></Contents></ListBucketResult>'''
        tiles, token = parse_catalog_page(xml)
        self.assertEqual(token, "next+page==")
        self.assertEqual(tiles[0].bounds, (-69, -24, -66, -21))
        self.assertEqual(tiles[0].etag, '"abcdef-2"')
        self.assertEqual(tiles[0].size_bytes, 12345)


class TransferTests(unittest.TestCase):
    def setUp(self):
        # Header smoke checking is intentional; raster decoding is outside this downloader.
        self.body = b"II\x2a\x00" + b"synthetic-transfer-payload" * 40
        self.mode = "resume"
        self.seen = []
        owner = self

        class Handler(BaseHTTPRequestHandler):
            def do_GET(self):
                requested = self.headers.get("Range")
                owner.seen.append((requested, self.headers.get("If-Match")))
                start = int(requested[6:-1]) if requested else 0
                if owner.mode == "changed":
                    self.send_response(412)
                    self.end_headers()
                    return
                if requested and owner.mode != "ignore":
                    self.send_response(206)
                    self.send_header("Content-Range", f"bytes {start}-{len(owner.body)-1}/{len(owner.body)}")
                else:
                    start = 0
                    self.send_response(200)
                self.send_header("ETag", '"source-v1"')
                self.send_header("Content-Length", str(len(owner.body) - start))
                self.end_headers()
                self.wfile.write(owner.body[start:])

            def log_message(self, format, *args):
                pass

        self.server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.temp = tempfile.TemporaryDirectory()
        self.folder = Path(self.temp.name)
        self.session = requests.Session()
        self.tile = Tile("sample.tif", f"http://127.0.0.1:{self.server.server_port}/sample.tif", len(self.body), '"source-v1"', (0, 0, 3, 3))

    def tearDown(self):
        self.session.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join()
        self.temp.cleanup()

    def prepare_partial(self):
        (self.folder / "sample.tif.part").write_bytes(self.body[:17])
        (self.folder / "sample.tif.part.json").write_text(json.dumps({"url": self.tile.url, "size_bytes": len(self.body), "etag": '"source-v1"'}))

    def test_resume_then_skip_verified_existing(self):
        self.prepare_partial()
        result = download_tile(self.session, self.tile, self.folder, attempts=1)
        self.assertEqual(result.read_bytes(), self.body)
        self.assertEqual(self.seen, [("bytes=17-", '"source-v1"')])
        download_tile(self.session, self.tile, self.folder, attempts=1)
        self.assertEqual(len(self.seen), 1)

    def test_ignored_range_restarts_without_duplicate_bytes(self):
        self.mode = "ignore"
        self.prepare_partial()
        result = download_tile(self.session, self.tile, self.folder, attempts=1)
        self.assertEqual(result.read_bytes(), self.body)

    def test_changed_remote_preserves_partial(self):
        self.mode = "changed"
        self.prepare_partial()
        with self.assertRaisesRegex(RuntimeError, "412"):
            download_tile(self.session, self.tile, self.folder, attempts=1)
        self.assertEqual((self.folder / "sample.tif.part").read_bytes(), self.body[:17])
        self.assertFalse((self.folder / "sample.tif").exists())

    def test_html_response_is_not_published_as_tiff(self):
        self.body = b"<html>" + self.body[6:]
        with self.assertRaisesRegex(RuntimeError, "TIFF header"):
            download_tile(self.session, self.tile, self.folder, attempts=1)
        self.assertFalse((self.folder / "sample.tif").exists())


if __name__ == "__main__":
    unittest.main()
