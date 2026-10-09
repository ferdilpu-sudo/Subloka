"""T10 offline Sony Base vs multilingual Small-q5_1 ASR experiment.

Only the already-frozen 20 Indonesian FLEURS clean WAVs. Never CP4.
Online candidate preparation: --prepare-small. Inference requires airplane
mode and Wi-Fi off. Start with --max-pairs 2, then --resume SESSION.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time
import uuid

from t10_asr_decode_ab import load_frozen_inputs
from t10_asr_error_audit import align_errors
from t10_asr_gain_ab import adb_command, battery_c, parse_remote_exit, sha, verify_environment
from t10_asr_small_protocol import (
    ROOT, BASELINE_SHA, BASE_SHA, SMALL_SHA, MANIFEST_SHA, VARIANTS,
    SHA_BY_VARIANT, FLAGS, PROTOCOL, STOP_C, MAX_WALL_SECONDS,
    PER_RUN_SECONDS, MIN_DEVICE_FREE_KIB, pairs, command, prepare_small,
    archive_summary, analyze,
)

def get_rss(adb: str, serial: str, remote: str) -> int | None:
    cmd = f"pid=$(cat {remote}/result.pid 2>/dev/null); case $pid in ''|*[!0-9]*) exit 1;; esac; grep '^VmRSS:' /proc/$pid/status"
    out = adb_command(adb, serial, ["shell", cmd], check=False, timeout=10)
    if out.returncode != 0:
        return None
    match = re.search(r"VmRSS:\s*(\d+)\s*kB", out.stdout)
    return int(match.group(1)) if match else None


def stop_own_process(adb: str, serial: str, remote: str) -> None:
    out = adb_command(adb, serial, ["shell", f"cat {remote}/result.pid"], check=False, timeout=8)
    if out.returncode == 0 and re.fullmatch(r"[1-9]\d{0,9}", out.stdout.strip()):
        adb_command(adb, serial, ["shell", "kill -TERM " + out.stdout.strip()], check=False, timeout=8)


def one_run(adb: str, serial: str, remote: str, sid: str, variant: str,
            fixture: dict, session: Path, index: int, session_start: float) -> dict:
    temperature = battery_c(adb, serial)
    if temperature >= STOP_C:
        raise RuntimeError(f"Battery thermal stop {temperature}C, before {sid}/{variant}")
    wav = Path(fixture["_file"])
    adb_command(adb, serial, ["push", str(wav), remote + "/input.wav"], timeout=75)
    adb_command(adb, serial, ["shell", f"rm -f {remote}/result.txt {remote}/result.exit {remote}/result.pid"])
    stdout_path = session / f"run-{index:02d}-{sid}-{variant}-stdout.log"
    stderr_path = session / f"run-{index:02d}-{sid}-{variant}-stderr.log"
    start = time.monotonic()
    sampled_rss: int | None = None
    proc = None
    with stdout_path.open("wb") as sout, stderr_path.open("wb") as serr:
        proc = subprocess.Popen([adb, "-s", serial, "shell", command(remote, variant)],
                                stdout=sout, stderr=serr)
        try:
            while proc.poll() is None:
                if time.monotonic() - start > PER_RUN_SECONDS:
                    raise RuntimeError(f"ASR inference timed out after {PER_RUN_SECONDS}s: {sid}/{variant}")
                if time.monotonic() - session_start > MAX_WALL_SECONDS:
                    raise RuntimeError("15-minute session safety budget exceeded; resume after cooling")
                temp = battery_c(adb, serial)
                if temp >= STOP_C:
                    raise RuntimeError(f"Battery thermal stop {temp}C during {sid}/{variant}")
                rss = get_rss(adb, serial, remote)
                if rss is not None:
                    sampled_rss = max(sampled_rss or 0, rss)
                time.sleep(2)
            proc.wait(timeout=8)
        except BaseException:
            try:
                stop_own_process(adb, serial, remote)
            finally:
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            raise

    elapsed = time.monotonic() - start
    marker = adb_command(adb, serial, ["shell", f"cat {remote}/result.exit"], check=False)
    transcript = adb_command(adb, serial, ["shell", f"cat {remote}/result.txt"], check=False)
    exit_code = parse_remote_exit(marker.stdout) if marker.returncode == 0 else None
    if exit_code != 0 or proc.returncode != 0 or transcript.returncode != 0 or not transcript.stdout.strip():
        tail = stderr_path.read_text("utf-8", errors="replace")[-700:]
        raise RuntimeError(f"Inference failed {sid}/{variant} Android={exit_code} ADB={proc.returncode}: {tail}")
    last_battery = battery_c(adb, serial)
    if last_battery >= STOP_C:
        raise RuntimeError(f"Battery thermal stop {last_battery}C after {sid}/{variant}")
    hypothesis = transcript.stdout.strip()
    edits = align_errors(fixture["reference"], hypothesis)
    return {
        "sample": sid, "variant": variant,
        "model_sha256": SHA_BY_VARIANT[variant],
        "word_errors": edits["errors"], "reference_words": edits["reference_words"],
        "wer_diagnostic": round(edits["errors"] / edits["reference_words"], 5),
        "duration_s": fixture["durationSeconds"],
        "elapsed_s": round(elapsed, 3),
        "rtf": round(elapsed / float(fixture["durationSeconds"]), 5),
        "battery_start_c": temperature, "battery_end_c": last_battery,
        "sampled_peak_rss_kb": sampled_rss,
        "remote_whisper_exit": exit_code, "host_adb_exit": proc.returncode,
        "hypothesis": hypothesis,
    }


def device_free_kib(adb: str, serial: str) -> int:
    out = adb_command(adb, serial, ["shell", "df -k /data/local/tmp"], check=False, timeout=15)
    if out.returncode != 0:
        raise RuntimeError("Cannot verify available device /data storage")
    lines = [line.strip() for line in out.stdout.splitlines() if line.strip()]
    if len(lines) < 2:
        raise RuntimeError("Unexpected Android df output")
    columns = lines[-1].split()
    if len(columns) < 5 or not columns[-3].isdigit():
        raise RuntimeError("Unable to parse free space from Android df output")
    return int(columns[-3])


def run() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=ROOT / "t10-dataset.json")
    p.add_argument("--baseline", type=Path, default=ROOT / ".t10-benchmark/asr-results.csv")
    p.add_argument("--workdir", type=Path, default=ROOT / ".t10-benchmark")
    p.add_argument("--serial", default="")
    p.add_argument("--prepare-small", action="store_true", help="ONLY phase requiring internet; SHA256 checked")
    p.add_argument("--preflight-only", action="store_true")
    p.add_argument("--max-pairs", type=int, default=2, help="1-20 new PAIRS per run; default safe pilot 2")
    p.add_argument("--resume", type=Path)
    args = p.parse_args()
    if not 1 <= args.max_pairs <= 20:
        p.error("--max-pairs must be 1..20")
    if args.prepare_small and (args.resume or args.preflight_only):
        p.error("Online model preparation is a separate phase")
    work = args.workdir.resolve()
    small = work / "models/ggml-small-q5_1.bin"
    if args.prepare_small:
        prepare_small(small)
        return 0
    fixtures, archived = load_frozen_inputs(args.manifest.resolve(), args.baseline.resolve())
    base = work / "models/ggml-base.bin"
    binary = work / "build-android/bin/whisper-cli"
    if not base.is_file() or sha(base) != BASE_SHA:
        raise RuntimeError("Original frozen Whisper Base file missing or SHA mismatch")
    if not small.is_file() or sha(small) != SMALL_SHA:
        raise RuntimeError("Whisper small-q5_1 missing or SHA mismatch; run --prepare-small online first")
    if not binary.is_file():
        raise RuntimeError("Existing verified Android Whisper CLI binary missing")
    binary_sha = sha(binary)
    adb = shutil.which("adb")
    if not adb:
        sdk = os.getenv("ANDROID_SDK_ROOT") or os.getenv("ANDROID_HOME")
        adb = str(Path(sdk) / "platform-tools/adb.exe") if sdk else str(Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe")
    if not Path(adb).is_file():
        raise RuntimeError("ADB not found")
    serial, battery, device = verify_environment(adb, args.serial)
    if battery >= 40.0:
        raise RuntimeError(f"Start battery {battery}C is >=40C; cool phone first")
    free_kib = device_free_kib(adb, serial)
    if free_kib < MIN_DEVICE_FREE_KIB:
        raise RuntimeError(f"Device /data lacks 600MiB free for isolated A/B model staging ({free_kib}KiB)")
    print(f"Offline preflight PASS: {device}, battery={battery}C, free={free_kib // 1024} MiB.")
    if args.preflight_only:
        return 0
    ids = sorted(fixtures)
    order = pairs(ids)
    fingerprints = {sid: fixtures[sid]["_sha"] for sid in ids}
    if args.resume:
        session = args.resume.resolve()
        if session.parent != work or not session.is_dir() or not session.name.startswith("small-model-ab-"):
            raise ValueError("Resume requires a small-model-ab-* session in the workdir")
        summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
        keys = ("protocol", "manifest_sha256", "baseline_sha256", "base_sha256",
                "small_sha256", "binary_sha256", "device_serial", "audio_sha256")
        expected = (PROTOCOL, MANIFEST_SHA, BASELINE_SHA, BASE_SHA, SMALL_SHA, binary_sha, serial, fingerprints)
        if tuple(summary.get(k) for k in keys) != expected:
            raise ValueError("Resume session/device/input hash mismatch")
        analyze(summary["runs"], fixtures, archived)
        if len(summary["runs"]) == 40:
            print("Already completed; no additional runs required")
            return 0
    else:
        session = work / ("small-model-ab-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
                          + "-" + uuid.uuid4().hex[:6])
        session.mkdir(parents=True, exist_ok=False)
        summary = {
            "evidence_type": "T10 pinned Base vs quantized Small offline diagnostic NOT CP4",
            "protocol": PROTOCOL, "status": "PREPARED", "stop_reason": None,
            "device": device, "device_serial": serial,
            "manifest_sha256": MANIFEST_SHA, "baseline_sha256": BASELINE_SHA,
            "base_sha256": BASE_SHA, "small_sha256": SMALL_SHA, "binary_sha256": binary_sha,
            "audio_sha256": fingerprints, "offline_verified": True,
            "battery_stop_c": STOP_C, "flags_both_models": FLAGS,
            "preregistered_rule": {
                "all_20_pairs_required": True, "small_max_errors_367_words": 73,
                "small_p95_max_rtf": 2.0, "small_max_sampled_rss_kb": 1599999,
                "second_unseen_set_required": True, "production_promotion": False
            },
            "limitations": "Old known FLEURS samples, incl 5 listener-ambiguous. "
                           "One device and per-model per-sample trial; resource RSS sampled, battery not CPU. "
                           "A quality gain here is only a diagnostic, not CP4.",
            "runs": [], "analysis": {}, "events": [],
        }
        archive_summary(session, summary)
    done = {(row["sample"], row["variant"]) for row in summary["runs"]}
    previous_pairs = sum(all((sid, v) in done for v in VARIANTS) for sid in ids)
    remote = "/data/local/tmp/subloka-t10-small-" + uuid.uuid4().hex[:12]
    problem = None
    start_wall = time.monotonic()
    summary["events"].append({"utc": datetime.now(timezone.utc).isoformat(),
                              "start_rows": len(done), "max_new_pairs": args.max_pairs,
                              "start_battery_c": battery})
    try:
        adb_command(adb, serial, ["shell", "mkdir -p " + remote])
        adb_command(adb, serial, ["push", str(binary), remote + "/whisper-cli"], timeout=100)
        adb_command(adb, serial, ["shell", "chmod 755 " + remote + "/whisper-cli"])
        adb_command(adb, serial, ["push", str(base), remote + "/base.bin"], timeout=200)
        adb_command(adb, serial, ["push", str(small), remote + "/small-q5_1.bin"], timeout=260)
        for sid, variant in order:
            finished_pairs = sum(all((s, v) in done for v in VARIANTS) for s in ids)
            if finished_pairs - previous_pairs >= args.max_pairs:
                break
            if (sid, variant) in done:
                continue
            row = one_run(adb, serial, remote, sid, variant, fixtures[sid],
                          session, len(summary["runs"]) + 1, start_wall)
            summary["runs"].append(row)
            done.add((sid, variant))
            summary["analysis"] = analyze(summary["runs"], fixtures, archived)
            summary["status"] = "PARTIAL_EXPERIMENT_NOT_CP4"
            archive_summary(session, summary)
            print(f"{len(done):02d}/40 {sid}/{variant}: {row['word_errors']}/"
                  f"{row['reference_words']} edits, RTF={row['rtf']}, "
                  f"RSS={row['sampled_peak_rss_kb']}KiB, battery={row['battery_end_c']}C")
        summary["analysis"] = analyze(summary["runs"], fixtures, archived)
        if len(done) == 40:
            summary["status"] = "COMPLETE_DIAGNOSTIC_NOT_CP4"
    except (Exception, KeyboardInterrupt) as error:
        problem = str(error)
        summary["status"] = "ABORTED_RESUMABLE"
        summary["stop_reason"] = problem
        print("ABORTED:", problem, file=sys.stderr)
    finally:
        try:
            adb_command(adb, serial, ["shell", "rm -rf " + remote], check=False, timeout=65)
        except Exception as cleanup_error:
            summary["events"].append({"cleanup_warning": str(cleanup_error)})
        summary["analysis"] = analyze(summary["runs"], fixtures, archived)
        try:
            summary["battery_last_c"] = battery_c(adb, serial)
        except Exception:
            summary["battery_last_c"] = None
        archive_summary(session, summary)
        print("REPORT:", session / "summary.json")
        print("STATUS:", summary["status"], "paired:", summary["analysis"]["paired_samples"], "/20")
        if summary["analysis"].get("paired_samples") == 20:
            print("WER BASE:", summary["analysis"]["paired_base_wer"],
                  "SMALL:", summary["analysis"]["paired_small_wer"],
                  "CANDIDATE:", summary["analysis"]["verdict"])
    return 1 if problem else 0


if __name__ == "__main__":
    raise SystemExit(run())
