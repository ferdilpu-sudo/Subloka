"""Dependency-free regression guards for T10 CP4 read-only evidence auditor."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
from copy import deepcopy
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

from t10_cp4_readiness import EVIDENCE, ROOT, audit, evaluate, main


class T10CP4ReadinessTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.evidence_root = ROOT / ".agents" / "evidence"
        cls.original = {
            name: json.loads((cls.evidence_root / path).read_text(encoding="utf-8-sig"))
            for name, path in EVIDENCE.items()
        }

    def test_real_committed_evidence_stays_blocked(self):
        result = audit(self.evidence_root)
        self.assertEqual(result["cp4_status"], "BLOCKED")
        self.assertEqual(result["asr_clean_id"]["base_word_errors"], 105)
        self.assertEqual(result["asr_clean_id"]["reference_words"], 367)
        self.assertEqual(result["asr_clean_id"]["minimum_edit_reduction_to_gate"], 32)
        self.assertEqual(result["translation_original_cp4"]["id_en_gap"], 3)
        self.assertEqual(result["translation_original_cp4"]["en_id_gap"], 0)
        self.assertEqual(result["t11_status"], "TODO")
        self.assertEqual(set(result["evidence_sha256"]), set(EVIDENCE))

    def test_asr_clean_failure_cannot_be_reinterpreted_as_media_success(self):
        result = evaluate(deepcopy(self.original))
        self.assertEqual(result["asr_clean_id"]["status"], "FAIL_MANDATORY_SUBSET")
        self.assertEqual(result["sony_real_video_media"]["status"],
                         "MEDIA_STAGE_PASS_NOT_FULL_E2E")
        self.assertEqual(result["sony_real_video_media"]["full_app_video_to_subtitle_export_e2e"],
                         "NOT_RUN")
        self.assertEqual(result["cp4_status"], "BLOCKED")

    def test_original_cp4_translation_is_not_60_paragraph_diagnostic(self):
        result = evaluate(deepcopy(self.original))
        self.assertEqual(result["translation_original_cp4"]["id_en_accepted"], 24)
        self.assertEqual(result["later_paragraph_translation_diagnostic"]["mlkit_id_en_whole_accepted"], 21)
        self.assertFalse(result["later_paragraph_translation_diagnostic"]["used_as_original_cp4"])

    def test_argos_pilot_does_not_promote_or_replace_cp4_translation(self):
        result = evaluate(deepcopy(self.original))
        self.assertEqual(result["argos_host_full30"]["argos_accepted"], 21)
        self.assertEqual(result["argos_host_full30"]["net_acceptance_gain"], 0)
        self.assertEqual(result["argos_host_full30"]["additional20_net_gain"], -2)
        self.assertFalse(result["argos_host_full30"]["android_inference_performed"])
        self.assertEqual(result["cp4_status"], "BLOCKED")

    def test_mutated_asr_control_is_rejected(self):
        data = deepcopy(self.original)
        data["asr"]["control_errors"] = 73
        with self.assertRaisesRegex(ValueError, "ASR baseline"):
            evaluate(data)

    def test_mutated_small_early_stop_rule_is_rejected(self):
        data = deepcopy(self.original)
        data["small"]["performance_pre_registered_rule"]["consequence"] = "PASS"
        with self.assertRaisesRegex(ValueError, "Small-q5_1"):
            evaluate(data)

    def test_falsely_promoted_media_e2e_is_rejected(self):
        data = deepcopy(self.original)
        data["media"]["observed_status"] = "E2E_PASS"
        with self.assertRaisesRegex(ValueError, "MEDIA-only"):
            evaluate(data)

    def test_modified_original_cp4_baseline_is_rejected(self):
        data = deepcopy(self.original)
        data["translation"]["official_gate_unchanged"]["historical_translation_ID_to_EN_ACCEPT"] = "27/30"
        with self.assertRaisesRegex(ValueError, "historical CP4"):
            evaluate(data)

    def test_modified_later_paragraph_data_cannot_replace_original_cp4(self):
        data = deepcopy(self.original)
        data["translation"]["experiment"]["results_by_direction"]["id->en"]["whole_ACCEPT"] = 27
        with self.assertRaisesRegex(ValueError, "paragraph ML Kit"):
            evaluate(data)

    def test_argos_fake_improvement_rejected(self):
        data = deepcopy(self.original)
        data["argos"]["confirmed_aggregates"]["full30"]["net_additional_accepted"] = 3
        with self.assertRaisesRegex(ValueError, "Argos full30"):
            evaluate(data)

    def test_missing_or_extra_evidence_types_rejected(self):
        for name in EVIDENCE:
            with self.subTest(missing=name):
                data = deepcopy(self.original)
                data.pop(name)
                with self.assertRaisesRegex(ValueError, "wrong number"):
                    evaluate(data)
        data = deepcopy(self.original)
        data["unknown"] = {}
        with self.assertRaisesRegex(ValueError, "wrong number"):
            evaluate(data)

    def test_json_written_once_with_fail_closed_identity(self):
        with tempfile.TemporaryDirectory() as tmp:
            target = Path(tmp) / "cp4.json"
            argv = ["t10_cp4_readiness.py", "--json", str(target)]
            with patch.object(sys, "argv", argv), redirect_stdout(io.StringIO()):
                self.assertEqual(main(), 0)
            result = json.loads(target.read_text(encoding="utf-8"))
            self.assertEqual(result["cp4_status"], "BLOCKED")
            self.assertEqual(result["t10_status"], "ACTIVE")
            before = target.read_bytes()
            errors = io.StringIO()
            with patch.object(sys, "argv", argv), redirect_stderr(errors):
                self.assertEqual(main(), 1)
            self.assertIn("Refusing to overwrite", errors.getvalue())
            self.assertEqual(target.read_bytes(), before)

    def test_malformed_or_missing_input_fails_without_promotion(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            self.assertRaises(FileNotFoundError, audit, root)
            for key, name in EVIDENCE.items():
                (root / name).write_text(json.dumps(self.original[key]), encoding="utf-8")
            (root / EVIDENCE["asr"]).write_text("{invalid json", encoding="utf-8")
            with self.assertRaises(json.JSONDecodeError):
                audit(root)


if __name__ == "__main__":
    unittest.main()
