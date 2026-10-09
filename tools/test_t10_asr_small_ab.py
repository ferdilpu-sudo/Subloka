"""Deterministic offline tests for NEW Base vs Small-q5_1 ASR candidate experiment.

Test fixtures are synthetic and never stand in for device benchmarks or
independent listening review. All tests must run without ADB, model downloads,
audio, network access, or modifying original T10 data.
"""
from __future__ import annotations

import csv
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
from types import SimpleNamespace
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_asr_small_protocol import (
    BASE_SHA, SMALL_SHA, SMALL_URL, REVISION, VARIANTS, COLUMNS, PROTOCOL,
    SHA_BY_VARIANT, pairs, command, analyze, prepare_small, archive_summary,
)
from t10_asr_small_ab import device_free_kib, get_rss, stop_own_process


def synthetic_fixture():
    fixtures = {}
    archive = {}
    for idx in range(1, 21):
        sid = f"id-clean-{idx:02d}"
        words = [f"w{j:02d}" for j in range(19 if idx <= 7 else 18)]
        ref = " ".join(words)
        fixtures[sid] = {"reference": ref}
        archive[sid] = {"hypothesis": ref}
    return fixtures, archive


def make_run(sid, variant, fixture, errors, rtf=1.0, rss=700_000):
    words = fixture["reference"].split()
    hypothesis = " ".join(["wrong"] * errors + words[errors:])
    return {
        "sample": sid, "variant": variant,
        "model_sha256": SHA_BY_VARIANT[variant],
        "word_errors": errors, "reference_words": len(words),
        "wer_diagnostic": errors / len(words),
        "duration_s": 10, "elapsed_s": rtf * 10, "rtf": rtf,
        "battery_start_c": 30.0, "battery_end_c": 31.0,
        "sampled_peak_rss_kb": rss, "remote_whisper_exit": 0,
        "host_adb_exit": 0, "hypothesis": hypothesis,
    }


def make_pairs(base_errors=5, small_errors=3, rtf=1.0, rss=700_000):
    fixtures, archive = synthetic_fixture()
    runs = []
    for sid, variant in pairs(sorted(fixtures)):
        errors = base_errors if variant == "base" else small_errors
        runs.append(make_run(sid, variant, fixtures[sid], errors,
                             rtf=(1.0 if variant == "base" else rtf),
                             rss=(200_000 if variant == "base" else rss)))
    return runs, fixtures, archive


