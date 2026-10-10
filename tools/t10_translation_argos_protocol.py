"""T10 Argos ID->EN offline candidate: pinned artifact and paired QA rules.

This module NEVER downloads or runs translation. It validates the already
user-reviewed whole-vs-linewise source and scores newly reviewed output without
changing the frozen ML Kit or CP4 benchmark. The first 10 IDs are selected by
fixture order before candidate inference, not by observed candidate quality.
"""
from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
import stat
import zipfile

from t10_translation_strategy_ab_review import (
    REVIEW_COLUMNS, STATUS, fixture_data, read_csv,
)

ROOT = Path(__file__).resolve().parent.parent
MODEL_REVISION = "a69e5d5f51945c24ad8653c3255b87320af21a48"
MODEL_FILENAME = "translate-id_en-1_9.argosmodel"
MODEL_SHA256 = "b494f6109dd7ceae32cb44cc721a14039abce938dc773a70087e73301ef4fed4"
MODEL_URL = (
    "https://huggingface.co/TiberiuCristianLeon/Argostranslate/resolve/"
    + MODEL_REVISION + "/" + MODEL_FILENAME
)
MODEL_BYTES_MIN = 60_000_000
MODEL_BYTES_MAX = 90_000_000
# This is the exact file that was uploaded and reviewed; re-exports with changed
# bytes must NOT silently inherit previous human/AI labels.
REVIEW_SHA256 = "516ca5d8967aefa7046db65e53fb1788ef7267bb48f7f34ada48eb72d20018a9"
PILOT_IDS = tuple(f"id-ab-{i:02d}" for i in range(1, 11))
DIAGNOSTIC = "T10_ARGOS_ID_EN_HOST_ONLY_NOT_ANDROID_NOT_CP4"
OUTPUT_COLUMNS = (
    "sample", "source_text", "risk_tag", "mlkit_whole_translation",
    "mlkit_whole_status", "mlkit_whole_notes", "argos_translation",
    "argos_latency_ms", "error", "candidate_review_status", "candidate_notes",
)


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def strict_review(review: Path) -> list[dict[str, str]]:
    if sha256(review) != REVIEW_SHA256:
        raise ValueError(
            "Reviewed ML Kit CSV SHA256 differs from frozen 120-row source; "
            "do not reuse old reviewer labels on modified outputs"
        )
    source = fixture_data()
    rows = read_csv(review, REVIEW_COLUMNS)
    if len(rows) != 120:
        raise ValueError("Exactly 120 original strategy A/B review rows are required")
    accepted = {"id": 0, "en": 0}
    for i, fixture in enumerate(source):
        order = ("whole", "linewise") if i % 2 == 0 else ("linewise", "whole")
        for j, strategy in enumerate(order):
            row = rows[2 * i + j]
            if (row["sample"], row["source_language"], row["target_language"],
                row["source_text"], row["strategy"]) != (
                fixture["id"], fixture["language"],
                "en" if fixture["language"] == "id" else "id",
                fixture["text"], strategy
            ):
                raise ValueError("Missing/changed source or strategy order")
            if (not row["translation"].strip() or row["error"].strip()
                or row["status"] not in STATUS):
                raise ValueError("Invalid frozen translation/review: " + fixture["id"])
            if row["status"] != "ACCEPT" and not row["notes"].strip():
                raise ValueError("Frozen rejection reason missing")
            if strategy == "whole" and row["status"] == "ACCEPT":
                accepted[fixture["language"]] += 1
    if accepted != {"id": 21, "en": 22}:
        raise ValueError("Expected unchanged reviewed paragraph baseline 21/30 ID and 22/30 EN")
    whole = {r["sample"]: r for r in rows if r["strategy"] == "whole"}
    return [
        {**f, "mlkit": whole[f["id"]]}
        for f in source[:30]
    ]


def validate_argos_archive(path: Path) -> None:
    if sha256(path) != MODEL_SHA256:
        raise ValueError("Argos candidate SHA256 mismatch; do not install/use")
    if not MODEL_BYTES_MIN <= path.stat().st_size <= MODEL_BYTES_MAX:
        raise ValueError("Unexpected Argos package length")
    with zipfile.ZipFile(path, "r") as zf:
        entries = zf.infolist()
        if not entries or len(entries) > 500:
            raise ValueError("Unexpected Argos ZIP entries")
        total = 0
        for entry in entries:
            normalized = entry.filename.replace("\\", "/")
            parts = normalized.split("/")
            if (normalized.startswith("/") or
                any(p in ("..", "") for p in parts[:-1]) or
                ":" in normalized or
                stat.S_IFMT(entry.external_attr >> 16) == stat.S_IFLNK):
                raise ValueError("Unsafe Argos ZIP member path/type")
            total += entry.file_size
            if total > 500_000_000:
                raise ValueError("Argos model ZIP expands beyond 500MB")
        if not any(e.filename.endswith("/metadata.json") or
                   e.filename == "metadata.json" for e in entries):
            raise ValueError("Argos model ZIP missing metadata.json")


