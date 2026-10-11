"""Offline-only synthetic gap audit for first matching / second invalid TAR header."""
from __future__ import annotations
from contextlib import redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as fixtures
import t10_atika_selected_header_gap_audit as audit
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to


def sample():
    source = {f"data/fiction/{i:02d}.wav": 44+i for i in range(35)}
    indexed = []
    offset = 0
    for i, (name, size) in enumerate(sorted(source.items())):
        indexed.append((i, offset, name, size))
        offset += 512 + ceil_to(size, 512)
    return indexed, source


class PureGapArithmetic(unittest.TestCase):
    def test_exact_first_to_second_metadata_arithmetic(self):
        indexed, cat = sample()
        result = audit.interval_metadata_arithmetic(indexed[:30], cat)
        self.assertEqual(result["metadata_members_strictly_between_selected"], 0)
        self.assertEqual(result["metadata_member_slots_from_first_to_before_second"], 1)
        self.assertEqual(result["hypothetical_header_distance_bytes"], 1024)
        self.assertFalse(result["range_contains_actual_tar_header_chain_verified"])

    def test_sorted_name_order_not_csv_order(self):
        indexed, cat = sample()
        reversed_csv = dict(reversed(list(cat.items())))
        self.assertEqual(
            audit.interval_metadata_arithmetic(indexed[:30], reversed_csv),
            audit.interval_metadata_arithmetic(indexed[:30], cat))

    def test_nonadjacent_gap_includes_every_intervening_entry(self):
        indexed, cat = sample()
        # Thirty unique selected candidates, five unselected items between
        # first matched header and second invalid predicted position.
        far = [indexed[0]] + indexed[6:35]
        self.assertEqual(len(far), 30)
        gap = audit.interval_metadata_arithmetic(far, cat)
        self.assertEqual(gap["metadata_members_strictly_between_selected"], 5)
        self.assertEqual(gap["metadata_member_slots_from_first_to_before_second"], 6)
        self.assertEqual(gap["hypothetical_header_distance_bytes"], 6*1024)
        self.assertEqual(gap["metadata_payload_sum_in_interval_bytes"],
                         sum(cat[k] for k in sorted(cat)[:6]))

    def test_mismatched_relative_offset_rejected(self):
        indexed, cat = sample()
        samples=indexed[:30]
        i,o,n,s=samples[1]
        samples[1]=(i,o+512,n,s)
        with self.assertRaisesRegex(ValueError, "mismatched"):
            audit.interval_metadata_arithmetic(samples, cat)

    def test_missing_member_name_rejected(self):
        indexed, cat = sample()
        samples=indexed[:30]
        i,o,_,s=samples[1]
        samples[1]=(i,o,"data/fiction/missing.wav",s)
        with self.assertRaises(ValueError):
            audit.interval_metadata_arithmetic(samples,cat)

    def test_duplicate_member_rejected(self):
        indexed, cat=sample()
        samples=indexed[:30]
        i,o,_,s=samples[1]
        samples[1]=(i,o,samples[0][2],s)
        with self.assertRaises(ValueError):
            audit.interval_metadata_arithmetic(samples,cat)

    def test_wrong_selected_total_refused(self):
        indexed,cat=sample()
        with self.assertRaisesRegex(ValueError,"Expected frozen"):
            audit.interval_metadata_arithmetic(indexed[:29],cat)

    def test_name_length_is_heuristic_not_pax_proof(self):
        indexed,cat=sample()
        result=audit.interval_metadata_arithmetic(indexed[:30],cat)
        self.assertFalse(result["metadata_name_length_proves_PAX_or_auxiliary_headers"])


class PrivateOfflineFixture(unittest.TestCase):
    make_files = fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        sorted_rows=sorted(self.rows,key=lambda row:row["audio_path"])
        expected_first=int(sorted_rows[0]["file_size_bytes"])
        sixth_offset=sum(512+ceil_to(int(row["file_size_bytes"]),512)
                         for row in sorted_rows[:6])
        expected_tar=ceil_to(1024+sum(512+ceil_to(
            int(row["file_size_bytes"]),512) for row in self.rows),10240)
        for p in (patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",expected_first),
                  patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",sixth_offset),
                  patch.object(tar_walk,"EXPECTED_TAR_BYTES",expected_tar)):
            p.start()
            self.addCleanup(p.stop)

    def test_private_preflight_offline_no_writes(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen",side_effect=AssertionError("HTTP")):
            result=audit.report(self.workspace)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.workspace.iterdir()}
        self.assertEqual(before,after)
        self.assertEqual(result["category_wav_rows"],35)
        self.assertEqual(result["network_requests_executed"],0)
        self.assertFalse(result["root_cause_proven"])

    def test_cli_output_censored_and_zero_network(self):
        buffer=io.StringIO()
        with patch.object(sys,"argv",["gap","--workspace",str(self.workspace)]),\
             redirect_stdout(buffer),\
             patch.object(tar_walk,"fetch_header",side_effect=AssertionError("TAR HTTP")):
            self.assertEqual(audit.main(),0)
        s=buffer.getvalue()
        self.assertIn("OFFLINE GAP AUDIT ONLY",s)
        self.assertNotIn("data/fictional",s)
        self.assertNotIn("fixture text",s)
        self.assertIn("global_TAR_order_verified",s)

    def test_tampered_selection_blocks(self):
        selection=self.workspace/tar_walk.SELECTION_NAME
        selection.write_bytes(selection.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            audit.report(self.workspace)

    def test_tampered_metadata_blocks(self):
        meta=self.workspace/fixtures.METADATA_FILENAME
        meta.write_bytes(meta.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            audit.report(self.workspace)


if __name__=="__main__":
    unittest.main()
