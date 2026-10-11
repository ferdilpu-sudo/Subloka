"""Synthetic-only USTAR path feasibility audit (never fetch TAR/WAV)."""
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
import t10_atika_tar_ustar_path_audit as audit
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to


SHORT = "data/M1/short.wav"
EXTENDED_FITS = "data/" + "a"*95 + "/" + "z"*13 + ".wav"
LONG_BASENAME = "data/" + "a"*110 + ".wav"
WAY_TOO_LONG = "data/" + "a"*270 + ".wav"


class PureUstarNameEncodingTests(unittest.TestCase):
    def test_short_ascii_ustar(self):
        self.assertTrue(audit.ustar_path_fits(SHORT))

    def test_long_path_can_fit_ustar_prefix(self):
        self.assertGreater(len(EXTENDED_FITS.encode("utf-8")), 100)
        self.assertTrue(audit.ustar_path_fits(EXTENDED_FITS))

    def test_long_basename_must_not_fit_single_ustar(self):
        self.assertFalse(audit.ustar_path_fits(LONG_BASENAME))

    def test_long_unbreakable_component_exceeds_capacity(self):
        self.assertFalse(audit.ustar_path_fits(WAY_TOO_LONG))

    def test_multibyte_names_count_bytes_not_codepoints(self):
        name = "data/" + "é"*51 + ".wav"
        self.assertGreater(len(name.encode("utf-8")), 100)
        self.assertFalse(audit.ustar_path_fits(name))

    def test_invalid_paths_fail_before_serializer(self):
        for name in ("/tmp/a.wav", "data/../a.wav", "data/a.txt",
                     "data/a\x00.wav", 12, ""):
            with self.subTest(name=repr(name)), self.assertRaises(ValueError):
                audit.ustar_path_fits(name)

    def test_aggregate_splits_ustar_feasible_and_infeasible(self):
        result = audit.check_path_capacity(
            [SHORT, EXTENDED_FITS, LONG_BASENAME]
        )
        self.assertEqual(result["metadata_names_within_100_utf8_bytes"], 1)
        self.assertEqual(result["metadata_names_over_100_ustar_serializable"], 1)
        self.assertEqual(result["metadata_names_over_100_ustar_not_serializable"], 1)
        self.assertFalse(result["all_metadata_names_ustar_serializable"])
        self.assertFalse(result["actual_extra_header_records_verified"])

    def test_only_long_but_ustar_feasible_does_not_prove_pax(self):
        result = audit.check_path_capacity([EXTENDED_FITS])
        self.assertEqual(result["metadata_names_over_100_utf8_bytes"], 1)
        self.assertEqual(result["metadata_names_over_100_ustar_not_serializable"], 0)
        self.assertFalse(result["over_100_bytes_alone_requires_pax_or_gnu"])

    def test_duplicate_names_blocked(self):
        with self.assertRaisesRegex(ValueError, "Invalid catalogue"):
            audit.check_path_capacity([SHORT,SHORT])

    def test_empty_list_blocked(self):
        with self.assertRaisesRegex(ValueError, "Invalid catalogue"):
            audit.check_path_capacity([])

    def test_invalid_member_does_not_leak_filename(self):
        with self.assertRaises(ValueError) as e:
            audit.check_path_capacity(["data/../secret.wav"])
        self.assertNotIn("secret",str(e.exception))


class SyntheticPinnedWorkspaceTests(unittest.TestCase):
    make_files = fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        indexed=sorted(self.rows,key=lambda row:row["audio_path"])
        first=int(indexed[0]["file_size_bytes"])
        sixth=sum(512+ceil_to(int(row["file_size_bytes"]),512) for row in indexed[:6])
        archive=ceil_to(
            1024+sum(512+ceil_to(int(row["file_size_bytes"]),512) for row in self.rows),
            10240,
        )
        for p in (patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",first),
                  patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",sixth),
                  patch.object(tar_walk,"EXPECTED_TAR_BYTES",archive)):
            p.start()
            self.addCleanup(p.stop)

    def test_offline_plan_no_network_no_writes(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen",side_effect=AssertionError("HTTP")),\
             patch.object(tar_walk,"fetch_header",side_effect=AssertionError("TAR")):
            result=audit.report(self.workspace)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.workspace.iterdir()}
        self.assertEqual(before,after)
        self.assertEqual(result["source_wav_metadata_rows"],35)
        self.assertEqual(result["network_requests_executed"],0)
        self.assertEqual(result["between_first_matching_and_second_invalid_candidates"]
                         ["metadata_names_total"],1)
        self.assertFalse(result["root_cause_of_header_mismatch_proven"])

    def test_cli_no_names_offsets_or_payload(self):
        buf=io.StringIO()
        with patch.object(sys,"argv",["audit","--workspace",str(self.workspace)]),\
             redirect_stdout(buf),\
             patch.object(tar_walk,"fetch_header",side_effect=AssertionError("TAR")):
            self.assertEqual(audit.main(),0)
        output=buf.getvalue()
        self.assertIn("OFFLINE USTAR CAPACITY ONLY",output)
        self.assertNotIn("data/fictional",output)
        self.assertNotIn("fixture text",output)
        self.assertNotIn("sample00.wav",output)
        self.assertIn('"network_requests_executed": 0',output)

    def test_modified_selection_refused_before_network(self):
        p=self.workspace/tar_walk.SELECTION_NAME
        p.write_bytes(p.read_bytes()+b"invalid")
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("TAR")):
            with self.assertRaises((ValueError,TypeError)):
                audit.report(self.workspace)

    def test_modified_pinned_csv_refused_before_network(self):
        p=self.workspace/fixtures.METADATA_FILENAME
        p.write_bytes(p.read_bytes()+b"invalid")
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("TAR")):
            with self.assertRaises((ValueError,TypeError)):
                audit.report(self.workspace)


if __name__ == "__main__":
    unittest.main()
