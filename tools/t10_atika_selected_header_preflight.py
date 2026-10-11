#!/usr/bin/env python3
"""T10 selected 30 WAV hypothetical TAR header plan; OFFLINE ONLY.

Use immutable publisher metadata, frozen 30 human-test selection, and lexical
flat-TAR hypothesis to calculate 30 ephemeral header candidates. No network,
no file writes, no fetched TAR/WAV, no claimed verified offsets or audio.
Actual remote header matching must be a separately reviewed operation.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from t10_atika_acquisition_budget import (
    CATEGORY, MAX_CATEGORY_ROWS, MAX_CATEGORY_SOURCE_WAV_BYTES,
    MAX_SELECTED, MAX_ACCEPTABLE_HEADER_REQUESTS,
)
import t10_atika_tar_header_walk as tar_walk
from t10_atika_tar_layout_budget import (
    TAR_BLOCK_BYTES, RECORD_BYTES_ILLUSTRATION,
    ceil_to, theoretical_layout,
)
from t10_atika_tar_order_hypotheses import analyze_order_hypotheses
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file,
)


def predicted_selected_headers(
        category_rows: list[tuple[str, int]],
        selected_paths: set[str],
        archive_bytes: int,
) -> list[tuple[int, int, str, int]]:
    """Ephemeral (index, header offset, name, size) tuples, NEVER serialized."""
    if (type(archive_bytes) is not int or archive_bytes <= 0
            or not MAX_SELECTED <= len(category_rows) <= MAX_CATEGORY_ROWS
            or not isinstance(selected_paths, set)
            or len(selected_paths) != MAX_SELECTED):
        raise ValueError("Invalid category/selected size")
    names = set()
    for name, size in category_rows:
        if (not isinstance(name, str) or not name.startswith("data/")
                or ".." in name.split("/")
                or not name.lower().endswith(".wav")
                or type(size) is not int or not 44 <= size <= MAX_CATEGORY_SOURCE_WAV_BYTES
                or name in names):
            raise ValueError("Invalid or repeated publisher WAV member")
        names.add(name)
    if not selected_paths <= names:
        raise ValueError("Frozen selected WAV missing from pinned category")
    if any(not isinstance(p, str) for p in selected_paths):
        raise ValueError("Unexpected selected path type")
    ordered = sorted(category_rows, key=lambda item: item[0])
    layout = theoretical_layout([size for _, size in ordered], archive_bytes)
    if not layout["published_archive_matches_flat_10240_example"]:
        raise ValueError("Pinned TAR size inconsistent with exact flat member hypothesis")
    candidates = []
    offset = 0
    for index, (name, size) in enumerate(ordered):
        if name in selected_paths:
            if offset % TAR_BLOCK_BYTES or offset + TAR_BLOCK_BYTES > archive_bytes:
                raise ValueError("Unsafe hypothetical header offset")
            candidates.append((index, offset, name, size))
        offset += TAR_BLOCK_BYTES + ceil_to(size, TAR_BLOCK_BYTES)
    if (len(candidates) != MAX_SELECTED
            or offset != layout["hypothetical_all_wav_members_end_bytes"]
            or len({offset for _, offset, _, _ in candidates}) != MAX_SELECTED):
        raise ValueError("Hypothetical selected headers inconsistent with layout")
    return candidates


def preflight(workspace: Path) -> dict:
    require_private_workspace(workspace)
    upstream = analyze_order_hypotheses(workspace)  # SHA and selection checks.
    if not upstream["lexicographic_audio_path_order"]["candidate_prefix_consistent_with_both_observations"]:
        raise ValueError("Lexicographic hypothesis conflicts with witnessed prefix")
    selected = tar_walk.load_selection(workspace)
    metadata = workspace / METADATA_FILENAME
    if (not metadata.is_file() or metadata.is_symlink()
            or metadata.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing or linked pinned metadata")
    all_rows = []
    with metadata.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Missing publisher CSV fields")
        for row in reader:
            if row["category"] == CATEGORY:
                try:
                    size = int(row["file_size_bytes"].replace(",", ""))
                except (TypeError, ValueError, AttributeError):
                    raise ValueError("Invalid publisher WAV byte count")
                all_rows.append((row["audio_path"], size))
                if len(all_rows) > MAX_CATEGORY_ROWS:
                    raise ValueError("Category exceeds read-only row cap")
    if sha256_file(metadata) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Original metadata SHA changed during preflight")
    if len(all_rows) != upstream["category_wav_count"]:
        raise ValueError("Category size differs from pinned-order audit")
    candidates = predicted_selected_headers(
        all_rows, selected, tar_walk.EXPECTED_TAR_BYTES
    )
    if MAX_SELECTED > MAX_ACCEPTABLE_HEADER_REQUESTS:
        raise ValueError("Selected headers would exceed approved research request cap")
    selected_bytes = sum(size for _, _, _, size in candidates)
    return {
        "schema_version": 1,
        "checkpoint": "PUBLIC_IMPERATIVE_SELECTED_30_HEADER_CANDIDATES_OFFLINE",
        "source_revision": upstream["source_revision"],
        "source_metadata_sha256": tar_walk.PINNED_METADATA_SHA,
        "category_wav_metadata_rows": len(all_rows),
        "frozen_selected_human_test_count": len(candidates),
        "selected_wav_bytes_from_publisher_metadata_only": selected_bytes,
        "candidate_header_locations": len(candidates),
        "candidate_order": "LEXICOGRAPHIC_MEMBER_ORDER_NO_AUX_HEADERS",
        "three_sparse_remote_headers_reported_separately": True,
        "predicted_offsets_internally_computed_but_not_printed": True,
        "exact_selected_header_checks_performed": 0,
        "network_requests_executed": 0,
        "if_separately_authorized_header_requests_max": MAX_SELECTED,
        "if_separately_authorized_application_read_bytes_max": (
            MAX_SELECTED * tar_walk.MAX_READ_BYTES
        ),
        "selected_header_offsets_verified": False,
        "wav_payloads_recovered": 0,
        "no_files_written": True,
        "no_network_or_audio_download": True,
        "source_audio_integrity_verified": False,
        "all_archive_members_order_verified": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(preflight(args.workspace), indent=2))
        print("OFFLINE ONLY | 30 HYPOTHETICAL HEADERS | 0 WAV | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error, UnicodeError):
        # Never expose private path strings or upstream transcript contents.
        print("ERROR: T10 selected-header preflight blocked", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
