#!/usr/bin/env python3
"""T10 public Atika IMPERATIVE audio acquisition cost evaluation, OFFLINE ONLY.

Read a previously downloaded CSV and immutable 30-case selection stored inside
gitignored .t10-benchmark. This command has NO network, no file writes, no WAV
download, no model/ADB/inference, and does not change frozen CP4 criteria.

The publisher TAR is not per-WAV indexed. Estimated header-scanning cost is
a feasibility heuristic, NOT a proof of exact TAR member order/offsets.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from t10_atika_tar_header_walk import (
    EXPECTED_TAR_BYTES, MAX_SELECTION_BYTES, PINNED_METADATA_SHA,
    SELECTION_NAME, load_selection,
)
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REVISION, REQUIRED, sha256_file,
    valid_human_test,
)

CATEGORY = "Imperative"
MAX_SELECTED = 30
MAX_INDIVIDUAL_WAV_BYTES = 3_000_000
MAX_CATEGORY_ROWS = 25_000
# This is a policy decision, not a server cap. Avoid tens of thousands of
# serial HTTP requests for small WAVs when index location is unknown.
MAX_ACCEPTABLE_HEADER_REQUESTS = 200


def budget(workspace: Path) -> dict:
    require_private_workspace(workspace)
    selected_paths = load_selection(workspace)  # Checks frozen source, 30 paths, metadata SHA.
    selection_path = workspace / SELECTION_NAME
    if selection_path.is_symlink() or selection_path.stat().st_size > MAX_SELECTION_BYTES:
        raise ValueError("Unsafe frozen selection")
    selected = json.loads(selection_path.read_text(encoding="utf-8"))
    items = selected["items"]
    if len(items) != MAX_SELECTED or len(selected_paths) != MAX_SELECTED:
        raise ValueError("Expected 30 frozen external test rows")
    csv_path = workspace / METADATA_FILENAME
    if (not csv_path.is_file() or csv_path.is_symlink()
            or csv_path.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing or linked upstream metadata CSV")
    digest = sha256_file(csv_path)
    if digest != PINNED_METADATA_SHA:
        raise ValueError("Local metadata CSV digest differs from verified Windows pin")
    matched = {}
    category_total = 0
    test_eligible = 0
    category_audio_bytes_from_metadata = 0
    with csv_path.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise ValueError("Unexpected publisher CSV columns")
        for row in reader:
            if row["category"] != CATEGORY:
                continue
            category_total += 1
            if category_total > MAX_CATEGORY_ROWS:
                raise ValueError("Publisher category row count exceeds research cap")
            try:
                sz = int(row["file_size_bytes"].replace(",", ""))
            except (TypeError, ValueError, AttributeError):
                raise ValueError("Non-numeric size in category metadata")
            if not 44 <= sz <= MAX_INDIVIDUAL_WAV_BYTES:
                raise ValueError("Out of bounds WAV size in publisher category metadata")
            category_audio_bytes_from_metadata += sz
            if valid_human_test(row):
                test_eligible += 1
            if row["audio_path"] in selected_paths:
                if row["audio_path"] in matched:
                    raise ValueError("Duplicate selected WAV path in publisher CSV")
                if not valid_human_test(row):
                    raise ValueError("Selected WAV not in eligible public human test partition")
                matched[row["audio_path"]] = row
    if set(matched) != selected_paths or category_total < MAX_SELECTED:
        raise ValueError("Selected WAV paths missing from pinned publisher CSV")
    selected_bytes = 0
    labels = set()
    normalized_texts = set()
    for item in items:
        source = matched[item["source_audio_tar_member"]]
        if (int(item["audio_expected_bytes_from_publisher"]) !=
                int(source["file_size_bytes"].replace(",", ""))):
            raise ValueError("Selected WAV claimed bytes do not match upstream metadata")
        if (item["speaker_label"] != source["speaker_id"]
                or item["reference_from_publisher_not_rechecked"] != source["transcript"]):
            raise ValueError("Selection source speaker/transcript mismatch")
        selected_bytes += int(source["file_size_bytes"].replace(",", ""))
        labels.add(source["speaker_id"])
        normalized_texts.add(source["transcript"].strip().casefold())
    # TAR overhead, directory entries and optional extended headers are not
    # completely derivable from source CSV: do not pretend to know offsets.
    heuristic_header_requests = category_total
    rtt_scenarios = [
        {"assumed_average_request_latency_ms": ms,
         "minimum_sequential_header_walk_minutes_if_no_index": round(
             heuristic_header_requests * ms / 60000, 1)}
        for ms in (200, 500, 1000)
    ]
    return {
        "schema_version": 1,
        "checkpoint": "PUBLIC_IMPERATIVE_INDEX_COST_DRY_RUN_NO_DOWNLOAD",
        "source_revision": REVISION,
        "category": CATEGORY,
        "source_metadata_sha256": digest,
        "category_rows_in_metadata": category_total,
        "category_human_test_rows_eligible": test_eligible,
        "source_archive_size_bytes_from_remote_metadata": EXPECTED_TAR_BYTES,
        "category_WAV_bytes_sum_from_publisher_metadata": category_audio_bytes_from_metadata,
        "selected_test_human_audio_count": len(matched),
        "selected_audio_bytes_sum_from_publisher_metadata": selected_bytes,
        "selected_public_speaker_label_count": len(labels),
        "selected_reference_texts_distinct_casefold_not_rechecked": len(normalized_texts),
        "selected_audio_locally_verified": False,
        "remote_tar_member_order_known": False,
        "public_per_WAV_tar_offset_index_verified": False,
        "estimated_one_request_per_WAV_header_scan": heuristic_header_requests,
        "estimated_header_request_count_exceeds_safety_budget": (
            heuristic_header_requests > MAX_ACCEPTABLE_HEADER_REQUESTS
        ),
        "safety_budget_header_requests": MAX_ACCEPTABLE_HEADER_REQUESTS,
        "network_delay_illustrations_not_predictions": rtt_scenarios,
        "full_tar_bytes_if_approved_for_download": EXPECTED_TAR_BYTES,
        "recommended_next_action": (
            "DO_NOT_SCAN_TAR_ONE_MEMBER_PER_REQUEST; SEEK REAL PER_WAV_INDEX "
            "OR ALTERNATE_SMALL_LICENSED_SOURCE; LARGE_TAR_NEEDS_EXPLICIT_APPROVAL"
            if heuristic_header_requests > MAX_ACCEPTABLE_HEADER_REQUESTS else
            "INDEX_FEASIBILITY_UNPROVEN; NO AUTOMATIC_ARCHIVE_DOWNLOAD"
        ),
        "no_network_or_files_written": True,
        "no_audio_or_model_downloaded": True,
        "no_ASR_inference": True,
        "fresh_consent_private_holdout_unchanged": True,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(budget(args.workspace), ensure_ascii=False, indent=2))
        print("OFFLINE ONLY | NO WAV OR TAR | NO MODEL OR ADB | NO INFERENCE | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, csv.Error, UnicodeError,
            json.JSONDecodeError) as exc:
        print("ERROR: T10 Atika offline acquisition budget:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
