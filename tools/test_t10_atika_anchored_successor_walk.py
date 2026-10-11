"""Synthetic-only anchored successor header chain tests; no live TAR network."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import io
from pathlib import Path
import sys
import tarfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as fixtures
import t10_atika_anchored_successor_walk as anchored
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to


def header(name: str, size: int, *, regular=True) -> bytes:
    info=tarfile.TarInfo(name)
    info.size=size
    if not regular:
        info.type=tarfile.DIRTYPE
        info.size=0
    return info.tobuf(format=tarfile.USTAR_FORMAT)[:512]


def chain():
    expected=[(f"data/fiction/a{i}.wav",80+i) for i in range(4)]
    start=1024
    offsets=[]
    for name,size in expected:
        offsets.append(start)
        start += 512+ceil_to(size,512)
    return offsets, expected


class StrictBoundedHeaderChainTests(unittest.TestCase):
    def test_four_successors_follow_actual_header_sizes(self):
        offsets, expected=chain()
        by_offset={off:header(name,size)
                   for off,(name,size) in zip(offsets,expected)}
        with patch.object(tar_walk,"fetch_header",
                          side_effect=lambda off:by_offset[off]) as req:
            r=anchored.inspect_successors(offsets[0], expected)
        self.assertEqual(req.call_count,4)
        self.assertTrue(r["all_requested_successors_match"])
        self.assertFalse(r["actual_second_selected_header_position_verified"])

    def test_only_one_successor(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",
                          return_value=header(*expected[0])) as req:
            r=anchored.inspect_successors(offsets[0],expected[:1])
        self.assertEqual(req.call_count,1)
        self.assertTrue(r["all_requested_successors_match"])

    def test_name_order_deviation_stops(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",
                          return_value=header("data/fiction/wrong.wav",88)) as req:
            r=anchored.inspect_successors(offsets[0],expected)
        self.assertEqual(req.call_count,1)
        self.assertEqual(r["classification"],"MEMBER_NAME_ORDER_DIVERGED")

    def test_expected_name_but_actual_size_differs(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",
                          return_value=header(expected[0][0],999)) as req:
            r=anchored.inspect_successors(offsets[0],expected)
        self.assertEqual(req.call_count,1)
        self.assertEqual(r["classification"],"MEMBER_SIZE_METADATA_DIVERGED")

    def test_nonfile_header_stops(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",
                          return_value=header(expected[0][0],44,regular=False)):
            r=anchored.inspect_successors(offsets[0],expected)
        self.assertEqual(r["classification"],"NON_REGULAR_OR_AUXILIARY_TAR_HEADER")

    def test_invalid_tar_checksum_stops(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",return_value=b"x"*512):
            r=anchored.inspect_successors(offsets[0],expected)
        self.assertEqual(r["classification"],"INVALID_TAR_HEADER_IN_ANCHORED_CHAIN")

    def test_zero_block_stops(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",return_value=bytes(512)):
            r=anchored.inspect_successors(offsets[0],expected)
        self.assertEqual(r["classification"],"UNEXPECTED_ZERO_TAR_BLOCK")

    def test_invalid_position_before_request(self):
        _,expected=chain()
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaisesRegex(ValueError,"Invalid bounded"):
                anchored.inspect_successors(513,expected)

    def test_five_successors_refused(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaisesRegex(ValueError,"Invalid bounded"):
                anchored.inspect_successors(offsets[0],expected+[expected[0]])

    def test_duplicate_member_refused(self):
        offsets,expected=chain()
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaisesRegex(ValueError,"Invalid bounded"):
                anchored.inspect_successors(offsets[0],[expected[0],expected[0]])


class PrivateFrozenFixtureTests(unittest.TestCase):
    make_files=fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches=fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        # Preserve the initial frozen 30; add five *unselected train* members
        # lexically between first and second selected candidates.
        first=dict(self.rows[30])
        for i in range(5):
            row=dict(first)
            row["audio_path"]=f"data/fictional/M1/sample00_extra{i}.wav"
            row["file_size_bytes"]=str(85000+i)
            self.rows.append(row)
        self.make_files()
        ordered=sorted(self.rows,key=lambda r:r["audio_path"])
        first_size=int(ordered[0]["file_size_bytes"])
        after_six=sum(512+ceil_to(int(r["file_size_bytes"]),512)
                      for r in ordered[:6])
        total=ceil_to(1024+sum(512+ceil_to(int(r["file_size_bytes"]),512)
                             for r in ordered),10240)
        for p in (patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",first_size),
                  patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",after_six),
                  patch.object(tar_walk,"EXPECTED_TAR_BYTES",total)):
            p.start()
            self.addCleanup(p.stop)

    def test_offline_plan_anchors_first_frozen_and_excludes_second(self):
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            _, successors, result=anchored.anchored_plan(self.workspace,4)
        self.assertEqual(len(successors),4)
        self.assertEqual(result["frozen_selected_count"],30)
        self.assertEqual(result["network_requests_executed"],0)
        self.assertFalse(result["selected_second_actual_offset_found"])

    def test_default_cli_never_calls_fetch(self):
        output=io.StringIO()
        with patch.object(sys,"argv",["anchor","--workspace",str(self.workspace)]),\
             redirect_stdout(output),\
             patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            self.assertEqual(anchored.main(),0)
        s=output.getvalue()
        self.assertIn("OFFLINE_ONLY_NO_HTTP",s)
        self.assertIn('"network_requests_executed": 0',s)
        self.assertNotIn("data/fictional",s)
        self.assertNotIn("fixture text",s)

    def test_opt_in_three_mocked_returns_0(self):
        first, expected,_=anchored.anchored_plan(self.workspace,3)
        body={}
        position=first
        for name,size in expected:
            body[position]=header(name,size)
            position+=512+ceil_to(size,512)
        out=io.StringIO()
        with patch.object(sys,"argv",["anchor","--workspace",str(self.workspace),
                                      "--execute-anchored-successors"]),\
             redirect_stdout(out),patch.object(tar_walk,"fetch_header",
                                 side_effect=lambda off:body[off]) as req:
            self.assertEqual(anchored.main(),0)
        self.assertEqual(req.call_count,3)
        self.assertIn('"network_requests_executed": 3',out.getvalue())
        self.assertNotIn("data/fictional",out.getvalue())

    def test_http_range_ignored_refuses_without_body(self):
        with patch.object(sys,"argv",["anchor","--workspace",str(self.workspace),
                                      "--execute-anchored-successors"]),\
             redirect_stderr(io.StringIO()),patch.object(
                tar_walk,"fetch_header",
                side_effect=tar_walk.RangeNotHonored("200")) as req:
            self.assertEqual(anchored.main(),2)
        self.assertEqual(req.call_count,1)

    def test_metadata_corruption_aborts_before_network(self):
        meta=self.workspace/fixtures.METADATA_FILENAME
        meta.write_bytes(meta.read_bytes()+b"modified")
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                anchored.anchored_plan(self.workspace,3)

    def test_selection_corruption_aborts_before_network(self):
        p=self.workspace/tar_walk.SELECTION_NAME
        p.write_bytes(p.read_bytes()+b"modified")
        with patch.object(tar_walk,"fetch_header",side_effect=AssertionError("HTTP")):
            with self.assertRaises((ValueError,TypeError)):
                anchored.anchored_plan(self.workspace,3)


if __name__=="__main__":
    unittest.main()
