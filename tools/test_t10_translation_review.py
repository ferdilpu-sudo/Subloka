"""Standard-library regression checks for T10 translation review scoring.

Run: python -m unittest discover -s tools -p test_t10_translation_review.py
"""

import csv
import json
import tempfile
import unittest
from pathlib import Path

from t10_translation_review import init, load, report


class T10TranslationReviewTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.raw = self.dir / "raw.csv"
        self.review = self.dir / "review.csv"
        fixture = (Path(__file__).resolve().parent.parent
                   / "engine/translation/src/androidTest/assets/t10_translation_fixtures.json")
        items = json.loads(fixture.read_text(encoding="utf-8"))["samples"]
        with self.raw.open("w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f, fieldnames=("sample", "source_language", "target_language",
                                    "source_text", "translation", "latency_ms", "error")
            )
            writer.writeheader()
            for item in items:
                writer.writerow({
                    "sample": item["id"],
                    "source_language": item["language"],
                    "target_language": "id" if item["language"] == "en" else "en",
                    "source_text": item["text"],
                    "translation": "mock output",
                    "latency_ms": "12.500",
                    "error": "",
                })
        init(self.raw, self.review)

    def save(self, rows):
        with self.review.open("w", newline="", encoding="utf-8-sig") as f:
            writer = csv.DictWriter(f, fieldnames=rows[0].keys())
            writer.writeheader()
            writer.writerows(rows)

    def test_incomplete_review_is_not_pass(self):
        self.assertFalse(report(self.review, None))

    def test_all_accepted_passes(self):
        rows = load(self.review)
        for row in rows:
            row["status"] = "ACCEPT"
        self.save(rows)
        self.assertTrue(report(self.review, None))

    def test_negation_failure_blocks_even_if_acceptance_above_ninety_percent(self):
        rows = load(self.review)
        for row in rows:
            row["status"] = "ACCEPT"
        rows[0]["status"] = "NEGATION_ERROR"
        self.save(rows)
        self.assertFalse(report(self.review, None))

    def test_engine_error_blocks_even_with_all_accept(self):
        rows = load(self.review)
        for row in rows:
            row["status"] = "ACCEPT"
        rows[0]["error"] = "MockError"
        self.save(rows)
        self.assertFalse(report(self.review, None))

    def test_duplicate_sample_id_is_rejected(self):
        rows = load(self.review)
        rows[1]["sample"] = rows[0]["sample"]
        self.save(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate sample"):
            report(self.review, None)


if __name__ == "__main__":
    unittest.main()
