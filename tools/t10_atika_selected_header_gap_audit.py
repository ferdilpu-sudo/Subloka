#!/usr/bin/env python3
"""T10 offline metadata gap audit between first matching and second invalid header.

In light of two remote selected checks and a one-header classification, the
flat-lexical TAR offset *at selected item 2* is no longer trustworthy.
Compute only the claimed 512-byte arithmetic for the metadata interval,
without accessing network, writing files, or printing participant paths or
individual candidate offsets. It does not identify the real TAR header.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from t10_atika_selected_header_check import prepare
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
from t10_atika_tar_layout_budget import TAR_BLOCK_BYTES, ceil_to
from t10_id_independent_holdout import require_private_workspace

EXPECTED_SELECTION_COUNT = 30
FIRST_MATCHED_SELECTED_ORDINAL = 1
SECOND_INVALID_SELECTED_ORDINAL = 2


def interval_metadata_arithmetic(
        selected: list[tuple[int, int, str, int]],
        size_by_name: dict[str, int],
) -> dict:
    """Offline-only counters. The only returned offset is a relative gap."""
    if not isinstance(selected, list) or len(selected) != EXPECTED_SELECTION_COUNT:
        raise ValueError("Expected frozen selected 30 candidates")
    if not isinstance(size_by_name, dict) or not 30 <= len(size_by_name) <= 25000:
        raise ValueError("Unexpected pinned catalogue")
    if (len(set(size_by_name)) != len(size_by_name)
            or any(not isinstance(k, str) or type(v) is not int or v < 44
                   for k, v in size_by_name.items())):
        raise ValueError("Invalid catalogue rows")
    keys = sorted(size_by_name)
    selected_names = set()
    for index, offset, name, size in selected:
        if (type(index) is not int or not 0 <= index < len(keys)
                or type(offset) is not int or offset < 0
                or offset % TAR_BLOCK_BYTES
                or not isinstance(name, str) or name in selected_names
                or keys[index] != name or size_by_name[name] != size):
            raise ValueError("Frozen selected candidate inconsistent with catalogue")
        selected_names.add(name)
    first, second = selected[:2]
    i0, start, _, _ = first
    i1, end, _, _ = second
    if i1 <= i0 or end <= start:
        raise ValueError("Selected first and second candidate out of order")
    covered_sizes = [size_by_name[name] for name in keys[i0:i1]]
    hypothetical_header_count = i1 - i0
    header_bytes = hypothetical_header_count * TAR_BLOCK_BYTES
    payload_bytes = sum(covered_sizes)
    padding_bytes = sum(ceil_to(n, TAR_BLOCK_BYTES) - n for n in covered_sizes)
    hypothetical_gap = header_bytes + payload_bytes + padding_bytes
    if hypothetical_gap != end - start:
        raise ValueError("Hypothetical first-to-second TAR gap arithmetic mismatched")
    # USTAR has a 100-byte name field, but names may also use the 155-byte
    # prefix field. Exceeding 100 bytes alone does not PROVE a PAX record.
    long_name_field_candidates = sum(
        len(k.encode("utf-8")) > 100 for k in keys[i0:i1]
    )
    return {
        "metadata_member_slots_from_first_to_before_second": hypothetical_header_count,
        "metadata_members_strictly_between_selected": i1 - i0 - 1,
        "metadata_payload_sum_in_interval_bytes": payload_bytes,
        "hypothetical_member_header_sum_bytes": header_bytes,
        "hypothetical_512_padding_sum_bytes": padding_bytes,
        "hypothetical_header_distance_bytes": hypothetical_gap,
        "metadata_names_over_100_utf8_bytes_in_interval": long_name_field_candidates,
        "metadata_name_length_proves_PAX_or_auxiliary_headers": False,
        "range_contains_actual_tar_header_chain_verified": False,
        "reason_for_invalid_second_header_proven": False,
    }


def report(workspace: Path) -> dict:
    require_private_workspace(workspace)
    candidates, base = prepare(workspace)
    catalogue = category_catalogue(
        workspace, int(base["category_wav_metadata_rows"])
    )
    gap = interval_metadata_arithmetic(candidates, catalogue)
    return {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_FIRST_MATCH_SECOND_INVALID_OFFLINE_METADATA_GAP_AUDIT",
        "source_revision": base["source_revision"],
        "source_metadata_sha256": base["source_metadata_sha256"],
        "category_wav_rows": len(catalogue),
        "frozen_selected": len(candidates),
        "prior_first_selected_header_remote_match": True,
        "prior_second_selected_predicted_block": "INVALID_TAR_HEADER_AT_PREDICTED_OFFSET",
        "prior_remote_diagnosis_reported_from_user_console": True,
        "disclaimer": "Published CSV arithmetic, not measured archive positions or actual WAV sizes",
        "metadata_interval": gap,
        "network_requests_executed": 0,
        "files_written": False,
        "WAV_payloads_downloaded": 0,
        "selected_30_offsets_verified": False,
        "global_TAR_order_verified": False,
        "root_cause_proven": False,
        "next_action": "DO_NOT_USE_GUESSED_SELECTED_OFFSETS; REQUIRE_DISTINCT_BOUNDED_CHAIN_OR_PUBLISHER_INDEX",
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    args = argparse.ArgumentParser(description=__doc__)
    args.add_argument("--workspace", type=Path, required=True)
    p = args.parse_args()
    try:
        print(json.dumps(report(p.workspace), indent=2))
        print("OFFLINE GAP AUDIT ONLY | NO HEADER NETWORK | NO WAV | CP4 BLOCKED")
        return 0
    except (ValueError, OSError, TypeError, KeyError, UnicodeError):
        print("ERROR: T10 offline TAR gap audit blocked", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
