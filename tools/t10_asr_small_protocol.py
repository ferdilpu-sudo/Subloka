"""Frozen model fingerprints, safe model preparation and paired ASR scoring.

All functions are offline after initial candidate-model preparation. Existing
T10 source/result fixtures are never modified; quality decisions stay diagnostic.
"""
from __future__ import annotations

import argparse
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
from urllib.request import urlopen

from t10_asr_decode_ab import load_frozen_inputs, BASELINE_SHA
from t10_asr_error_audit import align_errors
from t10_asr_gain_ab import (
    MODEL_SHA as BASE_SHA, MANIFEST_SHA, adb_command, battery_c,
    parse_remote_exit, sha, verify_environment,
)

ROOT = Path(__file__).resolve().parent.parent
REVISION = "80da2d8bfee42b0e836fc3a9890373e5defc00a6"
SMALL_SHA = "ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb"
SMALL_URL = ("https://huggingface.co/ggerganov/whisper.cpp/resolve/"
             + REVISION + "/ggml-small-q5_1.bin")
VARIANTS = ("base", "small_q5_1")
SHA_BY_VARIANT = {"base": BASE_SHA, "small_q5_1": SMALL_SHA}
MODEL_REMOTE = {"base": "base.bin", "small_q5_1": "small-q5_1.bin"}
FLAGS = "-nt -ng -nfa -otxt -of result"
PROTOCOL = "t10-id-clean-small-q5-model-ab-v1"
STOP_C = 43.0
MAX_WALL_SECONDS = 900
PER_RUN_SECONDS = 240
MIN_DEVICE_FREE_KIB = 600 * 1024
COLUMNS = (
    "sample", "variant", "model_sha256", "word_errors",
    "reference_words", "wer_diagnostic", "duration_s", "elapsed_s", "rtf",
    "battery_start_c", "battery_end_c", "sampled_peak_rss_kb",
    "remote_whisper_exit", "host_adb_exit", "hypothesis",
)


def pairs(ids: list[str]) -> list[tuple[str, str]]:
    if ids != [f"id-clean-{i:02d}" for i in range(1, 21)]:
        raise ValueError("Requires all 20 clean-ID sample IDs, no cherry-picking")
    return [
        (sid, variant) for index, sid in enumerate(ids)
        for variant in (VARIANTS if index % 2 == 0 else VARIANTS[::-1])
    ]


def command(remote: str, variant: str) -> str:
    if not re.fullmatch(r"/data/local/tmp/subloka-t10-small-[0-9a-f]{12}", remote):
        raise ValueError("Unsafe scoped Android remote directory")
    if variant not in VARIANTS:
        raise ValueError("Unexpected ASR model variant")
    model = MODEL_REMOTE[variant]
    return (
        f"cd {remote} || exit 98; "
        f"./whisper-cli -m {model} -f input.wav -l id {FLAGS} & "
        "pid=$!; echo $pid > result.pid; wait $pid; rc=$?; "
        "echo $rc > result.exit; exit $rc"
    )


