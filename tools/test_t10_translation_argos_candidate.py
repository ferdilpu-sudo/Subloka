"""Deterministic regression tests for host-only offline Argos ID->EN screening.

All tests use mock model outputs, fake small ZIPs and existing NEW paragraph
fixtures. No network, actual model, Argos Python package or Android required.
"""
from __future__ import annotations

import csv
import json
from pathlib import Path
import socket
import stat
import tempfile
import unittest
from unittest.mock import patch
import zipfile

from t10_translation_argos_protocol import (
    DIAGNOSTIC, MODEL_SHA256, MODEL_REVISION, MODEL_URL, OUTPUT_COLUMNS,
    PILOT_IDS, REVIEW_SHA256, STATUS,
    strict_review, pilot_rows, validate_argos_archive, write_csv, sha256, grade,
)
from t10_translation_strategy_ab_review import fixture_data, REVIEW_COLUMNS
from t10_translation_argos_candidate import (
    no_network, _generate_pilot, local_paths, isolated_argos_env,
    report,
)


def fake_review_data():
    fixtures = fixture_data()
    fails_id = {"id-ab-05", "id-ab-06", "id-ab-08", "id-ab-09",
                "id-ab-14", "id-ab-18", "id-ab-24", "id-ab-29", "id-ab-30"}
    fails_en = {"en-ab-01", "en-ab-04", "en-ab-09", "en-ab-10",
                "en-ab-16", "en-ab-19", "en-ab-26", "en-ab-29"}
    rows = []
    for i, fixture in enumerate(fixtures):
        order = ("whole", "linewise") if i % 2 == 0 else ("linewise", "whole")
        for strategy in order:
            rejected = fixture["id"] in (fails_id | fails_en)
            rows.append({
                "sample": fixture["id"],
                "source_language": fixture["language"],
                "target_language": "en" if fixture["language"] == "id" else "id",
                "source_text": fixture["text"],
                "strategy": strategy,
                "translation": "synthetic output for a test",
                "latency_ms": "40.0",
                "error": "",
                "call_count": "1" if strategy == "whole" else "2",
                "sequence": str(len(rows) + 1),
                "battery_c": "36.0",
                "status": "MAJOR_MEANING_ERROR" if rejected else "ACCEPT",
                "notes": "synthetic inaccurate meaning" if rejected else "",
            })
    return rows


