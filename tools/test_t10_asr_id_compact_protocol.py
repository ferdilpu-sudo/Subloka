"""T10 strict no-download Indonesian GGML candidate catalog and local SHA test."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_asr_id_compact_protocol import (
    CANDIDATES, MODEL_KEYS, catalog_report, main, verify_local, write_once,
)


class CompactASRProtocolTests(unittest.TestCase):
    def test_exact_two_publisher_sha256_pins(self):
        self.assertEqual(MODEL_KEYS, ("maleo_base_id_q8_0", "maleo_tiny_id_q8_0"))
        self.assertEqual(CANDIDATES["maleo_base_id_q8_0"]["sha256"],
                         "2ac0dc902f477389be18d8b6f6fbe97695197c12ab1392b2f4bea23732c2cfe8")
        self.assertEqual(CANDIDATES["maleo_tiny_id_q8_0"]["sha256"],
                         "423455afe438ff3b0d1f23613a223d052f34a2482a8dd8ef6433f75ccbf33a17")

    def test_reports_license_claim_distinct_from_legal_audit(self):
        report = catalog_report()
        self.assertEqual(report["CP4"], "BLOCKED")
        self.assertEqual(report["status"], "PINNED_SOURCE_SHA_ONLY_NO_LOCAL_ARTIFACT")
        self.assertTrue(any("legal audit" in line for line in report["limitations"]))
        for candidate in report["models"]:
            self.assertEqual(candidate["claimed_license"], "apache-2.0")
            self.assertTrue(candidate["source_page"].startswith("https://huggingface.co/"))
            self.assertFalse(candidate["safe_to_download_automatically"])
            self.assertFalse(candidate["safe_to_run_on_sony"])
            self.assertFalse(candidate["exact_local_model_verified"])

    def test_explicit_fleurs_training_overlap_warning(self):
        report = catalog_report()
        self.assertTrue(any("train/evaluation sample overlap" in msg for msg in report["limitations"]))
        self.assertTrue(any("human" in msg.lower() for msg in report["limitations"]))
        self.assertEqual(report["T10"], "ACTIVE")
        self.assertEqual(report["T11"], "TODO")

    def test_frozen_baseline_pins_retained(self):
        report = catalog_report()
        self.assertEqual(set(report["original_evidence_sha256"]), {"asr", "small", "cp4"})
        self.assertEqual(len(report["original_evidence_sha256"]["asr"]), 64)
        self.assertIn("105 edits / 367 words", report["original_id_clean"])

    def test_missing_local_artifact_fails(self):
        with tempfile.TemporaryDirectory() as temp:
            with self.assertRaisesRegex(ValueError, "ordinary file"):
                verify_local("maleo_base_id_q8_0", Path(temp) / "missing.bin")
            with self.assertRaisesRegex(ValueError, "ordinary file"):
                verify_local("maleo_base_id_q8_0", Path(temp))
        with self.assertRaisesRegex(ValueError, "Unknown"):
            verify_local("unregistered", Path("unused"))

    def test_bad_size_or_corrupt_sha_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "artifact.bin"
            p.write_bytes(b"x" * 200)
            with self.assertRaisesRegex(ValueError, "size"):
                verify_local("maleo_tiny_id_q8_0", p)
            p.write_bytes(b"x" * 43_500_000)
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                verify_local("maleo_tiny_id_q8_0", p)

    def test_exact_checksum_verification_is_only_bytes_not_quality(self):
        data = b"synthetic tiny data without network"
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "model.bin"
            p.write_bytes(data)
            overridden = dict(CANDIDATES["maleo_tiny_id_q8_0"])
            overridden["sha256"] = hashlib.sha256(data).hexdigest()
            overridden["display_size_mb_decimal"] = len(data) / 1_000_000
            with patch.dict(CANDIDATES, {"maleo_tiny_id_q8_0": overridden}):
                report = verify_local("maleo_tiny_id_q8_0", p)
            self.assertTrue(report["local_sha256_verified"])
            self.assertFalse(report["download_or_device_inference_performed"])
            self.assertFalse(report["sony_accuracy_and_runtime_proven"])
            self.assertFalse(report["independent_holdout_review_complete"])
            self.assertEqual(report["CP4"], "BLOCKED")

    def test_file_symlink_forbidden(self):
        with tempfile.TemporaryDirectory() as temp:
            p = Path(temp) / "real.bin"
            p.write_bytes(b"mock")
            link = Path(temp) / "shortcut.bin"
            try:
                link.symlink_to(p)
            except (OSError, NotImplementedError):
                self.skipTest("OS does not permit symlink in test environment")
            with self.assertRaisesRegex(ValueError, "ordinary file"):
                verify_local("maleo_tiny_id_q8_0", link)

    def test_write_once_never_overwrites(self):
        with tempfile.TemporaryDirectory() as temp:
            f = Path(temp) / "report.json"
            write_once(f, {"CP4": "BLOCKED"})
            frozen = f.read_bytes()
            with self.assertRaises(FileExistsError):
                write_once(f, {"CP4": "PASS"})
            self.assertEqual(f.read_bytes(), frozen)

    def test_cli_list_is_network_free_and_without_model(self):
        output = io.StringIO()
        with patch.object(sys, "argv", ["t10_asr_id_compact_protocol.py", "list"]), \
             redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertIn("maleo_base_id_q8_0", output.getvalue())
        self.assertIn("NO DOWNLOAD | NO ADB | NO INFERENCE", output.getvalue())
        self.assertIn("CP4 BLOCKED", output.getvalue())

    def test_cli_verify_missing_artifact_refuses_without_report(self):
        with tempfile.TemporaryDirectory() as temp:
            report = Path(temp) / "result.json"
            with patch.object(sys, "argv", [
                "t10_asr_id_compact_protocol.py", "verify",
                "--model", "maleo_base_id_q8_0",
                "--file", str(Path(temp) / "absent.bin"),
                "--json", str(report),
            ]), redirect_stderr(io.StringIO()):
                self.assertEqual(main(), 1)
            self.assertFalse(report.exists())

    def test_evidence_catalog_has_no_approval_even_with_sha_pin(self):
        report = catalog_report()
        self.assertEqual(len(report["models"]), 2)
        self.assertEqual([m["priority"] for m in report["models"]], [1, 2])
        self.assertEqual(
            [m["display_size_mb_decimal"] for m in report["models"]], [81.8, 43.5]
        )
        for m in report["models"]:
            self.assertFalse(m["eligible_to_replace_frozen_baseline"])
            self.assertFalse(m["independent_holdout_ready"])


if __name__ == "__main__":
    unittest.main()
