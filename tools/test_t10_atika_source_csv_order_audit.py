"""Offline synthetic tests for source CSV row-order hypothesis vs observed eighth TAR member."""
from __future__ import annotations
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parent))
import test_t10_atika_eighth_successor_anonymous_diagnostic as fx
import test_t10_atika_acquisition_budget as base
import t10_atika_source_csv_order_audit as audit
import t10_atika_tar_header_walk as walk


class OfflineCsvOrderTests(unittest.TestCase):
    make_files=base.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches=base.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fx.AnonymousHeaderDiagnosisTests.setUp(self)
        p=patch.object(audit,"OBSERVED_EIGHTH_LEXICAL_DISTANCE_LATER",2)
        p.start()
        self.addCleanup(p.stop)

    def ordered(self):
        return sorted(self.rows,key=lambda r:r["audio_path"])

    def test_offline_report_has_no_network_or_names(self):
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")) as req:
            result=audit.audit(self.workspace)
        req.assert_not_called()
        self.assertEqual(result["status"],"OFFLINE_ORDER_HYPOTHESIS_ONLY_NO_HTTP")
        self.assertEqual(result["network_requests_executed"],0)
        self.assertEqual(result["previous_matching_header_positions"],8)
        self.assertEqual(result["observed_eighth_member_catalogue_rank_distance"],2)
        self.assertFalse(result["source_csv_order_is_authoritative_tar_order"])
        self.assertFalse(result["actual_selected_second_offset_verified"])

    def test_unsorted_original_source_still_never_claims_order(self):
        result=audit.audit(self.workspace)
        self.assertIn(result["source_csv_order_first_eight_match_prior_header_prefix"],(True,False))
        self.assertIn(result["source_csv_next_row_matches_observed_eighth"],(True,False))
        self.assertFalse(result["full_tar_order_verified"])

    def test_sorted_source_has_matching_prefix_but_wrong_eighth(self):
        self.rows=self.ordered()
        self.make_files()
        result=audit.audit(self.workspace)
        self.assertTrue(result["source_csv_order_first_eight_match_prior_header_prefix"])
        self.assertFalse(result["source_csv_next_row_matches_observed_eighth"])
        self.assertFalse(result["source_csv_contiguous_prefix_and_eighth_consistent"])

    def test_source_order_can_match_witnessed_prefix_and_eighth(self):
        rows=self.ordered()
        actual=rows.pop(10)
        rows.insert(8,actual)
        self.rows=rows
        self.make_files()
        r=audit.audit(self.workspace)
        self.assertTrue(r["source_csv_order_first_eight_match_prior_header_prefix"])
        self.assertTrue(r["source_csv_next_row_matches_observed_eighth"])
        self.assertTrue(r["source_csv_contiguous_prefix_and_eighth_consistent"])
        self.assertFalse(r["source_csv_order_is_authoritative_tar_order"])

    def test_csv_tamper_refused(self):
        p=self.workspace/base.METADATA_FILENAME
        p.write_bytes(p.read_bytes()+b"mutation")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises(ValueError):
                audit.audit(self.workspace)

    def test_selection_tamper_refused(self):
        p=self.workspace/walk.SELECTION_NAME
        p.write_bytes(p.read_bytes()+b"mutation")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises(ValueError):
                audit.audit(self.workspace)

    def test_lex_rank_outside_catalogue_refused(self):
        with patch.object(audit,"OBSERVED_EIGHTH_LEXICAL_DISTANCE_LATER",9999),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises(ValueError):
                audit.audit(self.workspace)

    def test_default_cli_prints_no_paths_or_offsets(self):
        stdout=io.StringIO()
        with patch.object(sys,"argv",["audit","--workspace",str(self.workspace)]),\
             redirect_stdout(stdout),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            self.assertEqual(audit.main(),0)
        report=stdout.getvalue()
        self.assertIn("OFFLINE_ORDER_HYPOTHESIS_ONLY_NO_HTTP",report)
        self.assertNotIn("data/fictional",report)
        self.assertNotIn("sample00",report)
        self.assertNotIn(str(self.workspace),report)

    def test_no_private_file_mutations(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.iterdir()}
        audit.audit(self.workspace)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.workspace.iterdir()}
        self.assertEqual(before,after)

    def test_no_file_names_in_aggregate_report(self):
        r=audit.audit(self.workspace)
        s=str(r)
        self.assertNotIn("data/fictional",s)
        self.assertNotIn(".wav",s)
        self.assertNotIn("transcript",s)


if __name__=="__main__":
    unittest.main()
