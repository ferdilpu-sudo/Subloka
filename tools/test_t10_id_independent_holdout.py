"""Synthetic-only private Indonesian holdout audit/immutability regressions.

These fake WAV fixtures are generated in temp dirs and never count as genuine
human speech, consent, independence, benchmark quality or CP4 evidence.
"""
from __future__ import annotations

from contextlib import redirect_stdout, redirect_stderr
import hashlib
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_id_independent_holdout import (
    audit, init, main, seal, verify, sha256_file, validate_audio_path,
)


class IndependentHoldoutSyntheticTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name) / "private"
        self.root.mkdir()
        (self.root / "audio").mkdir()
        self.rows = []
        for i in range(1, 31):
            category = "clean" if i <= 20 else "challenging"
            local = i if i <= 20 else i - 20
            identifier = f"id-{category}-{local:02d}"
            relative = f"audio/{identifier}.wav"
            filepath = self.root / relative
            with wave.open(str(filepath), "wb") as w:
                w.setnchannels(1)
                w.setsampwidth(2)
                w.setframerate(16000)
                w.writeframes(bytes([i, 0]) * 16000)
            self.rows.append({
                "id": identifier, "category": category, "language": "id",
                "audio": relative, "audio_sha256": sha256_file(filepath),
                "reference": (
                    "Kami hari ini mendengar suara Indonesia yang jelas dan "
                    "menulis seluruh kalimat yang diucapkan dengan tepat untuk rekaman "
                    + str(i)
                ),
                "speaker_id": f"spk-{(i - 1) % 5 + 1:02d}",
                "recorded_utc": "2026-10-10T04:00:00Z",
                "consent_scope": "offline_asr_evaluation_only",
                "consent_declared": True,
                "human_reference_reviewed": True,
                "reference_reviewed_by": "rev-01",
                "origin": "fresh_consented_recording_not_public_corpus",
            })
        self.write_manifest()

    def write_manifest(self):
        (self.root / "manifest.json").write_text(json.dumps({
            "schema_version": 1, "purpose": "independent_id_asr_holdout",
            "samples": self.rows,
        }, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_full_synthetic_integrity_audit_is_not_independence(self):
        report = audit(self.root)
        self.assertEqual(report["clean_samples"], 20)
        self.assertEqual(report["challenging_samples"], 10)
        self.assertEqual(report["pseudonymous_speakers"], 5)
        self.assertGreaterEqual(report["clean_reference_words"], 250)
        self.assertEqual(len(report["assets"]), 30)
        self.assertEqual(report["CP4"], "BLOCKED")
        self.assertFalse(report["real_consent_and_human_independence_authenticated"])
        self.assertFalse(report["training_overlap_independently_excluded"])
        self.assertFalse(report["inference_performed"])

    def test_private_empty_init_is_not_real_dataset_and_cannot_overwrite(self):
        other = self.root.parent / "new-private"
        with redirect_stdout(io.StringIO()):
            init(other)
        self.assertEqual(json.loads((other / "manifest.json").read_text())["samples"], [])
        with self.assertRaisesRegex(ValueError, "Exactly 20"):
            audit(other)
        with self.assertRaises(FileExistsError):
            init(other)
        self.assertFalse((other / "manifest.lock.json").exists())

    def test_missing_consent_is_rejected(self):
        self.rows[0]["consent_declared"] = False
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "permission"):
            audit(self.root)
        self.assertFalse((self.root / "manifest.lock.json").exists())

    def test_unreviewed_human_reference_rejected(self):
        self.rows[4]["human_reference_reviewed"] = False
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "human listening"):
            audit(self.root)

    def test_fleurs_or_public_corpus_not_falsely_included(self):
        self.rows[0]["origin"] = "FLEURS"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "independent source"):
            audit(self.root)

    def test_reference_duplicates_or_weak_clean_word_total_rejected(self):
        self.rows[1]["reference"] = self.rows[0]["reference"]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Duplicate normalized"):
            audit(self.root)
        for idx in range(20):
            self.rows[idx]["reference"] = f"Ini adalah kalimat pendek {idx}"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "250 clean words"):
            audit(self.root)

    def test_audio_sha_mismatch_fails_without_lock(self):
        audio = self.root / self.rows[0]["audio"]
        with audio.open("ab") as f:
            f.write(b"\x01")
        with self.assertRaisesRegex(ValueError, "WAV bytes changed"):
            audit(self.root)
        with self.assertRaises(ValueError):
            seal(self.root)
        self.assertFalse((self.root / "manifest.lock.json").exists())

    def test_recording_non_pcm_wrong_rate_rejected(self):
        file = self.root / self.rows[0]["audio"]
        with wave.open(str(file), "wb") as w:
            w.setnchannels(1)
            w.setsampwidth(2)
            w.setframerate(8000)
            w.writeframes(bytes([1, 0]) * 8000)
        self.rows[0]["audio_sha256"] = sha256_file(file)
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "mono PCM16"):
            audit(self.root)

    def test_private_path_traversal_and_nonlocal_mount_rejected(self):
        for bad in ("../../escape.wav", "audio/../escape.wav",
                    "/tmp/x.wav", "C:\\private\\audio.wav", "outside/x.wav"):
            with self.subTest(path=bad):
                with self.assertRaises(ValueError):
                    validate_audio_path(self.root, bad)

    def test_missing_fifth_speaker_fails(self):
        for r in self.rows:
            r["speaker_id"] = "spk-01"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "five|>=5"):
            audit(self.root)

    def test_category_order_and_count_fails_closed(self):
        self.rows[0], self.rows[1] = self.rows[1], self.rows[0]
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "sample ID/order"):
            audit(self.root)
        self.rows.pop()
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Exactly 20"):
            audit(self.root)

    def test_missing_timezone_and_future_date_rejected(self):
        self.rows[0]["recorded_utc"] = "2026-10-10T10:00:00"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "timezone"):
            audit(self.root)
        self.rows[0]["recorded_utc"] = "2099-01-01T00:00:00Z"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "range"):
            audit(self.root)

    def test_seal_and_verify_detect_reference_and_wav_changes(self):
        original = seal(self.root)
        self.assertEqual(original["CP4"], "BLOCKED")
        self.assertEqual(verify(self.root)["manifest_sha256"],
                         original["audit"]["manifest_sha256"])
        with self.assertRaises(FileExistsError):
            seal(self.root)
        self.rows[0]["reference"] += " satu"
        self.write_manifest()
        with self.assertRaisesRegex(ValueError, "Locked manifest"):
            verify(self.root)
        self.rows[0]["reference"] = self.rows[0]["reference"][:-5]
        self.write_manifest()
        self.assertEqual(verify(self.root)["manifest_sha256"],
                         original["audit"]["manifest_sha256"])
        with (self.root / self.rows[0]["audio"]).open("ab") as f:
            f.write(b"unwanted")
        with self.assertRaisesRegex(ValueError, "WAV bytes changed"):
            verify(self.root)

    def test_lock_never_contains_transcript_or_raw_audio(self):
        seal(self.root)
        lock_text = (self.root / "manifest.lock.json").read_text(encoding="utf-8")
        self.assertNotIn("Kami hari ini mendengar suara", lock_text)
        self.assertNotIn("spk-01", lock_text)
        self.assertNotIn("rev-01", lock_text)
        self.assertIn("manifest_sha256", lock_text)

    def test_cli_audit_and_seal_never_promote_cp4(self):
        for command in ("audit", "seal", "verify"):
            buffer = io.StringIO()
            with patch.object(sys, "argv", [
                "t10_id_independent_holdout.py", command,
                "--workspace", str(self.root),
            ]), redirect_stdout(buffer):
                self.assertEqual(main(), 0)
            self.assertIn("CP4 BLOCKED", buffer.getvalue())
            self.assertIn("NO DOWNLOAD | NO ADB | NO INFERENCE", buffer.getvalue())
        self.assertTrue((self.root / "manifest.lock.json").is_file())

    def test_bad_lock_is_rejected(self):
        seal(self.root)
        p = self.root / "manifest.lock.json"
        payload = json.loads(p.read_text(encoding="utf-8"))
        payload["CP4"] = "PASS"
        p.write_text(json.dumps(payload), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "lock schema"):
            verify(self.root)

    def test_cli_empty_workspace_audit_fails_safe(self):
        other = self.root.parent / "empty"
        with redirect_stdout(io.StringIO()):
            init(other)
        with patch.object(sys, "argv", [
            "t10_id_independent_holdout.py", "audit", "--workspace", str(other),
        ]), redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
