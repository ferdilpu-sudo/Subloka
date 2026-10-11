#!/usr/bin/env python3
"""T10 offline USTAR path-name feasibility for pinned public WAV metadata.

The prior Windows gap audit found 40/40 path names >100 UTF-8 bytes between
the first matching and second invalid selected TAR header. USTAR supports a
100-byte basename AND a 155-byte path prefix, so >100 alone does not imply
GNU LongLink or PAX records. Test actual Python USTAR serialization feasibility
without reading TAR data, downloading WAVs, printing path names, or writing files.

Serialization compatibility DOES NOT reveal the publisher's actual TAR format.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys
import tarfile

from t10_atika_selected_header_check import prepare
from t10_atika_selected_header_mismatch_diagnostic import category_catalogue
from t10_id_independent_holdout import require_private_workspace

MAX_CATEGORY = 25000
TARGET_FIRST_SELECTED_ORDINAL = 1
TARGET_SECOND_SELECTED_ORDINAL = 2


def ustar_path_fits(name: str) -> bool:
    """Can a single USTAR file header exactly encode and decode this name?"""
    if (not isinstance(name, str) or not name.startswith("data/")
            or "\x00" in name or ".." in name.split("/")
            or not name.lower().endswith(".wav")):
        raise ValueError("Unsafe publisher member name")
    try:
        header = tarfile.TarInfo(name).tobuf(
            format=tarfile.USTAR_FORMAT,
            encoding="utf-8",
            errors="strict",
        )
        if len(header) != tarfile.BLOCKSIZE:
            return False
        restored = tarfile.TarInfo.frombuf(
            header, encoding="utf-8", errors="strict"
        )
        return restored.name == name and restored.isfile()
    except (ValueError, UnicodeError, tarfile.TarError):
        return False


def check_path_capacity(names: list[str]) -> dict:
    """Aggregate only, no actual publisher names or constructed TAR headers."""
    if (not isinstance(names, list) or not 1 <= len(names) <= MAX_CATEGORY
            or any(not isinstance(name, str) for name in names)
            or len(names) != len(set(names))):
        raise ValueError("Invalid catalogue member set")
    short = extended_fits = extended_fails = 0
    for name in names:
        byte_len = len(name.encode("utf-8"))
        fits = ustar_path_fits(name)
        if byte_len <= 100:
            if not fits:
                raise ValueError("Unexpected short WAV name not USTAR serializable")
            short += 1
        elif fits:
            extended_fits += 1
        else:
            extended_fails += 1
    return {
        "metadata_names_total": len(names),
        "metadata_names_within_100_utf8_bytes": short,
        "metadata_names_over_100_ustar_serializable": extended_fits,
        "metadata_names_over_100_ustar_not_serializable": extended_fails,
        "metadata_names_over_100_utf8_bytes": extended_fits + extended_fails,
        "all_metadata_names_ustar_serializable": extended_fails == 0,
        "over_100_bytes_alone_requires_pax_or_gnu": False,
        "actual_source_TAR_format_known": False,
        "actual_extra_header_records_verified": False,
    }


def report(workspace: Path) -> dict:
    require_private_workspace(workspace)
    candidates, base = prepare(workspace)
    catalogue = category_catalogue(
        workspace, int(base["category_wav_metadata_rows"])
    )
    ordered = sorted(catalogue)
    first, second = candidates[:2]
    if (len(candidates) != 30 or first[0] >= second[0]
            or ordered[first[0]] != first[2] or ordered[second[0]] != second[2]):
        raise ValueError("Frozen selected interval changed")
    interval_names = ordered[first[0]:second[0]]
    all_summary = check_path_capacity(ordered)
    gap_summary = check_path_capacity(interval_names)
    if gap_summary["metadata_names_total"] != second[0] - first[0]:
        raise ValueError("Interval name count inconsistent")
    if all_summary["metadata_names_total"] != len(catalogue):
        raise ValueError("Category name count inconsistent")
    return {
        "schema_version": 1,
        "checkpoint": "T10_ATIKA_USTAR_PATH_FEASIBILITY_OFFLINE_ONLY",
        "source_revision": base["source_revision"],
        "source_metadata_sha256": base["source_metadata_sha256"],
        "source_wav_metadata_rows": len(ordered),
        "frozen_selected_count": len(candidates),
        "between_first_matching_and_second_invalid_candidates": gap_summary,
        "full_category_path_capacity": all_summary,
        "interpretation": (
            "USTAR name+prefix capacity is only an encoding feasibility check. "
            "It does not identify source TAR format, actual auxiliary records, "
            "member order, offsets, or WAV byte integrity."
        ),
        "prior_second_selected_candidate_status": "INVALID_TAR_HEADER_AT_PREDICTED_OFFSET",
        "network_requests_executed": 0,
        "files_written": False,
        "wav_payloads_recovered": 0,
        "selected_30_actual_header_offsets_verified": False,
        "root_cause_of_header_mismatch_proven": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    args = parser.parse_args()
    try:
        print(json.dumps(report(args.workspace), indent=2))
        print("OFFLINE USTAR CAPACITY ONLY | NO HEADER FETCH | NO AUDIO | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, UnicodeError, tarfile.TarError):
        print("ERROR: T10 offline USTAR feasibility audit blocked", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
