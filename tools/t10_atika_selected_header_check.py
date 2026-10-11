#!/usr/bin/env python3
"""T10 frozen 30 selected TAR header checks; OFFLINE unless explicitly enabled.

The candidate positions are derived exclusively from the pinned publisher CSV
and the immutable 30-case selection. Remote mode makes at most 1..30 exact
512-byte HTTPS TAR HEADER Range requests. Zero WAV/TAR payload downloads,
disk writes, model runs, or private path/offset disclosures.

Positive checks validate individual observed headers at candidate offsets,
NOT the full 9500-member order, speaker consent, or the WAV bytes.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys
import tarfile

from t10_atika_acquisition_budget import CATEGORY, MAX_CATEGORY_ROWS, MAX_SELECTED
import t10_atika_selected_header_preflight as prep
import t10_atika_tar_header_walk as tar_walk
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file,
)

DEFAULT_LIMIT = 5
MAX_HEADER_REQUESTS = MAX_SELECTED


def prepare(workspace: Path) -> tuple[list[tuple[int, int, str, int]], dict]:
    """No HTTP. Revalidates full frozen selection and pinned local metadata."""
    require_private_workspace(workspace)
    base = prep.preflight(workspace)
    if (base["frozen_selected_human_test_count"] != MAX_SELECTED
            or base["candidate_header_locations"] != MAX_SELECTED
            or base["network_requests_executed"] != 0):
        raise ValueError("Selected 30 offline preflight did not succeed")
    selected = tar_walk.load_selection(workspace)
    csv_path = workspace / METADATA_FILENAME
    if (not csv_path.is_file() or csv_path.is_symlink()
            or csv_path.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Missing or unsafe pinned CSV")
    rows = []
    with csv_path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Publisher CSV fields missing")
        for row in reader:
            if row["category"] == CATEGORY:
                try:
                    size = int(row["file_size_bytes"].replace(",", ""))
                except (TypeError, AttributeError, ValueError):
                    raise ValueError("Publisher WAV size invalid") from None
                rows.append((row["audio_path"], size))
                if len(rows) > MAX_CATEGORY_ROWS:
                    raise ValueError("Publisher WAV category cap exceeded")
    if sha256_file(csv_path) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Publisher CSV changed during read")
    candidates = prep.predicted_selected_headers(
        rows, selected, tar_walk.EXPECTED_TAR_BYTES
    )
    if (len(candidates) != MAX_SELECTED
            or sum(sz for _, _, _, sz in candidates)
            != base["selected_wav_bytes_from_publisher_metadata_only"]):
        raise ValueError("Selected candidates inconsistent with pinned preflight")
    return candidates, base


def validate_headers(candidates: list[tuple[int, int, str, int]],
                     limit: int) -> dict:
    """Check at most limit sorted selected headers; stop at the first mismatch.

    Caller must have run prepare(). This routine returns aggregate evidence only.
    """
    if (type(limit) is not int or not 1 <= limit <= MAX_HEADER_REQUESTS
            or len(candidates) != MAX_SELECTED):
        raise ValueError("Invalid bounded selected TAR header request count")
    previous_idx = -1
    previous_offset = -1
    known_paths = set()
    # Validate the ENTIRE candidate batch before the first network call.
    for candidate in candidates:
        if not isinstance(candidate, tuple) or len(candidate) != 4:
            raise ValueError("Bad selected header candidate")
        index, offset, name, size = candidate
        if (type(index) is not int or index <= previous_idx
                or type(offset) is not int or offset <= previous_offset
                or offset % tar_walk.PROBE_BYTES
                or offset < 0 or offset + tar_walk.PROBE_BYTES > tar_walk.EXPECTED_TAR_BYTES
                or not isinstance(name, str) or not name.startswith("data/")
                or ".." in name.split("/") or not name.lower().endswith(".wav")
                or name in known_paths or type(size) is not int
                or not 44 <= size <= 10_000_000):
            raise ValueError("Unsafe selected header candidate")
        previous_idx, previous_offset = index, offset
        known_paths.add(name)

    attempted = matched = 0
    for _, offset, name, size in candidates[:limit]:
        attempted += 1  # Count the request even if the network aborts.
        header = tar_walk.fetch_header(offset)
        if header == bytes(tar_walk.PROBE_BYTES):
            break
        try:
            info = tarfile.TarInfo.frombuf(
                header, encoding="utf-8", errors="surrogateescape"
            )
        except (tarfile.TarError, ValueError, UnicodeError):
            break
        if not (info.isfile() and info.name == name and info.size == size):
            break
        matched += 1

    all_requested_match = matched == limit
    return {
        "headers_requested_limit": limit,
        "headers_attempted": attempted,
        "exact_name_size_and_type_matches": matched,
        "all_requested_selected_headers_match": all_requested_match,
        "all_30_selected_headers_match": all_requested_match and limit == MAX_SELECTED,
        "result": (
            "REQUESTED_SELECTED_HEADERS_MATCH_NOT_AUDIO"
            if all_requested_match else "SELECTED_HEADER_MISMATCH_STOP"
        ),
        "full_tar_order_verified": False,
        "wav_payloads_downloaded": 0,
        "audio_integrity_verified": False,
        "CP4": "BLOCKED",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--execute-selected-headers", action="store_true",
                        help="Explicit remote 512-byte header reads, never WAV payloads")
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT,
                        help="At most this many of 30; default 5, hard cap 30")
    args = parser.parse_args()
    if not 1 <= args.limit <= MAX_HEADER_REQUESTS:
        parser.error("--limit must be 1..30")
    try:
        candidates, base = prepare(args.workspace)
        report = {
            "schema_version": 1,
            "checkpoint": "PUBLIC_IMPERATIVE_FROZEN_SELECTED_30_HEADER_CHECK_ONLY",
            "source_revision": base["source_revision"],
            "source_metadata_sha256": base["source_metadata_sha256"],
            "frozen_selected_human_test_count": MAX_SELECTED,
            "candidate_header_count": len(candidates),
            "hypothesis": base["candidate_order"],
            "request_limit": args.limit,
            "maximum_allowed_header_requests": MAX_HEADER_REQUESTS,
            "per_request_http_body_read_cap_bytes": tar_walk.MAX_READ_BYTES,
            "hypothetical_offset_values_disclosed": False,
            "network_requests_executed": 0,
            "actual_selected_header_matches": 0,
            "all_30_selected_header_offsets_checked": False,
            "global_tar_member_order_verified": False,
            "wav_payloads_downloaded": 0,
            "files_written": False,
            "source_audio_sha_verified": False,
            "CP4": "BLOCKED",
            "T10": "ACTIVE",
            "T11": "TODO",
        }
        if args.execute_selected_headers:
            result = validate_headers(candidates, args.limit)
            report["check"] = result
            report["network_requests_executed"] = result["headers_attempted"]
            report["actual_selected_header_matches"] = result["exact_name_size_and_type_matches"]
            report["all_30_selected_header_offsets_checked"] = result[
                "all_30_selected_headers_match"
            ]
            rc = 0 if result["all_requested_selected_headers_match"] else 3
        else:
            report["status"] = "OFFLINE_PREFLIGHT_ONLY_NO_HTTP"
            rc = 0
        print(json.dumps(report, indent=2))
        print("HEADER ONLY | ZERO WAV PAYLOAD | CP4 BLOCKED")
        return rc
    except tar_walk.RangeNotHonored:
        print("RANGE_IGNORED_ZERO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, KeyError, TypeError, csv.Error,
            UnicodeError, tarfile.TarError):
        # Keep selected publisher member names/offsets out of terminal logs.
        print("ERROR: T10 selected-header check failed closed", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
