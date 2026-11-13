"""Protect the isolated P1-only download scope without network or data transfers."""
from contextlib import redirect_stderr, redirect_stdout
import importlib.util
import io
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    "environmental", Path(__file__).parents[1] / "download_environmental.py")
assert SPEC is not None and SPEC.loader is not None
env = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(env)


class EnvironmentalDownloadTests(unittest.TestCase):
    def test_default_inventory_has_exactly_the_four_core_entries(self):
        output = Path("data/raw").resolve()
        commands = dict(env.build_commands(output, list(env.DATASETS)))
        self.assertEqual(list(commands), ["earth-climate", "earth-climate-expansion",
                                         "lunar-temperature", "lunar-illumination"])
        self.assertEqual([Path(c[1]).name for c in commands.values()],
                         ["download_terraclimate.py", "download_terraclimate.py",
                          "download_diviner_south_polar.py", "download_lunar_illumination_2016.py"])
        for command in commands.values():
            self.assertEqual(command[0], sys.executable)
            self.assertNotIn("--download", command)
        climate = commands["earth-climate"]
        self.assertIn("--project-areas", climate)
        for key in ("earth-climate", "earth-climate-expansion"):
            command = commands[key]
            self.assertEqual(command[command.index("--start-year") + 1], "2015")
            self.assertEqual(command[command.index("--end-year") + 1], "2024")
            start = command.index("--variables") + 1
            self.assertEqual(command[start:start + 5], ["tmin", "tmax", "ppt", "ws", "srad"])
        expansion = commands["earth-climate-expansion"]
        self.assertNotIn("--project-areas", expansion)
        bounds = [expansion[i + 1:i + 5] for i, flag in enumerate(expansion) if flag == "--bbox"]
        self.assertEqual(bounds, [["-117.1", "36.0", "-116.6", "36.5"],
                                  ["35.2", "29.4", "35.65", "29.8"]])
        destinations = [Path(c[c.index("--output") + 1]) for c in commands.values()]
        self.assertEqual(destinations, [output / "earth/terraclimate",
                                       output / "earth/environment_expansion/20261030/terraclimate",
                                       output / "moon/diviner", output / "moon/illumination_2016"])

    def test_lunar_selection_cannot_add_other_collections_or_formats(self):
        commands = dict(env.build_commands(Path("data/raw"), list(env.DATASETS)))
        temperature = commands["lunar-temperature"]
        self.assertEqual(temperature[2:4], ["--collections", "seasonal"])
        self.assertNotIn("--metadata-only", temperature)
        self.assertNotIn("--max-files", temperature)
        illumination = commands["lunar-illumination"]
        self.assertEqual(illumination[2:5], ["--hemisphere", "south", "--skip-img"])
        self.assertNotIn("--skip-tif", illumination)
        self.assertNotIn("both", illumination)

    def test_subset_and_transfer_controls_only_reach_selected_children(self):
        selected = ["lunar-illumination", "earth-climate-expansion"]
        commands = env.build_commands(Path("custom raw root"), selected,
                                      download=True, timeout=45, attempts=5)
        self.assertEqual([name for name, _ in commands], selected)
        for name, command in commands:
            self.assertEqual(command[-1], "--download")
            self.assertEqual(command[command.index("--timeout") + 1], "45")
            retry = "--retries" if name == "lunar-illumination" else "--attempts"
            self.assertEqual(command[command.index(retry) + 1], "5")

    def test_dry_run_does_not_spawn_processes_or_create_output(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "not created"
            with patch.object(env.subprocess, "run") as run, redirect_stdout(io.StringIO()):
                self.assertEqual(env.core_main(["--dry-run", "--download", "--output", str(output)]), 0)
            run.assert_not_called()
            self.assertFalse(output.exists())

    def test_inventory_executes_selected_commands_without_shell_or_download(self):
        with patch.object(env.subprocess, "run") as run, redirect_stdout(io.StringIO()):
            self.assertEqual(env.core_main(["--datasets", "lunar-temperature", "lunar-illumination"]), 0)
        self.assertEqual(run.call_count, 2)
        for call in run.call_args_list:
            self.assertEqual(call.kwargs, {"check": True})
            self.assertIsInstance(call.args[0], list)
            self.assertNotIn("--download", call.args[0])
            destination = Path(call.args[0][call.args[0].index("--output") + 1])
            self.assertTrue(destination.is_relative_to(Path(env.__file__).resolve().parents[1] / "data"))
            self.assertEqual(Path(call.args[0][1]).parent,
                             Path(env.__file__).resolve().parent)

    def test_failed_child_stops_remaining_jobs_and_interrupt_is_reported(self):
        failure = subprocess.CalledProcessError(7, ["failed child"])
        with patch.object(env.subprocess, "run", side_effect=failure) as run:
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(env.core_main([]), 7)
            self.assertEqual(run.call_count, 1)
        with patch.object(env.subprocess, "run", side_effect=KeyboardInterrupt):
            with redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
                self.assertEqual(env.core_main([]), 130)

    def test_default_storage_is_the_darrel_stuff_data_directory(self):
        expected = Path(env.__file__).resolve().parents[1] / "data"
        self.assertEqual(env.DEFAULT_OUTPUT, expected)
        self.assertTrue(env.DEFAULT_OUTPUT.is_absolute())
        for _, command in env.build_commands(env.DEFAULT_OUTPUT, list(env.DATASETS)):
            destination = Path(command[command.index("--output") + 1])
            self.assertTrue(destination.is_relative_to(expected))

    def test_missing_directory_is_created_before_children_and_existing_files_survive(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "missing parent" / "data"

            def child_run(command, *, check):
                self.assertTrue(check)
                self.assertTrue(output.is_dir())
                self.assertTrue(Path(command[command.index("--output") + 1]).is_relative_to(output))

            flags = ["--datasets", "lunar-illumination", "--output", str(output)]
            with patch.object(env.subprocess, "run", side_effect=child_run), redirect_stdout(io.StringIO()):
                self.assertEqual(env.core_main(flags), 0)
                sentinel = output / "existing.txt"
                sentinel.write_text("preserve", encoding="utf-8")
                self.assertEqual(env.core_main(flags), 0)
            self.assertEqual(sentinel.read_text(encoding="utf-8"), "preserve")

    def test_file_instead_of_data_directory_fails_before_children(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "data"
            output.write_text("existing file", encoding="utf-8")
            errors = io.StringIO()
            with patch.object(env.subprocess, "run") as run:
                with redirect_stdout(io.StringIO()), redirect_stderr(errors):
                    self.assertEqual(env.core_main(["--output", str(output)]), 1)
            run.assert_not_called()
            self.assertIn("Unable to create data directory", errors.getvalue())
            self.assertEqual(output.read_text(encoding="utf-8"), "existing file")

    def test_invalid_scope_or_controls_fail_before_execution(self):
        for datasets in ([], ["worldclim"], ["lunar-temperature", "lunar-temperature"]):
            with self.subTest(datasets=datasets), self.assertRaises(ValueError):
                env.build_commands(Path("data/raw"), datasets)
        for options in ({"timeout": 0}, {"attempts": -1}):
            with self.subTest(options=options), self.assertRaises(ValueError):
                env.build_commands(Path("data/raw"), list(env.DATASETS), **options)
        for flags in (["--datasets", "worldcover"], ["--attempts", "0"], ["--datasets"]):
            with patch.object(env.subprocess, "run") as run, redirect_stderr(io.StringIO()):
                with self.assertRaises(SystemExit):
                    env.core_main(flags)
            run.assert_not_called()


if __name__ == "__main__":
    unittest.main()
