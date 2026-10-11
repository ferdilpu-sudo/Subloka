#!/usr/bin/env python3
"""T10: diagnose the repeatedly mismatched SECOND selected TAR header.

OFFLINE by default. --inspect-second-header explicitly performs exactly ONE
512-byte HTTP Range read at the previously failing second selected candidate
offset using the existing fail-closed pinned 206-only reader. Classify the TAR
header in memory, without printing its name, bytes, offset, transcript, label,
or exporting an index. Never access WAV payloads or automatically retry.
A diagnosis is not proof of 9500-member order, WAV integrity, or CP4 readiness.
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
import t10_atika_selected_header_check as selected_check
import t10_atika_tar_header_walk as tar_walk
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import (
    METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file,
)

FAILED_SELECTED_ORDINAL = 2
ONE_HEADER_MAX_REQUESTS = 1


def category_catalogue(workspace: Path, expected_count: int) -> dict[str, int]:
    """Read only the immutable publisher CSV; fail closed on duplicates."""
    require_private_workspace(workspace)
    p = workspace / METADATA_FILENAME
    if (not p.is_file() or p.is_symlink() or p.stat().st_size > MAX_METADATA_BYTES):
        raise ValueError("Pinned metadata missing or unsafe")
    if sha256_file(p) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Pinned source digest mismatch")
    catalogue = {}
    with p.open(encoding="utf-8-sig", newline="") as stream:
        rows = csv.DictReader(stream)
        if not REQUIRED.issubset(rows.fieldnames or []):
            raise ValueError("Pinned publisher CSV fields missing")
        for row in rows:
            if row["category"] != CATEGORY:
                continue
            name = row["audio_path"]
            try:
                size = int(row["file_size_bytes"].replace(",", ""))
            except (ValueError, TypeError, AttributeError):
                raise ValueError("Invalid WAV size in publisher metadata") from None
            if (not isinstance(name, str) or not name.startswith("data/")
                    or ".." in name.split("/") or not name.lower().endswith(".wav")
                    or name in catalogue or not 44 <= size <= MAX_CATEGORY_SOURCE_WAV_BYTES):
                raise ValueError("Duplicate or unsafe publisher WAV member")
            catalogue[name] = size
            if len(catalogue) > MAX_CATEGORY_ROWS:
                raise ValueError("Publisher category count beyond policy cap")
    if len(catalogue) != expected_count:
        raise ValueError("Pinned category count changed during diagnosis")
    if sha256_file(p) != tar_walk.PINNED_METADATA_SHA:
        raise ValueError("Pinned metadata changed during diagnosis")
    return catalogue


def classify_observed_header(raw: bytes, expected_name: str, expected_size: int,
                             catalogue: dict[str, int]) -> dict:
    """Return ONLY an aggregate diagnostic enum; never expose raw TAR fields."""
    if (not isinstance(raw, bytes) or len(raw) != tar_walk.PROBE_BYTES
            or not isinstance(expected_name, str)
            or type(expected_size) is not int or expected_size < 44
            or expected_name not in catalogue
            or catalogue[expected_name] != expected_size
            or not isinstance(catalogue, dict)):
        raise ValueError("Invalid pinned diagnostic inputs")
    if raw == bytes(tar_walk.PROBE_BYTES):
        classification = "ZERO_TAR_BLOCK_AT_PREDICTED_HEADER"
    else:
        try:
            info = tarfile.TarInfo.frombuf(
                raw, encoding="utf-8", errors="surrogateescape"
            )
        except (tarfile.TarError, ValueError, UnicodeError):
            classification = "INVALID_TAR_HEADER_AT_PREDICTED_OFFSET"
        else:
            if info.name == expected_name:
                if not info.isfile():
                    classification = "EXPECTED_NAME_IS_NOT_A_REGULAR_FILE"
                elif info.size != expected_size:
                    classification = "EXPECTED_NAME_BUT_SIZE_DIFFERS"
                else:
                    classification = "EXPECTED_HEADER_MATCHES_ON_RECHECK"
            elif not info.isfile():
                classification = "OTHER_TAR_MEMBER_NON_REGULAR_OR_AUXILIARY"
            elif info.name in catalogue:
                classification = (
                    "OTHER_PINNED_WAV_AT_OFFSET_NAME_AND_SIZE_VALID"
                    if info.size == catalogue[info.name]
                    else "OTHER_PINNED_WAV_AT_OFFSET_SIZE_DIFFERS"
                )
            else:
                classification = "REGULAR_TAR_MEMBER_NOT_IN_PINNED_IMPERATIVE_CSV"
    return {
        "diagnostic_classification": classification,
        "header_at_predicted_offset_equals_expected": (
            classification == "EXPECTED_HEADER_MATCHES_ON_RECHECK"
        ),
        "entire_tar_order_verified": False,
        "selected_30_headers_verified": False,
        "wav_payloads_recovered": 0,
        "CP4": "BLOCKED",
    }


def diagnosis_plan(workspace: Path) -> tuple[tuple[int, int, str, int], dict]:
    """Perform all pinned checks before any optional request."""
    candidates, base = selected_check.prepare(workspace)
    if len(candidates) != 30:
        raise ValueError("Selected count is not 30")
    catalogue = category_catalogue(
        workspace, int(base["category_wav_metadata_rows"])
    )
    target = candidates[FAILED_SELECTED_ORDINAL - 1]
    if (target[2] not in catalogue or catalogue[target[2]] != target[3]
            or type(target[1]) is not int
            or target[1] % tar_walk.PROBE_BYTES
            or target[1] < 0
            or target[1] + tar_walk.PROBE_BYTES > tar_walk.EXPECTED_TAR_BYTES):
        raise ValueError("Previously failed target is not within pinned catalogue")
    return target, {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_SELECTED_SECOND_HEADER_MISMATCH_DIAGNOSTIC",
        "source_revision": base["source_revision"],
        "source_metadata_sha256": base["source_metadata_sha256"],
        "target_selected_header_ordinal": FAILED_SELECTED_ORDINAL,
        "previous_remote_reports": "TWO_RUNS_EACH_2_REQUESTS_1_MATCH_1_MISMATCH",
        "category_rows": len(catalogue),
        "frozen_selected": len(candidates),
        "predicted_header_offset_printed": False,
        "selected_member_name_printed": False,
        "network_request_limit": ONE_HEADER_MAX_REQUESTS,
        "http_body_read_cap_bytes": tar_walk.MAX_READ_BYTES,
        "network_requests_executed": 0,
        "wav_payloads_recovered": 0,
        "full_tar_order_verified": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--inspect-second-header", action="store_true",
                        help="Deliberate ONE 512-byte remote TAR header read, no WAV")
    args = parser.parse_args()
    try:
        target, report = diagnosis_plan(args.workspace)
        if args.inspect_second_header:
            catalogue = category_catalogue(
                args.workspace, report["category_rows"]
            )
            header = tar_walk.fetch_header(target[1])
            report["network_requests_executed"] = 1
            result = classify_observed_header(
                header, target[2], target[3], catalogue
            )
            report["diagnosis"] = result
            report["status"] = "SINGLE_HEADER_CLASSIFIED_NOT_FULL_INDEX"
            rc = 0 if result["header_at_predicted_offset_equals_expected"] else 3
        else:
            report["status"] = "OFFLINE_ONLY_NO_HTTP"
            rc = 0
        print(json.dumps(report, indent=2))
        print("DIAGNOSTIC ONLY | ZERO WAV/TAR PAYLOAD | CP4 BLOCKED")
        return rc
    except tar_walk.RangeNotHonored:
        print("HTTP_RANGE_IGNORED_NO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, csv.Error,
            UnicodeError, tarfile.TarError):
        print("ERROR: T10 mismatch diagnosis refused safely", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
