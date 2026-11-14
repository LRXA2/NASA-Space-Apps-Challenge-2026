"""The upload driver must give the same output as Darrel's command line, and readable errors."""

import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
SCORER = ROOT / "env_algo_task" / "env_pipeline"
sys.path.insert(0, str(SCORER))
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from score_upload import score  # noqa: E402

SAMPLE = SCORER / "sample_input.csv"


class ScoreUploadTests(unittest.TestCase):
    def test_sample_input_matches_the_command_line_byte_for_byte(self) -> None:
        with tempfile.TemporaryDirectory() as folder:
            reference = Path(folder) / "cli.csv"
            subprocess.run([sys.executable, str(SCORER / "env_pipeline.py"), "--input", str(SAMPLE),
                            "--output", str(reference), "--detailed"], check=True, capture_output=True)
            result = json.loads(score(SAMPLE.read_text(encoding="utf-8-sig"), str(SCORER)))
            self.assertTrue(result["ok"], result.get("error"))
            self.assertEqual(result["csv"], reference.read_text(encoding="utf-8"))
        self.assertEqual(len(result["scenarios"]), 83)
        self.assertTrue(all(row["kind"] == "uploaded" for row in result["scenarios"]))
        # Detailed mode: every row carries its gate checks, with Pass/Fail rather than Passed/Failed.
        statuses = {g["status"] for row in result["scenarios"] for a in ("operations", "survival") for g in row[a]["gates"]}
        self.assertLessEqual(statuses, {"Pass", "Fail", "Unknown"})
        self.assertIn("Fail", statuses)

    def test_invalid_uploads_return_the_scorer_message(self) -> None:
        header, first, *_ = SAMPLE.read_text(encoding="utf-8-sig").splitlines()
        cases = {
            "duplicate ID": f"{header}\n{first}\n{first}\n",
            "unregistered column": f"{header},surprise\n{first},1\n",
            "ragged row": f"{header}\n{first},extra\n",
            "no rows": f"{header}\n",
        }
        for name, text in cases.items():
            with self.subTest(name):
                result = json.loads(score(text, str(SCORER)))
                self.assertFalse(result["ok"])
                self.assertTrue(result["error"])


if __name__ == "__main__":
    unittest.main()
