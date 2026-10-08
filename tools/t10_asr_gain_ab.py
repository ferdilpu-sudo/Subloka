"""Offline T10 diagnostic: compare original WAV vs gain-only WAV on Android.

Only id-clean-02 and id-clean-12; references are listener-marked AUDIO_AMBIGUOUS.
Never writes into frozen t10-dataset.json or baseline asr-results.csv.
No claim of CP4 quality improvement from this tiny paired experiment.
"""
from __future__ import annotations

import argparse
from array import array
import csv
from datetime import datetime, timezone
import hashlib
import json
import math
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid
import wave

from t10_wer import word_error_rate

ROOT = Path(__file__).resolve().parent.parent
MODEL_SHA = "60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe"
MANIFEST_SHA = "9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444"
SAMPLES = {
    "id-clean-02": {"gain_db": 17.2, "wav_sha": "c810ca538df450bcfe4d671c61f6e71d954abbb250ee3896f04b3070bfd8bb88"},
    "id-clean-12": {"gain_db": 8.5, "wav_sha": "8969b16c001e41e8f6bcff8468740915df28e9df87565c4eacd5e1e8742e5cce"},
}
ORDER = (("id-clean-02", "original"), ("id-clean-12", "gain"), ("id-clean-12", "original"), ("id-clean-02", "gain"))
HEADROOM_PEAK = 32767 * 10 ** (-1 / 20)
STOP_BATTERY_C = 43.0
START_BATTERY_C = 40.0


def sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def create_gain_file(original: Path, dest: Path, gain_db: float) -> dict:
    """Write PCM16 mono at same sample rate/length. Keep original untouched."""
    with wave.open(str(original), "rb") as reader:
        params = reader.getparams()
        if (params.nchannels, params.sampwidth, params.framerate, params.comptype) != (1, 2, 16000, "NONE"):
            raise ValueError("Expected WAV PCM16 mono 16 kHz: " + str(original))
        frames = reader.readframes(params.nframes)
    samples = array("h")
    samples.frombytes(frames)
    if sys.byteorder == "big":
        samples.byteswap()
    peak = max((abs(int(v)) for v in samples), default=0)
    if peak == 0:
        raise ValueError("Silent input WAV: " + str(original))
    requested = 10 ** (gain_db / 20)
    factor = min(requested, HEADROOM_PEAK / peak)
    transformed = array("h", (
        max(-32768, min(32767, round(int(v) * factor)))
        for v in samples
    ))
    if sys.byteorder == "big":
        transformed.byteswap()
    with wave.open(str(dest), "wb") as writer:
        writer.setparams(params)
        writer.writeframes(transformed.tobytes())
    return {
        "gain_requested_db": gain_db,
        "gain_actual_db": round(20 * math.log10(factor), 3),
        "audio_sha256": sha(dest),
        "samples": len(samples),
    }


def adb_command(adb: str, serial: str, args: list[str], *, check=True, timeout=40) -> subprocess.CompletedProcess:
    base = [adb] + (["-s", serial] if serial else [])
    done = subprocess.run(base + args, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=timeout)
    if check and done.returncode != 0:
        raise RuntimeError(f"ADB failed exit={done.returncode} args={args}: {done.stderr[-800:]}")
    return done


def checked_shell(adb: str, serial: str, command: str, *, timeout=40) -> str:
    return adb_command(adb, serial, ["shell", command], timeout=timeout).stdout.strip()


def verify_environment(adb: str, serial: str) -> tuple[str, float, str]:
    lines = adb_command(adb, "", ["devices"], timeout=20).stdout.splitlines()
    connected = [line.split()[0] for line in lines if re.search(r"\sdevice\s*$", line)]
    if serial:
        if serial not in connected:
            raise RuntimeError("Requested device not found in adb devices.")
        selected = serial
    else:
        if len(connected) != 1:
            raise RuntimeError("Connect exactly one authorized ADB device, or pass --serial.")
        selected = connected[0]
    abi = checked_shell(adb, selected, "getprop ro.product.cpu.abi")
    if abi != "arm64-v8a":
        raise RuntimeError("Only arm64-v8a devices are supported.")
    flight = checked_shell(adb, selected, "settings get global airplane_mode_on")
    wifi = checked_shell(adb, selected, "settings get global wifi_on")
    if (flight, wifi) != ("1", "0"):
        raise RuntimeError(f"Offline gate failed: airplane_mode_on={flight} wifi_on={wifi}")
    battery = battery_c(adb, selected)
    if battery >= START_BATTERY_C:
        raise RuntimeError(f"Battery {battery:.1f}C is too warm to start; wait for cooling.")
    return selected, battery, checked_shell(adb, selected, "getprop ro.product.model")


