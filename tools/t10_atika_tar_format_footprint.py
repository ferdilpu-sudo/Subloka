#!/usr/bin/env python3
"""Offline comparison of Python USTAR, PAX and GNU TAR header footprints.

The pinned publisher CSV contains WAV names which all fit one USTAR header,
yet actual remote second-selected predicted header was invalid. Compare
counterfactual Python tarfile layouts, NOT source TAR writer/layout claims.
Does not inspect remote TAR, print private names/offsets, write files, or
download any audio.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tarfile

from t10_atika_selected_header_check import prepare
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
import t10_atika_tar_header_walk as walk
from t10_atika_tar_layout_budget import TAR_BLOCK_BYTES, ceil_to
from t10_id_independent_holdout import require_private_workspace

FORMATS = {"USTAR": tarfile.USTAR_FORMAT, "PAX": tarfile.PAX_FORMAT,
           "GNU": tarfile.GNU_FORMAT}
END_BLOCK_BYTES = 1024
RECORD_PAD_BYTES = 10240
MAX_ROWS = 25000


def footprint(rows: list[tuple[str, int]], archive_bytes: int, *,
              full_archive_comparison: bool = True) -> dict:
    """Only size aggregates: no absolute offsets, names or headers returned."""
    if (not isinstance(rows, list) or not 1 <= len(rows) <= MAX_ROWS
            or type(archive_bytes) is not int or archive_bytes < 1024
            or archive_bytes % TAR_BLOCK_BYTES):
        raise ValueError("Unsafe TAR comparison input")
    if len({name for name, _ in rows}) != len(rows):
        raise ValueError("Duplicated source member name")
    sums = {fmt: 0 for fmt in FORMATS}
    overhead_count = {fmt: 0 for fmt in FORMATS}
    payload = 0
    for name, size in rows:
        if (not isinstance(name, str) or not name.startswith("data/")
                or ".." in name.split("/") or "\x00" in name
                or not name.lower().endswith(".wav")
                or type(size) is not int or not 44 <= size <= 10_000_000):
            raise ValueError("Invalid publisher WAV metadata")
        payload += ceil_to(size, TAR_BLOCK_BYTES)
        for label, fmt in FORMATS.items():
            info = tarfile.TarInfo(name)
            info.size = size
            try:
                header = info.tobuf(format=fmt, encoding="utf-8", errors="strict")
            except (ValueError, UnicodeError, tarfile.TarError):
                raise ValueError("Pinned WAV name is not encodable in simulation") from None
            if (len(header) < TAR_BLOCK_BYTES or
                    len(header) % TAR_BLOCK_BYTES or len(header) > 16384):
                raise ValueError("Unexpected Python TAR header serialization size")
            sums[label] += len(header)
            if len(header) > TAR_BLOCK_BYTES:
                overhead_count[label] += 1
    result = {}
    for label in FORMATS:
        members_end = sums[label] + payload
        archive_record_padded = ceil_to(members_end + END_BLOCK_BYTES,
                                       RECORD_PAD_BYTES)
        result[label] = {
            "comparison_to_published_full_archive_applicable": full_archive_comparison,
            "simulated_member_header_bytes": sums[label],
            "names_that_triggered_extra_header_bytes": overhead_count[label],
            "extra_header_bytes_vs_one_512_per_WAV":
                sums[label] - len(rows) * TAR_BLOCK_BYTES,
            "simulated_archive_bytes_with_2_end_blocks_10240_padding":
                archive_record_padded,
            "simulated_archive_length_matches_pinned_public_size":
                (archive_record_padded == archive_bytes
                 if full_archive_comparison else None),
            "simulated_minus_pinned_archive_bytes":
                (archive_record_padded - archive_bytes
                 if full_archive_comparison else None),
            "actual_upstream_writer_or_format_verified": False,
        }
    return {
        "metadata_members": len(rows),
        "metadata_wav_payload_padded_512_bytes": payload,
        "python_tarfile_serialization_models": result,
        "models_compared_only_not_source_TAR_header_walk": True,
        "extra_headers_in_publisher_archive_verified": False,
    }


def report(workspace: Path) -> dict:
    require_private_workspace(workspace)
    selected, pinned = prepare(workspace)
    catalogue = category_catalogue(workspace,
                                  int(pinned["category_wav_metadata_rows"]))
    names = sorted(catalogue)
    if (len(selected) != 30 or selected[0][0] >= selected[1][0]
            or names[selected[0][0]] != selected[0][2]
            or names[selected[1][0]] != selected[1][2]):
        raise ValueError("Unexpected frozen selected first-second interval")
    entire = [(name, catalogue[name]) for name in names]
    gap = [(name, catalogue[name])
           for name in names[selected[0][0]:selected[1][0]]]
    return {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_TAR_FORMAT_FOOTPRINT_MODELS_OFFLINE",
        "source_revision": pinned["source_revision"],
        "source_metadata_sha256": pinned["source_metadata_sha256"],
        "published_TAR_bytes": walk.EXPECTED_TAR_BYTES,
        "frozen_selected_WAV_count": len(selected),
        "first_to_second_selected_interval": footprint(gap, walk.EXPECTED_TAR_BYTES,
                                                  full_archive_comparison=False),
        "entire_Imperative_category": footprint(entire, walk.EXPECTED_TAR_BYTES),
        "interpretation": (
            "Counterfactual Python tarfile header models only. Equal total size "
            "does not verify TAR packaging and unequal sizes do not rule out "
            "different WAV sizes, archive members, or TAR writers."
        ),
        "prior_second_selected_predicted_header_status":
            "INVALID_TAR_HEADER_AT_PREDICTED_OFFSET",
        "network_requests_executed": 0,
        "files_written": False,
        "WAV_payloads_downloaded": 0,
        "actual_tar_order_or_header_offsets_verified": False,
        "root_cause_proven": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--workspace", type=Path, required=True)
    args = ap.parse_args()
    try:
        print(json.dumps(report(args.workspace), indent=2))
        print("OFFLINE TAR HEADER FOOTPRINT MODELS | NO HTTP | NO WAV | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, tarfile.TarError,
            UnicodeError):
        print("ERROR: T10 TAR format footprint audit blocked", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
