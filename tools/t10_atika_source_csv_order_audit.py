#!/usr/bin/env python3
"""T10 archival order hypothesis: source CSV row order versus witnessed TAR prefix.

OFFLINE ONLY. Uses immutable category CSV (SHA-pinned) and the previously
reported eighth TAR member identity relative to the lexical catalogue (+152).
This checks whether CSV source row order *could* explain seven matching
successors and a divergent eighth. Does not fetch TAR/WAV, write a new index,
print audio paths, or assert a publisher packager order. Private metadata stays
in the gitignored workspace. An observed match is necessary, NOT sufficient,
to prove TAR order. T10/CP4 remain blocked.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path
import sys

from t10_atika_acquisition_budget import CATEGORY, MAX_CATEGORY_ROWS
from t10_atika_eighth_successor_anonymous_diagnostic import diagnosis_plan
from t10_id_independent_holdout import require_private_workspace
import t10_atika_tar_header_walk as tar_walk
from t10_public_id_corpus import METADATA_FILENAME, MAX_METADATA_BYTES, REQUIRED, sha256_file

OBSERVED_EIGHTH_LEXICAL_DISTANCE_LATER = 152
CONFIRMED_PRIOR_SUCCESSORS = 7


def audit(workspace: Path) -> dict:
    require_private_workspace(workspace)
    # Re-derive the previously observed eighth's identity *in memory* using
    # the user-observed +152 rank, NOT guesses about individual archive offsets.
    _, eighth_expected, eighth_size, catalogue, pinned = diagnosis_plan(workspace)
    ordered = sorted(catalogue)
    expected_index = ordered.index(eighth_expected)
    anchor_index = expected_index - (CONFIRMED_PRIOR_SUCCESSORS + 1)
    observed_index = expected_index + OBSERVED_EIGHTH_LEXICAL_DISTANCE_LATER
    if (anchor_index < 0 or observed_index >= len(ordered)
            or catalogue[eighth_expected] != eighth_size
            or len(catalogue) > MAX_CATEGORY_ROWS):
        raise ValueError("Observed eighth relative rank outside pinned catalogue")
    previously_matching = ordered[anchor_index:expected_index]
    if len(previously_matching) != CONFIRMED_PRIOR_SUCCESSORS + 1:
        raise ValueError("Previously observed selected first plus seven missing")
    observed_eighth = ordered[observed_index]

    metadata = workspace / METADATA_FILENAME
    if (not metadata.is_file() or metadata.is_symlink()
            or metadata.stat().st_size > MAX_METADATA_BYTES
            or sha256_file(metadata) != tar_walk.PINNED_METADATA_SHA):
        raise ValueError("Pinned metadata SHA differs")
    source_order: list[str] = []
    with metadata.open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if not REQUIRED.issubset(reader.fieldnames or []):
            raise ValueError("Publisher CSV schema invalid")
        for row in reader:
            if row["category"] == CATEGORY:
                name = row["audio_path"]
                try:
                    size = int(row["file_size_bytes"].replace(",", ""))
                except (AttributeError, ValueError, TypeError):
                    raise ValueError("Invalid publisher source size") from None
                if name not in catalogue or catalogue[name] != size:
                    raise ValueError("Publisher source row differs from pinned catalogue")
                source_order.append(name)
                if len(source_order) > MAX_CATEGORY_ROWS:
                    raise ValueError("Publisher category source CSV over cap")
    if (len(source_order) != len(catalogue)
            or len(set(source_order)) != len(catalogue)
            or sha256_file(metadata) != tar_walk.PINNED_METADATA_SHA):
        raise ValueError("Publisher CSV mutated or contains duplicate rows")

    # Compare the observed header prefix against row order. These are
    # hypotheses only; they do not establish TAR packager behavior.
    row_indices = {name: i for i, name in enumerate(source_order)}
    row_anchor = row_indices[previously_matching[0]]
    prefix = source_order[row_anchor:row_anchor+len(previously_matching)]
    seven_follow_in_csv = prefix == previously_matching
    next_in_csv = (source_order[row_anchor+len(previously_matching)]
                   if row_anchor+len(previously_matching) < len(source_order)
                   else None)
    observed8_follows_in_csv = next_in_csv == observed_eighth

    return {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_SOURCE_CSV_ORDER_HYPOTHESIS_OFFLINE",
        "source_revision": pinned["source_revision"],
        "source_metadata_sha256": pinned["source_metadata_sha256"],
        "catalogue_wav_members": len(catalogue),
        "frozen_selected_count": pinned["frozen_selected_count"],
        "previous_matching_header_positions": len(previously_matching),
        "eighth_actual_member_identified_by_prior_anonymous_rank": True,
        "observed_eighth_member_catalogue_rank_direction": "LATER",
        "observed_eighth_member_catalogue_rank_distance":
            OBSERVED_EIGHTH_LEXICAL_DISTANCE_LATER,
        "source_csv_order_first_eight_match_prior_header_prefix":
            seven_follow_in_csv,
        "source_csv_next_row_matches_observed_eighth":
            observed8_follows_in_csv,
        "source_csv_contiguous_prefix_and_eighth_consistent":
            seven_follow_in_csv and observed8_follows_in_csv,
        "source_csv_order_is_authoritative_tar_order": False,
        "publisher_packager_order_verified": False,
        "actual_selected_second_offset_verified": False,
        "full_tar_order_verified": False,
        "member_names_offsets_transcripts_printed": False,
        "network_requests_executed": 0,
        "wav_payloads_downloaded": 0,
        "files_written": False,
        "status": "OFFLINE_ORDER_HYPOTHESIS_ONLY_NO_HTTP",
        "T10": "ACTIVE", "CP4": "BLOCKED", "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = audit(args.workspace)
        print(json.dumps(result, indent=2))
        print("CSV ORDER HYPOTHESIS ONLY | ZERO HTTP | ZERO WAV | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError):
        print("ERROR: pinned CSV order audit refused", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
