"""No-network synthetic regressions for external public ID-ASR corpus intake.

Fixtures are artificial metadata only: NOT real audio or evaluation evidence.
"""
from __future__ import annotations

import csv
from contextlib import redirect_stderr, redirect_stdout
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_public_id_corpus import (
    METADATA_FILENAME, REQUIRED, REVISION, SELECTION_FILENAME, choose_samples,
    archive_sizes, fetch_metadata, inspect, main, parse_bool, select, source_info, valid_human_test,
)


class PublicIDCorpusResearchTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name) / "public-corpus-research"
        self.root.mkdir()
        base_patch = patch("t10_id_independent_holdout.PRIVATE_BASE", Path(temp.name))
        base_patch.start()
        self.addCleanup(base_patch.stop)
        self.rows = []
        for n in range(1, 61):
            self.rows.append({
                "audio_path": (
                    "data/processed_balanced19_v7_natural_synth/"
                    f"Dataset_Balanced19/Declarative/M{n%5+1}/take/{n:02d}.wav"
                ),
                "split": "test" if n <= 50 else "train",
                "category": "Declarative",
                "speaker_id": f"M{n%5+1}",
                "speaker_type": "human",
                "is_synthetic": "false",
                "transcript": f"Saya sedang menguji suatu kalimat bahasa Indonesia dari rekaman asli nomor {n}.",
                "duration_sec": "4.5",
                "sample_rate": "16000",
                "num_channels": "1",
                "bits_per_sample": "16",
                "file_size_bytes": "144044",
            })
        self.write_metadata()

    def write_metadata(self):
        with (self.root / METADATA_FILENAME).open("w", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=sorted(REQUIRED))
            w.writeheader()
            w.writerows(self.rows)

    def test_public_source_is_immutable_revision_with_license_claim_only(self):
        source = source_info()
        self.assertEqual(source["immutable_upstream_revision"], REVISION)
        self.assertEqual(len(REVISION), 40)
        self.assertIn("c65fe8bc", source["upstream_metadata_url"])
        self.assertIn("CC-BY-4.0", source["license_metadata"])
        self.assertFalse(source["source_is_fresh_consent_holdout"])
        self.assertFalse(source["train_disjointness_from_maleo_independently_confirmed"])
        self.assertFalse(source["test_transcripts_human_rechecked"])
        self.assertEqual(source["CP4"], "BLOCKED")

    def test_inspect_filters_train_and_returns_only_safe_aggregate_counts(self):
        out = inspect(self.root)
        self.assertEqual(out["eligible_human_test_rows"], 50)
        self.assertEqual(len(out["categories"]), 1)
        self.assertEqual(out["categories"][0]["category"], "Declarative")
        self.assertEqual(out["categories"][0]["distinct_public_speaker_labels"], 5)
        self.assertFalse(out["audio_downloaded"])
        self.assertNotIn("Saya sedang menguji", json.dumps(out))
        self.assertEqual(out["CP4"], "BLOCKED")

    def test_select_pins_30_test_human_rows_with_unique_transcripts(self):
        result = select(self.root, "Declarative")
        self.assertEqual(result["sample_count"], 30)
        self.assertEqual(result["source_split"], "test")
        path = self.root / SELECTION_FILENAME
        report = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(len(report["items"]), 30)
        self.assertEqual(len({i["reference_from_publisher_not_rechecked"] for i in report["items"]}), 30)
        self.assertEqual(report["public_speaker_label_count"], 5)
        self.assertGreaterEqual(report["normalized_reference_words"], 180)
        self.assertFalse(report["all_audio_downloaded"])
        self.assertFalse(report["test_transcripts_human_rechecked"])
        self.assertFalse(report["evaluation_pass"])
        self.assertEqual(report["CP4"], "BLOCKED")
        self.assertFalse((self.root / "audio").exists())

    def test_authentic_style_repeated_public_prompts_are_disclosed_not_hidden(self):
        # Publisher notes ~19 sentence slots per category, many speaker takes.
        # Thirty different WAV paths do NOT imply thirty distinct reference texts.
        for idx, row in enumerate(self.rows):
            row["transcript"] = (
                "Kalimat bahasa Indonesia untuk percobaan suara dari rekaman orang "
                + str(idx % 5)
            )
        self.write_metadata()
        selected = choose_samples(self.root, "Declarative")
        self.assertEqual(selected["sample_count"], 30)
        self.assertEqual(selected["distinct_audio_paths"], 30)
        self.assertEqual(selected["distinct_reference_prompts"], 5)
        self.assertEqual(selected["repeated_reference_prompts"], 25)
        self.assertTrue(selected["reference_texts_may_repeat_across_speakers"])
        self.assertTrue(selected["not_unseen_prompt_or_open_vocabulary_benchmark"])
        self.assertFalse(selected["evaluation_pass"])
        self.assertEqual(selected["CP4"], "BLOCKED")

    def test_selection_deterministic_and_never_overwrite(self):
        first = choose_samples(self.root, "Declarative")
        second = choose_samples(self.root, "Declarative")
        self.assertEqual(first, second)
        select(self.root, "Declarative")
        before = (self.root / SELECTION_FILENAME).read_bytes()
        with self.assertRaises(FileExistsError):
            select(self.root, "Declarative")
        self.assertEqual((self.root / SELECTION_FILENAME).read_bytes(), before)

    def test_synthetic_rows_never_qualify_even_if_split_is_test(self):
        self.rows[0]["is_synthetic"] = "true"
        self.rows[1]["speaker_type"] = "synthetic"
        self.rows[2]["is_synthetic"] = ""
        self.rows[3]["split"] = "val"
        self.write_metadata()
        self.assertEqual(inspect(self.root)["eligible_human_test_rows"], 46)

    def test_reject_unsafe_audio_paths_and_wrong_wav_metadata(self):
        good = dict(self.rows[0])
        for replacement in ("../../private.wav", "/etc/passwd", "https://example.com/x.wav"):
            with self.subTest(path=replacement):
                bad = {**good, "audio_path": replacement}
                self.assertFalse(valid_human_test(bad))
        for key, badvalue in (
            ("sample_rate", "8000"), ("num_channels", "2"),
            ("bits_per_sample", "8"), ("duration_sec", "45"),
            ("file_size_bytes", "9999999999"),
        ):
            with self.subTest(key=key):
                self.assertFalse(valid_human_test({**good, key: badvalue}))

    def test_refuse_missing_ambiguous_synthetic_marker(self):
        for value in ("", "unknown", "nan", "null", "no"):
            self.assertIsNone(parse_bool(value))
        self.assertIs(parse_bool("false"), False)
        self.assertIs(parse_bool("true"), True)
        for marker in ("", "unknown", "null", "1"):
            self.assertFalse(valid_human_test({**self.rows[0], "is_synthetic": marker}))

    def test_insufficient_speaker_diversity_refuses_selection(self):
        for row in self.rows:
            row["speaker_id"] = "M1"
        self.write_metadata()
        with self.assertRaisesRegex(ValueError, "multiple distinct"):
            choose_samples(self.root, "Declarative")

    def test_insufficient_rows_or_category_rejected(self):
        with self.assertRaisesRegex(ValueError, "Insufficient human test"):
            choose_samples(self.root, "Nonexistent")
        with self.assertRaisesRegex(ValueError, "Category must"):
            choose_samples(self.root, "../private")

    def test_missing_or_corrupted_metadata_fails_closed(self):
        source = self.root / METADATA_FILENAME
        source.unlink()
        with self.assertRaisesRegex(ValueError, "fetch"):
            inspect(self.root)
        source.write_text("audio_path,split\n1,2\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "schema"):
            inspect(self.root)

    def _mock_archive_listing(self, *, missing=False, unsafe_size=False, redirect=False):
        names = (
            "Clarification", "Conditional", "Confirmation", "Declarative",
            "Exclamatory", "Imperative", "Interrogative", "Negation",
            "Persuasive", "Rhetorical", "Scheduling"
        )
        entries = [{
            "type": "file",
            "path": f"data/audio_shards/by_category/{name}.tar",
            "size": (0 if unsafe_size and name == "Imperative" else 1_000_000_000 + idx),
            "lfs": {"oid": "a" * 64},
        } for idx, name in enumerate(names)]
        if missing:
            entries.pop()
        payload = json.dumps(entries).encode("utf-8")
        class MockResponse:
            url = "https://bad-domain.example/file" if redirect else "https://huggingface.co/api/datasets/"
            def __init__(self):
                self.stream = io.BytesIO(payload)
            def read(self, n):
                return self.stream.read(n)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        return MockResponse()

    def test_archive_size_preflight_is_only_public_json_not_tar(self):
        with patch("t10_public_id_corpus.urllib.request.urlopen",
                   return_value=self._mock_archive_listing()) as req:
            report = archive_sizes(self.root)
        self.assertEqual(req.call_count, 1)
        self.assertEqual(report["archive_count"], 11)
        self.assertEqual(report["total_archive_bytes_publisher_api"], 11_000_000_055)
        self.assertTrue(report["archive_api_url"].startswith("https://huggingface.co/api/"))
        self.assertFalse(report["tar_or_wav_downloaded"])
        self.assertEqual(report["CP4"], "BLOCKED")
        for shard in report["categories_by_archive_size"]:
            self.assertFalse(shard["approved_for_download"])
            self.assertFalse(shard["local_archive_exists_or_verified"])
            self.assertIn("/resolve/", shard["pinned_tar_url_NOT_DOWNLOADED"])
        self.assertFalse(any(self.root.glob("*.tar")))

    def test_archive_size_preflight_rejects_missing_category(self):
        with patch("t10_public_id_corpus.urllib.request.urlopen",
                   return_value=self._mock_archive_listing(missing=True)):
            with self.assertRaisesRegex(ValueError, "mismatch"):
                archive_sizes(self.root)

    def test_archive_size_preflight_rejects_unsafe_size_and_redirect(self):
        for params, error in (({"unsafe_size": True}, "implausible"),
                              ({"redirect": True}, "HTTPS huggingface.co")):
            with self.subTest(params=params):
                with patch("t10_public_id_corpus.urllib.request.urlopen",
                           return_value=self._mock_archive_listing(**params)):
                    with self.assertRaisesRegex(ValueError, error):
                        archive_sizes(self.root)

    def test_cli_archive_sizes_preserves_local_metadata(self):
        original = (self.root / METADATA_FILENAME).read_bytes()
        buffer = io.StringIO()
        with patch("t10_public_id_corpus.urllib.request.urlopen",
                   return_value=self._mock_archive_listing()), patch.object(
                       sys, "argv", [
                           "t10_public_id_corpus.py", "archive-sizes",
                           "--workspace", str(self.root),
                       ]), redirect_stdout(buffer):
            self.assertEqual(main(), 0)
        self.assertIn("NO AUDIO SHARD DOWNLOAD", buffer.getvalue())
        self.assertIn("CP4 BLOCKED", buffer.getvalue())
        self.assertEqual(original, (self.root / METADATA_FILENAME).read_bytes())

    def test_public_workspace_forbidden_and_cli_source_no_network(self):
        with tempfile.TemporaryDirectory() as public:
            with self.assertRaisesRegex(ValueError, "gitignored"):
                inspect(Path(public))
        buffer = io.StringIO()
        with patch.object(sys, "argv", ["t10_public_id_corpus.py", "source"]), \
             redirect_stdout(buffer):
            self.assertEqual(main(), 0)
        self.assertIn("NO AUDIO SHARD DOWNLOAD", buffer.getvalue())
        self.assertIn("CP4 BLOCKED", buffer.getvalue())

    def test_cli_inspect_and_select_does_not_run_model_or_download_audio(self):
        for cmd, tail in (("inspect", []), ("select", ["--category", "Declarative"])):
            buffer = io.StringIO()
            with patch.object(sys, "argv", [
                "t10_public_id_corpus.py", cmd, "--workspace", str(self.root), *tail
            ]), redirect_stdout(buffer):
                self.assertEqual(main(), 0)
            self.assertIn("NO AUDIO SHARD DOWNLOAD", buffer.getvalue())
            self.assertIn("CP4 BLOCKED", buffer.getvalue())

    def test_metadata_fetch_bounded_and_schema_checked_without_wavs(self):
        csv_data = (self.root / METADATA_FILENAME).read_bytes()
        (self.root / METADATA_FILENAME).unlink()
        class MockResponse:
            url = "https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset/fake"
            headers = {"Content-Length": str(len(csv_data))}
            def __init__(self):
                self.stream = io.BytesIO(csv_data)
            def read(self, n):
                return self.stream.read(n)
            def __enter__(self):
                return self
            def __exit__(self, *args):
                return False
        with patch("t10_public_id_corpus.urllib.request.urlopen", return_value=MockResponse()):
            output = fetch_metadata(self.root)
        self.assertTrue(output["only_metadata"])
        self.assertGreater(output["downloaded_metadata_bytes"], 0)
        self.assertEqual((self.root / METADATA_FILENAME).read_bytes(), csv_data)
        self.assertFalse((self.root / "audio").exists())

    def test_fetch_does_not_keep_invalid_upstream_schema(self):
        source = self.root / METADATA_FILENAME
        source.unlink()
        invalid = b"foo,bar\nA,B\n"
        class Bad:
            url = "https://huggingface.co/example"
            headers = {"Content-Length": str(len(invalid))}
            def __init__(self): self.stream = io.BytesIO(invalid)
            def read(self, n): return self.stream.read(n)
            def __enter__(self): return self
            def __exit__(self, *args): return False
        with patch("t10_public_id_corpus.urllib.request.urlopen", return_value=Bad()):
            with self.assertRaisesRegex(ValueError, "required corpus columns"):
                fetch_metadata(self.root)
        self.assertFalse(source.exists())


if __name__ == "__main__":
    unittest.main()
