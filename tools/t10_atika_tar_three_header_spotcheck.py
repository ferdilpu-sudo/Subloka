#!/usr/bin/env python3
"""T10 speculative lexical-order TAR spot-check, bounded to 3 HEADER requests.

Default is offline dry-run. Explicit --execute-three-headers does at most three
512-byte HTTP Range GETs with 513-byte overread guards via the existing pinned
header fetcher. NEVER downloads WAV payloads, writes an index, or asserts that
a three-point match validates all 9500 members.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import tarfile

from t10_atika_acquisition_budget import (
    CATEGORY, MAX_CATEGORY_ROWS, MAX_CATEGORY_SOURCE_WAV_BYTES,
)
import t10_atika_tar_header_walk as tar_walk
from t10_atika_tar_layout_budget import (
    END_MARKER_BYTES, TAR_BLOCK_BYTES, RECORD_BYTES_ILLUSTRATION,
    ceil_to, theoretical_layout,
)
from t10_atika_tar_order_hypotheses import analyze_order_hypotheses
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file,
)

MAX_SPOTS = 3
SPOT_FRACS = (1, 2, 3)
MIN_MEMBERS = 30


def candidates_from_rows(rows: list[tuple[str, int]], archive_bytes: int
                         ) -> list[tuple[int, int, str, int]]:
    """Construct temporary hypothetical header locations; no persistence."""
    if (not MIN_MEMBERS <= len(rows) <= MAX_CATEGORY_ROWS
            or type(archive_bytes) is not int):
        raise ValueError("Unexpected pinned category count or TAR size")
    if len({name for name, _ in rows}) != len(rows):
        raise ValueError("Nonunique publisher member names")
    for name, sz in rows:
        if (not isinstance(name, str) or not name.startswith("data/")
                or ".." in name.split("/") or not name.lower().endswith(".wav")
                or type(sz) is not int or not 44 <= sz <= MAX_CATEGORY_SOURCE_WAV_BYTES):
            raise ValueError("Unsafe pinned WAV metadata")
    order = sorted(rows, key=lambda row: row[0])
    sizes = [size for _, size in order]
    arithmetic = theoretical_layout(sizes, archive_bytes)
    if not arithmetic["published_archive_matches_flat_10240_example"]:
        raise ValueError("Archive disagrees with no-auxiliary-member model")
    if arithmetic["hypothetical_all_wav_members_end_bytes"] + END_MARKER_BYTES > archive_bytes:
        raise ValueError("Flat TAR exceeds published size")
    idxs = [len(order) * f // 4 for f in SPOT_FRACS]
    if len(set(idxs)) != MAX_SPOTS:
        raise ValueError("Spot indices duplicated")
    found = []
    offset = 0
    for i, (name, size) in enumerate(order):
        if i in idxs:
            if offset % TAR_BLOCK_BYTES or offset + TAR_BLOCK_BYTES > archive_bytes:
                raise ValueError("Hypothetical header offset out of bounds")
            found.append((i, offset, name, size))
        offset += TAR_BLOCK_BYTES + ceil_to(size, TAR_BLOCK_BYTES)
    if offset != arithmetic["hypothetical_all_wav_members_end_bytes"]:
        raise ValueError("Hypothetical TAR accounting mismatch")
    if len(found) != MAX_SPOTS:
        raise ValueError("Missing hypothetical spots")
    return found


def plan(workspace: Path) -> tuple[list[tuple[int, int, str, int]], dict]:
    require_private_workspace(workspace)
    prior = analyze_order_hypotheses(workspace)
    if not prior["lexicographic_audio_path_order"]["candidate_prefix_consistent_with_both_observations"]:
        raise ValueError("Lexical candidate failed existing six-header observations")
    metadata = workspace / METADATA_FILENAME
    if (not metadata.is_file() or metadata.is_symlink()
            or metadata.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing pinned metadata")
    rows = []
    with metadata.open("r", encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Missing publisher CSV fields")
        for row in reader:
            if row["category"] == CATEGORY:
                rows.append((row["audio_path"], int(row["file_size_bytes"].replace(",", ""))))
                if len(rows) > MAX_CATEGORY_ROWS:
                    raise ValueError("Excess category rows")
    if sha256_file(metadata) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Pinned SHA mismatch during audit")
    if len(rows) != prior["category_wav_count"]:
        raise ValueError("Category count changed during audit")
    result = candidates_from_rows(rows, tar_walk.EXPECTED_TAR_BYTES)
    report = {
        "schema_version": 1,
        "checkpoint": "PUBLIC_IMPERATIVE_THREE_HEADER_SPOT_CHECK_ONLY",
        "source_revision": prior["source_revision"],
        "source_metadata_sha256": tar_walk.PINNED_METADATA_SHA,
        "pinned_category_count": len(rows),
        "hypothetical_spot_positions_one_based": [i + 1 for i, _, _, _ in result],
        "hypothesis": "LEXICOGRAPHIC_MEMBER_ORDER_NO_AUX_HEADERS",
        "prior_first_and_sixth_aggregate_checks": True,
        "spot_check_max_http_requests": MAX_SPOTS,
        "spot_check_body_read_upper_bound_bytes": MAX_SPOTS * tar_walk.MAX_READ_BYTES,
        "archive_or_wav_downloaded": False,
        "source_audio_sha_verified": False,
        "member_order_verified": False,
        "selected_30_wav_offsets_verified": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }
    return result, report


def check_headers(spots: list[tuple[int, int, str, int]]) -> dict:
    """Fetch only exact predicted headers, stop at the FIRST disagreement."""
    if (len(spots) != MAX_SPOTS or
            len({idx for idx, _, _, _ in spots}) != MAX_SPOTS):
        raise ValueError("Three distinct predetermined positions required")
    attempted = 0
    matched = 0
    for idx, offset, expected_name, expected_size in spots:
        if (type(idx) is not int or type(offset) is not int
                or offset < 0 or offset % TAR_BLOCK_BYTES
                or offset + TAR_BLOCK_BYTES > tar_walk.EXPECTED_TAR_BYTES
                or not isinstance(expected_name, str)
                or type(expected_size) is not int or expected_size < 44):
            raise ValueError("Unsafe candidate header")
        # Existing fail-closed 206-only reader: 200 -> ZERO bytes consumed.
        header = tar_walk.fetch_header(offset)
        attempted += 1
        if header == bytes(TAR_BLOCK_BYTES):
            break
        try:
            member = tarfile.TarInfo.frombuf(
                header, encoding="utf-8", errors="surrogateescape"
            )
        except (ValueError, tarfile.TarError, UnicodeError):
            break
        if not (member.isfile() and member.size == expected_size
                and member.name == expected_name):
            break
        matched += 1
    return {
        "headers_attempted": attempted,
        "full_name_and_size_headers_matching_hypothesis": matched,
        "all_three_sparse_headers_match": matched == MAX_SPOTS,
        "result": ("THREE_HEADER_HYPOTHESIS_CONSISTENT_NOT_VERIFIED"
                   if matched == MAX_SPOTS else "HYPOTHESIS_MISMATCH_STOP"),
        "member_order_verified": False,
        "selected_30_wav_offsets_verified": False,
        "no_audio_payload_or_archive_downloaded": True,
        "CP4": "BLOCKED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--execute-three-headers", action="store_true",
                        help="Explicitly authorize 3 bounded remote TAR HEADER reads, NO WAV")
    args = parser.parse_args()
    try:
        spots, report = plan(args.workspace)
        report["network_requests_executed"] = 0
        if args.execute_three_headers:
            audit = check_headers(spots)
            report["spot_check_result"] = audit
            report["network_requests_executed"] = audit["headers_attempted"]
        else:
            report["status"] = "OFFLINE_PREFLIGHT_ONLY_NO_HTTP"
        print(json.dumps(report, indent=2))
        print("NO WAV/TAR PAYLOAD | NO VERIFIED OFFSETS | CP4 BLOCKED")
        return 0 if not args.execute_three_headers or audit["all_three_sparse_headers_match"] else 3
    except tar_walk.RangeNotHonored:
        print("RANGE_NOT_HONORED_NO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, csv.Error, UnicodeError, tarfile.TarError):
        # Do not leak member names or signed redirect URLs in error messages.
        print("ERROR: T10 three-header preflight/check failed closed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
