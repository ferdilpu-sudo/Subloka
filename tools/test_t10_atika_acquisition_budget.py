"""Offline, synthetic-only regressions for Atika public WAV acquisition budgeting."""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import csv
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_atika_acquisition_budget import (
    budget, main, MAX_ACCEPTABLE_HEADER_REQUESTS, MAX_CATEGORY_ROWS,
)
from t10_atika_tar_header_walk import SELECTION_NAME
from t10_public_id_corpus import METADATA_FILENAME, REQUIRED, REVISION


class OfflineAtikaAcquisitionBudgetTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        privacy = patch("t10_id_independent_holdout.PRIVATE_BASE", self.base)
        privacy.start()
        self.addCleanup(privacy.stop)
        self.workspace = self.base / "test-public-atika"
        self.workspace.mkdir()
        self.paths = [f"data/fictional/M{i%3+1}/sample{i:02d}.wav" for i in range(30)]
        self.rows = [
            {
                "audio_path": f"data/fictional/M{i%3+1}/sample{i:02d}.wav",
                "split": "test" if i < 30 else "train",
                "category": "Imperative",
                "speaker_id": f"M{i%3+1}",
                "speaker_type": "human",
                "is_synthetic": "false",
                "transcript": "This is synthetic fixture text not actual human speech sample number " + str(i),
                "duration_sec": "3.0",
                "sample_rate": "16000",
                "num_channels": "1",
                "bits_per_sample": "16",
                "file_size_bytes": str(80000 + i * 100),
            }
            for i in range(35)
        ]
        self.make_files()

    def make_files(self):
        csv_file = self.workspace / METADATA_FILENAME
        with csv_file.open("w", encoding="utf-8", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=sorted(REQUIRED))
            writer.writeheader()
            writer.writerows(self.rows)
        digest = hashlib.sha256(csv_file.read_bytes()).hexdigest()
        self.patches = [
            patch("t10_atika_acquisition_budget.PINNED_METADATA_SHA", digest),
            patch("t10_atika_tar_header_walk.PINNED_METADATA_SHA", digest),
        ]
        for active in getattr(self, "_active_patches", []):
            active.stop()
        self._active_patches = self.patches
        for active in self._active_patches:
            active.start()
        self.addCleanup(self.cleanup_patches)
        selection = {
            "schema_version": 1,
            "source": {"immutable_upstream_revision": REVISION},
            "selected_category": "Imperative",
            "source_split": "test",
            "sample_count": 30,
            "metadata_sha256": digest,
            "all_audio_downloaded": False,
            "items": [{
                "source_audio_tar_member": row["audio_path"],
                "speaker_label": row["speaker_id"],
                "reference_from_publisher_not_rechecked": row["transcript"],
                "audio_expected_bytes_from_publisher": int(row["file_size_bytes"]),
            } for row in self.rows[:30]],
        }
        (self.workspace / SELECTION_NAME).write_text(
            json.dumps(selection), encoding="utf-8"
        )

    def cleanup_patches(self):
        for active in self._active_patches:
            active.stop()
        self._active_patches = []

    def edit_selection(self, updater):
        path = self.workspace / SELECTION_NAME
        doc = json.loads(path.read_text(encoding="utf-8"))
        updater(doc)
        path.write_text(json.dumps(doc), encoding="utf-8")

    def test_budget_reports_30_selected_and_35_category_rows(self):
        report = budget(self.workspace)
        self.assertEqual(report["category_rows_in_metadata"], 35)
        self.assertEqual(report["selected_test_human_audio_count"], 30)
        self.assertEqual(report["category_human_test_rows_eligible"], 30)
        self.assertEqual(report["selected_public_speaker_label_count"], 3)
        self.assertEqual(report["source_archive_size_bytes_from_remote_metadata"], 907765760)
        self.assertEqual(report["estimated_one_request_per_WAV_header_scan"], 35)
        self.assertFalse(report["estimated_header_request_count_exceeds_safety_budget"])
        self.assertFalse(report["selected_audio_locally_verified"])
        self.assertFalse(report["public_per_WAV_tar_offset_index_verified"])
        self.assertEqual(report["CP4"], "BLOCKED")

    def test_calculated_selected_bytes_sum_matches_metadata(self):
        report = budget(self.workspace)
        self.assertEqual(
            report["selected_audio_bytes_sum_from_publisher_metadata"],
            sum(80000 + i * 100 for i in range(30))
        )
        self.assertEqual(len(report["network_delay_illustrations_not_predictions"]), 3)

    def test_offline_reads_leave_both_private_files_identical(self):
        original = {p.name: p.read_bytes() for p in self.workspace.iterdir() if p.is_file()}
        budget(self.workspace)
        after = {p.name: p.read_bytes() for p in self.workspace.iterdir() if p.is_file()}
        self.assertEqual(original, after)

    def test_no_network_call_even_under_patch_guard(self):
        with patch("urllib.request.urlopen", side_effect=AssertionError("No network allowed")):
            budget(self.workspace)

    def test_missing_csv_fails_closed(self):
        (self.workspace / METADATA_FILENAME).unlink()
        with self.assertRaisesRegex(ValueError, "Missing"):
            budget(self.workspace)

    def test_modified_upstream_csv_hash_rejected(self):
        path = self.workspace / METADATA_FILENAME
        path.write_bytes(path.read_bytes() + b"\n")
        with self.assertRaisesRegex(ValueError, "digest"):
            budget(self.workspace)

    def test_selected_wav_length_mismatch_rejected(self):
        self.edit_selection(lambda s: s["items"][0].update({
            "audio_expected_bytes_from_publisher": 1
        }))
        with self.assertRaisesRegex(ValueError, "bytes"):
            budget(self.workspace)

    def test_selected_speaker_mismatch_rejected(self):
        self.edit_selection(lambda s: s["items"][0].update({
            "speaker_label": "wrong"
        }))
        with self.assertRaisesRegex(ValueError, "speaker/transcript"):
            budget(self.workspace)

    def test_reference_mismatch_rejected(self):
        self.edit_selection(lambda s: s["items"][0].update({
            "reference_from_publisher_not_rechecked": "fabricated reference"
        }))
        with self.assertRaisesRegex(ValueError, "speaker/transcript"):
            budget(self.workspace)

    def test_unknown_selection_path_refused(self):
        self.edit_selection(lambda s: s["items"][0].update({
            "source_audio_tar_member": "data/fictional/unknown/a.wav"
        }))
        with self.assertRaisesRegex(ValueError, "missing"):
            budget(self.workspace)

    def test_no_public_directory_allowed(self):
        with tempfile.TemporaryDirectory() as outside:
            with self.assertRaisesRegex(ValueError, "gitignored"):
                budget(Path(outside))

    def test_threshold_warning_if_representative_category_large(self):
        with patch("t10_atika_acquisition_budget.MAX_ACCEPTABLE_HEADER_REQUESTS", 20):
            result = budget(self.workspace)
        self.assertTrue(result["estimated_header_request_count_exceeds_safety_budget"])
        self.assertIn("DO_NOT_SCAN", result["recommended_next_action"])

    def test_cli_aggregate_does_not_disclose_paths_or_transcripts(self):
        output = io.StringIO()
        with patch.object(sys, "argv", [
            "t10_atika_acquisition_budget.py", "--workspace", str(self.workspace),
        ]), redirect_stdout(output):
            self.assertEqual(main(), 0)
        text = output.getvalue()
        self.assertIn("OFFLINE ONLY", text)
        self.assertNotIn("fictional/M1", text)
        self.assertNotIn("fixture text", text)
        self.assertIn('"CP4": "BLOCKED"', text)

    def test_invalid_wav_metadata_rejected_with_digest_still_pinned(self):
        self.rows[32]["file_size_bytes"] = "invalid"
        self.make_files()
        with self.assertRaisesRegex(ValueError, "Non-numeric"):
            budget(self.workspace)


if __name__ == "__main__":
    unittest.main()
