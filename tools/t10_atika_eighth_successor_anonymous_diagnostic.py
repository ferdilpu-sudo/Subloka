#!/usr/bin/env python3
"""T10: anonymous diagnosis of the *known divergent eighth successor*.

The previous live user report: first selected + successors 1..7 matched;
successor 8 was a valid regular TAR member whose name differed from the
lexically sorted pinned metadata prediction. This tool is OFFLINE by default.
With deliberate opt-in, it re-reads ONLY that one previously divergent
512-byte TAR header (not the earlier verified headers) and anonymously
classifies its member identity against the SHA-pinned 9,500-WAV catalogue.
No WAV payload, archive download, persistent local file, member name,
transcript, label, absolute offset or raw TAR bytes are disclosed.
A recheck cannot erase the prior recorded order mismatch.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tarfile

import t10_atika_tar_header_walk as walk
from t10_atika_anchored_successor_continuation import continuation_plan
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
from t10_atika_tar_layout_budget import ceil_to

FIRST_DIVERGENCE_SUCCESSOR = 8
PRIOR_MATCHED_SUCCESSORS = 7
REQUEST_BUDGET = 1


def diagnosis_plan(workspace: Path):
    """Pin and validate all corpus data before any possible network request."""
    seventh_start, following, base = continuation_plan(workspace, 3)
    if (base["checkpoint"] != "T10_ATIKA_ANCHORED_SIX_MATCHED_CONTINUATION"
            or base["new_successor_ordinals_after_first_selected"] != [7, 8, 9]
            or base["frozen_selected_count"] != 30):
        raise ValueError("Stale/failing pinned earlier successor anchor")
    seventh_name, seventh_size = following[0]
    expected_eighth_name, expected_eighth_size = following[1]
    catalogue = category_catalogue(workspace, base["source_metadata_wav_count"])
    names = sorted(catalogue)
    expected_index = names.index(expected_eighth_name)
    if (expected_index < 1 or names[expected_index - 1] != seventh_name
            or expected_eighth_size != catalogue[expected_eighth_name]):
        raise ValueError("Eighth predicted header does not follow seventh")
    eighth_candidate = seventh_start + walk.PROBE_BYTES + ceil_to(
        seventh_size, walk.PROBE_BYTES
    )
    if (eighth_candidate % walk.PROBE_BYTES or eighth_candidate < 0
            or eighth_candidate + walk.PROBE_BYTES > walk.EXPECTED_TAR_BYTES):
        raise ValueError("Unsafe eighth successor candidate")
    return eighth_candidate, expected_eighth_name, expected_eighth_size, catalogue, {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_EIGHTH_SUCCESSOR_ANONYMOUS_ORDER_DIVERGENCE",
        "source_revision": base["source_revision"],
        "source_metadata_sha256": base["source_metadata_sha256"],
        "catalogue_wav_members": len(catalogue),
        "frozen_selected_count": base["frozen_selected_count"],
        "previous_reported_matched_successors": PRIOR_MATCHED_SUCCESSORS,
        "prior_eighth_successor_member_name_divergence_observed": True,
        "previous_mismatch_reclassified_as_pass": False,
        "one_header_max_network_requests": REQUEST_BUDGET,
        "per_request_body_read_cap_bytes": walk.MAX_READ_BYTES,
        "network_requests_executed": 0,
        "WAV_payloads_downloaded": 0,
        "prints_names_offsets_or_header_bytes": False,
        "actual_second_selected_position_verified": False,
        "full_archive_order_verified": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def classify(raw: bytes, expected_name: str, expected_size: int,
             catalogue: dict[str, int]) -> dict:
    """Compare exactly one returned TAR header against pinned public metadata."""
    if (not isinstance(raw, bytes) or len(raw) != walk.PROBE_BYTES
            or expected_name not in catalogue
            or catalogue[expected_name] != expected_size):
        raise ValueError("Invalid header classification inputs")
    result = {
        "observed_header_name_printed": False,
        "absolute_offset_printed": False,
        "raw_bytes_printed": False,
        "actual_second_selected_position_verified": False,
        "full_archive_order_verified": False,
        "WAV_payloads_downloaded": 0,
        "CP4": "BLOCKED",
    }
    if raw == bytes(walk.PROBE_BYTES):
        result["classification"] = "UNEXPECTED_ZERO_TAR_BLOCK_ON_RECHECK"
        return result
    try:
        info = tarfile.TarInfo.frombuf(
            raw, encoding="utf-8", errors="surrogateescape"
        )
    except (ValueError, UnicodeError, tarfile.TarError):
        result["classification"] = "INVALID_HEADER_ON_RECHECK_PREVIOUS_MISMATCH_STANDS"
        return result
    if not info.isfile():
        result["classification"] = "NON_REGULAR_OR_AUXILIARY_MEMBER_ON_RECHECK"
        return result
    if info.name == expected_name:
        result["classification"] = (
            "EXPECTED_MEMBER_ON_RECHECK_PRIOR_NAME_DIVERGENCE_UNRESOLVED"
            if info.size == expected_size else
            "EXPECTED_MEMBER_WITH_SIZE_DIFFERENCE_ON_RECHECK"
        )
        return result
    if info.name not in catalogue:
        result["classification"] = "REGULAR_MEMBER_OUTSIDE_PINNED_IMPERATIVE_CATALOGUE"
        return result
    result["classification"] = (
        "OTHER_PINNED_MEMBER_AT_EIGHTH_POSITION_SIZE_MATCHES"
        if info.size == catalogue[info.name] else
        "OTHER_PINNED_MEMBER_AT_EIGHTH_POSITION_SIZE_DIFFERS"
    )
    names = sorted(catalogue)
    delta = names.index(info.name) - names.index(expected_name)
    result["catalogue_relative_order_direction"] = (
        "EARLIER" if delta < 0 else "LATER"
    )
    result["catalogue_relative_order_distance"] = abs(delta)
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--inspect-eighth-header", action="store_true",
                        help="Deliberate ONE 512-byte strict-206 Range recheck")
    args = parser.parse_args()
    try:
        offset, name, size, catalogue, report = diagnosis_plan(args.workspace)
        if args.inspect_eighth_header:
            report["network_requests_executed"] = 1
            report["observed"] = classify(walk.fetch_header(offset),
                                           name, size, catalogue)
            report["status"] = "ONE_HEADER_CLASSIFIED_PREVIOUS_FAIL_STANDS"
            code = 3  # The previously observed mismatch always remains FAIL.
        else:
            report["status"] = "OFFLINE_ONLY_NO_HTTP"
            code = 0
        print(json.dumps(report, indent=2))
        print("EIGHTH ANONYMOUS HEADER DIAGNOSIS | NO WAV | CP4 BLOCKED")
        return code
    except walk.RangeNotHonored:
        print("HTTP_RANGE_NOT_HONORED_ZERO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, tarfile.TarError):
        print("ERROR: eighth TAR successor anonymous diagnostic refused",
              file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
