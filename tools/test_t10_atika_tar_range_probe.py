"""Synthetic-only tests for a bounded public TAR HTTP byte-range probe."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_atika_tar_range_probe import (
    CATEGORY, EXPECTED_TAR_BYTES, MAX_READ_BYTES, PROBE_BYTES,
    TAR_URL, inspect_range_response, main, probe,
)


def first_tar_header() -> bytes:
    info = tarfile.TarInfo(name="anonymous-safe-fixture/sample.wav")
    info.size = 32044
    return info.tobuf(format=tarfile.USTAR_FORMAT)


class FakeResponse:
    def __init__(self, status=206, content_range=None, body=None, final_url=None,
                 content_length=None):
        self.status = status
        self.headers = {
            "Content-Range": content_range if content_range is not None else
            f"bytes 0-511/{EXPECTED_TAR_BYTES}",
            "Content-Length": str(PROBE_BYTES) if content_length is None else content_length,
        }
        self.url = final_url or "https://cas-bridge.xethub.hf.co/mock"
        self.data = io.BytesIO(first_tar_header() if body is None else body)
        self.bytes_read = 0
        self.read_calls = 0

    def geturl(self):
        return self.url

    def read(self, limit):
        self.read_calls += 1
        assert limit <= MAX_READ_BYTES, "No streaming or unbounded reads allowed"
        content = self.data.read(limit)
        self.bytes_read += len(content)
        return content

    def __enter__(self):
        return self

    def __exit__(self, *_):
        return False


class AtikaTarRangeProbeTests(unittest.TestCase):
    def test_pinned_tar_and_byte_limit(self):
        self.assertEqual(CATEGORY, "Imperative")
        self.assertEqual(EXPECTED_TAR_BYTES, 907765760)
        self.assertEqual(MAX_READ_BYTES, 513)
        self.assertIn("/resolve/", TAR_URL)
        self.assertTrue(TAR_URL.endswith("/Imperative.tar"))

    def test_valid_206_and_tar_first_header_only(self):
        response = FakeResponse()
        data = inspect_range_response(response)
        self.assertEqual(data["network_response_status"], 206)
        self.assertTrue(data["tar_range_206_verified"])
        self.assertEqual(data["first_member_data_bytes_declared_in_tar_header"], 32044)
        self.assertEqual(response.bytes_read, 512)
        self.assertEqual(response.read_calls, 1)
        self.assertEqual(data["audio_files_recovered"], 0)
        self.assertFalse(data["first_member_name_displayed"])
        self.assertEqual(data["CP4"], "BLOCKED")
        self.assertNotIn("anonymous-safe-fixture", json.dumps(data))

    def test_200_full_archive_response_never_reads_body(self):
        response = FakeResponse(status=200, body=b"Z" * 100_000)
        data = inspect_range_response(response)
        self.assertFalse(data["tar_range_206_verified"])
        self.assertEqual(data["result"], "RANGE_NOT_HONORED_NO_BODY_READ")
        self.assertEqual(response.bytes_read, 0)
        self.assertEqual(response.read_calls, 0)

    def test_206_must_have_exact_total_size(self):
        for cr in ("bytes 0-511/907765761", "bytes 0-512/907765760",
                   "bytes */907765760", "other junk"):
            with self.subTest(content_range=cr):
                response = FakeResponse(content_range=cr)
                with self.assertRaisesRegex(ValueError, "Content-Range"):
                    inspect_range_response(response)
                self.assertEqual(response.read_calls, 0)

    def test_206_wrong_content_length_rejected_before_body_read(self):
        response = FakeResponse(content_length="1024")
        with self.assertRaisesRegex(ValueError, "Content-Length"):
            inspect_range_response(response)
        self.assertEqual(response.read_calls, 0)

    def test_206_oversized_body_rejected_after_513_bytes_max(self):
        response = FakeResponse(body=first_tar_header() + b"x")
        with self.assertRaisesRegex(ValueError, "exactly 512"):
            inspect_range_response(response)
        self.assertEqual(response.bytes_read, 513)

    def test_206_invalid_tar_header_rejected(self):
        response = FakeResponse(body=b"\x00" * 512)
        with self.assertRaises(ValueError):
            inspect_range_response(response)
        self.assertEqual(response.bytes_read, 512)

    def test_insecure_final_redirect_refused_without_body_read(self):
        response = FakeResponse(final_url="http://insecure.invalid/tar")
        with self.assertRaisesRegex(ValueError, "Insecure"):
            inspect_range_response(response)
        self.assertEqual(response.read_calls, 0)

    def test_probe_sends_one_http_range_request_and_no_other_byte_data(self):
        response = FakeResponse()
        with patch("t10_atika_tar_range_probe.urllib.request.urlopen",
                   return_value=response) as request:
            result = probe()
        self.assertTrue(result["tar_range_206_verified"])
        self.assertEqual(request.call_count, 1)
        req = request.call_args.args[0]
        self.assertEqual(req.headers["Range"], "bytes=0-511")
        self.assertEqual(req.headers["Accept-encoding"], "identity")
        self.assertEqual(req.get_method(), "GET")
        self.assertEqual(response.bytes_read, 512)

    def test_cli_200_returns_nonzero_without_body(self):
        response = FakeResponse(status=200, body=b"x" * 100_000)
        with patch("t10_atika_tar_range_probe.urllib.request.urlopen",
                   return_value=response), patch.object(
                       sys, "argv", ["t10_atika_tar_range_probe.py"]
                   ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 2)
        self.assertIn("RANGE_NOT_HONORED_NO_BODY_READ", output.getvalue())
        self.assertEqual(response.read_calls, 0)

    def test_cli_206_produces_no_local_audio_or_model_actions(self):
        response = FakeResponse()
        with patch("t10_atika_tar_range_probe.urllib.request.urlopen",
                   return_value=response), patch.object(
                       sys, "argv", ["t10_atika_tar_range_probe.py"]
                   ), redirect_stdout(io.StringIO()) as output:
            self.assertEqual(main(), 0)
        text = output.getvalue()
        self.assertIn("NO FULL TAR | NO WAV SAVED | NO MODEL DOWNLOAD", text)
        self.assertIn("CP4 BLOCKED", text)
        self.assertNotIn("anonymous-safe-fixture", text)

    def test_cli_fails_closed_on_unexpected_content_range(self):
        response = FakeResponse(content_range="bytes 0-511/5")
        with patch("t10_atika_tar_range_probe.urllib.request.urlopen",
                   return_value=response), patch.object(
                       sys, "argv", ["t10_atika_tar_range_probe.py"]
                   ), redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
