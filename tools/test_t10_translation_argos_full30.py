"""Synthetic, dependency-free checks for distinct T10 Argos full-30 host gate.

No Argos model, Stanza/PyTorch install, external network or Android required.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from t10_translation_argos_candidate import no_network
from t10_translation_argos_full30 import _generate_full30, full30, report_full30
from t10_translation_argos_full30_protocol import (
    FULL30_DIAGNOSTIC, FULL30_IDS, EXTRA20_IDS,
    full30_rows, grade_full30,
)
from t10_translation_argos_protocol import (
    OUTPUT_COLUMNS, REVIEW_SHA256, MODEL_SHA256, sha256, write_csv,
)


class T10Full30Tests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)
        self.frozen = self.dir / "frozen.csv"
        self.frozen.write_bytes(b"synthetic only, do not use for actual inference")
        self.status_by_id = {
            "id-ab-05": "NUMBER_OR_NAME_ERROR",
            "id-ab-06": "MAJOR_MEANING_ERROR",
            "id-ab-08": "MAJOR_MEANING_ERROR",
            "id-ab-09": "MAJOR_MEANING_ERROR",
        }
        self.control = [
            {
                "id": sid,
                "text": "Sumber teks simulasi " + sid,
                "risk_tag": "synthetic",
                "mlkit": {
                    "translation": "ML Kit result " + sid,
                    "status": self.status_by_id.get(sid, "ACCEPT"),
                    "notes": "synthetic rejection" if sid in self.status_by_id else "",
                },
            }
            for sid in FULL30_IDS
        ]

    def _predictions(self):
        return {
            sid: {"translation": "Argos simulation " + sid, "latency_ms": 14.5}
            for sid in FULL30_IDS
        }

    def _raw_and_review(self):
        raw = self.dir / "full30.csv"
        rated = self.dir / "review.csv"
        session = {
            "experiment": FULL30_DIAGNOSTIC,
            "status": "HOST_FULL30_COMPLETE_REVIEW_PENDING_NOT_CP4",
            "source_review_sha256": REVIEW_SHA256,
            "model_sha256": MODEL_SHA256,
            "source_sample_ids": list(FULL30_IDS),
        }
        original = full30_rows(self.control, self._predictions())
        write_csv(raw, original)
        session["raw_sha256"] = sha256(raw)
        review_rows = [
            {
                **row,
                "candidate_review_status": (
                    "MAJOR_MEANING_ERROR" if row["sample"] == "id-ab-09" else
                    "NUMBER_OR_NAME_ERROR" if row["sample"] == "id-ab-05" else
                    "ACCEPT"
                ),
                "candidate_notes": (
                    "synthetic candidate issue" if row["sample"] in
                    ("id-ab-05", "id-ab-09") else ""
                ),
            }
            for row in original
        ]
        write_csv(rated, review_rows)
        return raw, rated, session, review_rows

    def test_exact_thirty_sources_and_blank_candidate_review(self):
        rows = full30_rows(self.control, self._predictions())
        self.assertEqual(len(rows), 30)
        self.assertEqual(tuple(r["sample"] for r in rows), FULL30_IDS)
        self.assertEqual([r["candidate_review_status"] for r in rows], [""] * 30)
        self.assertEqual(rows[0]["source_text"], self.control[0]["text"])
        self.assertEqual(rows[-1]["mlkit_whole_translation"],
                         self.control[-1]["mlkit"]["translation"])

    def test_missing_or_reordered_sample_ids_fail_closed(self):
        translations = self._predictions()
        translations.pop("id-ab-10")
        with self.assertRaisesRegex(ValueError, "exactly 30 pinned"):
            full30_rows(self.control, translations)
        altered = list(reversed(self.control))
        with self.assertRaisesRegex(ValueError, "30 frozen"):
            full30_rows(altered, self._predictions())

    def test_all_thirty_validate_candidate_nonempty_positive_latency(self):
        for invalid in ("", None, 1):
            with self.subTest(invalid=invalid):
                predictions = self._predictions()
                predictions["id-ab-17"]["translation"] = invalid
                with self.assertRaisesRegex(ValueError, "Invalid full30"):
                    full30_rows(self.control, predictions)
        for invalid in (0, -2, float("inf"), float("nan"), True):
            with self.subTest(latency=invalid):
                predictions = self._predictions()
                predictions["id-ab-20"]["latency_ms"] = invalid
                with self.assertRaisesRegex(ValueError, "Invalid full30"):
                    full30_rows(self.control, predictions)

    def test_grade_separates_pilot_overlap_and_existing_extra20(self):
        raw, review, session, rows = self._raw_and_review()
        result = grade_full30(raw, review, session)
        self.assertEqual(result["full30"]["sample_count"], 30)
        self.assertEqual(result["pilot_overlap_first10"]["sample_count"], 10)
        self.assertEqual(result["previously_unseen_fixture_extra20"]["sample_count"], 20)
        self.assertEqual(result["extra20_sample_ids"], list(EXTRA20_IDS))
        self.assertEqual(result["pilot_overlap_first10"]["mlkit_whole_accept"], 6)
        self.assertEqual(result["pilot_overlap_first10"]["argos_accept"], 8)
        self.assertEqual(result["pilot_overlap_first10"]["net_additional_accepted"], 2)
        self.assertEqual(result["previously_unseen_fixture_extra20"]["net_additional_accepted"], 0)
        self.assertEqual(result["full30"]["argos_accept"], 28)
        self.assertEqual(result["full30"]["mlkit_whole_accept"], 26)
        self.assertEqual(result["verdict"],
                         "DESCRIPTIVE_FULL30_ONLY_INDEPENDENT_HOLDOUT_REQUIRED")
        self.assertEqual(result["cp4"], "BLOCKED")

    def test_review_cannot_change_any_original_mlkit_or_argos_field(self):
        raw, review, session, rows = self._raw_and_review()
        rows[17]["argos_translation"] = "tampered Argos result"
        self._overwrite_review(review, rows)
        with self.assertRaisesRegex(ValueError, "altered immutable"):
            grade_full30(raw, review, session)

    def test_report_rejects_partial_review_and_missing_notes(self):
        raw, review, session, rows = self._raw_and_review()
        rows[24]["candidate_review_status"] = ""
        self._overwrite_review(review, rows)
        with self.assertRaisesRegex(ValueError, "Missing/invalid"):
            grade_full30(raw, review, session)
        rows[24]["candidate_review_status"] = "NEGATION_ERROR"
        rows[24]["candidate_notes"] = ""
        self._overwrite_review(review, rows)
        with self.assertRaisesRegex(ValueError, "rejection must include"):
            grade_full30(raw, review, session)

    def test_grade_detects_new_critical_error_in_additional20(self):
        raw, review, session, rows = self._raw_and_review()
        rows[21]["candidate_review_status"] = "NEGATION_ERROR"
        rows[21]["candidate_notes"] = "synthetic new negation failure"
        self._overwrite_review(review, rows)
        result = grade_full30(raw, review, session)
        self.assertEqual(result["previously_unseen_fixture_extra20"]["new_critical_errors"],
                         ["id-ab-22"])
        self.assertEqual(result["cp4"], "BLOCKED")

    def test_grade_rejects_wrong_raw_hash_source_or_model(self):
        raw, review, session, _ = self._raw_and_review()
        for field in ("raw_sha256", "source_review_sha256", "model_sha256"):
            with self.subTest(field=field):
                invalid = {**session, field: "invalid"}
                with self.assertRaises(ValueError):
                    grade_full30(raw, review, invalid)

    def test_full30_synthetic_inference_offline_and_separate_session(self):
        with patch("t10_translation_argos_full30.strict_review", return_value=self.control), patch(
            "t10_translation_argos_full30.validate_argos_archive"
        ):
            with no_network():
                session = full30(
                    self.frozen, self.dir,
                    translate_fn=lambda text: "synthetic-only: " + text,
                )
        self.assertTrue(session.name.startswith("argos-id-en-full30-"))
        self.assertTrue((session / "full30.csv").exists())
        self.assertFalse((session / "pilot.csv").exists())
        metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["source_sample_ids"], list(FULL30_IDS))
        self.assertEqual(metadata["status"], "HOST_FULL30_COMPLETE_REVIEW_PENDING_NOT_CP4")
        self.assertEqual(metadata["raw_sha256"], sha256(session / "full30.csv"))
        self.assertEqual(metadata["additional_existing_fixture20"], list(EXTRA20_IDS))
        self.assertEqual(metadata["cp4"], "BLOCKED")

    def test_partial_failure_refuses_scored_csv_and_records_partial(self):
        def fail_at_17(text):
            if "id-ab-17" in text:
                raise RuntimeError("synthetic offline inference failed")
            return text
        with self.assertRaisesRegex(RuntimeError, "synthetic offline inference failed"):
            _generate_full30(self.control, self.frozen, self.dir, fail_at_17,
                             sbd_mode="SYNTHETIC_TEST_ONLY")
        sessions = list(self.dir.glob("argos-id-en-full30-*"))
        self.assertEqual(len(sessions), 1)
        self.assertFalse((sessions[0] / "full30.csv").exists())
        metadata = json.loads((sessions[0] / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(metadata["successful_translations"], 16)
        self.assertEqual(metadata["status"], "HOST_FULL30_ABORTED_NO_QUALITY_VERDICT")

    def test_report_refuses_overwrite_even_after_success(self):
        raw, reviewed, meta, _ = self._raw_and_review()
        session = self.dir / "verified-session"
        session.mkdir()
        (session / "full30.csv").write_bytes(raw.read_bytes())
        (session / "session.json").write_text(json.dumps(meta), encoding="utf-8")
        report = report_full30(session, reviewed)
        self.assertEqual(report["cp4"], "BLOCKED")
        self.assertTrue((session / "full30-review-report.json").exists())
        with self.assertRaisesRegex(FileExistsError, "refusing overwrite"):
            report_full30(session, reviewed)

    @staticmethod
    def _overwrite_review(path, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS)
            writer.writeheader()
            writer.writerows(rows)


if __name__ == "__main__":
    unittest.main()
