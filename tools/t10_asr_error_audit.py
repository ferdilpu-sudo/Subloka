"""Reproducible T10 word-error audit for already-collected whisper.cpp evidence.

Diagnostics only: does not rewrite baselines, normalizer, translations, or CP4 status.
Reference accuracy requires human listening to the original WAV clips.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

from t10_wer import normalize

INPUT_COLUMNS = ("model", "sample", "language", "category", "wer", "hypothesis")
REVIEW_COLUMNS = (
    "sample", "language", "audio_path", "reference", "base_hypothesis",
    "base_wer", "tiny_wer", "reference_words", "base_errors",
    "substitutions", "deletions", "insertions", "audio_review_status", "review_notes",
)
REVIEW_STATUSES = ("UNREVIEWED", "REFERENCE_CONFIRMED", "REFERENCE_NEEDS_CORRECTION", "AUDIO_AMBIGUOUS")


def align_errors(reference: str, hypothesis: str) -> dict[str, int]:
    """Calculate exact Levenshtein S/D/I using the benchmark's token normalizer.

    Dynamic programming tie-breaking is deterministic. Error count is invariant;
    the split between S/D/I can depend on tie-breaking for ambiguous alignments.
    """
    a, b = normalize(reference), normalize(hypothesis)
    n, m = len(a), len(b)
    table = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(n + 1):
        table[i][0] = i
    for j in range(m + 1):
        table[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            table[i][j] = min(
                table[i - 1][j] + 1,
                table[i][j - 1] + 1,
                table[i - 1][j - 1] + (a[i - 1] != b[j - 1]),
            )
    i, j = n, m
    s = d = ins = 0
    while i or j:
        if i and j and table[i][j] == table[i - 1][j - 1] + (a[i - 1] != b[j - 1]):
            s += a[i - 1] != b[j - 1]
            i -= 1
            j -= 1
        elif i and table[i][j] == table[i - 1][j] + 1:
            d += 1
            i -= 1
        else:
            ins += 1
            j -= 1
    assert s + d + ins == table[n][m]
    return {
        "reference_words": n,
        "substitutions": s,
        "deletions": d,
        "insertions": ins,
        "errors": s + d + ins,
    }


def load_evidence(results_path: Path, manifest_path: Path) -> list[dict[str, Any]]:
    fixtures = json.loads(manifest_path.read_text(encoding="utf-8-sig"))["samples"]
    by_id: dict[str, dict[str, Any]] = {}
    for fixture in fixtures:
        sample_id = fixture["id"]
        if sample_id in by_id:
            raise ValueError(f"Duplicate manifest sample: {sample_id}")
        by_id[sample_id] = fixture
    with results_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not set(INPUT_COLUMNS).issubset(reader.fieldnames or ()):
            raise ValueError(f"Missing CSV columns. Required: {INPUT_COLUMNS}")
        csv_rows = list(reader)
    if not csv_rows:
        raise ValueError("Empty ASR benchmark CSV")
    seen: set[tuple[str, str]] = set()
    output = []
    for row in csv_rows:
        key = (row["model"], row["sample"])
        if key in seen:
            raise ValueError(f"Duplicate benchmark row: {key}")
        seen.add(key)
        if row["sample"] not in by_id:
            raise ValueError(f"Unknown fixture: {row['sample']}")
        fixture = by_id[row["sample"]]
        if (row["language"], row["category"]) != (fixture["language"], fixture["category"]):
            raise ValueError(f"Fixture labels do not match: {row['sample']}")
        reference = fixture["reference"]
        if not reference.strip() or not row["hypothesis"].strip():
            raise ValueError(f"Empty reference/hypothesis: {row['sample']}")
        edits = align_errors(reference, row["hypothesis"])
        if not edits["reference_words"]:
            raise ValueError(f"No reference words: {row['sample']}")
        reported = float(row["wer"])
        if not math.isfinite(reported) or reported < 0:
            raise ValueError(f"Invalid archived WER: {key}")
        recalculated = edits["errors"] / edits["reference_words"]
        output.append({
            "model": row["model"],
            "sample": row["sample"],
            "language": row["language"],
            "category": row["category"],
            "reference": reference,
            "hypothesis": row["hypothesis"],
            "audio_path": fixture["audio"],
            "wer_archived": reported,
            "wer_recalculated": recalculated,
            "wer_mismatch": abs(recalculated - reported) > 0.000051,
            **edits,
        })
    return output


def audit(
    results_path: Path,
    manifest_path: Path,
    output_dir: Path,
    wer_target: float = 0.20,
) -> dict[str, Any]:
    if not 0 <= wer_target <= 1:
        raise ValueError("WER target must be between 0 and 1")
    rows = load_evidence(results_path, manifest_path)
    group_rows: dict[tuple[str, str, str], list[dict[str, Any]]] = defaultdict(list)
    for row in rows:
        group_rows[(row["model"], row["language"], row["category"])].append(row)

    groups = []
    for (model, language, category), members in sorted(group_rows.items()):
        words = sum(m["reference_words"] for m in members)
        errors = sum(m["errors"] for m in members)
        groups.append({
            "model": model,
            "language": language,
            "category": category,
            "samples": len(members),
            "reference_words": words,
            "errors": errors,
            "substitutions": sum(m["substitutions"] for m in members),
            "deletions": sum(m["deletions"] for m in members),
            "insertions": sum(m["insertions"] for m in members),
            "micro_wer": errors / words,
            "macro_wer": sum(m["wer_recalculated"] for m in members) / len(members),
        })

    base_id = [
        r for r in rows
        if (r["model"], r["language"], r["category"]) == ("base", "id", "clean")
    ]
    base_id.sort(key=lambda r: (-r["errors"], r["sample"]))
    tiny = {
        r["sample"]: r for r in rows
        if (r["model"], r["language"], r["category"]) == ("tiny", "id", "clean")
    }
    words = sum(r["reference_words"] for r in base_id)
    errors = sum(r["errors"] for r in base_id)
    max_allowed = math.floor(wer_target * words + 1e-10)
    mismatches = [
        {
            "model": r["model"], "sample": r["sample"],
            "archived_wer": r["wer_archived"],
            "recalculated_wer": r["wer_recalculated"],
            "reference_words": r["reference_words"],
            "recalculated_errors": r["errors"],
        }
        for r in rows if r["wer_mismatch"]
    ]
    summary = {
        "evidence_type": "ASR textual word-error audit; audio reference review pending",
        "source_csv_sha256": hashlib.sha256(results_path.read_bytes()).hexdigest(),
        "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        "result_rows": len(rows),
        "manifest_matched_samples": len({r["sample"] for r in rows}),
        "wer_target": wer_target,
        "groups": groups,
        "id_clean_base": {
            "samples": len(base_id),
            "reference_words": words,
            "errors": errors,
            "micro_wer": (errors / words if words else None),
            "max_errors_at_target": max_allowed,
            "minimum_error_reduction": max(0, errors - max_allowed),
            "top_six": [
                {"sample": r["sample"], "errors": r["errors"], "wer": r["wer_recalculated"]}
                for r in base_id[:6]
            ],
        },
        "reported_wer_mismatches": mismatches,
        "limitation": "No WAV files were listened to; reference correctness is unverified. Do not modify CP4 baseline, threshold or transcripts based on this audit.",
    }
    if output_dir.exists() and any(output_dir.iterdir()):
        raise FileExistsError(f"Output directory must be empty: {output_dir}")
    output_dir.mkdir(parents=True, exist_ok=True)
    summary_file = output_dir / "asr-error-summary.json"
    summary_file.write_text(json.dumps(summary, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    with (output_dir / "id-clean-base-audio-review.csv").open("w", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=REVIEW_COLUMNS)
        writer.writeheader()
        for row in base_id:
            writer.writerow({
                "sample": row["sample"],
                "language": row["language"],
                "audio_path": row["audio_path"],
                "reference": row["reference"],
                "base_hypothesis": row["hypothesis"],
                "base_wer": round(row["wer_recalculated"], 4),
                "tiny_wer": round(tiny[row["sample"]]["wer_recalculated"], 4) if row["sample"] in tiny else "",
                "reference_words": row["reference_words"],
                "base_errors": row["errors"],
                "substitutions": row["substitutions"],
                "deletions": row["deletions"],
                "insertions": row["insertions"],
                "audio_review_status": "UNREVIEWED",
                "review_notes": "",
            })
    print(f"ASR audit saved: {output_dir}; {len(base_id)} Indonesian clean Base samples; {len(mismatches)} archived WER discrepancy(s).")
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("results", type=Path, help="asr-results.csv")
    parser.add_argument("manifest", type=Path, help="t10-dataset.json")
    parser.add_argument("out", type=Path, help="new or empty output directory")
    args = parser.parse_args()
    audit(args.results, args.manifest, args.out)


if __name__ == "__main__":
    main()