def write_test_csv(file: Path, fields, rows):
    with file.open("w", newline="", encoding="utf-8-sig") as fp:
        writer = csv.DictWriter(fp, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def make_pilot_controls():
    fixtures = fixture_data()[:30]
    failures = {"id-ab-05", "id-ab-06", "id-ab-08", "id-ab-09"}
    return [{**f, "mlkit": {"translation": f"baseline output for {f['id']}",
                           "status": "MAJOR_MEANING_ERROR" if f["id"] in failures else "ACCEPT",
                           "notes": "wrong reference" if f["id"] in failures else ""}}
            for f in fixtures]


class T10ArgosIDToENTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.dir = Path(self.temp.name)

    def frozen_review(self):
        path = self.dir / "full-fake-review.csv"
        write_test_csv(path, REVIEW_COLUMNS, fake_review_data())
        return path

    def sample_rows(self):
        controls = make_pilot_controls()
        candidates = {
            sid: {"translation": "model inferred " + sid, "latency_ms": 34.5}
            for sid in PILOT_IDS
        }
        return pilot_rows(controls, candidates)

    def write_raw_session(self):
        path = self.dir / "pilot.csv"
        write_csv(path, self.sample_rows())
        meta = {"raw_sha256": sha256(path), "model_sha256": MODEL_SHA256,
                "status": "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4"}
        (self.dir / "session.json").write_text(json.dumps(meta))
        return path, meta

    def completed_review(self, raw, decisions):
        original = list(csv.DictReader(raw.open(encoding="utf-8-sig", newline="")))
        for row in original:
            status = decisions.get(row["sample"], row["mlkit_whole_status"])
            row["candidate_review_status"] = status
            row["candidate_notes"] = "candidate error" if status != "ACCEPT" else ""
        rated = self.dir / "rated.csv"
        write_test_csv(rated, OUTPUT_COLUMNS, original)
        return rated

    def test_first_ten_are_deterministic_and_not_cherry_picked(self):
        self.assertEqual(PILOT_IDS, tuple(f"id-ab-{i:02d}" for i in range(1, 11)))
        self.assertEqual(len(PILOT_IDS), 10)
        self.assertTrue(all(f["language"] == "id" for f in fixture_data()[:30]))

    def test_source_fixture_is_distinct_from_frozen_cp4(self):
        rows = fixture_data()
        self.assertEqual(len(rows), 60)
        self.assertTrue(all(len(row["text"].splitlines()) == 2 for row in rows))

    def test_pinned_offline_model_metadata_is_complete(self):
        self.assertEqual(MODEL_REVISION, "a69e5d5f51945c24ad8653c3255b87320af21a48")
        self.assertEqual(MODEL_SHA256, "b494f6109dd7ceae32cb44cc721a14039abce938dc773a70087e73301ef4fed4")
        self.assertEqual(len(REVIEW_SHA256), 64)
        self.assertTrue(MODEL_URL.startswith("https://huggingface.co/"))
        self.assertTrue(MODEL_REVISION in MODEL_URL)
        self.assertTrue(MODEL_URL.endswith("/translate-id_en-1_9.argosmodel"))

    def test_original_review_sha_has_fail_closed_behavior(self):
        input_file = self.frozen_review()
        with self.assertRaisesRegex(ValueError, "SHA256"):
            strict_review(input_file)

    def test_original_full_review_120_source_rows_grade_guard(self):
        review = self.frozen_review()
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            result = strict_review(review)
        self.assertEqual(len(result), 30)
        self.assertEqual(sum(r["mlkit"]["status"] == "ACCEPT" for r in result), 21)
        self.assertEqual(tuple(r["id"] for r in result[:10]), PILOT_IDS)

    def test_reviewer_cannot_change_original_source_or_strategies(self):
        review = self.frozen_review()
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["source_text"] = "changed original paragraph"
        write_test_csv(review, REVIEW_COLUMNS, rows)
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            with self.assertRaisesRegex(ValueError, "source or strategy"):
                strict_review(review)

    def test_reviewer_cannot_edit_reviewed_status_counts(self):
        review = self.frozen_review()
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        next(r for r in rows if r["sample"] == "id-ab-01" and r["strategy"] == "whole")["status"] = "MAJOR_MEANING_ERROR"
        rows[0]["notes"] = "test fake"
        write_test_csv(review, REVIEW_COLUMNS, rows)
        with patch("t10_translation_argos_protocol.sha256", return_value=REVIEW_SHA256):
            with self.assertRaisesRegex(ValueError, "Expected unchanged"):
                strict_review(review)

    def test_model_zip_sha_mismatch_refused(self):
        model = self.dir / "fake.argosmodel"
        model.write_bytes(b"NOT model weights")
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            validate_argos_archive(model)

    def test_zip_traversal_refused_before_argos_install(self):
        model = self.dir / "fake.argosmodel"
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("../outside.txt", "unsafe")
            z.writestr("sample/metadata.json", "{}")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                validate_argos_archive(model)

    def test_zip_symlink_refused_before_argos_install(self):
        model = self.dir / "fake.argosmodel"
        symlink = zipfile.ZipInfo("package/symlink")
        symlink.create_system = 3
        symlink.external_attr = (stat.S_IFLNK | 0o777) << 16
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("sample/metadata.json", "{}")
            z.writestr(symlink, "target")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "Unsafe"):
                validate_argos_archive(model)

    def test_zip_valid_shape_requires_metadata(self):
        model = self.dir / "fake.argosmodel"
        with zipfile.ZipFile(model, "w") as z:
            z.writestr("package/model.bin", b"weights")
        with patch("t10_translation_argos_protocol.sha256", return_value=MODEL_SHA256), patch(
            "t10_translation_argos_protocol.MODEL_BYTES_MIN", 0
        ):
            with self.assertRaisesRegex(ValueError, "metadata.json"):
                validate_argos_archive(model)

    def test_network_is_forbidden_during_local_inference(self):
        with no_network():
            with socket.socket() as sk:
                with self.assertRaisesRegex(RuntimeError, "network is forbidden"):
                    sk.connect(("127.0.0.1", 1))
        # Restore the real methods after the guard exits.
        self.assertTrue(callable(socket.socket.connect))

    def test_argos_packages_are_isolated_in_benchmark_workspace(self):
        model, packages = local_paths(self.dir)
        self.assertTrue(str(model).startswith(str(self.dir)))
        self.assertTrue(str(packages).startswith(str(self.dir)))
        with patch.dict("sys.modules", {}, clear=False):
            with patch.dict("os.environ", {}, clear=False):
                isolated_argos_env(packages)
                self.assertEqual(__import__("os").environ["ARGOS_PACKAGES_DIR"], str(packages))
                self.assertEqual(__import__("os").environ["ARGOS_DEVICE_TYPE"], "cpu")

    def test_pilot_requires_complete_nonblank_outputs(self):
        controls = make_pilot_controls()
        text = {sid: {"translation": "OK", "latency_ms": 11.0} for sid in PILOT_IDS}
        text["id-ab-04"]["translation"] = ""
        with self.assertRaisesRegex(ValueError, "invalid"):
            pilot_rows(controls, text)

    def test_pilot_rejects_missing_sample_or_reordered_selection(self):
        controls = make_pilot_controls()
        text = {sid: {"translation": "OK", "latency_ms": 11.0} for sid in reversed(PILOT_IDS)}
        with self.assertRaisesRegex(ValueError, "first 10"):
            pilot_rows(controls, text)

    def test_pilot_raw_has_no_autofilled_decisions(self):
        p = self.dir / "pilot.csv"
        write_csv(p, self.sample_rows())
        rows = list(csv.DictReader(p.open(encoding="utf-8-sig", newline="")))
        self.assertEqual(len(rows), 10)
        self.assertEqual(tuple(rows[0]), OUTPUT_COLUMNS)
        self.assertTrue(all(row["candidate_review_status"] == "" for row in rows))
        self.assertEqual(rows[0]["sample"], PILOT_IDS[0])

    def test_grade_requires_all_ten_filled(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[3]["candidate_review_status"] = ""
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "missing/invalid"):
            grade(raw, review, meta)

    def test_grade_rejects_model_output_edit(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["argos_translation"] = "tampered response"
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "altered"):
            grade(raw, review, meta)

    def test_grade_rejects_missing_reason(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {"id-ab-01": "NEGATION_ERROR"})
        rows = list(csv.DictReader(review.open(encoding="utf-8-sig", newline="")))
        rows[0]["candidate_notes"] = ""
        write_test_csv(review, OUTPUT_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "reason"):
            grade(raw, review, meta)

    def test_no_gain_does_not_promote_candidate(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["baseline_accept"], 6)
        self.assertEqual(outcome["argos_accept"], 6)
        self.assertEqual(outcome["verdict"], "NO_BASIS_TO_PROMOTE_FROM_HOST_PILOT")
        self.assertEqual(outcome["cp4"], "BLOCKED")

    def test_two_recoveries_and_no_new_errors_only_promising(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {"id-ab-05": "ACCEPT", "id-ab-06": "ACCEPT"})
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["candidate_wins"], 2)
        self.assertEqual(outcome["candidate_losses"], 0)
        self.assertEqual(outcome["net_additional_accepted"], 2)
        self.assertEqual(outcome["verdict"], "PROMISING_FOR_FULL_30_AND_NEW_INDEPENDENT_HOLDOUT")
        self.assertEqual(outcome["cp4"], "BLOCKED")

    def test_new_critical_negation_error_vetoes_promotion(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {
            "id-ab-05": "ACCEPT", "id-ab-06": "ACCEPT", "id-ab-01": "NEGATION_ERROR"
        })
        outcome = grade(raw, review, meta)
        self.assertEqual(outcome["new_critical_errors"], ["id-ab-01"])
        self.assertEqual(outcome["verdict"], "NO_BASIS_TO_PROMOTE_FROM_HOST_PILOT")

    def test_review_report_is_immutable_after_first_write(self):
        raw, meta = self.write_raw_session()
        review = self.completed_review(raw, {})
        first = report(self.dir, review)
        self.assertEqual(first["cp4"], "BLOCKED")
        with self.assertRaisesRegex(FileExistsError, "overwrite"):
            report(self.dir, review)

    def test_mock_pilot_generates_ten_outputs_and_session_without_network(self):
        controls = make_pilot_controls()
        source_review = self.dir / "fake-original-review.csv"
        source_review.write_text("synthetic", encoding="utf-8")
        model = self.dir / "model.argosmodel"
        observed = []
        def mock_translate(source):
            observed.append(source)
            return "SIMULATED " + source
        session = _generate_pilot(
            controls, source_review, model, self.dir, mock_translate,
            enforce_offline=True,
        )
        rows = list(csv.DictReader((session / "pilot.csv").open(encoding="utf-8-sig", newline="")))
        self.assertEqual(len(rows), 10)
        self.assertEqual(len(observed), 10)
        self.assertTrue(all(row["candidate_review_status"] == "" for row in rows))
        self.assertEqual(json.loads((session / "session.json").read_text())["cp4"], "BLOCKED")
        self.assertEqual(json.loads((session / "session.json").read_text())["status"],
                         "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4")


if __name__ == "__main__":
    unittest.main()