def battery_c(adb: str, serial: str) -> float:
    data = checked_shell(adb, serial, "dumpsys battery")
    m = re.search(r"(?m)^\s*temperature:\s*(-?\d+)\s*$", data)
    if not m:
        raise RuntimeError("No battery temperature sensor data; refusing unsafe test.")
    c = int(m.group(1)) / 10
    if c < 15 or c > 60:
        raise RuntimeError("Unreasonable battery temperature; abort.")
    return round(c, 1)


def read_manifest(path: Path) -> dict:
    if sha(path) != MANIFEST_SHA:
        raise ValueError("Manifest changed from frozen T10 dataset; do not use for diagnostic comparison.")
    fixtures = {x["id"]: x for x in json.loads(path.read_text(encoding="utf-8-sig"))["samples"]}
    for sample_id in SAMPLES:
        fixture = fixtures[sample_id]
        if (fixture["language"], fixture["category"]) != ("id", "clean"):
            raise ValueError("Unexpected fixture language/category")
        if not fixture["reference"].strip():
            raise ValueError("Empty historical reference")
    return fixtures


def parse_remote_exit(text: str) -> int:
    text = text.strip()
    if not re.fullmatch(r"(?:0|[1-9]\d{0,2})", text) or int(text) > 255:
        raise ValueError("Android Whisper exit marker absent or invalid: " + repr(text))
    return int(text)


