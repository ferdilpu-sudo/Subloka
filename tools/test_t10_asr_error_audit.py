"""Unit tests for independent ASR error auditing; no Android device required."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).parent))
from t10_asr_error_audit import align_errors, audit, load_evidence


class TestT10ASRErrorAudit(unittest.TestCase):
    def test_alignment_substitution_insertion_deletion(self):
        self.assertEqual(align_errors("saya makan nasi", "saya makan nasi")["errors"], 0)
        self.assertEqual(align_errors("saya makan nasi", "saya makan roti")["substitutions"], 1)
        self.assertEqual(align_errors("saya makan nasi", "saya nasi")["deletions"], 1)
        self.assertEqual(align_errors("saya makan nasi", "saya sudah makan nasi")["insertions"], 1)

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.manifest = self.root / "t10-dataset.json"
        self.csv = self.root / "asr-results.csv"
        self.manifest.write_text(json.dumps({
            "samples": [
                {"id":"id-clean-01","language":"id","category":"clean","reference":"saya makan nasi","audio":"clip01.wav"},
                {"id":"id-clean-02","language":"id","category":"clean","reference":"mereka minum susu","audio":"clip02.wav"},
                {"id":"en-clean-01","language":"en","category":"clean","reference":"hello world","audio":"clip03.wav"},
            ]
        },ensure_ascii=False),encoding="utf-8")
        self.data = [
            {"model":"base","sample":"id-clean-01","language":"id","category":"clean","wer":"0.3333","hypothesis":"saya makan roti"},
            {"model":"tiny","sample":"id-clean-01","language":"id","category":"clean","wer":"0.6667","hypothesis":"saya makan mie dan"},
            {"model":"base","sample":"id-clean-02","language":"id","category":"clean","wer":"0.0000","hypothesis":"mereka minum susu"},
            {"model":"tiny","sample":"id-clean-02","language":"id","category":"clean","wer":"0.3333","hypothesis":"mereka minum kopi"},
            {"model":"base","sample":"en-clean-01","language":"en","category":"clean","wer":"0.5000","hypothesis":"hello moon"},
        ]
        self.write_csv()

    def write_csv(self):
        with self.csv.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=["model","sample","language","category","wer","hypothesis"])
            writer.writeheader()
            writer.writerows(self.data)

    def test_audit_emits_ordered_review_and_unchanged_baseline(self):
        summary = audit(self.csv,self.manifest,self.root/"out")
        result=summary["id_clean_base"]
        self.assertEqual(result["samples"],2)
        self.assertEqual(result["reference_words"],6)
        self.assertEqual(result["errors"],1)
        self.assertEqual(result["max_errors_at_target"],1)
        self.assertEqual(result["minimum_error_reduction"],0)
        self.assertEqual(len(summary["reported_wer_mismatches"]),0)
        with (self.root/"out/id-clean-base-audio-review.csv").open(encoding="utf-8-sig",newline="") as f:
            review=list(csv.DictReader(f))
        self.assertEqual(review[0]["sample"],"id-clean-01")
        self.assertEqual(review[0]["audio_review_status"],"UNREVIEWED")
        self.assertEqual(review[1]["sample"],"id-clean-02")
        self.assertEqual(self.data[0]["wer"],"0.3333")
        with self.assertRaises(FileExistsError):
            audit(self.csv,self.manifest,self.root/"out")

    def test_wer_discrepancy_is_flagged_not_overwritten(self):
        self.data[0]["wer"]="0.6000"
        self.write_csv()
        summary=audit(self.csv,self.manifest,self.root/"other")
        self.assertEqual(len(summary["reported_wer_mismatches"]),1)
        mismatch=summary["reported_wer_mismatches"][0]
        self.assertEqual(mismatch["sample"],"id-clean-01")
        self.assertEqual(mismatch["recalculated_errors"],1)
        self.assertAlmostEqual(mismatch["archived_wer"],0.6)

    def test_duplicate_rows_rejected(self):
        self.data.append(dict(self.data[0]))
        self.write_csv()
        with self.assertRaisesRegex(ValueError,"Duplicate benchmark row"):
            load_evidence(self.csv,self.manifest)

    def test_manifest_label_disagreement_rejected(self):
        self.data[0]["language"]="en"
        self.write_csv()
        with self.assertRaisesRegex(ValueError,"Fixture labels"):
            load_evidence(self.csv,self.manifest)


if __name__=="__main__":
    unittest.main()
