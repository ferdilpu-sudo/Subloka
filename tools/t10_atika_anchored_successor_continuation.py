#!/usr/bin/env python3
"""T10: OFFLINE-default continuation after six USER-REPORTED matched successors.

Two user-reported remote runs verified successors 1..3 and 4..6 after the
first selected TAR member. This tool relies on that observation; it DOES NOT recheck
those headers. It computes the next candidate from immutable pinned metadata
and the earlier bounded live continuation observed successor 7 matching and
successor 8 differing in name. Network continuation is now fail-closed even
with the old opt-in flag: never replay stale positions. A separate one-header
anonymous diagnosis may be undertaken deliberately after offline QA.
Never reads WAV payload, writes files or exposes names, transcripts or offsets.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from t10_atika_anchored_successor_walk import inspect_successors  # synthetic regression only
from t10_atika_selected_header_check import prepare
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
from t10_atika_tar_layout_budget import ceil_to
import t10_atika_tar_header_walk as walk
from t10_id_independent_holdout import require_private_workspace

PRIOR_VERIFIED_SUCCESSORS = 6
DEFAULT_NEW_SUCCESSORS = 3
HARD_CAP_NEW_SUCCESSORS = 3


def continuation_plan(workspace: Path, count: int):
    """Zero network. Pinned metadata plus witnessed checkpoint only."""
    require_private_workspace(workspace)
    if type(count) is not int or not 1 <= count <= HARD_CAP_NEW_SUCCESSORS:
        raise ValueError("Successor continuation limit must be 1..3")
    selected, preflight = prepare(workspace)
    catalogue = category_catalogue(
        workspace, int(preflight["category_wav_metadata_rows"])
    )
    ordered = sorted(catalogue)
    first, second = selected[0], selected[1]
    first_index, first_offset, first_name, first_size = first
    second_index = second[0]
    if (len(selected) != 30 or
            len(ordered) != int(preflight["category_wav_metadata_rows"]) or
            ordered[first_index] != first_name or
            catalogue[first_name] != first_size or
            second_index <= first_index + PRIOR_VERIFIED_SUCCESSORS + count):
        raise ValueError("Frozen first-to-second selected interval too short")
    # Only the first selected header plus six immediate successors have
    # been observed in separate user-reported live probes. For those seven,
    # publisher-declared size matched the remote TAR header size; recompute
    # the next *candidate* without repeating any earlier header request.
    prior_names = ordered[first_index+1:first_index+1+PRIOR_VERIFIED_SUCCESSORS]
    if len(prior_names) != PRIOR_VERIFIED_SUCCESSORS:
        raise ValueError("Missing previously verified metadata successors")
    position = first_offset + walk.PROBE_BYTES + ceil_to(
        first_size, walk.PROBE_BYTES
    )
    for name in prior_names:
        position += walk.PROBE_BYTES + ceil_to(catalogue[name], walk.PROBE_BYTES)
    if (position < 0 or position % walk.PROBE_BYTES or
            position + walk.PROBE_BYTES > walk.EXPECTED_TAR_BYTES):
        raise ValueError("Continuation candidate outside pinned source TAR")
    start_index = first_index + PRIOR_VERIFIED_SUCCESSORS + 1
    wanted = ordered[start_index:start_index+count]
    if (len(wanted) != count or
            any(not isinstance(n,str) or n not in catalogue for n in wanted)):
        raise ValueError("Invalid bounded continuation candidates")
    expected = [(name, catalogue[name]) for name in wanted]
    report = {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_ANCHORED_SIX_MATCHED_CONTINUATION",
        "source_revision": preflight["source_revision"],
        "source_metadata_sha256": preflight["source_metadata_sha256"],
        "frozen_selected_count": len(selected),
        "source_metadata_wav_count": len(ordered),
        "previous_remote_matched_first_selected_from_user_report": True,
        "previous_remote_matched_successors_from_user_report":
            PRIOR_VERIFIED_SUCCESSORS,
        "previous_matched_headers_rechecked_this_run": False,
        "prior_remote_report_not_cryptographically_reverified": True,
        "new_successor_ordinals_after_first_selected": list(range(
            PRIOR_VERIFIED_SUCCESSORS+1,
            PRIOR_VERIFIED_SUCCESSORS+count+1
        )),
        "new_header_request_hard_cap": HARD_CAP_NEW_SUCCESSORS,
        "per_request_body_read_cap_bytes": walk.MAX_READ_BYTES,
        "member_names_or_offsets_disclosed": False,
        "network_requests_executed": 0,
        "wav_payloads_recovered": 0,
        "full_archive_order_verified": False,
        "actual_second_selected_offset_found": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }
    return position, expected, report


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--execute-new-successors", action="store_true",
                        help="Opt-in max 3 NEW strict 206-only 512-byte Range reads")
    parser.add_argument("--max-new-successors", type=int,
                        default=DEFAULT_NEW_SUCCESSORS)
    args = parser.parse_args()
    try:
        position, expected, report = continuation_plan(
            args.workspace, args.max_new_successors
        )
        if args.execute_new_successors:
            # Live Windows found successor 7 matching and successor 8
            # containing a valid, different regular TAR member. Do not
            # reprobe 7/8 or skip ahead to 9 using stale assumptions.
            # A separate single-header anonymized classifier is available.
            report["status"] = "HALTED_AFTER_OBSERVED_SUCCESSOR_8_NAME_ORDER_DIVERGENCE"
            report["successor_7_previously_observed_match"] = True
            report["successor_8_previously_observed_name_mismatch"] = True
            report["new_remote_retries_blocked"] = True
            report["network_requests_executed"] = 0
            rc = 3
        else:
            report["status"] = "OFFLINE_ONLY_NO_HTTP"
            rc = 0
        print(json.dumps(report, indent=2))
        print("CONTINUATION HEADER ONLY | NO WAV | CP4 BLOCKED")
        return rc
    except walk.RangeNotHonored:
        print("RANGE_IGNORED_NO_BODY_READ | CP4 BLOCKED", file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("ERROR: T10 six-successor continuation refused", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
