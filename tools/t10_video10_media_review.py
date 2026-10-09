#!/usr/bin/env python3
"""Validate a real 10-minute Android MEDIA-stage run (NOT full app E2E).

Usage: python tools/t10_video10_media_review.py HOST.json DEVICE.json
       python tools/t10_video10_media_review.py HOST.json DEVICE.json --json REPORT.json

Works on locally saved, gitignored device evidence. It does not declare CP4 PASS,
review speech transcription, attest identity, or infer CPU-die temperature.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


EXPECTED_TYPE = "T10_REAL_VIDEO_MEDIA_STAGE_ONLY_NOT_CP4"
EXPECTED_HOST_TYPE = "T10_REAL_VIDEO_MEDIA_STAGE_ONLY"
EXPECTED_DISCLOSURE = "BLOCKED_ASR_TRANSLATION_RENDER_EXPORT_NOT_INTEGRATED"
KNOWN_PCM_FORMATS = {"S16_LE", "FLOAT32_LE", "U8"}


def load_json(path: Path) -> dict:
    result = json.loads(path.read_text(encoding="utf-8-sig"))
    if not isinstance(result, dict):
        raise ValueError("Evidence must be JSON object: " + str(path))
    return result


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def number(o: dict, name: str, *, low: float, high: float) -> float:
    value = o.get(name)
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"Missing numeric {name}")
    value = float(value)
    if not math.isfinite(value) or not low <= value <= high:
        raise ValueError(f"Invalid {name}: {value}")
    return value


def validate(host: dict, device: dict) -> dict:
    if host.get("evidence_type") != EXPECTED_HOST_TYPE or host.get("cp4") != "BLOCKED":
        raise ValueError("Unexpected host preflight evidence type or CP4 status")
    if host.get("airplane_mode") != "1" or host.get("wifi_on") != "0":
        raise ValueError("Device host preflight did not verify airplane=1 and wifi=0")
    if device.get("schema_version") != 1 or device.get("type") != EXPECTED_TYPE:
        raise ValueError("Invalid device report schema/type")
    if device.get("status") != "MEDIA_STAGE_PASS_NOT_FULL_E2E":
        raise ValueError("Device did not complete the real-video media stage")
    if device.get("full_app_e2e") != EXPECTED_DISCLOSURE:
        raise ValueError("Do not label this result full application E2E")
    if device.get("offline_connection_verified_by") != (
        "Windows ADB harness preflight; not verified in-test"
    ):
        raise ValueError("Offline source/limitation disclosure missing")
    if device.get("temperature_is_battery_not_cpu_die") is not True:
        raise ValueError("Battery proxy must be clearly distinguished from SoC temperature")
    if device.get("memory_is_sampled_not_true_peak") is not True:
        raise ValueError("Memory snapshot does not establish actual allocation peak")
    if device.get("source_file_name") != "t10-real-video.mp4":
        raise ValueError("Unknown scoped source video name")
    digest = host.get("video_sha256")
    if (not isinstance(digest, str) or len(digest) != 64 or
        any(ch not in "0123456789abcdef" for ch in digest)):
        raise ValueError("Missing canonical host SHA256 for original video")
    if device.get("source_sha256") != digest or device.get("source_sha256_after") != digest:
        raise ValueError("Host and pre/post device video SHA256 mismatch")
    if device.get("source_unchanged") is not True:
        raise ValueError("Media source mutation detected")

    size = number(host, "video_bytes", low=1, high=5e10)
    if number(device, "source_bytes", low=1, high=5e10) != size:
        raise ValueError("Device source size != original host input size")
    initial = number(host, "battery_start_c", low=10, high=39.999)
    start = number(device, "battery_start_c", low=10, high=39.999)
    if abs(initial - start) > 2:
        raise ValueError("Battery start difference >2 C between host and device")
    end = number(device, "battery_end_c", low=10, high=42.999)
    peak = number(device, "battery_peak_c", low=max(start, end), high=42.999)

    duration = number(device, "duration_us", low=600e6, high=900e6)
    last_pts = number(device, "pcm_last_pts_us", low=duration - 5e6, high=duration + 5e6)
    first_pts = number(device, "pcm_first_pts_us", low=0, high=5e6)
    if last_pts < first_pts:
        raise ValueError("PCM timestamps not ordered")
    if device.get("pcm_truncated") is not False:
        raise ValueError("PCM stream truncated")
    pcm_bytes = number(device, "pcm_bytes_decoded", low=1, high=20e9)
    chunks = number(device, "chunks", low=1, high=10e7)
    rate = number(device, "pcm_sample_rate", low=8000, high=384000)
    channels = number(device, "pcm_channel_count", low=1, high=32)
    if device.get("pcm_sample_format") not in KNOWN_PCM_FORMATS:
        raise ValueError("Output PCM sample format not supported for evidence")
    if not str(device.get("video_mime", "")).startswith("video/"):
        raise ValueError("No supported video track")
    if not str(device.get("audio_mime", "")).startswith("audio/"):
        raise ValueError("No supported audio track")
    number(device, "width_px", low=1, high=16384)
    number(device, "height_px", low=1, high=16384)
    number(device, "audio_track_count", low=1, high=32)
    if device.get("rotation_degrees") not in (0, 90, 180, 270):
        raise ValueError("Invalid video rotation")
    pss_kb = number(device, "peak_process_pss_kb_sampled", low=1, high=1e8)
    heap_bytes = number(device, "peak_java_heap_used_bytes_sampled", low=1, high=1e10)
    inspection_ms = number(device, "inspect_wall_ms", low=0, high=1_200_000)
    decode_ms = number(device, "decode_wall_ms", low=1, high=1_200_000)
    wall_ms = number(device, "total_wall_ms", low=1, high=1_200_000)
    if inspection_ms + decode_ms > wall_ms + 1000:
        raise ValueError("Inspect/decode timings exceed total wall time")

    # This validator never turns missing ASR, subtitles, translation or export into PASS.
    return {
        "evidence_type": "T10_REAL_10MIN_VIDEO_MEDIA_STAGE_VALIDATED_NOT_CP4",
        "status": "MEDIA_STAGE_PASS_NOT_FULL_E2E",
        "physical_video_duration_sec": round(duration / 1e6, 3),
        "video_source_sha256": digest,
        "video_source_bytes": int(size),
        "video_source_unchanged": True,
        "offline_preflight_user_run": True,
        "inspected_video_mime": device["video_mime"],
        "audio_mime": device["audio_mime"],
        "decoded_pcm_bytes": int(pcm_bytes),
        "decoded_pcm_chunks": int(chunks),
        "audio_sample_rate_hz": int(rate),
        "audio_channels": int(channels),
        "last_decoded_audio_pts_sec": round(last_pts / 1e6, 3),
        "inspect_wall_sec": round(inspection_ms / 1000, 3),
        "decode_wall_sec": round(decode_ms / 1000, 3),
        "whole_media_stage_wall_sec": round(wall_ms / 1000, 3),
        "decode_real_time_factor": round(decode_ms * 1000.0 / duration, 4),
        "battery_start_c": start,
        "battery_end_c": end,
        "battery_peak_c": peak,
        "battery_proxy_not_cpu_die": True,
        "sampled_peak_process_pss_mib": round(pss_kb / 1024.0, 3),
        "sampled_peak_java_heap_mib": round(heap_bytes / 1048576.0, 3),
        "not_actual_memory_allocation_peak": True,
        "limitations": (
            "Video media metadata and streaming audio decode only. No speech ASR, "
            "caption generation/timing, offline translation or subtitle MP4 export "
            "was performed. Production full app E2E remains blocked by T11-T14. "
            "Phone temperature is a battery proxy; host offline settings are "
            "recorded but not cryptographically attested."
        ),
        "cp4_status": "BLOCKED",
        "t11_status": "TODO",
    }


def summarize(host_path: Path, device_path: Path, output_path: Path | None) -> dict:
    host, device = load_json(host_path), load_json(device_path)
    summary = validate(host, device)
    summary["host_json_sha256"] = sha256(host_path)
    summary["device_json_sha256"] = sha256(device_path)
    if output_path is not None:
        if output_path.exists():
            raise FileExistsError("Refusing to overwrite validated evidence: " + str(output_path))
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    print("MEDIA STAGE PASS (NOT full app E2E / CP4)")
    print(f"Duration: {summary['physical_video_duration_sec']} sec, audio last PTS "
          f"{summary['last_decoded_audio_pts_sec']} sec")
    print(f"Decoder: {summary['decode_wall_sec']} sec, RTF {summary['decode_real_time_factor']}")
    print(f"Sampled peak PSS: {summary['sampled_peak_process_pss_mib']} MiB; "
          f"battery peak {summary['battery_peak_c']} C (not CPU die)")
    print("T10 ACTIVE; CP4 BLOCKED; T11 TODO")
    return summary


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("host", type=Path)
    p.add_argument("device", type=Path)
    p.add_argument("--json", type=Path, default=None)
    args = p.parse_args()
    try:
        summarize(args.host, args.device, args.json)
        return 0
    except (KeyError, ValueError, TypeError, FileNotFoundError, FileExistsError,
            json.JSONDecodeError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