def prepare_small(path: Path) -> None:
    if path.exists():
        if sha(path) != SMALL_SHA:
            raise ValueError("Existing small model SHA256 mismatch; delete ONLY the corrupt candidate file manually")
        print("Already ready: verified small-q5_1 model", path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name(path.name + "." + uuid.uuid4().hex[:12] + ".part")
    digest = hashlib.sha256()
    count = 0
    try:
        with urlopen(SMALL_URL, timeout=75) as response, tmp.open("xb") as writer:
            if response.geturl().split(":", 1)[0].lower() != "https":
                raise ValueError("Download redirected outside HTTPS")
            while True:
                block = response.read(1024 * 1024)
                if not block:
                    break
                count += len(block)
                if count > 260_000_000:
                    raise ValueError("Candidate model download exceeded 260MB safety limit")
                writer.write(block)
                digest.update(block)
        if count < 100_000_000 or digest.hexdigest() != SMALL_SHA:
            raise ValueError("Small model file size/SHA256 differs from pinned official artifact")
        if path.exists():
            raise FileExistsError("Model destination appeared during download; refusing overwrite")
        tmp.replace(path)
        print(f"Verified small-q5_1 model ({count} bytes): {path}")
    finally:
        if tmp.exists():
            tmp.unlink()


def archive_summary(session: Path, report: dict) -> None:
    target = session / "summary.json"
    pending = session / "summary.pending"
    pending.write_text(json.dumps(report, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    pending.replace(target)
    with (session / "runs.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader()
        for row in report["runs"]:
            writer.writerow({field: row[field] for field in COLUMNS})


def analyze(runs: list[dict], fixtures: dict, archived: dict) -> dict:
    seen = set()
    by_id: dict[str, dict] = {}
    for row in runs:
        sid, variant = row["sample"], row["variant"]
        if sid not in fixtures or variant not in VARIANTS or (sid, variant) in seen:
            raise ValueError("Unexpected or duplicate sample/variant")
        seen.add((sid, variant))
        if row["model_sha256"] != SHA_BY_VARIANT[variant]:
            raise ValueError("Changed candidate/control model fingerprint")
        if row["remote_whisper_exit"] != 0 or row["host_adb_exit"] != 0:
            raise ValueError("Failed inference may not be graded as success")
        aligned = align_errors(fixtures[sid]["reference"], row["hypothesis"])
        if (row["word_errors"], row["reference_words"]) != (
            aligned["errors"], aligned["reference_words"]
        ):
            raise ValueError("Word-error count does not match unchanged fixture")
        by_id.setdefault(sid, {})[variant] = row

    paired = {sid: rows for sid, rows in by_id.items() if set(rows) == set(VARIANTS)}
    result = {
        "status": "DIAGNOSTIC_ONLY_NOT_CP4",
        "paired_samples": len(paired), "runs": len(runs),
        "baseline_original_frozen_errors": 105,
        "baseline_original_reference_words": 367,
        "baseline_original_wer": 105 / 367,
        "cp4": "BLOCKED", "comparison": [],
    }
    if paired:
        words = sum(align_errors(fixtures[sid]["reference"], archived[sid]["hypothesis"])["reference_words"]
                    for sid in paired)
        base_errors = sum(paired[sid]["base"]["word_errors"] for sid in paired)
        small_errors = sum(paired[sid]["small_q5_1"]["word_errors"] for sid in paired)
        for sid in sorted(paired):
            b, s = paired[sid]["base"], paired[sid]["small_q5_1"]
            result["comparison"].append({
                "sample": sid, "base_errors": b["word_errors"],
                "small_errors": s["word_errors"],
                "small_minus_base_edits": s["word_errors"] - b["word_errors"],
                "base_rtf": b["rtf"], "small_rtf": s["rtf"],
                "base_rss_kb_sampled": b["sampled_peak_rss_kb"],
                "small_rss_kb_sampled": s["sampled_peak_rss_kb"],
            })
        result.update({
            "paired_reference_words": words, "paired_base_errors": base_errors,
            "paired_small_errors": small_errors,
            "paired_base_wer": base_errors / words,
            "paired_small_wer": small_errors / words,
            "small_minus_base_errors": small_errors - base_errors,
        })
    if len(paired) == 20:
        small_rows = [paired[sid]["small_q5_1"] for sid in sorted(paired)]
        small_rtfs = sorted(float(row["rtf"]) for row in small_rows)
        rss_values = [row["sampled_peak_rss_kb"] for row in small_rows]
        all_rss_sampled = all(isinstance(v, int) and v > 0 for v in rss_values)
        result["small_p95_rtf"] = small_rtfs[math.ceil(len(small_rtfs) * .95) - 1]
        result["small_peak_sampled_rss_kb"] = max(rss_values) if all_rss_sampled else None
        meets = (small_errors <= 73 and result["small_p95_rtf"] <= 2.0
                 and all_rss_sampled and result["small_peak_sampled_rss_kb"] < 1_600_000)
        result["preregistered_diagnostic_criteria_met"] = meets
        result["verdict"] = (
            "PROMISING_REQUIRES_TRULY_UNSEEN_HOLDOUT_AND_APP_ENGINE_INTEGRATION_TESTS"
            if meets else "NOT_ELIGIBLE_FOR_PROMOTION_FROM_THIS_EXPERIMENT"
        )
    else:
        result["verdict"] = "PARTIAL_DATA_NO_QUALITY_VERDICT"
    return result


