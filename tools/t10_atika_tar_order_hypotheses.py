#!/usr/bin/env python3
"""T10 pinned-metadata order-hypothesis diagnostic. Entirely offline.

Compare two explicit candidate orders with previously witnessed first TAR
member size and six-header end offset. NOT an index or extraction tool.
Do not infer selected clip offsets from matching six-header aggregates.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from t10_atika_acquisition_budget import CATEGORY, MAX_CATEGORY_ROWS
import t10_atika_tar_header_walk as tar_walk
from t10_atika_tar_layout_budget import layout_budget, ceil_to, TAR_BLOCK_BYTES
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file,
)

OBSERVED_FIRST_MEMBER_SIZE = 91364
OBSERVED_SIX_HEADER_NEXT_OFFSET = 490496
OBSERVED_FILE_HEADERS = 6


def assess_prefix(rows: list[tuple[str, int]],
                  first_size: int | None = None,
                  sixth_end: int | None = None,
                  prefix_count: int | None = None) -> dict:
    """Read the pinned observations at call time; synthetic fixtures can patch them."""
    if first_size is None:
        first_size = OBSERVED_FIRST_MEMBER_SIZE
    if sixth_end is None:
        sixth_end = OBSERVED_SIX_HEADER_NEXT_OFFSET
    if prefix_count is None:
        prefix_count = OBSERVED_FILE_HEADERS
    if (type(prefix_count) is not int or prefix_count < 1
            or len(rows) < prefix_count):
        raise ValueError("Not enough well-formed candidate members")
    if (type(first_size) is not int or first_size < 44
            or type(sixth_end) is not int or sixth_end <= 0):
        raise ValueError("Invalid witnessed TAR observations")
    if any(not isinstance(name, str) or not name or type(size) is not int
           or size < 44 for name, size in rows):
        raise ValueError("Malformed candidate WAV metadata")
    first_matches = rows[0][1] == first_size
    next_offset = sum(
        TAR_BLOCK_BYTES + ceil_to(size, TAR_BLOCK_BYTES)
        for _, size in rows[:prefix_count]
    )
    endpoint_matches = next_offset == sixth_end
    return {
        "first_member_size_matches_observed_header": first_matches,
        "sixth_next_header_offset_matches_observation": endpoint_matches,
        "candidate_prefix_consistent_with_both_observations": (
            first_matches and endpoint_matches
        ),
        "order_verified": False,
        "individual_member_offsets_verified": False,
    }


def analyze_order_hypotheses(workspace: Path) -> dict:
    require_private_workspace(workspace)
    base = layout_budget(workspace)  # Pinned SHA, selection 30, no network.
    csv_path = workspace / METADATA_FILENAME
    if (not csv_path.is_file() or csv_path.is_symlink()
            or csv_path.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing or linked pinned metadata")
    csv_order = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise ValueError("Missing publisher columns")
        for row in reader:
            if row["category"] == CATEGORY:
                csv_order.append((
                    row["audio_path"],
                    int(row["file_size_bytes"].replace(",", "")),
                ))
                if len(csv_order) > MAX_CATEGORY_ROWS:
                    raise ValueError("Category exceeds hard row cap")
    if sha256_file(csv_path) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Metadata SHA changed during order audit")
    layout = base["tar_layout_arithmetic"]
    if (len(csv_order) != layout["category_wav_count"]
            or sum(sz for _, sz in csv_order) != layout["wav_payload_bytes_from_publisher_metadata"]):
        raise ValueError("Pinned category metadata inconsistency")
    lexical = sorted(csv_order, key=lambda item: item[0])
    return {
        "schema_version": 1,
        "checkpoint": "PUBLIC_IMPERATIVE_ORDER_HYPOTHESES_OFFLINE_NO_OFFSETS",
        "source_revision": base["source_revision"],
        "source_metadata_sha256": tar_walk.PINNED_METADATA_SHA,
        "category_wav_count": len(csv_order),
        "previously_observed_first_member_size_bytes": OBSERVED_FIRST_MEMBER_SIZE,
        "previously_observed_six_header_next_offset_bytes": OBSERVED_SIX_HEADER_NEXT_OFFSET,
        "hypotheses_are_same_order": csv_order == lexical,
        "csv_source_row_order": assess_prefix(csv_order),
        "lexicographic_audio_path_order": assess_prefix(lexical),
        "notes": (
            "These are only candidate-order consistency checks against two "
            "published earlier aggregates. Even a double match is NOT a "
            "verified TAR member sequence, offset table, or download authorization."
        ),
        "number_of_audio_downloads": 0,
        "no_network_or_files_written": True,
        "member_order_verified": False,
        "selected_member_offsets_verified": False,
        "T10": "ACTIVE",
        "CP4": "BLOCKED",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(analyze_order_hypotheses(args.workspace), indent=2))
        print("OFFLINE ONLY | NO TAR/WAV | NO VERIFIED OFFSETS | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, KeyError, TypeError, csv.Error, UnicodeError) as exc:
        print("ERROR: T10 TAR order hypotheses:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
