"""Unit regression tests: no evidence tampering or CP4 gate promotion for new A/B."""
import csv
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_translation_strategy_ab_review import (
    RAW_COLUMNS, REVIEW_COLUMNS, FIXTURE, ORIGINAL_FIXTURE, analyze, fixture_data,
    init, read_csv, report, validate_raw,
)


class T10TranslationStrategyABTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.dir = Path(self.tmp.name)
        self.raw = self.dir / "device.csv"
        self.session = self.dir / "review-session"
        self.downloaded = self.dir / "completed.csv"
        self.samples = fixture_data()
        rows = []
        for i, sample in enumerate(self.samples):
            order = ("whole", "linewise") if i % 2 == 0 else ("linewise", "whole")
            for strategy in order:
                rows.append({
                    "sample": sample["id"],
                    "source_language": sample["language"],
                    "target_language": "en" if sample["language"] == "id" else "id",
                    "source_text": sample["text"],
                    "strategy": strategy,
                    "translation": f"MOCK translated {sample['id']} {strategy}",
                    "latency_ms": "50.000" if strategy == "whole" else "75.000",
                    "error": "",
                    "call_count": "1" if strategy == "whole" else "2",
                    "sequence": str(len(rows) + 1),
                    "battery_c": "31.2",
                })
        self.write(self.raw, RAW_COLUMNS, rows)

    def write(self, path, columns, rows):
        with path.open("w", encoding="utf-8-sig", newline="") as stream:
            w = csv.DictWriter(stream, fieldnames=columns)
            w.writeheader()
            w.writerows(rows)

    def prepared(self):
        init(self.raw, self.session)

    def completed(self, worse_whole_ids=(), critical_candidate_ids=()):
        rows = read_csv(self.session / "review-blank.csv", REVIEW_COLUMNS)
        for row in rows:
            row["status"] = "ACCEPT"
            row["notes"] = ""
            if row["sample"] in worse_whole_ids and row["strategy"] == "whole":
                row["status"] = "MAJOR_MEANING_ERROR"
                row["notes"] = "Source meaning is incorrect"
            if row["sample"] in critical_candidate_ids and row["strategy"] == "linewise":
                row["status"] = "NEGATION_ERROR"
                row["notes"] = "Negation disappeared"
        self.write(self.downloaded, REVIEW_COLUMNS, rows)
        return rows

    def test_new_fixture_60_distinct_from_original(self):
        self.assertEqual(len(self.samples), 60)
        self.assertEqual(len([s for s in self.samples if s["language"] == "id"]), 30)
        self.assertEqual(len([s for s in self.samples if s["language"] == "en"]), 30)
        self.assertTrue(all(len(s["text"].split("\n")) == 2 for s in self.samples))
        original = json.loads(ORIGINAL_FIXTURE.read_text(encoding="utf-8"))["samples"]
        old_sources = {r["text"].casefold().strip() for r in original}
        self.assertFalse(any(s["text"].casefold().strip() in old_sources for s in self.samples))

    def test_full_120_pairs_validation_and_alternation(self):
        self.assertEqual(len(validate_raw(self.raw)), 120)
        self.assertEqual(validate_raw(self.raw)[0]["strategy"], "whole")
        self.assertEqual(validate_raw(self.raw)[2]["strategy"], "linewise")

    def test_prepare_creates_readable_browser_blank_decisions_and_hashes(self):
        self.prepared()
        meta = json.loads((self.session / "session.json").read_text(encoding="utf-8"))
        self.assertEqual(meta["paired_samples"], 60)
        self.assertEqual(meta["cp4"], "BLOCKED")
        self.assertEqual(meta["predeclared_candidate_thresholds"]["min_net_additional_accepted_per_direction"], 3)
        sheet = read_csv(self.session / "review-blank.csv", REVIEW_COLUMNS)
        self.assertTrue(all(not row["status"] for row in sheet))
        html = (self.session / "review.html").read_text(encoding="utf-8")
        self.assertIn("Output 1", html)
        self.assertIn("Ekspor review CSV", html)
        self.assertIn("id-ab-01", html)
        with self.assertRaises(FileExistsError):
            self.prepared()

    def test_html_escapes_untrusted_translation_script_tags(self):
        raw = read_csv(self.raw, RAW_COLUMNS)
        raw[0]["translation"] = "</script><script>alert(1)</script>"
        self.write(self.raw, RAW_COLUMNS, raw)
        self.prepared()
        html = (self.session / "review.html").read_text(encoding="utf-8")
        self.assertNotIn("</script><script>alert(1)</script>", html)
        self.assertIn("\\u003c/script>", html)

    def test_missing_human_review_refuses_to_report(self):
        self.prepared()
        with self.assertRaisesRegex(ValueError, "Missing/invalid human review"):
            analyze(self.raw, self.session, self.session / "review-blank.csv")

    def test_all_accepted_does_not_imply_causal_gain_or_cp4_pass(self):
        self.prepared()
        self.completed()
        result = report(self.raw, self.session, self.downloaded)
        self.assertEqual(result["overall"], "NO_BASIS_TO_PROMOTE_CANDIDATE")
        self.assertEqual(result["cp4_status"], "BLOCKED")
        self.assertEqual(result["directions"]["id->en"]["net_accepted_gain_candidate"], 0)

    def test_paired_benefit_is_only_promising_never_cp4_pass(self):
        self.prepared()
        bad_whole = [f"id-ab-{i:02d}" for i in range(1, 6)]
        bad_whole += [f"en-ab-{i:02d}" for i in range(1, 6)]
        self.completed(worse_whole_ids=set(bad_whole))
        result = report(self.raw, self.session, self.downloaded,
                        self.session / "report.json")
        self.assertEqual(result["overall"], "CANDIDATE_PROMISING_REQUIRES_INDEPENDENT_FOLLOWUP")
        self.assertEqual(result["cp4_status"], "BLOCKED")
        self.assertEqual(result["directions"]["id->en"]["paired_wins_candidate"], 5)
        self.assertEqual(result["directions"]["en->id"]["whole"]["accepted"], 25)
        self.assertEqual(result["directions"]["en->id"]["linewise"]["accepted"], 30)
        with self.assertRaises(FileExistsError):
            report(self.raw, self.session, self.downloaded, self.session / "report.json")

    def test_new_critical_regression_vetoes_candidate(self):
        self.prepared()
        poor_whole = {f"id-ab-{i:02d}" for i in range(1, 6)}
        poor_whole |= {f"en-ab-{i:02d}" for i in range(1, 6)}
        self.completed(worse_whole_ids=poor_whole, critical_candidate_ids={"id-ab-09"})
        result = analyze(self.raw, self.session, self.downloaded)
        self.assertIn("id-ab-09", result["directions"]["id->en"]["new_material_negation_or_number_name_errors"])
        self.assertEqual(result["overall"], "NO_BASIS_TO_PROMOTE_CANDIDATE")

    def test_latency_regression_blocks_even_good_reviews(self):
        self.prepared()
        raw = read_csv(self.raw, RAW_COLUMNS)
        for row in raw:
            if row["strategy"] == "linewise":
                row["latency_ms"] = "250.000"
        self.write(self.raw, RAW_COLUMNS, raw)
        with self.assertRaisesRegex(ValueError, "Session identity"):
            # Session was generated before altering raw device evidence.
            self.completed()
            analyze(self.raw, self.session, self.downloaded)
        # A *new* session with properly recorded slow results must also fail.
        fresh = self.dir / "new-slow-session"
        init(self.raw, fresh)
        sheet = read_csv(fresh / "review-blank.csv", REVIEW_COLUMNS)
        for row in sheet:
            row["status"] = "MAJOR_MEANING_ERROR" if row["strategy"] == "whole" and int(row["sample"][-2:]) <= 5 else "ACCEPT"
            row["notes"] = "Inaccurate model meaning" if row["status"] != "ACCEPT" else ""
        self.write(self.dir / "slow-review.csv", REVIEW_COLUMNS, sheet)
        result = analyze(self.raw, fresh, self.dir / "slow-review.csv")
        self.assertEqual(result["overall"], "NO_BASIS_TO_PROMOTE_CANDIDATE")
        self.assertGreater(result["directions"]["id->en"]["candidate_to_control_p95_latency_ratio"], 2.5)

    def test_raw_order_and_pair_tampering_rejected(self):
        rows = read_csv(self.raw, RAW_COLUMNS)
        rows[0], rows[1] = rows[1], rows[0]
        self.write(self.raw, RAW_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "Missing/tampered A/B pair"):
            validate_raw(self.raw)

    def test_review_output_and_sequence_locked(self):
        self.prepared()
        sheet = self.completed()
        sheet[0]["translation"] = "An edited model response"
        self.write(self.downloaded, REVIEW_COLUMNS, sheet)
        with self.assertRaisesRegex(ValueError, "Reviewer changed raw"):
            analyze(self.raw, self.session, self.downloaded)

    def test_rejection_requires_note(self):
        self.prepared()
        sheet = self.completed()
        sheet[0]["status"] = "MAJOR_MEANING_ERROR"
        sheet[0]["notes"] = ""
        self.write(self.downloaded, REVIEW_COLUMNS, sheet)
        with self.assertRaisesRegex(ValueError, "Rejection must have"):
            analyze(self.raw, self.session, self.downloaded)

    def test_engine_error_cannot_be_accepted(self):
        rows = read_csv(self.raw, RAW_COLUMNS)
        rows[0]["error"] = "Mock Model Error"
        rows[0]["translation"] = ""
        self.write(self.raw, RAW_COLUMNS, rows)
        self.prepared()
        self.completed()
        with self.assertRaisesRegex(ValueError, "Cannot ACCEPT engine error"):
            analyze(self.raw, self.session, self.downloaded)

    def test_battery_thermal_guard_and_missing_pair(self):
        rows = read_csv(self.raw, RAW_COLUMNS)
        rows[0]["battery_c"] = "43.0"
        self.write(self.raw, RAW_COLUMNS, rows)
        with self.assertRaisesRegex(ValueError, "Missing/unsafe battery"):
            validate_raw(self.raw)
        rows[0]["battery_c"] = "30.5"
        self.write(self.raw, RAW_COLUMNS, rows[:-1])
        with self.assertRaisesRegex(ValueError, "Expected 120"):
            validate_raw(self.raw)

    def test_original_fixture_text_cannot_be_changed(self):
        source = read_csv(self.raw, RAW_COLUMNS)
        source[0]["source_text"] = "Edited source paragraph."
        self.write(self.raw, RAW_COLUMNS, source)
        with self.assertRaisesRegex(ValueError, "Missing/tampered A/B pair"):
            validate_raw(self.raw)


if __name__ == "__main__":
    unittest.main()
