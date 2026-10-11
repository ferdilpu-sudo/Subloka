#!/usr/bin/env python3
"""Read-only TAR layout arithmetic from pinned Atika WAV-size metadata.

NOT an offset index. Total-byte agreement cannot prove member order, PAX
records, directory members, or authorization to fetch audio.
No network, writes, WAV/model download, or inference.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from t10_atika_acquisition_budget import (
    CATEGORY, MAX_CATEGORY_ROWS, MAX_CATEGORY_SOURCE_WAV_BYTES, budget,
)
import t10_atika_tar_header_walk as tar_walk
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import METADATA_FILENAME, MAX_METADATA_BYTES, sha256_file

TAR_BLOCK_BYTES = 512
RECORD_BYTES_ILLUSTRATION = 10240
END_MARKER_BYTES = 1024


def ceil_to(value: int, alignment: int) -> int:
    return ((value + alignment - 1) // alignment) * alignment


def theoretical_layout(wav_sizes: list[int], archive_bytes: int) -> dict:
    """Order-independent size arithmetic; intentionally returns zero offsets."""
    if (not wav_sizes or len(wav_sizes) > MAX_CATEGORY_ROWS
            or type(archive_bytes) is not int or archive_bytes <= 0
            or archive_bytes % TAR_BLOCK_BYTES):
        raise ValueError("Invalid TAR size or category WAV count")
    if any(type(n) is not int or not 44 <= n <= MAX_CATEGORY_SOURCE_WAV_BYTES
           for n in wav_sizes):
        raise ValueError("Invalid publisher WAV size")
    payload = sum(wav_sizes)
    padded_payload = sum(ceil_to(n, TAR_BLOCK_BYTES) for n in wav_sizes)
    min_headers = len(wav_sizes) * TAR_BLOCK_BYTES
    no_aux_members_end = min_headers + padded_payload
    min_with_end = no_aux_members_end + END_MARKER_BYTES
    python_style = ceil_to(min_with_end, RECORD_BYTES_ILLUSTRATION)
    return {
        "category_wav_count": len(wav_sizes),
        "wav_payload_bytes_from_publisher_metadata": payload,
        "hypothetical_one_header_per_wav_bytes": min_headers,
        "wav_512_alignment_padding_bytes": padded_payload - payload,
        "hypothetical_all_wav_members_end_bytes": no_aux_members_end,
        "hypothetical_minimum_including_two_end_blocks_bytes": min_with_end,
        "hypothetical_10240_record_padded_archive_bytes": python_style,
        "published_archive_bytes": archive_bytes,
        "archive_minus_hypothetical_minimum_bytes": archive_bytes - min_with_end,
        "published_archive_at_least_theoretical_minimum": archive_bytes >= min_with_end,
        "published_archive_matches_flat_10240_example": archive_bytes == python_style,
        "archive_layout_proven": False,
        "wav_member_order_proven": False,
        "wav_offsets_verified": False,
        "explanation": "Size arithmetic ignores directory/PAX/GNU metadata and cannot reconstruct TAR member order or validate WAV bytes. A matching total is not an offset index.",
    }


def layout_budget(workspace: Path) -> dict:
    require_private_workspace(workspace)
    verified = budget(workspace)
    metadata = workspace / METADATA_FILENAME
    if (not metadata.is_file() or metadata.is_symlink()
            or metadata.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing or unsafe original pinned metadata CSV")
    sizes = []
    with metadata.open("r", encoding="utf-8-sig", newline="") as handle:
        rows = csv.DictReader(handle)
        for row in rows:
            if row.get("category") == CATEGORY:
                sizes.append(int(row["file_size_bytes"].replace(",", "")))
                if len(sizes) > MAX_CATEGORY_ROWS:
                    raise ValueError("Category WAV count exceeds audit cap")
    if sha256_file(metadata) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Pinned CSV digest changed during layout audit")
    if (len(sizes) != verified["category_rows_in_metadata"]
            or sum(sizes) != verified["category_WAV_bytes_sum_from_publisher_metadata"]):
        raise ValueError("Metadata changed during layout audit")
    report = theoretical_layout(sizes, tar_walk.EXPECTED_TAR_BYTES)
    return {
        "schema_version": 1,
        "checkpoint": "PUBLIC_IMPERATIVE_TAR_LAYOUT_ARITHMETIC_OFFLINE_ONLY",
        "source_revision": verified["source_revision"],
        "source_metadata_sha256": tar_walk.PINNED_METADATA_SHA,
        "selected_metadata_count_unchanged": verified["selected_test_human_audio_count"],
        "selected_wav_bytes_publisher_metadata_only": verified["selected_audio_bytes_sum_from_publisher_metadata"],
        "tar_layout_arithmetic": report,
        "network_calls": 0,
        "files_written": False,
        "wav_or_tar_downloaded": False,
        "actual_wav_locally_verified": False,
        "per_wav_offset_index_available": False,
        "next_action": "DO_NOT_DERIVE_OFFSETS_FROM_METADATA_ALONE; REQUIRE_VERIFIED_MEMBER_ORDER_AND_HEADER_SIZES",
        "T10": "ACTIVE",
        "CP4": "BLOCKED",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        result = layout_budget(args.workspace)
        print(json.dumps(result, indent=2))
        print("OFFLINE ONLY | NO WAV/TAR | NO OFFSET CLAIM | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error, UnicodeError) as exc:
        print("ERROR: T10 TAR layout budget:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
