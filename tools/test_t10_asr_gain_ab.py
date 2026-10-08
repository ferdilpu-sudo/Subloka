"""Unit tests for the T10 gain-only diagnostic; no device, models or network."""
from __future__ import annotations

from array import array
import math
from pathlib import Path
import sys
import tempfile
import unittest
import wave

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_asr_gain_ab import (
    HEADROOM_PEAK, MANIFEST_SHA, ORDER, SAMPLES,
    create_gain_file, parse_remote_exit, read_manifest, sha,
)


class TestT10GainAB(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def write_wav(self, path, values):
        samples = array("h", values)
        if sys.byteorder == "big":
            samples.byteswap()
        with wave.open(str(path), "wb") as f:
            f.setnchannels(1)
            f.setsampwidth(2)
            f.setframerate(16000)
            f.writeframes(samples.tobytes())

    def test_gain_preserves_original_file_length_rate_and_headroom(self):
        source = self.root / "input.wav"
        derived = self.root / "derived.wav"
        self.write_wav(source, [0, -500, 500, -2000, 2000, 0] * 10)
        old_hash = sha(source)
        information = create_gain_file(source, derived, 17.2)
        self.assertEqual(sha(source), old_hash)
        with wave.open(str(derived), "rb") as f:
            self.assertEqual((f.getnchannels(), f.getsampwidth(), f.getframerate()), (1, 2, 16000))
            self.assertEqual(f.getnframes(), 60)
            samples = array("h")
            samples.frombytes(f.readframes(f.getnframes()))
        if sys.byteorder == "big":
            samples.byteswap()
        self.assertLessEqual(max(abs(int(s)) for s in samples), math.ceil(HEADROOM_PEAK))
        self.assertGreater(information["gain_actual_db"], 0)
        self.assertLessEqual(information["gain_actual_db"], 17.2)

    def test_high_peak_is_capped(self):
        source = self.root / "input.wav"
        self.write_wav(source, [30000, -30000, 0, 40])
        information = create_gain_file(source, self.root / "derived.wav", 17.2)
        self.assertLess(information["gain_actual_db"], 1)
        self.assertGreater(information["gain_actual_db"], -1)

    def test_silent_and_bad_audio_rejected(self):
        source = self.root / "silent.wav"
        self.write_wav(source, [0, 0, 0, 0])
        with self.assertRaisesRegex(ValueError, "Silent"):
            create_gain_file(source, self.root / "out.wav", 8.5)
        with wave.open(str(self.root / "bad.wav"), "wb") as f:
            f.setnchannels(2); f.setsampwidth(2); f.setframerate(16000)
            f.writeframes(b"\x00" * 16)
        with self.assertRaisesRegex(ValueError, "Expected WAV PCM16"):
            create_gain_file(self.root / "bad.wav", self.root / "badout.wav", 8.5)

    def test_marker_parser_rejects_invalid_status(self):
        self.assertEqual(parse_remote_exit("0\r\n"), 0)
        self.assertEqual(parse_remote_exit("7\n"), 7)
        for invalid in ("", "abc", "-1", "256", "1 0", "07"):
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                parse_remote_exit(invalid)

    def test_frozen_manifest_rejects_unrelated_data(self):
        fake = self.root / "manifest.json"
        fake.write_text('{"samples": []}', encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "Manifest changed"):
            read_manifest(fake)

    def test_finalized_listening_review_is_five_ambiguous_one_matching(self):
        import json
        path = Path(__file__).resolve().parent.parent / ".agents/evidence/t10-asr-listening-review-final.json"
        review = json.loads(path.read_text(encoding="utf-8"))
        samples = review["samples"]
        self.assertEqual(len(samples), 6)
        self.assertEqual(len({x["sample"] for x in samples}), 6)
        self.assertEqual(sum(x["status"] == "AUDIO_AMBIGUOUS" for x in samples), 5)
        self.assertEqual(sum(x["status"] == "REF_MATCHES_AUDIO" for x in samples), 1)
        self.assertEqual(review["baseline_reference_texts_changed"], 0)
        self.assertEqual(review["baseline_samples_removed"], 0)
        self.assertEqual(review["official_id_clean_base_wer"], 0.2861)
        self.assertEqual(review["cp4_status"], "BLOCKED")

    def test_scope_is_two_clip_balanced_and_not_a_gate(self):
        self.assertEqual(set(SAMPLES), {"id-clean-02", "id-clean-12"})
        self.assertEqual(len(ORDER), 4)
        self.assertEqual({(sid, variant) for sid, variant in ORDER}, {
            ("id-clean-02", "original"), ("id-clean-02", "gain"),
            ("id-clean-12", "original"), ("id-clean-12", "gain"),
        })
        self.assertEqual(len(MANIFEST_SHA), 64)


if __name__ == "__main__":
    unittest.main()