def write_summary(path: Path, summary: dict) -> None:
    path.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=ROOT / "t10-dataset.json")
    p.add_argument("--workdir", type=Path, default=ROOT / ".t10-benchmark")
    p.add_argument("--serial", default="")
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    manifest = args.manifest.resolve()
    work = args.workdir.resolve()
    fixtures = read_manifest(manifest)
    audio = {}
    for sid, info in SAMPLES.items():
        source = (manifest.parent / fixtures[sid]["audio"]).resolve()
        if not source.is_file() or sha(source) != info["wav_sha"]:
            raise ValueError(f"Missing or modified frozen original WAV: {source}")
        audio[sid] = source
    binary = work / "build-android/bin/whisper-cli"
    model = work / "models/ggml-base.bin"
    if not binary.is_file() or not model.is_file() or sha(model) != MODEL_SHA:
        raise ValueError("Cached Android whisper-cli or pinned Base model missing/changed. Run original setup first.")
    adb = shutil.which("adb")
    if not adb:
        sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME") or str(Path.home() / "AppData/Local/Android/Sdk")
        adb = str(Path(sdk) / "platform-tools/adb.exe")
    if not Path(adb).is_file():
        raise RuntimeError("ADB not found. Ensure Android SDK platform-tools is on PATH.")
    serial, start_temp, device = verify_environment(adb, args.serial)
    print(f"PREFLIGHT PASS: {device}, arm64, offline, battery={start_temp:.1f}C; original WAV/model checksums match.")
    if args.preflight_only:
        return 0

    output = work / ("gain-ab-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
    output.mkdir(parents=True, exist_ok=False)
    remote = "/data/local/tmp/subloka-t10-gain-ab-" + uuid.uuid4().hex[:10]
    summary = {
        "evidence_type": "T10 two-clip original/gain A/B diagnostic; NOT official CP4 benchmark",
        "status": "ABORTED",
        "stop_reason": None,
        "language": "id", "model": "base", "model_sha256": MODEL_SHA,
        "manifest_sha256": MANIFEST_SHA, "device_model": device,
        "offline_verified": True, "usb_powered_possible": True,
        "battery_temp_start_c": start_temp, "battery_stop_c": STOP_BATTERY_C,
        "sample_reference_status": "AUDIO_AMBIGUOUS for id-clean-02 and id-clean-12",
        "limitations": "Four one-off cold-start inference runs on TWO listener-ambiguous WAVs, no statistical significance; gain changes amplitude not SNR. WER against frozen reference is diagnostic ONLY, not official CP4.",
        "audio": {}, "runs": [], "pairs": {},
    }
    errors = None
    try:
        for sid, source in audio.items():
            derived = output / (sid + "-gain.wav")
            metadata = create_gain_file(source, derived, SAMPLES[sid]["gain_db"])
            summary["audio"][sid] = {"original_sha256": sha(source), **metadata}
        adb_command(adb, serial, ["shell", "mkdir -p " + remote])
        adb_command(adb, serial, ["push", str(binary), remote + "/whisper-cli"], timeout=90)
        adb_command(adb, serial, ["shell", "chmod 755 " + remote + "/whisper-cli"])
        adb_command(adb, serial, ["push", str(model), remote + "/model.bin"], timeout=150)
        for i, (sid, variant) in enumerate(ORDER, start=1):
            temp = battery_c(adb, serial)
            if temp >= STOP_BATTERY_C:
                raise RuntimeError(f"THERMAL_STOP: battery={temp:.1f}C >= {STOP_BATTERY_C}C")
            path = audio[sid] if variant == "original" else output / (sid + "-gain.wav")
            adb_command(adb, serial, ["push", str(path), remote + "/input.wav"], timeout=70)
            adb_command(adb, serial, ["shell", "rm -f " + remote + "/result.txt " + remote + "/result.exit"])
            cmd = (
                f"cd {remote} && ./whisper-cli -m model.bin -f input.wav -l id"
                " -nt -ng -nfa -otxt -of result; rc=$?; echo $rc > result.exit; exit $rc"
            )
            start = time.monotonic()
            inference = adb_command(adb, serial, ["shell", cmd], check=False, timeout=180)
            elapsed = time.monotonic() - start
            (output / f"run-{i:02d}-{sid}-{variant}-stderr.log").write_text(inference.stderr, encoding="utf-8")
            marker = adb_command(adb, serial, ["shell", "cat " + remote + "/result.exit"], check=False)
            if marker.returncode != 0:
                raise RuntimeError(f"No readable Android exit marker for {sid}/{variant}")
            remote_rc = parse_remote_exit(marker.stdout)
            transcript = adb_command(adb, serial, ["shell", "cat " + remote + "/result.txt"], check=False)
            if remote_rc != 0 or transcript.returncode != 0 or not transcript.stdout.strip():
                raise RuntimeError(f"Whisper inference failed {sid}/{variant}: remote_rc={remote_rc} transcript_read={transcript.returncode}")
            temp_end = battery_c(adb, serial)
            reference = fixtures[sid]["reference"]
            hypothesis = transcript.stdout.strip()
            (output / f"run-{i:02d}-{sid}-{variant}-hypothesis.txt").write_text(hypothesis + "\n", encoding="utf-8")
            row = {
                "run": i, "sample": sid, "variant": variant,
                "original_reference_unchanged": True,
                "wer_against_unverified_reference_DIAGNOSTIC": round(word_error_rate(reference, hypothesis), 4),
                "duration_s": fixtures[sid]["durationSeconds"],
                "elapsed_s": round(elapsed, 3),
                "rtf": round(elapsed / float(fixtures[sid]["durationSeconds"]), 4),
                "battery_temp_start_c": temp,
                "battery_temp_end_c": temp_end,
                "remote_whisper_exit": remote_rc,
                "host_adb_exit": inference.returncode,
                "hypothesis": hypothesis,
            }
            summary["runs"].append(row)
            print(f"{i}/4 {sid}/{variant}: exit={remote_rc} rtf={row['rtf']:.3f} battery={temp_end:.1f}C")
            if temp_end >= STOP_BATTERY_C:
                raise RuntimeError(f"THERMAL_STOP after run {i}: battery {temp_end:.1f}C")
        for sid in SAMPLES:
            orig = next(x for x in summary["runs"] if x["sample"] == sid and x["variant"] == "original")
            gain = next(x for x in summary["runs"] if x["sample"] == sid and x["variant"] == "gain")
            summary["pairs"][sid] = {
                "hypothesis_identical": orig["hypothesis"] == gain["hypothesis"],
                "wer_original_DIAGNOSTIC": orig["wer_against_unverified_reference_DIAGNOSTIC"],
                "wer_gain_DIAGNOSTIC": gain["wer_against_unverified_reference_DIAGNOSTIC"],
                "delta_wer_DIAGNOSTIC": round(
                    gain["wer_against_unverified_reference_DIAGNOSTIC"] - orig["wer_against_unverified_reference_DIAGNOSTIC"], 4
                ),
            }
        summary["status"] = "DIAGNOSTIC_COLLECTED_NOT_CP4"
    except Exception as exc:
        errors = str(exc)
        summary["stop_reason"] = errors
        print("ABORTED:", errors, file=sys.stderr)
    finally:
        try:
            adb_command(adb, serial, ["shell", "rm -rf " + remote], check=False)
        except Exception:
            pass
        summary["battery_temp_last_c"] = None
        try:
            summary["battery_temp_last_c"] = battery_c(adb, serial)
        except Exception:
            pass
        write_summary(output / "summary.json", summary)
        if summary["runs"]:
            with (output / "runs.csv").open("w", newline="", encoding="utf-8-sig") as fh:
                writer = csv.DictWriter(fh, fieldnames=list(summary["runs"][0].keys()))
                writer.writeheader()
                writer.writerows(summary["runs"])
        print("Diagnostic evidence:", output / "summary.json")
    return 1 if errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
