"""Offline regression tests for frozen 20-pair whisper.cpp decoding A/B."""
from __future__ import annotations

import json
from pathlib import Path
import re
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_asr_decode_ab import (
    BASELINE_SHA, DEFAULT_COMMAND, EXPECTED_ERRORS, EXPECTED_WORDS,
    MANIFEST_SHA, VARIANTS, aggregate, build_remote_command,
    load_frozen_inputs, schedule,
)

IDS = [f"id-clean-{i:02d}" for i in range(1, 21)]


class TestT10DecodeAB(unittest.TestCase):
    def test_all_twenty_have_exactly_two_conditions_in_balanced_order(self):
        actual = schedule(IDS)
        self.assertEqual(len(actual), 40)
        self.assertEqual(len(set(actual)), 40)
        self.assertEqual(actual[:4], [
            ("id-clean-01", "default"), ("id-clean-01", "beam1"),
            ("id-clean-02", "beam1"), ("id-clean-02", "default"),
        ])
        self.assertEqual(actual[-2:], [
            ("id-clean-20", "beam1"), ("id-clean-20", "default"),
        ])
        self.assertEqual({(x, y) for x, y in actual}, {
            (x, y) for x in IDS for y in VARIANTS
        })
        self.assertEqual(DEFAULT_COMMAND, "-nt -ng -nfa -otxt -of result")

    def test_cherry_picking_and_reordered_fixtures_rejected(self):
        for bad in (IDS[:19], IDS + IDS[:1], list(reversed(IDS)),
                    IDS[:19] + ["id-clean-19"]):
            with self.subTest(fixture=bad[:2]), self.assertRaises(ValueError):
                schedule(bad)

    def test_remote_shell_exits_from_actual_whisper_pid_and_clears_temp(self):
        prefix = "/data/local/tmp/subloka-t10-decode-123456abcdef"
        original = build_remote_command(prefix, "default")
        narrow = build_remote_command(prefix, "beam1")
        self.assertIn(" -l id -nt -ng -nfa -otxt -of result & pid=$!", original)
        self.assertIn("wait $pid; rc=$?; echo $rc > result.exit; exit $rc", original)
        self.assertIn("echo $pid > result.pid", original)
        self.assertNotIn(" -bs 1", original)
        self.assertIn(" -bs 1 & pid=$!", narrow)
        with self.assertRaises(ValueError):
            build_remote_command("/tmp/foo;rm -rf /", "beam1")
        with self.assertRaises(ValueError):
            build_remote_command(prefix, "beam7")

    def test_manifest_fingerprint_is_frozen_and_baseline_fixed(self):
        self.assertEqual(len(BASELINE_SHA), 64)
        self.assertEqual(len(MANIFEST_SHA), 64)
        self.assertEqual((EXPECTED_ERRORS, EXPECTED_WORDS), (105, 367))
        with tempfile.TemporaryDirectory() as dir:
            root = Path(dir)
            m = root / "manifest.json"
            a = root / "asr-results.csv"
            m.write_text(json.dumps({"samples": []}), encoding="utf-8")
            a.write_text("", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "manifest SHA-256 mismatch"):
                load_frozen_inputs(m, a)

    def test_aggregation_does_not_promote_paired_result_to_cp4(self):
        fixtures = {
            sid: {"reference": "saya makan nasi"} for sid in IDS
        }
        archived = {sid: {"hypothesis": "saya makan roti"} for sid in IDS}
        runs = [
            {"sample": "id-clean-01", "variant": "default",
             "word_errors": 1, "reference_words": 3,
             "remote_whisper_exit": 0, "host_adb_exit": 0,
             "hypothesis": "saya makan roti", "rtf": 0.8},
            {"sample": "id-clean-01", "variant": "beam1",
             "word_errors": 0, "reference_words": 3,
             "remote_whisper_exit": 0, "host_adb_exit": 0,
             "hypothesis": "saya makan nasi", "rtf": 0.9},
            {"sample": "id-clean-02", "variant": "default",
             "word_errors": 1, "reference_words": 3,
             "remote_whisper_exit": 0, "host_adb_exit": 0,
             "hypothesis": "saya makan roti", "rtf": 0.7},
        ]
        output = aggregate(runs, fixtures, archived)
        self.assertEqual(output["paired_samples"], 1)
        self.assertEqual(output["control_errors"], 1)
        self.assertEqual(output["beam1_errors"], 0)
        self.assertEqual(output["beam1_minus_control_micro_wer"], -1 / 3)
        self.assertEqual(output["original_archived_baseline_errors"], 105)
        self.assertEqual(output["original_archived_reference_words"], 367)
        self.assertEqual(output["official_cp4_status"], "BLOCKED")
        self.assertEqual(output["control_matches_archived_hypothesis"], 1)
        self.assertEqual(output["paired_hypotheses_changed"], 1)

    def test_tampered_word_edit_counts_are_rejected_on_resume(self):
        fixtures = {"id-clean-01": {"reference": "saya makan nasi"}}
        archived = {"id-clean-01": {"hypothesis": "saya makan roti"}}
        fake = {"sample": "id-clean-01", "variant": "default",
                "word_errors": 0, "reference_words": 3,
                "remote_whisper_exit": 0, "host_adb_exit": 0,
                "hypothesis": "saya makan roti", "rtf": 1.0}
        with self.assertRaisesRegex(ValueError, "disagree"):
            aggregate([fake], fixtures, archived)

    def test_duplicate_partial_or_failed_run_cannot_be_counted_as_good(self):
        fixtures = {"id-clean-01": {"reference": "hai dunia"}}
        archived = {"id-clean-01": {"hypothesis": "hai bumi"}}
        good = {"sample": "id-clean-01", "variant": "beam1",
                "word_errors": 1, "reference_words": 2,
                "remote_whisper_exit": 0, "host_adb_exit": 0,
                "hypothesis": "hai bumi", "rtf": 1.0}
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            aggregate([good, dict(good)], fixtures, archived)
        with self.assertRaisesRegex(ValueError, "failed CLI"):
            aggregate([dict(good, remote_whisper_exit=7)], fixtures, archived)
        with self.assertRaisesRegex(ValueError, "failed CLI"):
            aggregate([dict(good, host_adb_exit=1)], fixtures, archived)


if __name__ == "__main__":
    unittest.main()
