"""T10 30 selected TAR-header candidate preflight (synthetic, offline only)."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
import test_t10_atika_acquisition_budget as _fixtures
import t10_atika_tar_header_walk as tar_walk
import t10_atika_tar_order_hypotheses as order
import t10_atika_selected_header_preflight as selected
from t10_atika_tar_layout_budget import ceil_to
from t10_public_id_corpus import METADATA_FILENAME


def packed_archive(rows):
    return ceil_to(
        1024 + sum(512 + ceil_to(size, 512) for _, size in rows),
        10240,
    )


class PurePredictedHeaderTests(unittest.TestCase):
    def setUp(self):
        self.rows = [(f"data/sample/{i:03}.wav", 44+i) for i in range(40)]
        self.names = {p for p, _ in self.rows[::2][:30]}
        # 20 even rows + 10 odd rows => precisely 30 unique selections.
        self.names.update(p for p, _ in self.rows[1::2][:10])
        self.tar_bytes = packed_archive(self.rows)

    def test_30_distinct_header_candidates_are_aligned(self):
        c = selected.predicted_selected_headers(
            list(reversed(self.rows)), self.names, self.tar_bytes
        )
        self.assertEqual(len(c), 30)
        self.assertEqual(len({off for _,off,_,_ in c}), 30)
        self.assertTrue(all(off % 512 == 0 for _,off,_,_ in c))
        self.assertEqual([idx for idx,_,_,_ in c], sorted(idx for idx,_,_,_ in c))

    def test_exact_order_offsets_not_csv_order(self):
        c = selected.predicted_selected_headers(
            list(reversed(self.rows)), self.names, self.tar_bytes
        )
        self.assertEqual(c[0][1], 0)
        self.assertEqual(c[1][1], 1024)

    def test_duplicate_metadata_blocks(self):
        with self.assertRaisesRegex(ValueError, "repeated"):
            selected.predicted_selected_headers(
                self.rows[:-1] + [self.rows[0]], self.names, self.tar_bytes
            )

    def test_missing_selected_path_blocks(self):
        bad = set(self.names)
        bad.pop()
        bad.add("data/unknown/selected.wav")
        with self.assertRaisesRegex(ValueError, "missing"):
            selected.predicted_selected_headers(self.rows, bad, self.tar_bytes)

    def test_nonflat_size_blocks(self):
        with self.assertRaisesRegex(ValueError, "inconsistent"):
            selected.predicted_selected_headers(self.rows, self.names, 907765760)

    def test_invalid_path_size_rejected(self):
        broken = list(self.rows)
        broken[7] = ("data/../unsafe.wav", 100)
        with self.assertRaisesRegex(ValueError, "Invalid"):
            selected.predicted_selected_headers(broken, self.names, self.tar_bytes)

    def test_bad_selection_count_rejected(self):
        with self.assertRaisesRegex(ValueError, "Invalid category"):
            selected.predicted_selected_headers(self.rows, set(), self.tar_bytes)


class FrozenPrivateFixtureTests(unittest.TestCase):
    make_files = _fixtures.OfflineAtikaAcquisitionBudgetTests.make_files
    cleanup_patches = _fixtures.OfflineAtikaAcquisitionBudgetTests.cleanup_patches

    def setUp(self):
        _fixtures.OfflineAtikaAcquisitionBudgetTests.setUp(self)
        self.ordered = sorted(self.rows, key=lambda r:r["audio_path"])
        self.first = patch.object(
            order, "OBSERVED_FIRST_MEMBER_SIZE",
            int(self.ordered[0]["file_size_bytes"]))
        self.end6 = patch.object(
            order, "OBSERVED_SIX_HEADER_NEXT_OFFSET",
            sum(512 + ceil_to(int(r["file_size_bytes"]),512) for r in self.ordered[:6]))
        self.flat = patch.object(
            tar_walk, "EXPECTED_TAR_BYTES",
            packed_archive([(r["audio_path"],int(r["file_size_bytes"])) for r in self.rows]))
        for obj in (self.first,self.end6,self.flat):
            obj.start()
            self.addCleanup(obj.stop)

    def test_private_offline_preflight_reports_counts_not_locations(self):
        result = selected.preflight(self.workspace)
        self.assertEqual(result["candidate_header_locations"], 30)
        self.assertEqual(result["category_wav_metadata_rows"], 35)
        self.assertEqual(result["frozen_selected_human_test_count"], 30)
        self.assertEqual(result["exact_selected_header_checks_performed"], 0)
        self.assertFalse(result["selected_header_offsets_verified"])
        self.assertEqual(result["CP4"], "BLOCKED")

    def test_no_network_wav_download_or_file_mutation(self):
        before = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                  for p in self.workspace.iterdir()}
        with patch("urllib.request.urlopen", side_effect=AssertionError("network")), patch.object(
                tar_walk, "fetch_header", side_effect=AssertionError("header network")):
            result = selected.preflight(self.workspace)
        after = {p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                 for p in self.workspace.iterdir()}
        self.assertEqual(before, after)
        self.assertEqual(result["network_requests_executed"], 0)

    def test_cli_never_discloses_paths_transcripts_or_offsets(self):
        out = io.StringIO()
        with patch.object(sys,"argv",["preflight","--workspace",str(self.workspace)]), redirect_stdout(out):
            self.assertEqual(selected.main(),0)
        displayed=out.getvalue()
        self.assertIn("OFFLINE ONLY",displayed)
        self.assertNotIn("data/sample",displayed)
        self.assertNotIn("data/fictional",displayed)
        self.assertNotIn("fixture text",displayed)
        self.assertNotIn("0, 1024",displayed)

    def test_mutated_metadata_sha_blocks(self):
        path=self.workspace/METADATA_FILENAME
        path.write_bytes(path.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            selected.preflight(self.workspace)

    def test_unfrozen_selection_blocks(self):
        path=self.workspace/tar_walk.SELECTION_NAME
        path.write_bytes(path.read_bytes()+b"tamper")
        with self.assertRaises((ValueError,TypeError)):
            selected.preflight(self.workspace)


if __name__ == "__main__":
    unittest.main()
