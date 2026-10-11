"""Synthetic-only TAR arithmetic tests; never authorize WAV acquisition."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_atika_tar_layout_budget import (
    theoretical_layout, layout_budget, main, ceil_to,
)
import test_t10_atika_acquisition_budget as _budget_fixtures
from t10_atika_tar_header_walk import SELECTION_NAME
from t10_public_id_corpus import METADATA_FILENAME


class TarLayoutSyntheticTests(unittest.TestCase):
    def test_padding_exact_boundary(self):
        self.assertEqual(ceil_to(512, 512), 512)
        self.assertEqual(ceil_to(513, 512), 1024)

    def test_minimum_math_and_record_example(self):
        out = theoretical_layout([512, 513], 10240)
        self.assertEqual(out["hypothetical_one_header_per_wav_bytes"], 1024)
        self.assertEqual(out["wav_512_alignment_padding_bytes"], 511)
        self.assertEqual(out["hypothetical_all_wav_members_end_bytes"], 2560)
        self.assertEqual(out["hypothetical_minimum_including_two_end_blocks_bytes"], 3584)
        self.assertTrue(out["published_archive_matches_flat_10240_example"])
        self.assertFalse(out["wav_offsets_verified"])

    def test_matching_total_never_proves_layout(self):
        out = theoretical_layout([100000] * 20, 2048000)
        self.assertFalse(out["archive_layout_proven"])
        self.assertFalse(out["wav_member_order_proven"])

    def test_too_short_archive_is_visible_not_approved(self):
        out = theoretical_layout([9000], 1024)
        self.assertFalse(out["published_archive_at_least_theoretical_minimum"])
        self.assertLess(out["archive_minus_hypothetical_minimum_bytes"], 0)
        self.assertFalse(out["wav_offsets_verified"])

    def test_invalid_sizes_and_empty_rejected(self):
        for sizes in ([], [0], [True], [43], [10000001]):
            with self.subTest(sizes=sizes), self.assertRaises(ValueError):
                theoretical_layout(sizes, 10240)

    def test_invalid_archive_rejected(self):
        for length in (0, 123, True, -512):
            with self.subTest(length=length), self.assertRaises(ValueError):
                theoretical_layout([44], length)


class TarLayoutPinnedWorkspaceTests(unittest.TestCase):
    # Reuse synthetic fixtures, never fetching public audio or private records.
    make_files = _budget_fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = _budget_fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        _budget_fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)

    def test_aggregate_and_no_offset_claim(self):
        out = layout_budget(self.workspace)
        self.assertEqual(out["selected_metadata_count_unchanged"], 30)
        self.assertEqual(out["tar_layout_arithmetic"]["category_wav_count"], 35)
        self.assertFalse(out["per_wav_offset_index_available"])
        self.assertEqual(out["CP4"], "BLOCKED")

    def test_readonly_private_files_unchanged(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.workspace.iterdir()}
        layout_budget(self.workspace)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.workspace.iterdir()}
        self.assertEqual(before, after)

    def test_zero_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("NO NETWORK")):
            layout_budget(self.workspace)

    def test_mismatched_csv_rejected(self):
        csv_file = self.workspace / METADATA_FILENAME
        csv_file.write_bytes(csv_file.read_bytes() + b"altered")
        with self.assertRaisesRegex(ValueError, "digest"):
            layout_budget(self.workspace)

    def test_missing_selection_rejected(self):
        (self.workspace / SELECTION_NAME).unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            layout_budget(self.workspace)

    def test_cli_no_paths_or_transcripts(self):
        out = io.StringIO()
        with patch.object(sys, "argv", ["script", "--workspace", str(self.workspace)]), redirect_stdout(out):
            self.assertEqual(main(), 0)
        self.assertNotIn("data/fictional", out.getvalue())
        self.assertNotIn("fixture text", out.getvalue())
        self.assertIn("NO OFFSET CLAIM", out.getvalue())


if __name__ == "__main__":
    unittest.main()
