"""T10 publisher CSV ordering hypotheses: offline synthetic tests only."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import unittest
from contextlib import redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as _fixtures
from t10_atika_tar_order_hypotheses import assess_prefix, analyze_order_hypotheses, main
from t10_public_id_corpus import METADATA_FILENAME


class PureOrderHypothesisTests(unittest.TestCase):
    def test_consistent_six_member_prefix_not_verified(self):
        r = [("a%d" % i, 100) for i in range(6)]
        out = assess_prefix(r, first_size=100, sixth_end=6 * 1024)
        self.assertTrue(out["candidate_prefix_consistent_with_both_observations"])
        self.assertFalse(out["order_verified"])
        self.assertFalse(out["individual_member_offsets_verified"])

    def test_first_size_mismatch_rejects_candidate(self):
        r = [("a%d" % i, 100) for i in range(6)]
        out = assess_prefix(r, first_size=101, sixth_end=6144)
        self.assertFalse(out["candidate_prefix_consistent_with_both_observations"])
        self.assertTrue(out["sixth_next_header_offset_matches_observation"])

    def test_sixth_offset_mismatch_rejects_candidate(self):
        r = [("a%d" % i, 100) for i in range(6)]
        out = assess_prefix(r, first_size=100, sixth_end=6656)
        self.assertTrue(out["first_member_size_matches_observed_header"])
        self.assertFalse(out["candidate_prefix_consistent_with_both_observations"])

    def test_invalid_inputs_rejected(self):
        for rows in ([], [("a", 100)], [("", 100)] * 6, [("a", True)] * 6):
            with self.subTest(rows=rows), self.assertRaises(ValueError):
                assess_prefix(rows)

    def test_order_matters_and_stays_hypothetical(self):
        rows = [("z", 200), ("a", 100)] + [("b%d" % i, 100) for i in range(4)]
        self.assertTrue(assess_prefix(rows, first_size=200, sixth_end=6*1024)["candidate_prefix_consistent_with_both_observations"])
        self.assertFalse(assess_prefix(sorted(rows), first_size=200, sixth_end=6*1024)["candidate_prefix_consistent_with_both_observations"])


class PinnedMetadataOrderHypothesisTests(unittest.TestCase):
    make_files = _fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = _fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        _fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)

    def test_readonly_report_remains_blocked(self):
        out = analyze_order_hypotheses(self.workspace)
        self.assertEqual(out["category_wav_count"], 35)
        self.assertFalse(out["member_order_verified"])
        self.assertFalse(out["selected_member_offsets_verified"])
        self.assertEqual(out["CP4"], "BLOCKED")

    def test_no_network(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("NETWORK FORBIDDEN")):
            analyze_order_hypotheses(self.workspace)

    def test_no_file_changes(self):
        before = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.workspace.iterdir()}
        analyze_order_hypotheses(self.workspace)
        after = {p.name: hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.workspace.iterdir()}
        self.assertEqual(before, after)

    def test_altered_csv_rejected(self):
        target = self.workspace / METADATA_FILENAME
        target.write_bytes(target.read_bytes() + b"changed")
        with self.assertRaisesRegex(ValueError, "digest"):
            analyze_order_hypotheses(self.workspace)

    def test_no_paths_or_transcripts_in_cli(self):
        buff = io.StringIO()
        with patch.object(sys, "argv", ["order", "--workspace", str(self.workspace)]), redirect_stdout(buff):
            self.assertEqual(main(), 0)
        output = buff.getvalue()
        self.assertNotIn("data/fictional", output)
        self.assertNotIn("fixture text", output)
        self.assertIn("NO VERIFIED OFFSETS", output)


if __name__ == "__main__":
    unittest.main()
