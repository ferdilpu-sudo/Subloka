"""No-network, synthetic-only private holdout topic kit regressions."""
from __future__ import annotations

from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_id_collection_kit import (
    CLEAN_TOPICS, CHALLENGING_TOPICS, PLAN_FILENAME,
    check_template, create_plan, expected_ids, main, plan_payload, progress,
)
from t10_id_independent_holdout import init


class PrivateCollectionKitTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.base = Path(temp.name)
        p = patch("t10_id_independent_holdout.PRIVATE_BASE", self.base)
        p.start()
        self.addCleanup(p.stop)
        self.workspace = self.base / "id-holdout"
        with redirect_stdout(io.StringIO()):
            init(self.workspace)

    def test_topics_are_cues_not_predicted_or_fabricated_transcripts(self):
        plan = plan_payload()
        self.assertEqual(plan["sample_count"], 30)
        self.assertEqual(len(plan["items"]), 30)
        self.assertEqual(len(CLEAN_TOPICS), 20)
        self.assertEqual(len(CHALLENGING_TOPICS), 10)
        self.assertTrue(plan["prompt_is_not_reference"])
        self.assertTrue(plan["do_not_fill_reference_from_topic_cue"])
        self.assertFalse(plan["record_real_audio"])
        self.assertEqual(plan["CP4"], "BLOCKED")
        self.assertTrue(all("reference" not in x for x in plan["items"]))
        self.assertTrue(all("consent_declared" not in x for x in plan["items"]))
        self.assertTrue(all("audio_sha256" not in x for x in plan["items"]))

    def test_plan_has_original_order_and_balanced_speakers(self):
        p = plan_payload()
        self.assertEqual([v["id"] for v in p["items"]], expected_ids())
        for speaker_idx in range(1, 6):
            chosen = [v for v in p["items"]
                      if v["suggested_speaker_id"] == f"spk-{speaker_idx:02d}"]
            self.assertEqual(len(chosen), 6)
            self.assertEqual([v["category"] for v in chosen].count("clean"), 4)
            self.assertEqual([v["category"] for v in chosen].count("challenging"), 2)
        self.assertEqual(len({x["topic_cue_not_reference_transcript"] for x in p["items"]}), 30)

    def test_create_plan_keeps_manifest_bytes_and_false_flags_untouched(self):
        manifest = self.workspace / "manifest.json"
        before = manifest.read_bytes()
        out = create_plan(self.workspace)
        self.assertEqual(out.name, PLAN_FILENAME)
        self.assertEqual(before, manifest.read_bytes())
        slot = json.loads(before)["samples"][0]
        self.assertIs(slot["consent_declared"], False)
        self.assertIs(slot["human_reference_reviewed"], False)
        self.assertEqual(slot["reference"], "")
        self.assertEqual(slot["audio_sha256"], "")
        self.assertFalse((self.workspace / "manifest.lock.json").exists())
        self.assertFalse(any((self.workspace / "audio").iterdir()))

    def test_plan_existing_never_overwrites(self):
        output = create_plan(self.workspace)
        original = output.read_bytes()
        with self.assertRaises(FileExistsError):
            create_plan(self.workspace)
        self.assertEqual(output.read_bytes(), original)

    def test_counts_only_empty_template_status(self):
        result = progress(self.workspace)
        self.assertEqual(result["total_slots"], 30)
        self.assertEqual(result["clean_slots"], 20)
        self.assertEqual(result["challenging_slots"], 10)
        for k in (
            "wav_present_not_verified", "reference_filled_not_verified",
            "audio_hash_entered_not_verified", "permission_declared_not_authenticated",
            "review_declared_not_authenticated", "rows_with_all_declarations_not_audited",
        ):
            self.assertEqual(result[k], 0)
        self.assertFalse(result["consent_authenticated_by_this_tool"])
        self.assertFalse(result["independent_dataset_ready"])
        self.assertEqual(result["CP4"], "BLOCKED")

    def test_status_filled_fields_still_not_authenticated_or_audited(self):
        path = self.workspace / "manifest.json"
        raw = json.loads(path.read_text(encoding="utf-8"))
        row = raw["samples"][0]
        row["reference"] = "SECRET PRIVATE REFERENCE NOT FOR OUTPUT"
        row["audio_sha256"] = "x" * 64
        row["consent_declared"] = True
        row["human_reference_reviewed"] = True
        row["speaker_id"] = "spk-01"
        row["recorded_utc"] = "2026-10-10T05:00:00Z"
        path.write_text(json.dumps(raw), encoding="utf-8")
        (self.workspace / "audio" / "id-clean-01.wav").write_bytes(b"fake-not-real-wav")
        status = progress(self.workspace)
        self.assertEqual(status["wav_present_not_verified"], 1)
        self.assertEqual(status["rows_with_all_declarations_not_audited"], 1)
        self.assertFalse(status["independent_dataset_ready"])
        self.assertFalse(status["consent_authenticated_by_this_tool"])
        output = io.StringIO()
        with patch.object(sys, "argv", [
            "t10_id_collection_kit.py", "status", "--workspace", str(self.workspace),
        ]), redirect_stdout(output):
            self.assertEqual(main(), 0)
        self.assertNotIn("SECRET", output.getvalue())
        self.assertNotIn("spk-01", output.getvalue())
        self.assertNotIn("2026-10-10T05", output.getvalue())

    def test_invalid_ids_fail_closed_and_do_not_make_plan(self):
        path = self.workspace / "manifest.json"
        manifest = json.loads(path.read_text(encoding="utf-8"))
        manifest["samples"][0]["id"] = "id-clean-99"
        path.write_text(json.dumps(manifest), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "original 30 ordered"):
            create_plan(self.workspace)
        self.assertFalse((self.workspace / PLAN_FILENAME).exists())

    def test_public_workspace_rejected(self):
        with tempfile.TemporaryDirectory() as temp:
            public = Path(temp) / "wrong-location"
            public.mkdir()
            with self.assertRaisesRegex(ValueError, "gitignored"):
                create_plan(public)
            with self.assertRaisesRegex(ValueError, "gitignored"):
                progress(public)

    def test_plan_refused_after_holdout_lock_even_if_template_unfilled(self):
        (self.workspace / "manifest.lock.json").write_text("dummy", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "already sealed"):
            create_plan(self.workspace)
        self.assertFalse((self.workspace / PLAN_FILENAME).exists())

    def test_status_does_not_create_any_files(self):
        before = {p.relative_to(self.workspace).as_posix(): p.read_bytes()
                  for p in self.workspace.rglob("*") if p.is_file()}
        progress(self.workspace)
        after = {p.relative_to(self.workspace).as_posix(): p.read_bytes()
                 for p in self.workspace.rglob("*") if p.is_file()}
        self.assertEqual(before, after)

    def test_cli_create_and_status_no_inference(self):
        for command in ("create", "status"):
            output = io.StringIO()
            with patch.object(sys, "argv", [
                "t10_id_collection_kit.py", command, "--workspace", str(self.workspace),
            ]), redirect_stdout(output):
                self.assertEqual(main(), 0)
            self.assertIn("NO MODEL DOWNLOAD | NO ADB | NO INFERENCE", output.getvalue())
            self.assertIn("CP4 BLOCKED", output.getvalue())
        self.assertTrue((self.workspace / PLAN_FILENAME).is_file())

    def test_cli_repeated_create_fails_closed(self):
        create_plan(self.workspace)
        with patch.object(sys, "argv", [
            "t10_id_collection_kit.py", "create", "--workspace", str(self.workspace),
        ]), redirect_stderr(io.StringIO()):
            self.assertEqual(main(), 1)


if __name__ == "__main__":
    unittest.main()
