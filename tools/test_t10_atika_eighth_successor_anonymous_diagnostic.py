"""Synthetic-only tests: anonymous eighth-member identification; no live HTTP."""
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
import t10_atika_eighth_successor_anonymous_diagnostic as diagnose
import t10_atika_tar_header_walk as walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to


def header(name, size, *, regular=True):
    info=tarfile.TarInfo(name)
    info.size=size
    if not regular:
        info.type=tarfile.DIRTYPE
        info.size=0
    return info.tobuf(format=tarfile.USTAR_FORMAT)[:512]


class AnonymousHeaderDiagnosisTests(unittest.TestCase):
    make_files=fixture.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches=fixture.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixture.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        source=dict(self.rows[30])
        for i in range(9):
            row=dict(source)
            row["audio_path"]=f"data/fictional/M1/sample00_extra{i}.wav"
            row["file_size_bytes"]=str(85000+i)
            self.rows.append(row)
        self.make_files()
        ordered=sorted(self.rows,key=lambda r:r["audio_path"])
        first_size=int(ordered[0]["file_size_bytes"])
        sixth=sum(512+ceil_to(int(r["file_size_bytes"]),512)
                  for r in ordered[:6])
        full=ceil_to(1024+sum(512+ceil_to(int(r["file_size_bytes"]),512)
                             for r in ordered),10240)
        for p in (patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",first_size),
                  patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",sixth),
                  patch.object(walk,"EXPECTED_TAR_BYTES",full)):
            p.start()
            self.addCleanup(p.stop)

    def plan(self):
        return diagnose.diagnosis_plan(self.workspace)

    def test_offline_plan_pin_and_eighth_offset(self):
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            offset,name,size,cat,report=self.plan()
        ordered=sorted(self.rows,key=lambda r:r["audio_path"])
        self.assertEqual(name,ordered[8]["audio_path"])
        self.assertEqual(size,int(ordered[8]["file_size_bytes"]))
        predicted=sum(512+ceil_to(int(r["file_size_bytes"]),512)
                      for r in ordered[:8])
        self.assertEqual(offset,predicted)
        self.assertEqual(len(cat),len(ordered))
        self.assertEqual(report["network_requests_executed"],0)

    def test_default_cli_no_network_or_mutation_and_no_private_data(self):
        before={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
                for f in self.workspace.iterdir()}
        output=io.StringIO()
        with patch.object(sys,"argv",["diagnose","--workspace",str(self.workspace)]),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")),\
             redirect_stdout(output):
            self.assertEqual(diagnose.main(),0)
        after={f.name:hashlib.sha256(f.read_bytes()).hexdigest()
               for f in self.workspace.iterdir()}
        self.assertEqual(before,after)
        self.assertIn("OFFLINE_ONLY_NO_HTTP",output.getvalue())
        self.assertNotIn("data/fictional",output.getvalue())
        self.assertNotIn("fixture text",output.getvalue())

    def test_other_pinned_later_matching_size(self):
        _,name,size,cat,_=self.plan()
        ordered=sorted(cat)
        other=ordered[ordered.index(name)+1]
        r=diagnose.classify(header(other,cat[other]),name,size,cat)
        self.assertEqual(r["classification"],
                         "OTHER_PINNED_MEMBER_AT_EIGHTH_POSITION_SIZE_MATCHES")
        self.assertEqual(r["catalogue_relative_order_direction"],"LATER")
        self.assertEqual(r["catalogue_relative_order_distance"],1)
        self.assertNotIn("member_name",r)

    def test_other_pinned_earlier_matching_size(self):
        _,name,size,cat,_=self.plan()
        ordered=sorted(cat)
        other=ordered[ordered.index(name)-1]
        r=diagnose.classify(header(other,cat[other]),name,size,cat)
        self.assertEqual(r["catalogue_relative_order_direction"],"EARLIER")
        self.assertEqual(r["catalogue_relative_order_distance"],1)

    def test_other_pinned_member_size_mismatch(self):
        _,name,size,cat,_=self.plan()
        other=sorted(cat)[-1]
        result=diagnose.classify(header(other,cat[other]+512),name,size,cat)
        self.assertEqual(result["classification"],
                         "OTHER_PINNED_MEMBER_AT_EIGHTH_POSITION_SIZE_DIFFERS")

    def test_regular_member_outside_category(self):
        _,name,size,cat,_=self.plan()
        result=diagnose.classify(header("data/other/wrong.wav",60),name,size,cat)
        self.assertEqual(result["classification"],
                         "REGULAR_MEMBER_OUTSIDE_PINNED_IMPERATIVE_CATALOGUE")

    def test_expected_name_on_recheck_never_erases_prior_fail(self):
        _,name,size,cat,_=self.plan()
        result=diagnose.classify(header(name,size),name,size,cat)
        self.assertEqual(result["classification"],
                         "EXPECTED_MEMBER_ON_RECHECK_PRIOR_NAME_DIVERGENCE_UNRESOLVED")

    def test_expected_name_with_size_difference(self):
        _,name,size,cat,_=self.plan()
        result=diagnose.classify(header(name,size+5),name,size,cat)
        self.assertEqual(result["classification"],
                         "EXPECTED_MEMBER_WITH_SIZE_DIFFERENCE_ON_RECHECK")

    def test_invalid_checksum(self):
        _,name,size,cat,_=self.plan()
        self.assertIn("INVALID_HEADER",
                      diagnose.classify(b"x"*512,name,size,cat)["classification"])

    def test_nonregular_header(self):
        _,name,size,cat,_=self.plan()
        result=diagnose.classify(header(name,44,regular=False),name,size,cat)
        self.assertEqual(result["classification"],
                         "NON_REGULAR_OR_AUXILIARY_MEMBER_ON_RECHECK")

    def test_zero_header(self):
        _,name,size,cat,_=self.plan()
        r=diagnose.classify(bytes(512),name,size,cat)
        self.assertEqual(r["classification"],"UNEXPECTED_ZERO_TAR_BLOCK_ON_RECHECK")

    def test_one_explicit_request_only_and_return_code_three(self):
        _,name,size,cat,_=self.plan()
        other=sorted(cat)[-1]
        output=io.StringIO()
        with patch.object(sys,"argv",["diagnose","--workspace",str(self.workspace),
             "--inspect-eighth-header"]),\
             patch.object(walk,"fetch_header",return_value=header(other,cat[other])) as request,\
             redirect_stdout(output):
            self.assertEqual(diagnose.main(),3)
        self.assertEqual(request.call_count,1)
        self.assertIn('"network_requests_executed": 1',output.getvalue())
        self.assertNotIn(other,output.getvalue())
        self.assertNotIn(name,output.getvalue())
        self.assertIn("ONE_HEADER_CLASSIFIED_PREVIOUS_FAIL_STANDS",output.getvalue())

    def test_http_range_ignored_stops(self):
        with patch.object(sys,"argv",["diagnose","--workspace",str(self.workspace),
             "--inspect-eighth-header"]),\
             patch.object(walk,"fetch_header",side_effect=walk.RangeNotHonored("200")) as request,\
             redirect_stderr(io.StringIO()):
            self.assertEqual(diagnose.main(),2)
        self.assertEqual(request.call_count,1)

    def test_csv_modified_fails_before_http(self):
        p=self.workspace/fixture.METADATA_FILENAME
        p.write_bytes(p.read_bytes()+b"tamper")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                self.plan()

    def test_selection_modified_fails_before_http(self):
        p=self.workspace/walk.SELECTION_NAME
        p.write_bytes(p.read_bytes()+b"tamper")
        with patch.object(walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                self.plan()


if __name__=="__main__":
    unittest.main()
