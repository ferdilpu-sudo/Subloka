#!/usr/bin/env python3
"""T10 translation review: create a human-review CSV and report CP4 evidence.

Use independently judged outcomes; this tool does not grade ML Kit automatically.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import statistics
import sys
from collections import Counter
from pathlib import Path

STATUS = {
    "ACCEPT",
    "MAJOR_MEANING_ERROR",
    "NEGATION_ERROR",
    "NUMBER_OR_NAME_ERROR",
}
REQUIRED = (
    "sample", "source_language", "target_language", "source_text",
    "translation", "latency_ms", "error",
)
FIELDS = (*REQUIRED, "status", "notes")


def load(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not reader.fieldnames or not set(REQUIRED).issubset(reader.fieldnames):
            raise ValueError(f"Missing columns: {sorted(set(REQUIRED) - set(reader.fieldnames or []))}")
        rows = list(reader)
    return rows


def verify(rows: list[dict[str, str]]) -> None:
    if len(rows) != 60:
        raise ValueError(f"Expected 60 rows, found {len(rows)}")
    ids = [r["sample"] for r in rows]
    if len(ids) != len(set(ids)):
        raise ValueError("Duplicate sample IDs")
    counts = Counter((r["source_language"], r["target_language"]) for r in rows)
    if counts != {("en", "id"): 30, ("id", "en"): 30}:
        raise ValueError(f"Expected 30 EN->ID and 30 ID->EN; got {dict(counts)}")
    for r in rows:
        if not r["source_text"].strip():
            raise ValueError(f"Empty source: {r['sample']}")
        try:
            value = float(r["latency_ms"])
        except ValueError as exc:
            raise ValueError(f"Invalid latency for {r['sample']}") from exc
        if not math.isfinite(value) or value < 0:
            raise ValueError(f"Invalid latency for {r['sample']}")


def fingerprint(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def init(raw: Path, review: Path) -> None:
    rows = load(raw)
    verify(rows)
    if review.exists():
        raise FileExistsError(f"Review exists; refusing overwrite: {review}")
    review.parent.mkdir(parents=True, exist_ok=True)
    with review.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            writer.writerow({**row, "status": "", "notes": ""})
    print(f"Created: {review}")
    print(f"Raw CSV SHA-256: {fingerprint(raw)}")
    print("Review all 60 rows; allowed status: " + ", ".join(sorted(STATUS)))


def content_digest(rows: list[dict[str, str]]) -> str:
    """Order-sensitive digest of the exact source/translation pairs, not CSV formatting."""
    identity = ("sample", "source_language", "target_language", "source_text", "translation")
    canonical = [{key: row[key] for key in identity} for row in rows]
    payload = json.dumps(canonical, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def apply_draft(raw: Path, output: Path, draft_file: Path) -> None:
    """Reapply AI-assessed labels ONLY to the exact already-reviewed model outputs.

    This does not create independently verified human review evidence.
    """
    rows = load(raw)
    verify(rows)
    draft = json.loads(draft_file.read_text(encoding="utf-8"))
    if draft.get("version") != 1 or draft.get("default_status") != "ACCEPT":
        raise ValueError("Unsupported AI draft format")
    actual_digest = content_digest(rows)
    if actual_digest != draft.get("source_content_sha256"):
        raise ValueError(
            "Source/translation text differs from approved draft; "
            "perform a fresh human review instead of reusing old labels"
        )
    if output.exists():
        raise FileExistsError(f"Review exists; refusing overwrite: {output}")
    if any(row["error"].strip() or not row["translation"].strip() for row in rows):
        raise ValueError("Unexpected missing translation or engine error; fresh review required")
    overrides = draft.get("overrides")
    if not isinstance(overrides, dict) or not set(overrides).issubset(
        {row["sample"] for row in rows}
    ):
        raise ValueError("Unknown or malformed review override IDs")
    accept_notes = draft.get("accept_notes", {})
    if not isinstance(accept_notes, dict) or not set(accept_notes).issubset(
        {row["sample"] for row in rows} - set(overrides)
    ) or any(not isinstance(note, str) for note in accept_notes.values()):
        raise ValueError("Invalid draft ACCEPT notes")
    for key, decision in overrides.items():
        if not isinstance(decision, dict) or decision.get("status") not in STATUS:
            raise ValueError(f"Invalid draft status for {key}")
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8-sig", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=FIELDS)
        writer.writeheader()
        for row in rows:
            decision = overrides.get(row["sample"], {})
            writer.writerow({
                **row,
                "status": decision.get("status", "ACCEPT"),
                "notes": decision.get("notes", accept_notes.get(row["sample"], "")),
            })
    print(f"AI-assisted provisional review created: {output}")
    print("NOT independently human-verified; CP4 requires explicit reviewer sign-off.")


def p95_nearest_rank(values: list[float]) -> float:
    ordered = sorted(values)
    return ordered[math.ceil(0.95 * len(ordered)) - 1]


def report(review: Path, json_path: Path | None) -> bool:
    rows = load(review)
    verify(rows)
    results = {}
    for source, target in [("en", "id"), ("id", "en")]:
        direction = f"{source}->{target}"
        subset = [r for r in rows if r["source_language"] == source]
        latencies = [float(r["latency_ms"]) for r in subset]
        completed = [r for r in subset if r.get("status", "").strip() in STATUS]
        invalid = [r["sample"] for r in subset if r.get("status", "").strip() and r["status"].strip() not in STATUS]
        if invalid:
            raise ValueError(f"Invalid review status for {invalid}")
        errors = [r["sample"] for r in subset if r["error"].strip() or not r["translation"].strip()]
        outcomes = Counter(r.get("status", "").strip() for r in completed)
        accepted = outcomes["ACCEPT"]
        good = (
            len(completed) == 30
            and not errors
            and accepted >= 27
            and outcomes["NEGATION_ERROR"] == 0
            and outcomes["NUMBER_OR_NAME_ERROR"] == 0
        )
        results[direction] = {
            "samples": 30,
            "reviewed": len(completed),
            "accepted": accepted,
            "acceptance_percent": round(100.0 * accepted / 30, 2),
            "major_meaning_errors": outcomes["MAJOR_MEANING_ERROR"],
            "negation_errors": outcomes["NEGATION_ERROR"],
            "number_or_name_errors": outcomes["NUMBER_OR_NAME_ERROR"],
            "engine_or_empty_outputs": errors,
            "median_latency_ms": round(statistics.median(latencies), 3),
            "p95_latency_ms": round(p95_nearest_rank(latencies), 3),
            "status": "PASS" if good else "NOT_PASS",
        }
    payload = {
        "evidence_type": "T10 reviewer-labelled ML Kit translation results; human sign-off not inferred",
        "review_csv_sha256": fingerprint(review),
        "offline_mode": "Must be verified and documented manually; not asserted by this report",
        "directions": results,
    }
    for name, result in results.items():
        print(
            f"{name}: {result['status']} | reviewed {result['reviewed']}/30 | "
            f"ACCEPT {result['accepted']}/30 ({result['acceptance_percent']:.1f}%) | "
            f"negation {result['negation_errors']} | "
            f"number/name {result['number_or_name_errors']} | "
            f"engine/empty {len(result['engine_or_empty_outputs'])} | "
            f"median {result['median_latency_ms']:.1f} ms | "
            f"p95 {result['p95_latency_ms']:.1f} ms"
        )
    if json_path is not None:
        if json_path.exists():
            raise FileExistsError(f"Refusing overwrite: {json_path}")
        json_path.parent.mkdir(parents=True, exist_ok=True)
        json_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        print(f"Report saved: {json_path}")
    return all(x["status"] == "PASS" for x in results.values())


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    make = sub.add_parser("init", help="Create blank human review CSV from device output")
    make.add_argument("raw", type=Path)
    make.add_argument("review", type=Path)
    review = sub.add_parser("report", help="Validate scores and summarize both directions")
    review.add_argument("review", type=Path)
    review.add_argument("--json", dest="json_path", type=Path)
    apply = sub.add_parser(
        "apply-draft", help="Apply previously AI-reviewed labels to exact matching outputs"
    )
    apply.add_argument("raw", type=Path)
    apply.add_argument("review", type=Path)
    apply.add_argument("--draft", type=Path, default=Path(__file__).with_name("t10_translation_ai_draft.json"))
    args = parser.parse_args()
    try:
        if args.cmd == "init":
            init(args.raw, args.review)
            return 0
        if args.cmd == "apply-draft":
            apply_draft(args.raw, args.review, args.draft)
            return 0
        return 0 if report(args.review, args.json_path) else 2
    except (ValueError, FileNotFoundError, FileExistsError, csv.Error) as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