class T10ASRSmallABTests(unittest.TestCase):
    def test_schedule_exact_twenty_clean_samples(self):
        names = [f"id-clean-{i:02d}" for i in range(1, 21)]
        plan = pairs(names)
        self.assertEqual(len(plan), 40)
        self.assertEqual(plan[:4], [(names[0], "base"), (names[0], "small_q5_1"),
                                    (names[1], "small_q5_1"), (names[1], "base")])
        self.assertEqual({name for name, _ in plan}, set(names))

    def test_schedule_does_not_accept_selected_subset_or_missing(self):
        with self.assertRaisesRegex(ValueError, "20"):
            pairs([f"id-clean-{i:02d}" for i in range(1, 6)])
        with self.assertRaisesRegex(ValueError, "20"):
            pairs([f"id-clean-{i:02d}" for i in range(2, 22)])

    def test_android_command_is_scoped_and_pins_model(self):
        remote = "/data/local/tmp/subloka-t10-small-012345abcdef"
        b = command(remote, "base")
        s = command(remote, "small_q5_1")
        self.assertIn("-m base.bin", b)
        self.assertIn("-m small-q5_1.bin", s)
        self.assertIn("result.exit", s)
        self.assertIn("-l id", s)
        self.assertIn("-nt -ng -nfa", s)

    def test_android_command_rejects_unscoped_directory_and_variant(self):
        with self.assertRaisesRegex(ValueError, "Unsafe"):
            command("/data/local/tmp/../../data", "base")
        with self.assertRaisesRegex(ValueError, "Unexpected"):
            command("/data/local/tmp/subloka-t10-small-012345abcdef", "medium")

    def test_sha_metadata_is_immutable_and_distinct(self):
        self.assertEqual(len(BASE_SHA), 64)
        self.assertEqual(len(SMALL_SHA), 64)
        self.assertNotEqual(BASE_SHA, SMALL_SHA)
        self.assertTrue(PROTOCOL.startswith("t10-id-clean-"))
        self.assertEqual(VARIANTS, ("base", "small_q5_1"))

    def test_pinned_candidate_url_matches_verified_official_artifact(self):
        # Exact official Hugging Face file page confirms this Git revision,
        # quantized multilingual Small name, 190MB and the fixed SHA256.
        self.assertEqual(
            REVISION, "c521a4b02f422512d734391fdf08bb08c0862f68"
        )
        self.assertEqual(
            SMALL_URL,
            "https://huggingface.co/ggerganov/whisper.cpp/resolve/"
            "c521a4b02f422512d734391fdf08bb08c0862f68/ggml-small-q5_1.bin",
        )
        self.assertEqual(
            SMALL_SHA,
            "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb",
        )
        self.assertNotIn("80da2d8bfee42b0e836fc3a9890373e5defc00a6", SMALL_URL)

    def test_missing_official_revision_download_fails_cleanly_without_part(self):
        with tempfile.TemporaryDirectory() as temp, patch(
            "t10_asr_small_protocol.urlopen",
            side_effect=HTTPError(SMALL_URL, 404, "Not Found", None, None),
        ):
            destination = Path(temp) / "ggml-small-q5_1.bin"
            with self.assertRaisesRegex(RuntimeError, "HTTP 404"):
                prepare_small(destination)
            self.assertFalse(destination.exists())
            self.assertEqual(list(Path(temp).glob("*.part")), [])

    def test_full_paired_candidate_below_20_percent_is_promising_only(self):
        runs, fixtures, archive = make_pairs()
        result = analyze(runs, fixtures, archive)
        self.assertEqual(result["paired_samples"], 20)
        self.assertEqual(result["paired_reference_words"], 367)
        self.assertEqual(result["paired_base_errors"], 100)
        self.assertEqual(result["paired_small_errors"], 60)
        self.assertEqual(result["cp4"], "BLOCKED")
        self.assertTrue(result["preregistered_diagnostic_criteria_met"])
        self.assertIn("REQUIRES_TRULY_UNSEEN_HOLDOUT", result["verdict"])

    def test_partial_pairs_cannot_certify_candidate(self):
        runs, fixtures, archive = make_pairs()
        report = analyze(runs[:12], fixtures, archive)
        self.assertEqual(report["paired_samples"], 6)
        self.assertEqual(report["verdict"], "PARTIAL_DATA_NO_QUALITY_VERDICT")

    def test_low_quality_candidate_rejected(self):
        runs, f, a = make_pairs(base_errors=5, small_errors=4)
        report = analyze(runs, f, a)
        self.assertEqual(report["paired_small_errors"], 80)
        self.assertFalse(report["preregistered_diagnostic_criteria_met"])
        self.assertEqual(report["cp4"], "BLOCKED")

    def test_candidate_too_slow_rejected(self):
        runs, f, a = make_pairs(rtf=2.1)
        report = analyze(runs, f, a)
        self.assertFalse(report["preregistered_diagnostic_criteria_met"])
        self.assertEqual(report["small_p95_rtf"], 2.1)

    def test_candidate_memory_too_high_rejected(self):
        runs, f, a = make_pairs(rss=1_700_000)
        report = analyze(runs, f, a)
        self.assertFalse(report["preregistered_diagnostic_criteria_met"])

    def test_absent_sampled_rss_cannot_be_called_pass(self):
        runs, f, a = make_pairs()
        runs[1]["sampled_peak_rss_kb"] = None
        report = analyze(runs, f, a)
        self.assertIsNone(report["small_peak_sampled_rss_kb"])
        self.assertFalse(report["preregistered_diagnostic_criteria_met"])

    def test_duplicate_runs_rejected(self):
        runs, f, a = make_pairs()
        with self.assertRaisesRegex(ValueError, "duplicate"):
            analyze(runs + [runs[0]], f, a)

    def test_model_hash_change_rejected(self):
        runs, f, a = make_pairs()
        runs[1]["model_sha256"] = "0" * 64
        with self.assertRaisesRegex(ValueError, "fingerprint"):
            analyze(runs, f, a)

    def test_transcript_and_error_must_match(self):
        runs, f, a = make_pairs()
        runs[1]["hypothesis"] = f[runs[1]["sample"]]["reference"]
        with self.assertRaisesRegex(ValueError, "Word-error"):
            analyze(runs, f, a)

    def test_failed_inference_cannot_be_scored(self):
        runs, f, a = make_pairs()
        runs[0]["remote_whisper_exit"] = 1
        with self.assertRaisesRegex(ValueError, "Failed inference"):
            analyze(runs, f, a)

    def test_summary_archive_does_not_touch_original_baseline(self):
        runs, f, a = make_pairs()
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            (directory / "asr-results.csv").write_text("immutable original", encoding="utf-8")
            summary = {"protocol": PROTOCOL, "runs": runs, "analysis": analyze(runs, f, a)}
            archive_summary(directory, summary)
            rows = list(csv.DictReader((directory / "runs.csv").open(encoding="utf-8-sig", newline="")))
            self.assertEqual(len(rows), 40)
            self.assertEqual(tuple(rows[0]), COLUMNS)
            self.assertEqual((directory / "asr-results.csv").read_text(), "immutable original")
            self.assertEqual(json.loads((directory / "summary.json").read_text())["protocol"], PROTOCOL)

    def test_download_corruption_cannot_replace_candidate(self):
        class FakeResponse(io.BytesIO):
            def geturl(self):
                return "https://huggingface.co/fake"
        with tempfile.TemporaryDirectory() as temp, patch(
            "t10_asr_small_protocol.urlopen", return_value=FakeResponse(b"not a real model")
        ):
            path = Path(temp) / "ggml-small-q5_1.bin"
            with self.assertRaisesRegex(ValueError, "size/SHA256"):
                prepare_small(path)
            self.assertFalse(path.exists())
            self.assertEqual(list(Path(temp).glob("*.part")), [])

    def test_corrupt_existing_model_file_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / "ggml-small-q5_1.bin"
            path.write_bytes(b"corrupt model")
            with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
                prepare_small(path)
            self.assertEqual(path.read_bytes(), b"corrupt model")

    def test_android_df_storage_estimator_fail_closed(self):
        good = SimpleNamespace(returncode=0, stdout="Filesystem 1K-blocks Used Available Use% Mounted\n/dev/block/dm-1 3000000 1000000 2000000 34% /data\n")
        with patch("t10_asr_small_ab.adb_command", return_value=good):
            self.assertEqual(device_free_kib("adb", "device"), 2_000_000)
        bad = SimpleNamespace(returncode=0, stdout="unknown")
        with patch("t10_asr_small_ab.adb_command", return_value=bad):
            with self.assertRaisesRegex(RuntimeError, "Unexpected Android df"):
                device_free_kib("adb", "device")

    def test_rss_sampling_reads_own_scoped_pid(self):
        good = SimpleNamespace(returncode=0, stdout="VmRSS:\t880000 kB\n")
        with patch("t10_asr_small_ab.adb_command", return_value=good) as call:
            self.assertEqual(get_rss("adb", "serial", "/data/local/tmp/subloka-t10-small-012345abcdef"), 880000)
            self.assertIn("result.pid", str(call.call_args))

    def test_stop_own_cli_only_valid_numeric_pid(self):
        invalid = SimpleNamespace(returncode=0, stdout="555; rm /")
        with patch("t10_asr_small_ab.adb_command", return_value=invalid) as call:
            stop_own_process("adb", "serial", "/data/local/tmp/subloka-t10-small-012345abcdef")
            self.assertEqual(call.call_count, 1)
        valid = SimpleNamespace(returncode=0, stdout="1234\n")
        with patch("t10_asr_small_ab.adb_command", return_value=valid) as call:
            stop_own_process("adb", "serial", "/data/local/tmp/subloka-t10-small-012345abcdef")
            self.assertEqual(call.call_count, 2)
            self.assertIn("kill -TERM 1234", str(call.call_args_list[-1]))


if __name__ == "__main__":
    unittest.main()
