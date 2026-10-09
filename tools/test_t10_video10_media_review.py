"""Self-contained T10 media 10-min evidence validator regressions (no actual video)."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parent))
from t10_video10_media_review import summarize, validate, load_json


SHA = "a" * 64


def valid_host():
    return {
        "evidence_type": "T10_REAL_VIDEO_MEDIA_STAGE_ONLY",
        "video_file": "example.mp4",
        "video_bytes": 19_000_000,
        "video_sha256": SHA,
        "battery_start_c": 33.4,
        "airplane_mode": "1",
        "wifi_on": "0",
        "runner": "app.subloka.caption.test/androidx.test.runner.AndroidJUnitRunner",
        "cp4": "BLOCKED",
    }


def valid_device():
    return {
        "schema_version": 1,
        "type": "T10_REAL_VIDEO_MEDIA_STAGE_ONLY_NOT_CP4",
        "status": "MEDIA_STAGE_PASS_NOT_FULL_E2E",
        "full_app_e2e": "BLOCKED_ASR_TRANSLATION_RENDER_EXPORT_NOT_INTEGRATED",
        "source_file_name": "t10-real-video.mp4",
        "source_bytes": 19_000_000,
        "source_sha256": SHA,
        "source_sha256_after": SHA,
        "source_unchanged": True,
        "battery_start_c": 33.5,
        "battery_end_c": 36.3,
        "battery_peak_c": 36.3,
        "duration_us": 600_000_000,
        "pcm_first_pts_us": 0,
        "pcm_last_pts_us": 599_995_000,
        "pcm_truncated": False,
        "pcm_bytes_decoded": 56_000_000,
        "chunks": 11000,
        "pcm_sample_rate": 48000,
        "pcm_channel_count": 2,
        "pcm_sample_format": "S16_LE",
        "video_mime": "video/avc",
        "audio_mime": "audio/mp4a-latm",
        "audio_track_count": 1,
        "width_px": 1920,
        "height_px": 1080,
        "rotation_degrees": 0,
        "peak_process_pss_kb_sampled": 90_000,
        "peak_java_heap_used_bytes_sampled": 20_000_000,
        "inspect_wall_ms": 900,
        "decode_wall_ms": 9000,
        "total_wall_ms": 12000,
        "offline_connection_verified_by": "Windows ADB harness preflight; not verified in-test",
        "temperature_is_battery_not_cpu_die": True,
        "memory_is_sampled_not_true_peak": True,
    }


class T10RealVideoTenMinuteReviewTest(unittest.TestCase):
    def test_healthy_real_duration_sample_is_media_only(self):
        result = validate(valid_host(), valid_device())
        self.assertEqual(result["status"], "MEDIA_STAGE_PASS_NOT_FULL_E2E")
        self.assertEqual(result["cp4_status"], "BLOCKED")
        self.assertEqual(result["t11_status"], "TODO")
        self.assertAlmostEqual(result["physical_video_duration_sec"], 600.0)
        self.assertEqual(result["decode_real_time_factor"], .015)
        self.assertTrue(result["battery_proxy_not_cpu_die"])

    def test_not_full_e2e_even_with_valid_media(self):
        device = valid_device()
        device["full_app_e2e"] = "PASS"
        with self.assertRaisesRegex(ValueError, "full application E2E"):
            validate(valid_host(), device)

    def test_instrumented_test_must_pass(self):
        device = valid_device()
        device["status"] = "MEDIA_STAGE_FAILED"
        with self.assertRaisesRegex(ValueError, "did not complete"):
            validate(valid_host(), device)

    def test_short_fake_video_cannot_meet_ten_minute_gate(self):
        device = valid_device()
        device["duration_us"] = 599_999_999
        with self.assertRaisesRegex(ValueError, "duration_us"):
            validate(valid_host(), device)

    def test_incomplete_audio_tail_rejected(self):
        device = valid_device()
        device["pcm_last_pts_us"] = 590_000_000
        with self.assertRaisesRegex(ValueError, "pcm_last_pts_us"):
            validate(valid_host(), device)

    def test_truncated_decode_or_no_audio_rejected(self):
        device = valid_device()
        device["pcm_truncated"] = True
        with self.assertRaisesRegex(ValueError, "truncated"):
            validate(valid_host(), device)
        device = valid_device()
        device["pcm_bytes_decoded"] = 0
        with self.assertRaisesRegex(ValueError, "pcm_bytes_decoded"):
            validate(valid_host(), device)

    def test_host_sha_must_match_both_device_checksums(self):
        device = valid_device()
        device["source_sha256_after"] = "b" * 64
        with self.assertRaisesRegex(ValueError, "SHA256 mismatch"):
            validate(valid_host(), device)
        device = valid_device()
        device["source_unchanged"] = False
        with self.assertRaisesRegex(ValueError, "mutation"):
            validate(valid_host(), device)

    def test_media_source_size_cannot_change(self):
        device = valid_device()
        device["source_bytes"] = 19000001
        with self.assertRaisesRegex(ValueError, "source size"):
            validate(valid_host(), device)

    def test_offline_airplane_and_wifi_required(self):
        host = valid_host()
        host["wifi_on"] = "1"
        with self.assertRaisesRegex(ValueError, "offline"):
            validate(host, valid_device())
        host = valid_host()
        host["airplane_mode"] = "0"
        with self.assertRaisesRegex(ValueError, "offline"):
            validate(host, valid_device())

    def test_temperature_and_identity_fail_closed(self):
        device = valid_device()
        device["battery_peak_c"] = 43
        with self.assertRaisesRegex(ValueError, "battery_peak_c"):
            validate(valid_host(), device)
        device = valid_device()
        device["battery_start_c"] = 38.3
        with self.assertRaisesRegex(ValueError, "Battery start difference"):
            validate(valid_host(), device)

    def test_lost_disclosures_not_treated_as_gate_pass(self):
        device = valid_device()
        device["temperature_is_battery_not_cpu_die"] = False
        with self.assertRaisesRegex(ValueError, "Battery proxy"):
            validate(valid_host(), device)
        device = valid_device()
        device["memory_is_sampled_not_true_peak"] = False
        with self.assertRaisesRegex(ValueError, "Memory snapshot"):
            validate(valid_host(), device)

    def test_no_video_audio_track_fails(self):
        device = valid_device()
        device["video_mime"] = "audio/mp4a-latm"
        with self.assertRaisesRegex(ValueError, "video track"):
            validate(valid_host(), device)
        device = valid_device()
        device["audio_mime"] = "video/avc"
        with self.assertRaisesRegex(ValueError, "audio track"):
            validate(valid_host(), device)

    def test_unsupported_pcm_format_rejected(self):
        device = valid_device()
        device["pcm_sample_format"] = "UNKNOWN"
        with self.assertRaisesRegex(ValueError, "PCM sample format"):
            validate(valid_host(), device)

    def test_real_time_factor_is_decode_time_not_video_wall(self):
        device = valid_device()
        device["decode_wall_ms"] = 100_000
        device["total_wall_ms"] = 102_000
        result = validate(valid_host(), device)
        self.assertAlmostEqual(result["decode_real_time_factor"], 0.1667, places=4)
        self.assertEqual(result["physical_video_duration_sec"], 600.0)

    def test_report_written_once_and_tracks_evidence_digests(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            host = root/"host.json"
            device = root/"device.json"
            out = root/"report.json"
            host.write_text(json.dumps(valid_host()), encoding="utf-8")
            device.write_text(json.dumps(valid_device()), encoding="utf-8")
            result = summarize(host, device, out)
            self.assertEqual(result["cp4_status"], "BLOCKED")
            self.assertEqual(load_json(out)["status"], "MEDIA_STAGE_PASS_NOT_FULL_E2E")
            self.assertEqual(len(load_json(out)["host_json_sha256"]), 64)
            with self.assertRaisesRegex(FileExistsError, "overwrite"):
                summarize(host, device, out)

    def test_untrustworthy_data_types_fail(self):
        device = valid_device()
        device["decode_wall_ms"] = True
        with self.assertRaisesRegex(ValueError, "decode_wall_ms"):
            validate(valid_host(), device)
        device = valid_device()
        device["total_wall_ms"] = 8000
        with self.assertRaisesRegex(ValueError, "timings"):
            validate(valid_host(), device)


if __name__ == "__main__":
    unittest.main()
