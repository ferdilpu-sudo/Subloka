#!/usr/bin/env python3
"""T10 compact Indonesian ASR model preregistration, OFFLINE and read-only.

Two research candidates are publisher-provided GGML q8_0 models. No model
downloads, ADB, inference or benchmark metric promotion are implemented.
The SHA256 is from the upstream Hugging Face *file blob* details; revision
main is mutable, so only a SHA256-matching local byte-for-byte file qualifies.

Usage:
  python tools/t10_asr_id_compact_protocol.py list
  python tools/t10_asr_id_compact_protocol.py verify --model maleo_base_id_q8_0 --file <local-file>
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import sys

from t10_asr_next_feasibility import read_frozen_pins

# Upstream source model cards: https://huggingface.co/maleo-ai/whisper-{tiny,base}-id
# Verified FILE blob metadata (public SHA256 visible on each linked page).
CANDIDATES = {
    "maleo_base_id_q8_0": {
        "repo": "maleo-ai/whisper-base-id",
        "filename": "ggml-base-id-q8_0.bin",
        "sha256": "2ac0dc902f477389be18d8b6f6fbe97695197c12ab1392b2f4bea23732c2cfe8",
        "source_page": "https://huggingface.co/maleo-ai/whisper-base-id/blob/main/ggml-base-id-q8_0.bin",
        "display_size_mb_decimal": 81.8,
        "claimed_license": "apache-2.0",
        "claimed_fleurs_id_wer_percent": 15.0,
        "priority": 1,
        "status": "RESEARCH_ONLY_NO_DOWNLOADED_ARTIFACT_CONFIRMED",
    },
    "maleo_tiny_id_q8_0": {
        "repo": "maleo-ai/whisper-tiny-id",
        "filename": "ggml-tiny-id-q8_0.bin",
        "sha256": "423455afe438ff3b0d1f23613a223d052f34a2482a8dd8ef6433f75ccbf33a17",
        "source_page": "https://huggingface.co/maleo-ai/whisper-tiny-id/blob/main/ggml-tiny-id-q8_0.bin",
        "display_size_mb_decimal": 43.5,
        "claimed_license": "apache-2.0",
        "claimed_fleurs_id_wer_percent": 19.1,
        "priority": 2,
        "status": "RESEARCH_ONLY_NO_DOWNLOADED_ARTIFACT_CONFIRMED",
    },
}
MODEL_KEYS = tuple(CANDIDATES)
MAX_FILE_BYTES = 150_000_000

LIMITATIONS = [
    "Author-reported FLEURS WER is NOT the SUBLOKA 20-case WER and not a device benchmark.",
    "Upstream fine-tuning claims FLEURS ID in training; train/evaluation sample overlap "
    "and holdout independence NOT independently established.",
    "All original frozen SUBLOKA FLEURS dev samples and scoring remain unchanged.",
    "Before model selection for CP4: verify disjoint train/test provenance, obtain "
    "new independently sourced consented Indonesian speech holdout with human "
    "checked text, preregister pass/fail and paired runtime metrics.",
    "Publisher's reported Orange Pi speed does not imply Sony SO-03L latency or RSS.",
    "Model-card Apache-2.0 claim is public metadata, not a legal audit of all training data.",
    "No Android inference, new audio/video evaluation, production promotion or CP4 PASS.",
]


def catalog_report() -> dict:
    pins = read_frozen_pins()
    candidates = []
    for key in MODEL_KEYS:
        model = CANDIDATES[key]
        if not re.fullmatch(r"[0-9a-f]{64}", model["sha256"]):
            raise ValueError("Missing upstream artifact SHA256 pin")
        if not model["source_page"].startswith("https://huggingface.co/"):
            raise ValueError("Unexpected upstream source")
        record = {"id": key, **model}
        record["exact_local_model_verified"] = False
        record["safe_to_download_automatically"] = False
        record["safe_to_run_on_sony"] = False
        record["independent_holdout_ready"] = False
        record["eligible_to_replace_frozen_baseline"] = False
        candidates.append(record)
    return {
        "schema_version": 1,
        "type": "T10_ID_COMPACT_GGML_RESEARCH_ONLY_NOT_BENCHMARK",
        "status": "PINNED_SOURCE_SHA_ONLY_NO_LOCAL_ARTIFACT",
        "model_priority_order": list(MODEL_KEYS),
        "models": candidates,
        "original_evidence_sha256": pins,
        "original_id_clean": "105 edits / 367 words (28.61%); CP4 target <=20%",
        "sony_storage_snapshot_rounded_mib": 1732,
        "independent_human_translation_signoff": "PENDING",
        "T10": "ACTIVE",
        "CP4": "BLOCKED",
        "T11": "TODO",
        "limitations": LIMITATIONS,
    }


def verify_local(model_id: str, path: Path) -> dict:
    """Verify only bytes of an already-local model, never fetch or modify it."""
    if model_id not in CANDIDATES:
        raise ValueError("Unknown preregistered model ID")
    model = CANDIDATES[model_id]
    if not path.is_file() or path.is_symlink():
        raise ValueError("Local model must exist as an ordinary file")
    expected_size = float(model["display_size_mb_decimal"]) * 1_000_000
    size = path.stat().st_size
    if not 0 < size <= MAX_FILE_BYTES or abs(size - expected_size) > 2_000_000:
        raise ValueError("Local artifact bytes inconsistent with upstream published size")
    digest = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            digest.update(chunk)
    if digest.hexdigest() != model["sha256"]:
        raise ValueError("Local artifact SHA256 mismatch; do NOT use this model")
    return {
        "model_id": model_id,
        "local_file_sha256": digest.hexdigest(),
        "file_bytes": size,
        "local_sha256_verified": True,
        "download_or_device_inference_performed": False,
        "sony_accuracy_and_runtime_proven": False,
        "independent_holdout_review_complete": False,
        "CP4": "BLOCKED",
        "next": "Protocol and heldout data review before host-only benchmark, then Sony ADB",
    }


def write_once(path: Path, report: dict) -> None:
    """Create local JSON evidence without overwriting existing files."""
    if path.exists():
        raise FileExistsError("Report already exists; never overwrite evidence")
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(report, indent=2, ensure_ascii=False) + "\n"
    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(payload)
    except FileExistsError:
        raise FileExistsError("Report already exists; never overwrite evidence") from None


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    show = sub.add_parser("list", help="List SHA-pinned research candidates, no network")
    show.add_argument("--json", type=Path)
    verify = sub.add_parser("verify", help="Read/check already-local model bytes only")
    verify.add_argument("--model", choices=MODEL_KEYS, required=True)
    verify.add_argument("--file", type=Path, required=True)
    verify.add_argument("--json", type=Path)
    args = p.parse_args()
    try:
        if args.command == "list":
            report = catalog_report()
        else:
            # Also validate frozen SUBLOKA evidence before even accepting a
            # local model file as bytes-verified (never as quality-verified).
            catalog_report()
            report = verify_local(args.model, args.file)
        if args.json:
            write_once(args.json, report)
        if args.command == "list":
            for x in report["models"]:
                print(x["id"], x["display_size_mb_decimal"], "MB",
                      "SHA256", x["sha256"], "LICENSE CLAIM", x["claimed_license"])
        else:
            print("LOCAL ARTIFACT SHA256 PASS:", report["model_id"],
                  report["local_file_sha256"])
        print("NO DOWNLOAD | NO ADB | NO INFERENCE | FLEURS HOLDOUT INDEPENDENCE UNVERIFIED")
        print("T10 ACTIVE | CP4 BLOCKED | T11 TODO")
        return 0
    except (OSError, ValueError, KeyError, TypeError, json.JSONDecodeError) as exc:
        print("ERROR: Compact ID ASR protocol:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
