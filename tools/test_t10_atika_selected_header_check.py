"""Synthetic tests for explicit bounded selected-header checks, no live HTTP."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as fixtures
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
import t10_atika_selected_header_check as check
import t10_atika_selected_header_preflight as selected
from t10_atika_tar_layout_budget import ceil_to


def tar_header(name: str, size: int, is_file: bool = True) -> bytes:
    info = tarfile.TarInfo(name)
    info.size = size
    if not is_file:
        info.type = tarfile.DIRTYPE
        info.size = 0
    return info.tobuf(format=tarfile.USTAR_FORMAT)[:512]


def candidates():
    return [(i, i * 1024, f"data/test/f{i:02d}.wav", 44+i)
            for i in range(30)]


class PureBoundedRemoteHeaderChecks(unittest.TestCase):
    def test_limit_five_only_five_requests(self):
        inp = candidates()
        headers = {off: tar_header(name, sz) for _, off, name, sz in inp}
        with patch.object(tar_walk, "fetch_header", side_effect=lambda off: headers[off]) as req:
            report = check.validate_headers(inp, 5)
        self.assertEqual(req.call_count, 5)
        self.assertEqual(report["exact_name_size_and_type_matches"], 5)
        self.assertTrue(report["all_requested_selected_headers_match"])
        self.assertFalse(report["all_30_selected_headers_match"])

    def test_full_30_header_cap_only_explicit(self):
        inp = candidates()
        headers = {off: tar_header(name, sz) for _, off, name, sz in inp}
        with patch.object(tar_walk, "fetch_header", side_effect=lambda off: headers[off]) as req:
            report = check.validate_headers(inp, 30)
        self.assertEqual(req.call_count, 30)
        self.assertTrue(report["all_30_selected_headers_match"])
        self.assertFalse(report["full_tar_order_verified"])
        self.assertFalse(report["audio_integrity_verified"])

    def test_first_name_mismatch_stops_after_one_request(self):
        with patch.object(tar_walk, "fetch_header",
                          return_value=tar_header("data/wrong.wav", 44)) as req:
            report = check.validate_headers(candidates(), 30)
        self.assertEqual(req.call_count, 1)
        self.assertEqual(report["exact_name_size_and_type_matches"], 0)
        self.assertEqual(report["result"], "SELECTED_HEADER_MISMATCH_STOP")

    def test_wrong_size_stops(self):
        with patch.object(tar_walk, "fetch_header",
                          return_value=tar_header("data/test/f00.wav", 99)) as req:
            report = check.validate_headers(candidates(), 5)
        self.assertEqual(req.call_count, 1)
        self.assertFalse(report["all_requested_selected_headers_match"])

    def test_nonfile_member_rejected(self):
        with patch.object(tar_walk, "fetch_header",
                          return_value=tar_header("data/test/f00.wav", 44, False)) as req:
            report = check.validate_headers(candidates(), 5)
        self.assertEqual(req.call_count, 1)
        self.assertFalse(report["all_requested_selected_headers_match"])

    def test_zero_or_invalid_header_stops(self):
        with patch.object(tar_walk, "fetch_header", return_value=bytes(512)) as req:
            report = check.validate_headers(candidates(), 5)
        self.assertEqual(req.call_count, 1)
        self.assertEqual(report["exact_name_size_and_type_matches"], 0)

    def test_wrong_candidate_offset_rejected_before_network(self):
        inp = candidates()
        inp[2] = (2, 1025, inp[2][2], inp[2][3])
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                check.validate_headers(inp, 5)

    def test_repeated_candidate_name_rejected_before_network(self):
        inp = candidates()
        inp[3] = (3, 3072, inp[2][2], inp[3][3])
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                check.validate_headers(inp, 5)

    def test_31_requests_rejected_before_network(self):
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            with self.assertRaisesRegex(ValueError, "Invalid bounded"):
                check.validate_headers(candidates(), 31)


class FrozenSyntheticWorkspaceChecks(unittest.TestCase):
    make_files = fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        source_sorted = sorted(self.rows, key=lambda r: r["audio_path"])
        p1 = patch.object(order, "OBSERVED_FIRST_MEMBER_SIZE",
                          int(source_sorted[0]["file_size_bytes"]))
        p2 = patch.object(
            order, "OBSERVED_SIX_HEADER_NEXT_OFFSET",
            sum(512 + ceil_to(int(row["file_size_bytes"]), 512)
                for row in source_sorted[:6])
        )
        size = ceil_to(
            1024 + sum(512 + ceil_to(int(row["file_size_bytes"]), 512)
                       for row in self.rows), 10240
        )
        p3 = patch.object(tar_walk, "EXPECTED_TAR_BYTES", size)
        for p in (p1, p2, p3):
            p.start()
            self.addCleanup(p.stop)

    def test_default_cli_offline_no_header_fetch(self):
        out = io.StringIO()
        with patch.object(sys, "argv", [
            "selected-check", "--workspace", str(self.workspace),
        ]), redirect_stdout(out), patch.object(
                tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            self.assertEqual(check.main(), 0)
        text = out.getvalue()
        self.assertIn("OFFLINE_PREFLIGHT_ONLY_NO_HTTP", text)
        self.assertIn('"network_requests_executed": 0', text)
        self.assertNotIn("data/fictional", text)
        self.assertNotIn("fixture text", text)

    def test_preparation_never_modifies_frozen_files(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("NETWORK")):
            actual, report = check.prepare(self.workspace)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.workspace.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(len(actual), 30)
        self.assertEqual(report["network_requests_executed"], 0)

    def test_opt_in_cli_five_only_with_mock(self):
        actual, _ = check.prepare(self.workspace)
        by_offset = {offset: tar_header(name, size)
                     for _, offset, name, size in actual}
        out = io.StringIO()
        with patch.object(sys, "argv", [
            "selected-check", "--workspace", str(self.workspace),
            "--execute-selected-headers", "--limit", "5",
        ]), redirect_stdout(out), patch.object(
            tar_walk, "fetch_header",
            side_effect=lambda offset: by_offset[offset]
        ) as remote:
            self.assertEqual(check.main(), 0)
        self.assertEqual(remote.call_count, 5)
        self.assertIn('"actual_selected_header_matches": 5', out.getvalue())
        self.assertNotIn("data/fictional", out.getvalue())

    def test_opt_in_range_ignored_exits_two(self):
        with patch.object(sys, "argv", [
            "selected-check", "--workspace", str(self.workspace),
            "--execute-selected-headers",
        ]), redirect_stderr(io.StringIO()), patch.object(
            tar_walk, "fetch_header",
            side_effect=tar_walk.RangeNotHonored("HTTP 200")
        ) as remote:
            self.assertEqual(check.main(), 2)
        self.assertEqual(remote.call_count, 1)

    def test_tampered_csv_refused_without_fetch(self):
        f = self.workspace / selected.METADATA_FILENAME
        f.write_bytes(f.read_bytes() + b"tampered")
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            with self.assertRaises((ValueError, TypeError)):
                check.prepare(self.workspace)

    def test_tampered_selection_refused_without_fetch(self):
        f = self.workspace / tar_walk.SELECTION_NAME
        f.write_bytes(f.read_bytes() + b"tampered")
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NETWORK")):
            with self.assertRaises((ValueError, TypeError)):
                check.prepare(self.workspace)


if __name__ == "__main__":
    unittest.main()
