"""Synthetic-only regression for T10 anchored successors 7..9 continuation."""
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
import test_t10_atika_acquisition_budget as fixture
import t10_atika_anchored_successor_continuation as continuation
import t10_atika_tar_order_hypotheses as order
import t10_atika_tar_header_walk as walk
from t10_atika_tar_layout_budget import ceil_to


def synthetic_header(name: str, size: int) -> bytes:
    entry = tarfile.TarInfo(name)
    entry.size = size
    return entry.tobuf(format=tarfile.USTAR_FORMAT)[:512]


class FrozenSyntheticContinuation(unittest.TestCase):
    make_files = fixture.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixture.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixture.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        source = dict(self.rows[30])
        # Put nine unselected train WAVs between selected #1 and selected #2.
        for i in range(9):
            record = dict(source)
            record["audio_path"] = f"data/fictional/M1/sample00_extra{i}.wav"
            record["file_size_bytes"] = str(85000 + i)
            self.rows.append(record)
        self.make_files()
        ordered = sorted(self.rows, key=lambda r: r["audio_path"])
        first_size = int(ordered[0]["file_size_bytes"])
        sixth = sum(512 + ceil_to(int(r["file_size_bytes"]), 512)
                    for r in ordered[:6])
        full_bytes = ceil_to(
            1024 + sum(512+ceil_to(int(r["file_size_bytes"]),512)
                       for r in ordered), 10240
        )
        for p in (patch.object(order, "OBSERVED_FIRST_MEMBER_SIZE", first_size),
                  patch.object(order, "OBSERVED_SIX_HEADER_NEXT_OFFSET", sixth),
                  patch.object(walk, "EXPECTED_TAR_BYTES", full_bytes)):
            p.start()
            self.addCleanup(p.stop)

    def plan(self, count=3):
        return continuation.continuation_plan(self.workspace, count)

    def test_offline_plan_skips_six_and_limits_to_before_selected_second(self):
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            offset, expected, report = self.plan()
        self.assertEqual(len(expected), 3)
        ordered = sorted(self.rows, key=lambda r:r["audio_path"])
        self.assertEqual([x[0] for x in expected],
                         [r["audio_path"] for r in ordered[7:10]])
        self.assertEqual(report["new_successor_ordinals_after_first_selected"],
                         [7,8,9])
        self.assertEqual(report["previous_remote_matched_successors_from_user_report"], 6)
        self.assertEqual(report["network_requests_executed"], 0)
        self.assertFalse(report["previous_matched_headers_rechecked_this_run"])
        self.assertFalse(report["full_archive_order_verified"])
        predicted = sum(512 + ceil_to(int(r["file_size_bytes"]),512)
                        for r in ordered[:7])
        self.assertEqual(offset,predicted)

    def test_default_cli_no_http_or_private_paths(self):
        before={x.name:hashlib.sha256(x.read_bytes()).hexdigest()
                for x in self.workspace.iterdir()}
        buf=io.StringIO()
        with patch.object(sys,"argv",["continue","--workspace",str(self.workspace)]),\
             redirect_stdout(buf),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            self.assertEqual(continuation.main(),0)
        self.assertEqual(before,{x.name:hashlib.sha256(x.read_bytes()).hexdigest()
                                 for x in self.workspace.iterdir()})
        s=buf.getvalue()
        self.assertIn("OFFLINE_ONLY_NO_HTTP",s)
        self.assertNotIn("data/fictional",s)
        self.assertNotIn("fixture text",s)
        self.assertIn('"network_requests_executed": 0',s)

    def test_old_remote_flag_now_fails_closed_without_network(self):
        output=io.StringIO()
        with patch.object(sys,"argv",["continue","--workspace",str(self.workspace),
                          "--execute-new-successors","--max-new-successors","3"]),\
             redirect_stdout(output),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("NETWORK")) as remote:
            self.assertEqual(continuation.main(),3)
        remote.assert_not_called()
        self.assertIn("HALTED_AFTER_OBSERVED_SUCCESSOR_8_NAME_ORDER_DIVERGENCE",
                      output.getvalue())
        self.assertIn('"network_requests_executed": 0',output.getvalue())

    def test_synthetic_direct_walker_name_divergence_stops(self):
        offset,expected,_=self.plan()
        with patch.object(walk,"fetch_header",
                          return_value=synthetic_header("data/foreign/wrong.wav",99)) as remote:
            out=continuation.inspect_successors(offset,expected)
        self.assertEqual(remote.call_count,1)
        self.assertEqual(out["classification"],"MEMBER_NAME_ORDER_DIVERGED")

    def test_synthetic_direct_walker_size_divergence_stops(self):
        offset,expected,_=self.plan()
        with patch.object(walk,"fetch_header",
                          return_value=synthetic_header(expected[0][0],expected[0][1]+1)) as remote:
            out=continuation.inspect_successors(offset,expected)
        self.assertEqual(remote.call_count,1)
        self.assertEqual(out["classification"],"MEMBER_SIZE_METADATA_DIVERGED")

    def test_synthetic_direct_walker_range_ignored_stops(self):
        offset,expected,_=self.plan()
        with patch.object(walk,"fetch_header",
                          side_effect=walk.RangeNotHonored("200")) as remote:
            with self.assertRaises(walk.RangeNotHonored):
                continuation.inspect_successors(offset,expected)
        self.assertEqual(remote.call_count,1)

    def test_four_requests_refused_before_http(self):
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises(ValueError):
                self.plan(4)

    def test_zero_requests_refused(self):
        with self.assertRaises(ValueError):
            self.plan(0)

    def test_one_requested_successor_supported(self):
        _, expected, report=self.plan(1)
        self.assertEqual(len(expected),1)
        self.assertEqual(report["new_successor_ordinals_after_first_selected"],[7])

    def test_selection_tamper_refused(self):
        path=self.workspace/walk.SELECTION_NAME
        path.write_bytes(path.read_bytes()+b"x")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                self.plan()

    def test_csv_tamper_refused(self):
        path=self.workspace/fixture.METADATA_FILENAME
        path.write_bytes(path.read_bytes()+b"x")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                self.plan()

    def test_never_claims_selected_second_or_archive_order(self):
        _,expected,_=self.plan()
        with patch.object(walk,"fetch_header",
                          return_value=synthetic_header(expected[0][0],expected[0][1])):
            # One *synthetic* header can match, but cannot prove complete TAR.
            outcome=continuation.inspect_successors(0,expected[:1])
        self.assertTrue(outcome["all_requested_successors_match"])
        self.assertFalse(outcome["actual_second_selected_header_position_verified"])
        self.assertFalse(outcome["full_archive_member_order_verified"])


if __name__ == "__main__":
    unittest.main()
