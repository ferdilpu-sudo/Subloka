"""Offline-only synthetic tests for Python USTAR/PAX/GNU header footprint."""
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
import t10_atika_tar_format_footprint as audit
import t10_atika_tar_header_walk as walk
import t10_atika_tar_order_hypotheses as order
from t10_atika_tar_layout_budget import ceil_to


SHORT = "data/M1/short.wav"
LONG_SPLITTABLE = "data/" + "a"*95 + "/" + "z"*13 + ".wav"


def expected_archive(rows):
    return ceil_to(1024 + sum(512 + ceil_to(size, 512)
                              for _, size in rows), 10240)


class PureFormatModels(unittest.TestCase):
    def test_short_path_one_header_each(self):
        rows=[(SHORT, 100)]
        r=audit.footprint(rows,expected_archive(rows))
        self.assertEqual(r["python_tarfile_serialization_models"]["USTAR"]
                         ["simulated_member_header_bytes"],512)
        for fmt in ("PAX","GNU"):
            self.assertEqual(r["python_tarfile_serialization_models"][fmt]
                             ["extra_header_bytes_vs_one_512_per_WAV"],0)

    def test_long_splittable_ustar_single_header_and_pax_gnu_extra(self):
        self.assertGreater(len(LONG_SPLITTABLE.encode("utf-8")),100)
        rows=[(LONG_SPLITTABLE, 44)]
        r=audit.footprint(rows,expected_archive(rows))
        self.assertEqual(r["python_tarfile_serialization_models"]["USTAR"]
                         ["extra_header_bytes_vs_one_512_per_WAV"],0)
        for fmt in ("PAX","GNU"):
            result=r["python_tarfile_serialization_models"][fmt]
            self.assertEqual(result["extra_header_bytes_vs_one_512_per_WAV"],1024)
            self.assertEqual(result["names_that_triggered_extra_header_bytes"],1)

    def test_pax_extra_can_change_padded_archive_length(self):
        rows=[("data/" + "z"*95 + f"/f{i:03d}.wav",44) for i in range(30)]
        tar_bytes=expected_archive(rows)
        r=audit.footprint(rows,tar_bytes)["python_tarfile_serialization_models"]
        self.assertTrue(r["USTAR"]["simulated_archive_length_matches_pinned_public_size"])
        self.assertFalse(r["PAX"]["simulated_archive_length_matches_pinned_public_size"])
        self.assertFalse(r["GNU"]["simulated_archive_length_matches_pinned_public_size"])

    def test_padding_roundup_uses_10240(self):
        rows=[(SHORT,44)]
        r=audit.footprint(rows,expected_archive(rows))
        for fmt in audit.FORMATS:
            self.assertEqual(r["python_tarfile_serialization_models"][fmt]
                             ["simulated_archive_bytes_with_2_end_blocks_10240_padding"]
                             % 10240,0)

    def test_duplicate_name_rejected(self):
        rows=[(SHORT,44),(SHORT,55)]
        with self.assertRaisesRegex(ValueError,"Duplicated"):
            audit.footprint(rows,expected_archive(rows))

    def test_bad_member_path_rejected(self):
        for path in ("data/../bad.wav","/bad.wav","data/secret.txt"):
            with self.subTest(path=path), self.assertRaisesRegex(ValueError,"Invalid"):
                audit.footprint([(path,44)],10240)

    def test_bad_size_rejected(self):
        with self.assertRaisesRegex(ValueError,"Invalid"):
            audit.footprint([(SHORT,1)],10240)

    def test_empty_corpus_rejected(self):
        with self.assertRaisesRegex(ValueError,"Unsafe"):
            audit.footprint([],10240)

    def test_ustar_name_too_long_fails_closed(self):
        with self.assertRaisesRegex(ValueError,"encodable"):
            audit.footprint([("data/"+"z"*260+".wav",44)],10240)


class FrozenSyntheticWorkspace(unittest.TestCase):
    make_files=fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches=fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        ordered=sorted(self.rows,key=lambda x:x["audio_path"])
        one=int(ordered[0]["file_size_bytes"])
        first6=sum(512+ceil_to(int(r["file_size_bytes"]),512)
                   for r in ordered[:6])
        tar_bytes=expected_archive(
            [(r["audio_path"],int(r["file_size_bytes"])) for r in self.rows])
        for p in (
            patch.object(order,"OBSERVED_FIRST_MEMBER_SIZE",one),
            patch.object(order,"OBSERVED_SIX_HEADER_NEXT_OFFSET",first6),
            patch.object(walk,"EXPECTED_TAR_BYTES",tar_bytes),
        ):
            p.start()
            self.addCleanup(p.stop)

    def test_synthetic_private_no_network_no_mutation(self):
        before={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen",side_effect=AssertionError("network")),\
             patch.object(walk,"fetch_header",side_effect=AssertionError("fetch")):
            r=audit.report(self.workspace)
        after={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
               for p in self.workspace.iterdir()}
        self.assertEqual(before,after)
        self.assertEqual(r["network_requests_executed"],0)
        self.assertFalse(r["root_cause_proven"])
        self.assertEqual(r["entire_Imperative_category"]["metadata_members"],35)

    def test_cli_does_not_expose_names_or_offsets(self):
        buf=io.StringIO()
        with patch.object(sys,"argv",["format-audit","--workspace",str(self.workspace)]),\
             redirect_stdout(buf),patch.object(walk,"fetch_header",
                                        side_effect=AssertionError("fetch")):
            self.assertEqual(audit.main(),0)
        text=buf.getvalue()
        self.assertIn("OFFLINE TAR HEADER FOOTPRINT MODELS",text)
        self.assertNotIn("data/fictional",text)
        self.assertNotIn("fixture text",text)
        self.assertIn('"files_written": false',text)

    def test_mutated_selection_rejected(self):
        p=self.workspace/walk.SELECTION_NAME
        p.write_bytes(p.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            audit.report(self.workspace)

    def test_mutated_csv_rejected(self):
        p=self.workspace/fixtures.METADATA_FILENAME
        p.write_bytes(p.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            audit.report(self.workspace)


if __name__=="__main__":
    unittest.main()
