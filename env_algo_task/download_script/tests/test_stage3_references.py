from contextlib import redirect_stdout
import io
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as downloader


class GoldenReferenceTests(unittest.TestCase):
    def test_stage3_preview_is_offline_and_preserves_legacy_catalog(self):
        before = set(downloader.catalog())
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp) / "not_created"
            with patch.object(downloader, "session") as network, redirect_stdout(io.StringIO()):
                self.assertEqual(downloader.main(["--stage3-references", "--dry-run", "--output", str(out)]), 0)
            network.assert_not_called(); self.assertFalse(out.exists())
        self.assertEqual(set(downloader.catalog()), before)
        self.assertEqual({r["id"] for r in downloader.STAGE3_SOURCES}, {"S01", "S02", "S03"})

    def test_pdf_validation_rejects_non_pdf(self):
        with tempfile.TemporaryDirectory() as tmp:
            file = Path(tmp) / "reference.pdf"
            item = {"relative_path": "reference.pdf", "dataset": "S02"}
            file.write_bytes(b"not a PDF")
            with self.assertRaises(ValueError): downloader.validate_payload(file, item)
            file.write_bytes(b"%PDF-1.7\nfixture")
            downloader.validate_payload(file, item)


if __name__ == "__main__": unittest.main()
