"""Independent small CF fixtures for regional download validation."""
import importlib.util
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, patch
from datetime import datetime

from scipy.io import netcdf_file

SPEC = importlib.util.spec_from_file_location(
    "terraclimate", Path(__file__).parents[1] / "download_terraclimate.py")
assert SPEC is not None and SPEC.loader is not None
tc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(tc)


class SubsetTests(unittest.TestCase):
    def test_html_response_retries_then_verifies_receipt(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            fixture = root / "fixture.nc"
            self.fixture(fixture)
            session = MagicMock()
            responses = [MagicMock(), MagicMock()]
            for response, body in zip(responses, (b"<html>temporary error</html>", fixture.read_bytes())):
                response.__enter__.return_value = response
                response.iter_content.return_value = [body]
            session.get.side_effect = responses
            bounds = (-112, 35, -112 + 1 / 12, 35 + 1 / 12)
            source = tc.request_spec("tmax", 2024, bounds)
            target = root / "download.nc"
            with patch.object(tc.time, "sleep"):
                self.assertEqual(tc.download(session, target, source, "tmax", 2024, bounds, 5, 2), "downloaded")
            self.assertEqual(session.get.call_count, 2)
            self.assertEqual(target.read_bytes(), fixture.read_bytes())
            self.assertEqual(tc.download(session, target, source, "tmax", 2024, bounds, 5, 2), "verified_existing")
            self.assertEqual(session.get.call_count, 2)
            target.write_bytes(b"corrupt")
            with self.assertRaisesRegex(ValueError, "preserved"):
                tc.download(session, target, source, "tmax", 2024, bounds, 5, 2)
            self.assertEqual(target.read_bytes(), b"corrupt")

    def fixture(self, path: Path, version: str = "V1.1", year: int = 2024,
                empty: bool = False) -> None:
        with netcdf_file(str(path), "w") as nc:
            nc.version = version
            for name, count in (("time", 12), ("lat", 2), ("lon", 2)):
                nc.createDimension(name, count)
            times = nc.createVariable("time", "d", ("time",))
            times.units = "days since 1900-01-01 00:00:00"
            times.calendar = "gregorian"
            times[:] = [(datetime(year, m, 1) - datetime(1900, 1, 1)).days for m in range(1, 13)]
            nc.createVariable("lat", "d", ("lat",))[:] = [35 + 1 / 48, 35 + 3 / 48]
            nc.createVariable("lon", "d", ("lon",))[:] = [-112 + 1 / 48, -112 + 3 / 48]
            data = nc.createVariable("tmax", "h", ("time", "lat", "lon"))
            data.units = "degC"
            data.scale_factor = 0.01
            data.add_offset = -99.0
            data._FillValue = -32768
            data[:] = -32768 if empty else 12000
            # The publisher includes a colliding legacy text attribute.
            data._attributes["dimensions"] = "lon lat time"

    def test_valid_packed_months_and_rejections(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "sample.nc"
            bounds = (-112, 35, -112 + 1 / 12, 35 + 1 / 12)
            self.fixture(path)
            before = path.read_bytes()
            result = tc.validate_netcdf(path, "tmax", 2024, bounds)
            self.assertEqual(result["shape"], [12, 2, 2])
            self.assertEqual(result["valid_values"], 48)
            self.assertEqual(path.read_bytes(), before)
            for version, year, empty in (("V1.0", 2024, False), ("V1.1", 2023, False),
                                         ("V1.1", 2024, True)):
                self.fixture(path, version, year, empty)
                with self.assertRaises(ValueError):
                    tc.validate_netcdf(path, "tmax", 2024, bounds)

    def test_request_and_box_guard(self):
        result = tc.request_spec("ppt", 2020, (-14, 28, -13, 30))
        self.assertEqual(result["params"]["time_end"], "2020-12-31T23:59:59Z")
        self.assertEqual(result["params"]["west"], -14)
        self.assertEqual(result["params"]["accept"], "netcdf")
        for bounds in ((170, 0, -170, 1), (0, 0, 1, 91), (0, 0, float("nan"), 1)):
            with self.assertRaises(ValueError):
                tc.request_spec("ppt", 2020, bounds)

    def test_catalog_preserves_historical_paths(self):
        xml = '<catalog xmlns="http://www.unidata.ucar.edu/namespaces/thredds/InvCatalog/v1.0"><dataset urlPath="TERRACLIMATE_ALL/data/TerraClimate_ppt_2024.nc"><date type="modified">2026-06-01</date></dataset></catalog>'
        self.assertEqual(tc.catalog_entries(xml), {
            "TERRACLIMATE_ALL/data/TerraClimate_ppt_2024.nc": "2026-06-01"})


if __name__ == "__main__":
    unittest.main()
