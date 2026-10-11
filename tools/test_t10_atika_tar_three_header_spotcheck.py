"""Synthetic-only regression for speculative 3-header TAR sparse probe."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as fixtures
import t10_atika_tar_order_hypotheses as order
import t10_atika_tar_three_header_spotcheck as spot
import t10_atika_tar_header_walk as tar_walk


def tar_header(name, size):
    info = tarfile.TarInfo(name=name)
    info.size = size
    return info.tobuf(format=tarfile.USTAR_FORMAT)[:512]


class PureSparseChecks(unittest.TestCase):
    def test_model_3_positions_are_distinct_aligned(self):
        rows = [(f"data/M1/a{i:04}.wav", 44 + i) for i in range(40)]
        archive_length = sum(512 + spot.ceil_to(sz, 512) for _, sz in rows)
        archive_length = spot.ceil_to(archive_length + 1024, 10240)
        candidates = spot.candidates_from_rows(rows, archive_length)
        self.assertEqual(len(candidates), 3)
        self.assertEqual([p[0] for p in candidates], [10, 20, 30])
        self.assertTrue(all(p[1] % 512 == 0 for p in candidates))

    def test_flat_model_mismatch_rejected(self):
        rows = [(f"data/M1/a{i:04}.wav", 44) for i in range(35)]
        with self.assertRaisesRegex(ValueError, "disagrees"):
            spot.candidates_from_rows(rows, 907765760)

    def test_duplicate_metadata_rejected(self):
        rows = [("data/M1/a.wav", 44)] * 35
        with self.assertRaisesRegex(ValueError, "Nonunique"):
            spot.candidates_from_rows(rows, 10240)

    def test_no_unbounded_header_calls_success(self):
        entries = [(10, 5120, "a.wav", 256), (20, 10240, "b.wav", 513),
                   (30, 20480, "c.wav", 44)]
        with patch.object(tar_walk, "fetch_header", side_effect=lambda off: {
                5120: tar_header("a.wav", 256), 10240: tar_header("b.wav", 513),
                20480: tar_header("c.wav", 44)}[off]) as mocked:
            out = spot.check_headers(entries)
        self.assertEqual(mocked.call_count, 3)
        self.assertEqual(out["full_name_and_size_headers_matching_hypothesis"], 3)
        self.assertTrue(out["all_three_sparse_headers_match"])
        self.assertFalse(out["member_order_verified"])

    def test_first_name_mismatch_stops_after_one(self):
        entries = [(10, 5120, "a.wav", 256), (20, 10240, "b.wav", 513),
                   (30, 20480, "c.wav", 44)]
        with patch.object(tar_walk, "fetch_header", return_value=tar_header("other.wav", 256)) as f:
            out = spot.check_headers(entries)
        self.assertEqual(f.call_count, 1)
        self.assertEqual(out["result"], "HYPOTHESIS_MISMATCH_STOP")

    def test_pax_header_or_zero_rejected(self):
        entries = [(10, 5120, "a.wav", 256), (20, 10240, "b.wav", 513),
                   (30, 20480, "c.wav", 44)]
        with patch.object(tar_walk, "fetch_header", return_value=bytes(512)):
            self.assertEqual(spot.check_headers(entries)["headers_attempted"], 1)

    def test_three_distinct_positions_required(self):
        with self.assertRaisesRegex(ValueError, "Three distinct"):
            spot.check_headers([])
        with self.assertRaisesRegex(ValueError, "Three distinct"):
            spot.check_headers([(1, 0, "a.wav", 44)] * 3)

    def test_invalid_offset_rejected_before_network(self):
        rows = [(1, 1, "a.wav", 44), (2, 1024, "b.wav", 44),
                (3, 2048, "c.wav", 44)]
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("network attempted")):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                spot.check_headers(rows)


class SyntheticFrozenWorkspace(unittest.TestCase):
    make_files = fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        self.sorted_sizes = sorted(self.rows, key=lambda row: row["audio_path"])
        self.first_size = int(self.sorted_sizes[0]["file_size_bytes"])
        self.end_six = sum(512 + spot.ceil_to(int(row["file_size_bytes"]), 512)
                           for row in self.sorted_sizes[:6])
        self.first = patch.object(order, "OBSERVED_FIRST_MEMBER_SIZE", self.first_size)
        self.sixth = patch.object(order, "OBSERVED_SIX_HEADER_NEXT_OFFSET", self.end_six)
        self.first.start()
        self.sixth.start()
        self.addCleanup(self.first.stop)
        self.addCleanup(self.sixth.stop)
        expected_flat = sum(512 + spot.ceil_to(int(row["file_size_bytes"]), 512)
                            for row in self.rows)
        tar_length = spot.ceil_to(expected_flat + 1024, 10240)
        tar_patch = patch.object(tar_walk, "EXPECTED_TAR_BYTES", tar_length)
        tar_patch.start()
        self.addCleanup(tar_patch.stop)

    def test_offline_plan_no_http_no_mutation(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")):
            slots, report = spot.plan(self.workspace)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.workspace.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(len(slots), 3)
        self.assertFalse(report["selected_30_wav_offsets_verified"])

    def test_default_cli_never_fetches_header(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["spot", "--workspace", str(self.workspace)]), redirect_stdout(out), patch.object(tar_walk, "fetch_header", side_effect=AssertionError("NO HTTP")):
            self.assertEqual(spot.main(), 0)
        self.assertIn("OFFLINE_PREFLIGHT_ONLY_NO_HTTP", out.getvalue())
        self.assertNotIn("data/fictional", out.getvalue())
        self.assertNotIn("fixture text", out.getvalue())

    def test_explicit_cli_three_only(self):
        candidates, _ = spot.plan(self.workspace)
        by_offset = {off: tar_header(name, sz) for _, off, name, sz in candidates}
        with patch.object(sys, "argv", ["spot", "--workspace", str(self.workspace),
                "--execute-three-headers"]), redirect_stdout(io.StringIO()), patch.object(tar_walk, "fetch_header", side_effect=lambda off: by_offset[off]) as fetched:
            self.assertEqual(spot.main(), 0)
        self.assertEqual(fetched.call_count, 3)

    def test_cli_range_not_honored_yields_exit2(self):
        with patch.object(sys, "argv", ["spot", "--workspace", str(self.workspace),
                "--execute-three-headers"]), redirect_stderr(io.StringIO()), patch.object(tar_walk, "fetch_header", side_effect=tar_walk.RangeNotHonored("HTTP 200")) as fetched:
            self.assertEqual(spot.main(), 2)
        self.assertEqual(fetched.call_count, 1)

    def test_private_selection_mismatch_blocks_before_http(self):
        f = self.workspace / tar_walk.SELECTION_NAME
        f.write_bytes(f.read_bytes() + b"broken")
        with patch.object(tar_walk, "fetch_header", side_effect=AssertionError("network")):
            with self.assertRaises((ValueError, TypeError)):
                spot.plan(self.workspace)


if __name__ == "__main__":
    unittest.main()
