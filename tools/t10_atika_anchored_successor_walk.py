#!/usr/bin/env python3
"""T10 selected first-header anchored TAR successor walk, OFFLINE by default.

Uses immutable 9500-row CSV to find the first frozen selected WAV candidate.
The user's earlier bounded remote pilot matched that header's name, type and
size twice. An explicit request can follow ONLY the first up to four successor
headers by reading one 512-byte TAR header at a time, recomputing the next
offset from the observed TAR header size after each match. No guesses at
the second frozen selected member's remote position, WAV payloads, disk
writes, participant names/transcripts or absolute offsets are emitted.
Pointwise success is NOT proof of archive member order or WAV integrity.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tarfile

from t10_atika_selected_header_check import prepare
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
from t10_atika_tar_layout_budget import ceil_to
import t10_atika_tar_header_walk as tar_walk
from t10_id_independent_holdout import require_private_workspace

MAX_SUCCESSOR_REQUESTS = 4
DEFAULT_SUCCESSORS = 3


def anchored_plan(workspace: Path, count: int) -> tuple[int, list[tuple[str, int]], dict]:
    """Validate pins/whole CSV before optional HTTP; never expose absolute offset."""
    require_private_workspace(workspace)
    if type(count) is not int or not 1 <= count <= MAX_SUCCESSOR_REQUESTS:
        raise ValueError("Invalid anchored TAR successor request count")
    selected, metadata = prepare(workspace)
    catalogue = category_catalogue(workspace, int(metadata["category_wav_metadata_rows"]))
    ordered = sorted(catalogue)
    if (len(selected) != 30 or
            len(ordered) != int(metadata["category_wav_metadata_rows"])):
        raise ValueError("Frozen category or selected count differs")
    anchor_index, anchor_offset, anchor_name, anchor_size = selected[0]
    second_index, _, _, _ = selected[1]
    if (ordered[anchor_index] != anchor_name
            or catalogue[anchor_name] != anchor_size
            or second_index <= anchor_index + count):
        raise ValueError("First selected anchor cannot accommodate bounded walk")
    start = anchor_offset + tar_walk.PROBE_BYTES + ceil_to(
        anchor_size, tar_walk.PROBE_BYTES
    )
    if (start % tar_walk.PROBE_BYTES or start < 0
            or start + tar_walk.PROBE_BYTES > tar_walk.EXPECTED_TAR_BYTES):
        raise ValueError("Anchored next header outside pinned TAR")
    successors = [(name, catalogue[name]) for name in
                  ordered[anchor_index+1:anchor_index+count+1]]
    if len(successors) != count:
        raise ValueError("Bounded follow-up count inconsistent")
    return start, successors, {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_FIRST_SELECTED_ANCHORED_TAR_SUCCESSOR_WALK",
        "source_revision": metadata["source_revision"],
        "source_metadata_sha256": metadata["source_metadata_sha256"],
        "prior_first_selected_header_match_proven_in_separate_host_report": True,
        "prior_second_selected_prediction_invalid_header": True,
        "frozen_selected_count": len(selected),
        "source_metadata_wav_count": len(ordered),
        "metadata_members_strictly_between_selected": second_index - anchor_index - 1,
        "planned_successor_headers": count,
        "hard_max_successors_per_invocation": MAX_SUCCESSOR_REQUESTS,
        "application_read_cap_per_request_bytes": tar_walk.MAX_READ_BYTES,
        "absolute_offsets_and_member_names_disclosed": False,
        "network_requests_executed": 0,
        "wav_payloads_recovered": 0,
        "actual_archive_order_verified": False,
        "selected_second_actual_offset_found": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def inspect_successors(start: int, expected: list[tuple[str, int]]) -> dict:
    """No network unless caller explicitly requests; stop on first discrepancy."""
    if (type(start) is not int or start < 0 or start % tar_walk.PROBE_BYTES
            or start + tar_walk.PROBE_BYTES > tar_walk.EXPECTED_TAR_BYTES
            or not isinstance(expected, list)
            or not 1 <= len(expected) <= MAX_SUCCESSOR_REQUESTS
            or len({n for n, _ in expected}) != len(expected)):
        raise ValueError("Invalid bounded TAR successor inputs")
    for name, size in expected:
        if (not isinstance(name, str) or not name.startswith("data/")
                or ".." in name.split("/") or not name.lower().endswith(".wav")
                or type(size) is not int or not 44 <= size <= 10_000_000):
            raise ValueError("Unsafe expected TAR member")
    attempts = matched = 0
    position = start
    classification = "ALL_REQUESTED_SUCCESSOR_HEADERS_MATCH"
    for name, size in expected:
        attempts += 1
        block = tar_walk.fetch_header(position)
        if block == bytes(tar_walk.PROBE_BYTES):
            classification = "UNEXPECTED_ZERO_TAR_BLOCK"
            break
        try:
            info = tarfile.TarInfo.frombuf(
                block, encoding="utf-8", errors="surrogateescape"
            )
        except (tarfile.TarError, ValueError, UnicodeError):
            classification = "INVALID_TAR_HEADER_IN_ANCHORED_CHAIN"
            break
        if not info.isfile():
            classification = "NON_REGULAR_OR_AUXILIARY_TAR_HEADER"
            break
        if info.name != name:
            classification = "MEMBER_NAME_ORDER_DIVERGED"
            break
        if info.size != size:
            classification = "MEMBER_SIZE_METADATA_DIVERGED"
            break
        matched += 1
        next_header = position + tar_walk.PROBE_BYTES + ceil_to(
            info.size, tar_walk.PROBE_BYTES
        )
        if (next_header <= position or
                next_header + tar_walk.PROBE_BYTES > tar_walk.EXPECTED_TAR_BYTES):
            classification = "SUCCESSOR_NEXT_HEADER_OUTSIDE_PINNED_TAR"
            break
        position = next_header
    success = attempts == len(expected) and matched == len(expected)
    return {
        "requested_successor_headers": len(expected),
        "headers_attempted": attempts,
        "exact_member_name_size_type_matches": matched,
        "all_requested_successors_match": success,
        "classification": classification,
        "actual_second_selected_header_position_verified": False,
        "full_archive_member_order_verified": False,
        "wav_payloads_downloaded": 0,
        "CP4": "BLOCKED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--workspace", type=Path, required=True)
    p.add_argument("--execute-anchored-successors", action="store_true",
                   help="Opt in to at most 4 strict 206-only TAR header GETs")
    p.add_argument("--max-successors", type=int, default=DEFAULT_SUCCESSORS)
    args = p.parse_args()
    try:
        start, expected, report = anchored_plan(args.workspace, args.max_successors)
        if args.execute_anchored_successors:
            outcome = inspect_successors(start, expected)
            report["network_requests_executed"] = outcome["headers_attempted"]
            report["observed"] = outcome
            report["status"] = (
                "BOUNDED_ANCHORED_HEADERS_MATCH_NOT_FULL_TAR"
                if outcome["all_requested_successors_match"] else
                "BOUNDED_ANCHORED_HEADER_MISMATCH_STOP"
            )
            rc = 0 if outcome["all_requested_successors_match"] else 3
        else:
            report["status"] = "OFFLINE_ONLY_NO_HTTP"
            rc = 0
        print(json.dumps(report, indent=2))
        print("ANCHOR CHAIN ONLY | ZERO WAV PAYLOAD | CP4 BLOCKED")
        return rc
    except tar_walk.RangeNotHonored:
        print("HTTP_RANGE_NOT_HONORED_ZERO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, UnicodeError,
            tarfile.TarError):
        print("ERROR: T10 anchored walk refused", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
