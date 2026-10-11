"""Synthetic-only selected-second-header mismatch classifier tests; zero HTTP."""
from __future__ import annotations

import hashlib
import io
from pathlib import Path
import sys
import tarfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as fixtures
import t10_atika_selected_header_mismatch_diagnostic as diag
import t10_atika_selected_header_preflight as prep
import t10_atika_selected_header_check as check
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to
from t10_public_id_corpus import METADATA_FILENAME


def head(name: str, size: int, regular: bool = True) -> bytes:
    entry = tarfile.TarInfo(name)
    entry.size = size
    if not regular:
        entry.type = tarfile.DIRTYPE
        entry.size = 0
    return entry.tobuf(format=tarfile.USTAR_FORMAT)[:512]


class SingleHeaderClassifier(unittest.TestCase):
    def setUp(self):
        self.catalogue = {
            "data/case/a.wav": 100,
            "data/case/b.wav": 200,
        }

    def classify(self, header):
        return diag.classify_observed_header(
            header, "data/case/a.wav", 100, self.catalogue
        )["diagnostic_classification"]

    def test_expected_header_matches_but_does_not_verify_order(self):
        r=diag.classify_observed_header(
            head("data/case/a.wav",100),
            "data/case/a.wav",100,self.catalogue)
        self.assertEqual(r["diagnostic_classification"], "EXPECTED_HEADER_MATCHES_ON_RECHECK")
        self.assertFalse(r["entire_tar_order_verified"])

    def test_expected_name_wrong_size(self):
        self.assertEqual(self.classify(head("data/case/a.wav",150)),
                         "EXPECTED_NAME_BUT_SIZE_DIFFERS")

    def test_wrong_valid_known_member_and_size(self):
        self.assertEqual(self.classify(head("data/case/b.wav",200)),
                         "OTHER_PINNED_WAV_AT_OFFSET_NAME_AND_SIZE_VALID")

    def test_wrong_known_member_wrong_size(self):
        self.assertEqual(self.classify(head("data/case/b.wav",201)),
                         "OTHER_PINNED_WAV_AT_OFFSET_SIZE_DIFFERS")

    def test_wrong_unknown_regular_member(self):
        self.assertEqual(self.classify(head("data/case/other.wav",44)),
                         "REGULAR_TAR_MEMBER_NOT_IN_PINNED_IMPERATIVE_CSV")

    def test_nonregular_directory(self):
        self.assertEqual(self.classify(head("data/case/b.wav",44,False)),
                         "OTHER_TAR_MEMBER_NON_REGULAR_OR_AUXILIARY")

    def test_expected_name_nonregular(self):
        self.assertEqual(self.classify(head("data/case/a.wav",44,False)),
                         "EXPECTED_NAME_IS_NOT_A_REGULAR_FILE")

    def test_zero_block_and_bad_checksum(self):
        self.assertEqual(self.classify(bytes(512)),
                         "ZERO_TAR_BLOCK_AT_PREDICTED_HEADER")
        self.assertEqual(self.classify(b"x"*512),
                         "INVALID_TAR_HEADER_AT_PREDICTED_OFFSET")

    def test_broken_input_rejected(self):
        for bad in (b"x",None):
            with self.subTest(value=bad),self.assertRaises(ValueError):
                self.classify(bad)

    def test_bad_catalogue_expected_size_rejected(self):
        with self.assertRaises(ValueError):
            diag.classify_observed_header(
                head("data/case/a.wav",100),
                "data/case/a.wav",999,self.catalogue)


class FrozenWorkspaceDiagnostic(unittest.TestCase):
    make_files = fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        data=sorted(self.rows,key=lambda r:r["audio_path"])
        expected_end=sum(512+ceil_to(int(r["file_size_bytes"]),512)
                         for r in data[:6])
        archive=ceil_to(1024+sum(512+ceil_to(int(r["file_size_bytes"]),512)
                         for r in self.rows),10240)
        for p in (
            patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",
                         int(data[0]["file_size_bytes"])),
            patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",expected_end),
            patch.object(tar_walk,"EXPECTED_TAR_BYTES",archive),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_offline_plan_no_http_and_no_mutation(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen",side_effect=AssertionError("HTTP")):
            target,report=diag.diagnosis_plan(self.workspace)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.workspace.iterdir()}
        self.assertEqual(before,after)
        self.assertEqual(report["target_selected_header_ordinal"],2)
        self.assertFalse(report["predicted_header_offset_printed"])
        self.assertFalse(report["selected_member_name_printed"])
        self.assertEqual(report["network_requests_executed"],0)

    def test_default_cli_no_fetch_and_no_sensitive_output(self):
        buffer=io.StringIO()
        with patch.object(sys,"argv",["diag","--workspace",str(self.workspace)]),\
             redirect_stdout(buffer),patch.object(tar_walk,"fetch_header",
                                  side_effect=AssertionError("FETCH")):
            self.assertEqual(diag.main(),0)
        s=buffer.getvalue()
        self.assertIn("OFFLINE_ONLY_NO_HTTP",s)
        self.assertNotIn("data/fictional",s)
        self.assertNotIn("fixture text",s)

    def test_opt_in_only_one_request_and_reports_enum(self):
        target,_=diag.diagnosis_plan(self.workspace)
        out=io.StringIO()
        with patch.object(sys,"argv",["diag","--workspace",str(self.workspace),
                                      "--inspect-second-header"]),\
             redirect_stdout(out), patch.object(tar_walk,"fetch_header",
                return_value=head(target[2],target[3])) as remote:
            self.assertEqual(diag.main(),0)
        self.assertEqual(remote.call_count,1)
        self.assertIn('"network_requests_executed": 1',out.getvalue())
        self.assertIn("EXPECTED_HEADER_MATCHES_ON_RECHECK",out.getvalue())
        self.assertNotIn(target[2],out.getvalue())
        self.assertNotIn(str(target[1]),out.getvalue())

    def test_mismatch_exit_three_and_no_names(self):
        result=io.StringIO()
        with patch.object(sys,"argv",["diag","--workspace",str(self.workspace),
                                      "--inspect-second-header"]),\
             redirect_stdout(result),patch.object(tar_walk,"fetch_header",
                    return_value=head("data/case/unlisted.wav",44)) as remote:
            self.assertEqual(diag.main(),3)
        self.assertEqual(remote.call_count,1)
        self.assertIn("REGULAR_TAR_MEMBER_NOT_IN_PINN_IMPERATIVE_CSV",result.getvalue())
        self.assertNotIn("unlisted.wav",result.getvalue())

    def test_http_range_ignored_exit_two(self):
        with patch.object(sys,"argv",["diag","--workspace",str(self.workspace),
                                      "--inspect-second-header"]),\
             redirect_stderr(io.StringIO()),patch.object(tar_walk,"fetch_header",
                    side_effect=tar_walk.RangeNotHonored("200")) as remote:
            self.assertEqual(diag.main(),2)
        self.assertEqual(remote.call_count,1)

    def test_tampered_selection_and_csv_stops_before_http(self):
        for target in (self.workspace/tar_walk.SELECTION_NAME,
                       self.workspace/METADATA_FILENAME):
            saved=target.read_bytes()
            target.write_bytes(saved+b"x")
            try:
                with patch.object(tar_walk,"fetch_header",
                                  side_effect=AssertionError("FETCH")):
                    with self.assertRaises((ValueError,TypeError)):
                        diag.diagnosis_plan(self.workspace)
            finally:
                target.write_bytes(saved)


if __name__=="__main__":
    unittest.main()
