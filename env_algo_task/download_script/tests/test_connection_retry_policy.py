from contextlib import redirect_stderr, redirect_stdout
from http.client import IncompleteRead
import io
from pathlib import Path
import sys
import tempfile
from unittest.mock import MagicMock, patch
import unittest
from urllib3.exceptions import IncompleteRead as StreamIncompleteRead

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import download_environmental as support
import download_environmental as eda


class ConnectionRetryTests(unittest.TestCase):
    def setUp(self):
        support.DEFAULT_OUTPUT.mkdir(parents=True, exist_ok=True)
        self.temp = tempfile.TemporaryDirectory(prefix=".connection-retry-test-", dir=support.DEFAULT_OUTPUT)
        self.root = Path(self.temp.name).resolve()
        self.assertTrue(self.root.is_relative_to(support.DEFAULT_OUTPUT.resolve()))
        self.addCleanup(self.temp.cleanup)
        eda.STOP.clear()

    def response(self, payload, url, status=200, headers=None):
        result = MagicMock()
        result.__enter__.return_value = result
        result.url, result.status_code = url, status
        result.headers = headers or {}
        result.iter_content.return_value = [payload]
        return result

    def test_connection_classifier_uses_types_and_preserved_causes_not_message_text(self):
        connection = support.requests.exceptions.ChunkedEncodingError("broken stream", StreamIncompleteRead(3, 1))
        wrapped = RuntimeError("original helper exhausted")
        wrapped.__cause__ = connection
        self.assertTrue(support.is_connection_error(wrapped))
        self.assertTrue(support.is_connection_error(IncompleteRead(b"abc", 1)))
        self.assertTrue(support.is_connection_error(support.requests.Timeout("timeout")))
        self.assertFalse(support.is_connection_error(RuntimeError("ChunkedEncodingError in a message only")))
        self.assertFalse(support.is_connection_error(support.requests.exceptions.SSLError("certificate rejected")))
        self.assertFalse(support.is_connection_error(support.requests.HTTPError("401 login required")))
        self.assertFalse(support.is_connection_error(ValueError("bad checksum")))

    def test_default_connection_retry_stops_after_three_retries(self):
        error = support.requests.exceptions.ChunkedEncodingError("broken stream")
        operation = MagicMock(side_effect=[error] * 6 + ["finished"])
        logger = MagicMock()
        with patch.object(support.time, "sleep") as sleep, redirect_stderr(io.StringIO()), self.assertRaises(support.requests.exceptions.ChunkedEncodingError):
            support.retry_connections(operation, "fixture file", logger)
        self.assertEqual(operation.call_count, 4)
        self.assertEqual([c.args[0] for c in sleep.call_args_list], [5, 10, 20])
        self.assertEqual(logger.warning.call_count, 3)
        logger.error.assert_called_once()

    def test_optional_connection_limit_and_stop_event(self):
        operation = MagicMock(side_effect=support.requests.Timeout("offline"))
        with patch.object(support.time, "sleep"), redirect_stderr(io.StringIO()), self.assertRaises(support.requests.Timeout):
            support.retry_connections(operation, "fixture", MagicMock(), retries=2)
        self.assertEqual(operation.call_count, 3)
        stop = MagicMock()
        stop.is_set.return_value = False
        stop.wait.return_value = True
        with redirect_stderr(io.StringIO()), self.assertRaises(InterruptedError):
            support.retry_connections(operation, "fixture", MagicMock(), stop_event=stop)
        stop.wait.assert_called_once_with(5)

    def test_login_and_validation_errors_are_not_retried(self):
        for error in [support.requests.HTTPError("401 login required"),
                      support.requests.HTTPError("403 forbidden"),
                      support.requests.exceptions.SSLError("certificate failure"),
                      ValueError("checksum mismatch")]:
            operation = MagicMock(side_effect=error)
            with self.subTest(error=error), patch.object(support.time, "sleep") as sleep, self.assertRaises(type(error)):
                support.retry_connections(operation, "fixture", MagicMock())
            self.assertEqual(operation.call_count, 1)
            sleep.assert_not_called()

    def test_real_legacy_helper_incomplete_read_resumes_instead_of_skipping(self):
        payload = b"II*\x00valid TIFF fixture"
        item = {"filename": "map.TIF", "url": "https://example.test/map.TIF", "size_bytes": len(payload),
                "relative_path": "moon/lola_product90/large_area_dem/map.TIF", "format": "TIF"}
        first = self.response(payload, item["url"])
        def broken_stream(*args, **kwargs):
            yield payload[:8]
            raise support.requests.exceptions.ChunkedEncodingError("Connection broken", StreamIncompleteRead(8, len(payload) - 8))
        first.iter_content.side_effect = broken_stream
        second = self.response(payload[8:], item["url"], 206,
                               {"Content-Range": f"bytes 8-{len(payload)-1}/{len(payload)}"})
        client = MagicMock()
        client.get.side_effect = [first, second]
        with patch.object(support.time, "sleep") as sleep, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            path = support.retry_connections(
                lambda: support.download_file(client, item, self.root, 5, 1), "map.TIF", MagicMock())
        self.assertEqual(path.read_bytes(), payload)
        self.assertEqual(client.get.call_count, 2)
        self.assertEqual(client.get.call_args.kwargs["headers"], {"Range": "bytes=8-"})
        sleep.assert_called_once_with(5)

    def test_real_legacy_helper_does_not_repeat_login_even_with_five_attempts(self):
        item = {"filename": "map.TIF", "url": "https://example.test/map.TIF", "size_bytes": 20,
                "relative_path": "map.TIF", "format": "TIF"}
        denied = self.response(b"", item["url"], 401)
        denied.raise_for_status.side_effect = support.requests.HTTPError("401 login required")
        client = MagicMock()
        client.get.return_value = denied
        with patch.object(support.time, "sleep") as sleep, redirect_stderr(io.StringIO()), self.assertRaises(RuntimeError):
            support.retry_connections(lambda: support.download_file(client, item, self.root, 5, 5), "map.TIF", MagicMock())
        self.assertEqual(client.get.call_count, 1)
        sleep.assert_not_called()

    def test_threaded_worker_retries_after_batch_exhaustion_and_keeps_range(self):
        item = {"dataset": "D13", "url": "https://example.test/data.csv", "relative_path": "data.csv",
                "size_bytes": 4, "etag": '"v1"', "last_modified": None, "metadata": False}
        first = self.response(b"data", item["url"], headers={"ETag": '"v1"'})
        def broken_stream(*args, **kwargs):
            yield b"da"
            raise eda.requests.exceptions.ChunkedEncodingError("Connection broken", StreamIncompleteRead(2, 2))
        first.iter_content.side_effect = broken_stream
        second = self.response(b"ta", item["url"], 206,
                               {"ETag": '"v1"', "Content-Range": "bytes 2-3/4"})
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.side_effect = [first, second]
        args = eda.argparse.Namespace(workers=1, timeout=5, attempts=1, cookies=None, connection_retries=3)
        record = {"files": [item], "datasets": [{"id": "D13", "status": "planned"}]}
        with patch.object(eda, "session", return_value=client), patch.object(eda.STOP, "wait", return_value=False) as wait, redirect_stdout(io.StringIO()), redirect_stderr(io.StringIO()):
            self.assertEqual(eda.run_downloads(record, self.root, self.root, args), 0)
        self.assertEqual((self.root / "data.csv").read_bytes(), b"data")
        self.assertEqual(client.get.call_args.kwargs["headers"], {"Range": "bytes=2-", "If-Range": '"v1"'})
        wait.assert_called_once_with(5)
        self.assertEqual(record["status"], "complete_pilot")

    def test_eda_login_response_is_not_repeated_for_remaining_attempts(self):
        item = {"dataset": "D13", "url": "https://example.test/private.csv", "relative_path": "private.csv",
                "size_bytes": 4, "etag": None, "last_modified": None, "metadata": False}
        denied = self.response(b"", item["url"], 403)
        denied.raise_for_status.side_effect = eda.requests.HTTPError("403 login required")
        client = MagicMock()
        client.__enter__.return_value = client
        client.get.return_value = denied
        with patch.object(eda, "session", return_value=client), patch.object(eda.time, "sleep") as sleep, self.assertRaises(eda.requests.HTTPError):
            eda.transfer(item, self.root, 5, 5)
        self.assertEqual(client.get.call_count, 1)
        sleep.assert_not_called()
        self.assertFalse((self.root / "private.csv").exists())


if __name__ == "__main__":
    unittest.main()
