"""T10 frozen-set decoding A/B on physical Android: whisper-cli default vs -bs 1.

Diagnostic research, NOT the CP4 gate. Runs all 20 original Indonesian clean
FLEURS WAVs in balanced, paired order. Requires existing pinned Base model,
arm64 CLI and original asr-results.csv; never alters these inputs.
Use --max-pairs 3 for a short pilot and --resume SESSION_DIR to finish.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
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

from t10_asr_error_audit import align_errors
from t10_asr_gain_ab import (
    MODEL_SHA, MANIFEST_SHA, adb_command, battery_c, parse_remote_exit,
    sha, verify_environment,
)

ROOT = Path(__file__).resolve().parent.parent
BASELINE_SHA = "39a9570cd621d81c9607332c34a068fa83c48c4c142f3594d3243144eab08daa"
PROTOCOL_VERSION = "t10-id-clean-beam1-v1"
VARIANTS = ("default", "beam1")
EXPECTED_WORDS = 367
EXPECTED_ERRORS = 105
STOP_BATTERY_C = 43.0
DEFAULT_COMMAND = "-nt -ng -nfa -otxt -of result"
CLI_OPTION = {"default": "", "beam1": " -bs 1"}


def schedule(sample_ids: list[str]) -> list[tuple[str, str]]:
    """Alternate AB/BA within pairs so a monotonically warming phone is less biased."""
    if len(sample_ids) != 20 or len(set(sample_ids)) != 20:
        raise ValueError("Full 20-item clean-ID set required; no cherry-picking.")
    if sample_ids != sorted(sample_ids):
        raise ValueError("Expected deterministic sorted sample order.")
    return [
        (sid, variant)
        for index, sid in enumerate(sample_ids)
        for variant in (VARIANTS if index % 2 == 0 else VARIANTS[::-1])
    ]


def build_remote_command(remote: str, variant: str) -> str:
    if not re.fullmatch(r"/data/local/tmp/subloka-t10-decode-[a-f0-9]{12}", remote):
        raise ValueError("Remote directory outside isolated benchmark namespace.")
    if variant not in VARIANTS:
        raise ValueError("Unrecognized decoding variant.")
    flags = DEFAULT_COMMAND + CLI_OPTION[variant]
    # Android /system/bin/sh writes a real Whisper exit code and a scoped process
    # PID for safe targeted thermal cancellation, independent of host ADB exit.
    return (
        f"cd {remote} || exit 98; "
        f"./whisper-cli -m model.bin -f input.wav -l id {flags} & "
        "pid=$!; echo $pid > result.pid; wait $pid; rc=$?; "
        "echo $rc > result.exit; exit $rc"
    )


def load_frozen_inputs(manifest: Path, baseline_csv: Path) -> tuple[dict, dict]:
    if sha(manifest) != MANIFEST_SHA:
        raise ValueError("Frozen FLEURS manifest SHA-256 mismatch.")
    if sha(baseline_csv) != BASELINE_SHA:
        raise ValueError("Frozen original ASR baseline CSV SHA-256 mismatch.")
    source = json.loads(manifest.read_text(encoding="utf-8-sig"))
    clean_list = [s for s in source["samples"] if s["language"] == "id" and s["category"] == "clean"]
    if len(clean_list) != 20:
        raise ValueError("Expected exactly 20 Indonesian clean FLEURS samples.")
    fixtures = {}
    for fixture in clean_list:
        sample_id = fixture["id"]
        if sample_id in fixtures:
            raise ValueError("Duplicate fixture ID.")
        path = (manifest.parent / fixture["audio"]).resolve()
        if not path.is_file():
            raise FileNotFoundError("Missing original WAV: " + str(path))
        with wave.open(str(path), "rb") as reader:
            if (reader.getnchannels(), reader.getsampwidth(), reader.getframerate(), reader.getcomptype()) != (1, 2, 16000, "NONE"):
                raise ValueError("Original WAV has incompatible format: " + sample_id)
        if float(fixture["durationSeconds"]) <= 0 or not fixture["reference"].strip():
            raise ValueError("Invalid original fixture: " + sample_id)
        fixtures[sample_id] = {**fixture, "_file": str(path), "_sha": sha(path)}
    if sorted(fixtures) != [f"id-clean-{index:02d}" for index in range(1, 21)]:
        raise ValueError("Unexpected or missing clean sample IDs.")

    with baseline_csv.open(newline="", encoding="utf-8-sig") as handle:
        rows = list(csv.DictReader(handle))
    archived = {r["sample"]: r for r in rows
                if r["model"] == "base" and r["language"] == "id" and r["category"] == "clean"}
    if len(archived) != 20 or set(archived) != set(fixtures):
        raise ValueError("Baseline CSV lacks 20 unique Base Indonesian clean rows.")
    errors = words = 0
    for sid, original in archived.items():
        f = fixtures[sid]
        if not original["hypothesis"].strip():
            raise ValueError("Empty archived baseline hypothesis.")
        aligned = align_errors(f["reference"], original["hypothesis"])
        errors += aligned["errors"]
        words += aligned["reference_words"]
    if (errors, words) != (EXPECTED_ERRORS, EXPECTED_WORDS):
        raise ValueError("Archived baseline no longer equals frozen 105/367 edits.")
    return fixtures, archived


def aggregate(runs: list[dict], fixtures: dict, archived: dict) -> dict:
    paired: dict[str, dict] = {}
    seen = set()
    for row in runs:
        sid, v = row["sample"], row["variant"]
        if (sid, v) in seen or sid not in fixtures or v not in VARIANTS:
            raise ValueError("Duplicate or unexpected run in evidence.")
        seen.add((sid, v))
        if row["remote_whisper_exit"] != 0 or row["host_adb_exit"] != 0:
            raise ValueError("Cannot aggregate a failed CLI or ADB run.")
        validated = align_errors(fixtures[sid]["reference"], row["hypothesis"])
        if (row["word_errors"], row["reference_words"]) != (
            validated["errors"], validated["reference_words"]
        ):
            raise ValueError("Recorded run errors/reference words disagree with transcripts.")
        paired.setdefault(sid, {})[v] = row
    complete = {sid: pair for sid, pair in paired.items() if set(pair) == set(VARIANTS)}
    metrics = {"paired_samples": len(complete), "runs_collected": len(runs),
               "original_archived_baseline_wer": EXPECTED_ERRORS / EXPECTED_WORDS,
               "original_archived_baseline_errors": EXPECTED_ERRORS,
               "original_archived_reference_words": EXPECTED_WORDS,
               "official_cp4_status": "BLOCKED", "comparison": []}
    if complete:
        ref_words = sum(align_errors(fixtures[sid]["reference"], archived[sid]["hypothesis"])["reference_words"]
                        for sid in complete)
        control_errors = sum(int(complete[sid]["default"]["word_errors"]) for sid in complete)
        candidate_errors = sum(int(complete[sid]["beam1"]["word_errors"]) for sid in complete)
        metrics.update({
            "paired_reference_words": ref_words,
            "control_errors": control_errors, "beam1_errors": candidate_errors,
            "control_micro_wer": control_errors / ref_words,
            "beam1_micro_wer": candidate_errors / ref_words,
            "beam1_minus_control_micro_wer": (candidate_errors - control_errors) / ref_words,
            "paired_hypotheses_changed": sum(
                complete[sid]["default"]["hypothesis"] != complete[sid]["beam1"]["hypothesis"]
                for sid in complete
            ),
            "control_matches_archived_hypothesis": sum(
                complete[sid]["default"]["hypothesis"] == archived[sid]["hypothesis"]
                for sid in complete
            ),
        })
        for sid in sorted(complete):
            c, b = complete[sid]["default"], complete[sid]["beam1"]
            metrics["comparison"].append({
                "sample": sid, "control_errors": c["word_errors"],
                "beam1_errors": b["word_errors"],
                "delta_word_errors": b["word_errors"] - c["word_errors"],
                "hypotheses_identical": c["hypothesis"] == b["hypothesis"],
                "control_equals_archived_text": c["hypothesis"] == archived[sid]["hypothesis"],
                "control_rtf": c["rtf"], "beam1_rtf": b["rtf"],
            })
    return metrics


def write_evidence(session: Path, summary: dict) -> None:
    (session / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    if summary["runs"]:
        path = session / "runs.csv"
        columns = ["sample", "variant", "word_errors", "reference_words",
                   "wer_diagnostic", "duration_s", "elapsed_s", "rtf",
                   "battery_start_c", "battery_end_c", "remote_whisper_exit",
                   "host_adb_exit", "hypothesis"]
        with path.open("w", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(summary["runs"])


def stop_own_cli(adb: str, serial: str, remote: str) -> None:
    pid = adb_command(adb, serial, ["shell", "cat " + remote + "/result.pid"], check=False, timeout=8)
    candidate = pid.stdout.strip()
    if pid.returncode == 0 and re.fullmatch(r"[1-9]\d{0,9}", candidate):
        adb_command(adb, serial, ["shell", "kill -TERM " + candidate], check=False, timeout=8)


def one_inference(adb: str, serial: str, remote: str, sid: str, variant: str,
                  wav: Path, fixture: dict, session: Path, run_index: int) -> dict:
    start_battery = battery_c(adb, serial)
    if start_battery >= STOP_BATTERY_C:
        raise RuntimeError(f"THERMAL_STOP: battery={start_battery:.1f}C")
    adb_command(adb, serial, ["push", str(wav), remote + "/input.wav"], timeout=75)
    adb_command(adb, serial, ["shell", f"rm -f {remote}/result.txt {remote}/result.exit {remote}/result.pid"])
    command = build_remote_command(remote, variant)
    errlog = session / f"run-{run_index:02d}-{sid}-{variant}-stderr.log"
    outlog = session / f"run-{run_index:02d}-{sid}-{variant}-stdout.log"
    clock = time.monotonic()
    with outlog.open("wb") as output, errlog.open("wb") as errors:
        proc = subprocess.Popen([adb, "-s", serial, "shell", command], stdout=output, stderr=errors)
        try:
            while proc.poll() is None:
                if time.monotonic() - clock > 120:
                    raise RuntimeError(f"TIMEOUT 120s: {sid}/{variant}")
                temp = battery_c(adb, serial)
                if temp >= STOP_BATTERY_C:
                    raise RuntimeError(f"THERMAL_STOP at {temp:.1f}C: {sid}/{variant}")
                time.sleep(2)
            proc.wait(timeout=5)
        except BaseException:
            try:
                stop_own_cli(adb, serial, remote)
            finally:
                try:
                    proc.wait(timeout=6)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait(timeout=5)
            raise
    elapsed = time.monotonic() - clock
    marker = adb_command(adb, serial, ["shell", f"cat {remote}/result.exit"], check=False)
    if marker.returncode != 0:
        raise RuntimeError(f"Missing remote exit marker for {sid}/{variant}")
    remote_code = parse_remote_exit(marker.stdout)
    transcript = adb_command(adb, serial, ["shell", f"cat {remote}/result.txt"], check=False)
    if remote_code != 0 or proc.returncode != 0 or transcript.returncode != 0 or not transcript.stdout.strip():
        tail = errlog.read_text(encoding="utf-8", errors="replace")[-600:]
        raise RuntimeError(f"Whisper failed {sid}/{variant}; Android={remote_code}, ADB={proc.returncode}; {tail}")
    end_battery = battery_c(adb, serial)
    if end_battery >= STOP_BATTERY_C:
        raise RuntimeError(f"THERMAL_STOP after {sid}/{variant} at {end_battery:.1f}C")
    hypothesis = transcript.stdout.strip()
    edit = align_errors(fixture["reference"], hypothesis)
    return {
        "sample": sid, "variant": variant, "word_errors": edit["errors"],
        "reference_words": edit["reference_words"],
        "wer_diagnostic": round(edit["errors"] / edit["reference_words"], 4),
        "duration_s": fixture["durationSeconds"],
        "elapsed_s": round(elapsed, 3),
        "rtf": round(elapsed / float(fixture["durationSeconds"]), 4),
        "battery_start_c": start_battery, "battery_end_c": end_battery,
        "remote_whisper_exit": remote_code, "host_adb_exit": proc.returncode,
        "hypothesis": hypothesis,
    }


def run() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--manifest", type=Path, default=ROOT / "t10-dataset.json")
    p.add_argument("--baseline", type=Path, default=ROOT / ".t10-benchmark/asr-results.csv")
    p.add_argument("--workdir", type=Path, default=ROOT / ".t10-benchmark")
    p.add_argument("--serial", default="")
    p.add_argument("--max-pairs", type=int, default=None, help="Pairs per invocation; try 3 first")
    p.add_argument("--resume", type=Path, default=None, help="Existing decode-ab-* session folder")
    p.add_argument("--preflight-only", action="store_true")
    args = p.parse_args()
    if args.max_pairs is not None and not 1 <= args.max_pairs <= 20:
        p.error("--max-pairs must be between 1 and 20")
    work = args.workdir.resolve()
    manifest, baseline = args.manifest.resolve(), args.baseline.resolve()
    fixtures, archived = load_frozen_inputs(manifest, baseline)
    model = work / "models/ggml-base.bin"
    binary = work / "build-android/bin/whisper-cli"
    if not model.is_file() or sha(model) != MODEL_SHA or not binary.is_file():
        raise RuntimeError("Pinned Base model / cached arm64 whisper-cli missing or invalid.")
    binary_sha = sha(binary)
    adb = shutil.which("adb")
    if not adb:
        sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
        adb = str(Path(sdk) / "platform-tools/adb.exe") if sdk else str(Path.home() / "AppData/Local/Android/Sdk/platform-tools/adb.exe")
    if not Path(adb).is_file():
        raise RuntimeError("ADB not found (install Platform-Tools or set ANDROID_SDK_ROOT).")
    serial, start_temp, device = verify_environment(adb, args.serial)
    print(f"PREFLIGHT PASS: {device} ({serial}) offline, Base SHA verified, 20 original clean WAV, battery={start_temp:.1f}C.")
    if args.preflight_only:
        return 0
    ids = sorted(fixtures)
    run_order = schedule(ids)
    fingerprints = {sid: fixtures[sid]["_sha"] for sid in ids}
    if args.resume:
        session = args.resume.resolve()
        if session.parent != work or not session.name.startswith("decode-ab-"):
            raise ValueError("Resume folder must be an existing decode-ab-* folder in workdir.")
        summary = json.loads((session / "summary.json").read_text(encoding="utf-8"))
        if (summary.get("protocol"), summary.get("manifest_sha256"),
            summary.get("baseline_sha256"), summary.get("model_sha256"),
            summary.get("binary_sha256"), summary.get("device_serial"),
            summary.get("audio_sha256")) != (
                PROTOCOL_VERSION, MANIFEST_SHA, BASELINE_SHA, MODEL_SHA, binary_sha,
                serial, fingerprints):
            raise ValueError("Resume evidence/input/device fingerprint mismatch; refusing to mix runs.")
        aggregate(summary["runs"], fixtures, archived)  # validate stored evidence
    else:
        session = work / ("decode-ab-" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:6])
        session.mkdir(parents=True, exist_ok=False)
        summary = {
            "evidence_type": "T10 full-set paired decoding diagnostic; NOT the official CP4 gate",
            "protocol": PROTOCOL_VERSION, "status": "PREPARED", "stop_reason": None,
            "model": "base", "device_model": device, "device_serial": serial,
            "manifest_sha256": MANIFEST_SHA, "baseline_sha256": BASELINE_SHA,
            "model_sha256": MODEL_SHA, "binary_sha256": binary_sha,
            "audio_sha256": fingerprints, "offline_verified": True,
            "battery_start_c": start_temp, "battery_stop_c": STOP_BATTERY_C,
            "baseline_flag_set": DEFAULT_COMMAND,
            "candidate_flag_set": DEFAULT_COMMAND + CLI_OPTION["beam1"],
            "official_CP4_base_id_clean_wer": EXPECTED_ERRORS / EXPECTED_WORDS,
            "limitations": "Paired 20 original FLEURS clean ID audio. Post-hoc 5 listener-ambiguous items retained. One cold-start inference per condition, order balanced AB/BA; no significance claim. Do not overwrite CP4 105/367 baseline.",
            "runs": [], "analysis": {}, "events": [],
        }
        write_evidence(session, summary)
    remote = "/data/local/tmp/subloka-t10-decode-" + uuid.uuid4().hex[:12]
    completed_at_start = len({x["sample"] for x in summary["runs"] if
        {"default", "beam1"}.issubset({y["variant"] for y in summary["runs"] if y["sample"] == x["sample"]})})
    done = {(x["sample"], x["variant"]) for x in summary["runs"]}
    event = {"time_utc": datetime.now(timezone.utc).isoformat(), "start_rows": len(done),
             "max_pairs": args.max_pairs, "battery_start_c": start_temp}
    summary["events"].append(event)
    problem = None
    try:
        adb_command(adb, serial, ["shell", "mkdir -p " + remote])
        adb_command(adb, serial, ["push", str(binary), remote + "/whisper-cli"], timeout=90)
        adb_command(adb, serial, ["shell", "chmod 755 " + remote + "/whisper-cli"])
        help_result = adb_command(adb, serial, ["shell", f"cd {remote} && ./whisper-cli -h"],
                                  check=False, timeout=35)
        help_text = help_result.stdout + "\n" + help_result.stderr
        if not re.search(r"(?m)(?:^|\s)-bs(?:\s+N|,)", help_text):
            raise RuntimeError("Cached whisper-cli does not advertise -bs (beam-size); stop before experiment.")
        adb_command(adb, serial, ["push", str(model), remote + "/model.bin"], timeout=150)
        # All 20 pairs are processed, with an optional per-session limit for thermal staging.
        for sid, variant in run_order:
            completed = sum(
                1 for item in ids if (item, "default") in done and (item, "beam1") in done
            )
            if args.max_pairs is not None and completed - completed_at_start >= args.max_pairs:
                break
            if (sid, variant) in done:
                continue
            result = one_inference(adb, serial, remote, sid, variant,
                                   Path(fixtures[sid]["_file"]), fixtures[sid],
                                   session, len(summary["runs"]) + 1)
            summary["runs"].append(result)
            done.add((sid, variant))
            summary["analysis"] = aggregate(summary["runs"], fixtures, archived)
            summary["status"] = "IN_PROGRESS"
            write_evidence(session, summary)
            print(f"{len(done):02d}/40  {sid}/{variant}: "
                  f"{result['word_errors']}/{result['reference_words']} edits, "
                  f"RTF={result['rtf']:.3f}, battery={result['battery_end_c']:.1f}C.")
        summary["analysis"] = aggregate(summary["runs"], fixtures, archived)
        summary["status"] = (
            "COMPLETE_EXPERIMENT_NOT_CP4" if len(done) == 40
            else "PARTIAL_EXPERIMENT_NOT_CP4"
        )
    except (Exception, KeyboardInterrupt) as exc:
        problem = str(exc)
        summary["status"] = "ABORTED_RESUMABLE"
        summary["stop_reason"] = problem
        print("ABORTED:", problem, file=sys.stderr)
    finally:
        try:
            adb_command(adb, serial, ["shell", "rm -rf " + remote], check=False, timeout=30)
        except Exception:
            pass
        try:
            summary["battery_last_c"] = battery_c(adb, serial)
        except Exception:
            summary["battery_last_c"] = None
        summary["analysis"] = aggregate(summary["runs"], fixtures, archived)
        write_evidence(session, summary)
        print("T10 decoding diagnostic:", session / "summary.json")
        print("STATUS:", summary["status"], "| paired:", summary["analysis"]["paired_samples"], "/20")
    return 1 if problem else 0


if __name__ == "__main__":
    raise SystemExit(run())
