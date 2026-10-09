"""T10 human translation QA sheet integrity, full review and signoff regression."""
from __future__ import annotations

import csv
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_translation_review import content_digest, fingerprint, load
from t10_translation_human_qa import (
    DRAFT, FIXTURES, HUMAN_COLUMNS, prepare, finalize, validate_human_sheet,
)


class T10TranslationHumanQATests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.raw = self.root / "raw.csv"
        self.session = self.root / "human-qa"
        self.draft = self.root / "draft.json"
        source = json.loads(FIXTURES.read_text(encoding="utf-8"))
        fixtures = source["samples"]
        self.assertEqual(len(fixtures), 60)
        data = [
            {
                "sample": x["id"],
                "source_language": x["language"],
                "target_language": "id" if x["language"] == "en" else "en",
                "source_text": x["text"],
                "translation": "sample translated text " + x["id"],
                "latency_ms": "12.500",
                "error": "",
            }
            for x in fixtures
        ]
        self.write(self.raw, tuple(data[0]), data)
        self.draft.write_text(json.dumps({
            "version": 1,
            "source_content_sha256": content_digest(data),
            "default_status": "ACCEPT",
            "overrides": {
                "id-02": {"status": "MAJOR_MEANING_ERROR", "notes": "Future became past"},
                "id-05": {"status": "MAJOR_MEANING_ERROR", "notes": "Delay became speed"},
            },
            "accept_notes": {"id-08": "Date needs manual check"},
        }), encoding="utf-8")

    def write(self, path, fields, rows):
        with path.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)

    def prepare(self):
        return prepare(self.raw, self.session, FIXTURES, self.draft)

    def review_rows(self):
        with (self.session / "human-review.csv").open(newline="", encoding="utf-8-sig") as f:
            return list(csv.DictReader(f))

    def save_rows(self, rows):
        self.write(self.session / "human-review.csv", HUMAN_COLUMNS, rows)

    def completed_rows(self, *, reject=("id-02", "id-05"), override_notes=True):
        rows = self.review_rows()
        for row in rows:
            if row["sample"] in reject:
                row["human_status"] = "MAJOR_MEANING_ERROR"
                row["human_notes"] = "Human checked source meaning: error."
            else:
                row["human_status"] = "ACCEPT"
                if override_notes and row["provisional_ai_status"] != "ACCEPT":
                    row["human_notes"] = "Human independently checked and found acceptable."
        self.save_rows(rows)
        return rows

    def test_preparation_retains_all_rows_and_ai_is_only_provisional(self):
        source_sha = fingerprint(self.raw)
        session = self.prepare()
        rows = self.review_rows()
        self.assertEqual(len(rows), 60)
        self.assertTrue(all(row["human_status"] == "" for row in rows))
        by_id = {row["sample"]: row for row in rows}
        self.assertEqual(by_id["id-02"]["provisional_ai_status"], "MAJOR_MEANING_ERROR")
        self.assertEqual(by_id["id-08"]["provisional_ai_notes"], "Date needs manual check")
        self.assertTrue(session["ai_draft_exact_output_match"])
        self.assertEqual(fingerprint(self.raw), source_sha)
        with self.assertRaises(FileExistsError):
            self.prepare()

    def test_no_stale_ai_label_reuse_on_new_model_outputs(self):
        raw = load(self.raw)
        raw[0]["translation"] = "different new ML Kit output"
        self.write(self.raw, tuple(raw[0]), raw)
        session = self.prepare()
        self.assertFalse(session["ai_draft_exact_output_match"])
        self.assertEqual({r["provisional_ai_status"] for r in self.review_rows()}, {"NOT_APPLICABLE"})

    def test_only_complete_review_produces_signoff_and_no_gate_promotion(self):
        self.prepare()
        self.completed_rows()
        original_hash = fingerprint(self.raw)
        signed = finalize(self.raw, self.session, "Bilingual QA reviewer", True, FIXTURES, self.draft)
        self.assertTrue(signed["reviewed_all_60"])
        self.assertTrue(signed["both_directions_quality_threshold_met_from_labels"])
        self.assertEqual(signed["cp4_status"], "BLOCKED")
        self.assertEqual(signed["quality_directions"]["id->en"]["accepted"], 28)
        self.assertEqual(signed["quality_directions"]["en->id"]["accepted"], 30)
        self.assertEqual(fingerprint(self.raw), original_hash)
        reviewed = load(self.session / "human-reviewed.csv")
        self.assertEqual(len(reviewed), 60)
        self.assertEqual(reviewed[31]["status"], "MAJOR_MEANING_ERROR")
        with self.assertRaises(FileExistsError):
            finalize(self.raw, self.session, "Bilingual QA reviewer", True, FIXTURES, self.draft)

    def test_missing_human_decision_cannot_sign(self):
        self.prepare()
        with self.assertRaisesRegex(ValueError, "Missing/invalid human decision"):
            finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)
        self.assertFalse((self.session / "human-signoff.json").exists())

    def test_ai_disagreement_must_be_explained(self):
        self.prepare()
        rows = self.completed_rows(override_notes=False)
        self.assertEqual(rows[31]["sample"], "id-02")
        rows[31]["human_status"] = "ACCEPT"
        rows[31]["human_notes"] = ""
        self.save_rows(rows)
        with self.assertRaisesRegex(ValueError, "Disagreement"):
            finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)

    def test_raw_content_mutation_and_locked_columns_rejected(self):
        self.prepare()
        rows = self.completed_rows()
        rows[0]["translation"] = "human changed model output!"
        self.save_rows(rows)
        with self.assertRaisesRegex(ValueError, "Original model evidence edited"):
            finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)
        rows[0]["translation"] = "sample translated text en-01"
        rows[0]["provisional_ai_status"] = "NEGATION_ERROR"
        self.save_rows(rows)
        with self.assertRaisesRegex(ValueError, "Provisional AI labels were edited"):
            finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)

    def test_historical_raw_change_rejected_after_preparation(self):
        self.prepare()
        self.completed_rows()
        source = load(self.raw)
        source[0]["translation"] = "unexpected new source text"
        self.write(self.raw, tuple(source[0]), source)
        with self.assertRaisesRegex(ValueError, "Original raw CSV changed"):
            finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)

    def test_attestation_required_and_negation_blocks_even_at_high_acceptance(self):
        self.prepare()
        rows = self.completed_rows(reject=())
        for row in rows:
            if row["sample"] == "id-09":
                row["human_status"] = "NEGATION_ERROR"
                row["human_notes"] = "Negation inverted"
        self.save_rows(rows)
        with self.assertRaisesRegex(ValueError, "Require named reviewer"):
            finalize(self.raw, self.session, "Reviewer", False, FIXTURES, self.draft)
        signed = finalize(self.raw, self.session, "Reviewer", True, FIXTURES, self.draft)
        self.assertFalse(signed["both_directions_quality_threshold_met_from_labels"])
        self.assertEqual(signed["quality_directions"]["id->en"]["negation_errors"], 1)
        self.assertEqual(signed["cp4_status"], "BLOCKED")

    def test_fixture_source_tamper_rejected(self):
        content = load(self.raw)
        content[0]["source_text"] = "changed by user"
        self.write(self.raw, tuple(content[0]), content)
        with self.assertRaisesRegex(ValueError, "Fixture/source text mismatch"):
            self.prepare()


if __name__ == "__main__":
    unittest.main()