def pilot_rows(reviewed: list[dict[str, str | dict]], translated: dict) -> list[dict]:
    if tuple(translated) != PILOT_IDS:
        raise ValueError("Candidate runs must cover exactly first 10 ID->EN fixtures in order")
    result = []
    for row in reviewed[:10]:
        sid = row["id"]
        value = translated[sid]
        if (not isinstance(value, dict) or
            not isinstance(value.get("translation"), str) or
            not value["translation"].strip() or
            not isinstance(value.get("latency_ms"), (int, float)) or
            not math.isfinite(value["latency_ms"]) or value["latency_ms"] <= 0):
            raise ValueError("Candidate translation/latency invalid for " + sid)
        control = row["mlkit"]
        result.append({
            "sample": sid,
            "source_text": row["text"],
            "risk_tag": row["risk_tag"],
            "mlkit_whole_translation": control["translation"],
            "mlkit_whole_status": control["status"],
            "mlkit_whole_notes": control["notes"],
            "argos_translation": value["translation"],
            "argos_latency_ms": f'{value["latency_ms"]:.3f}',
            "error": "",
            "candidate_review_status": "",
            "candidate_notes": "",
        })
    return result


def grade(raw: Path, review: Path, session: dict) -> dict:
    original = read_csv(raw, OUTPUT_COLUMNS)
    revised = read_csv(review, OUTPUT_COLUMNS)
    if len(original) != 10 or len(revised) != 10:
        raise ValueError("Only complete 10-case candidate pilot can be graded")
    if session["raw_sha256"] != sha256(raw) or session["model_sha256"] != MODEL_SHA256:
        raise ValueError("Candidate raw evidence/model SHA changed")
    wins = losses = accepted = 0
    new_critical = []
    for initial, rated in zip(original, revised):
        if any(initial[k] != rated[k] for k in OUTPUT_COLUMNS[:-2]):
            raise ValueError("Reviewer altered source/control/candidate raw fields")
        if initial["sample"] not in PILOT_IDS:
            raise ValueError("Unexpected sample ID")
        status = rated["candidate_review_status"]
        if status not in STATUS:
            raise ValueError("Candidate review missing/invalid for " + initial["sample"])
        if status != "ACCEPT" and not rated["candidate_notes"].strip():
            raise ValueError("Candidate rejection requires reason")
        was_ok = initial["mlkit_whole_status"] == "ACCEPT"
        now_ok = status == "ACCEPT"
        wins += int(now_ok and not was_ok)
        losses += int(was_ok and not now_ok)
        accepted += int(now_ok)
        if (status in {"NEGATION_ERROR", "NUMBER_OR_NAME_ERROR"} and
            initial["mlkit_whole_status"] not in {"NEGATION_ERROR", "NUMBER_OR_NAME_ERROR"}):
            new_critical.append(initial["sample"])
    net = wins - losses
    promising = wins >= 2 and net >= 2 and not new_critical
    return {
        "experiment": DIAGNOSTIC,
        "raw_sha256": session["raw_sha256"],
        "review_sha256": sha256(review),
        "sample_count": 10,
        "baseline_accept": sum(x["mlkit_whole_status"] == "ACCEPT" for x in original),
        "argos_accept": accepted,
        "candidate_wins": wins,
        "candidate_losses": losses,
        "net_additional_accepted": net,
        "new_critical_errors": new_critical,
        "preregistered_pilot_threshold_met": promising,
        "verdict": ("PROMISING_FOR_FULL_30_AND_NEW_INDEPENDENT_HOLDOUT"
                    if promising else "NO_BASIS_TO_PROMOTE_FROM_HOST_PILOT"),
        "performance": "Windows CPU timing cannot be transferred to Android",
        "cp4": "BLOCKED",
        "android_engine": "NOT_INTEGRATED_OR_TESTED",
    }


def write_csv(path: Path, rows: list[dict]) -> None:
    if path.exists():
        raise FileExistsError("Refusing to overwrite: " + str(path))
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=OUTPUT_COLUMNS)
        writer.writeheader()
        writer.writerows(rows)
