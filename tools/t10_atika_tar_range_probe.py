#!/usr/bin/env python3
"""T10 Atika Imperative TAR remote HTTP byte-range FEASIBILITY ONLY.

Performs one bounded HTTPS GET asking for bytes=0-511 of pinned public TAR.
If server ignores Range and streams 865.7MiB file, detect status != 206
BEFORE body read and close. At most 513 response bytes read. No files written.
No model, ADB, selected-audio download, inference or CP4 promotion.

Probe does not supply member offsets, prove low-bandwidth access to all
30 selected WAVs, or authorize a large archive download.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import tarfile
import urllib.request

from t10_public_id_corpus import REVISION, ROOT_URL

CATEGORY = "Imperative"
EXPECTED_TAR_BYTES = 907_765_760
UPSTREAM_LFS_SHA256_UNVERIFIED = (
    "54725d7ecd573c6fbe88cc6d43337be3910599842dc1711b8e7f5fbae88dc938"
)
PROBE_BYTES = 512
MAX_READ_BYTES = PROBE_BYTES + 1
TAR_URL = (
    f"{ROOT_URL}/resolve/{REVISION}"
    "/data/audio_shards/by_category/Imperative.tar"
)


def inspect_range_response(response) -> dict:
    """Never read body unless a strict 206 Partial Content is received."""
    status = response.status
    result = {
        "schema_version": 1,
        "source_revision": REVISION,
        "category": CATEGORY,
        "pinned_archive_total_bytes_from_upstream_metadata": EXPECTED_TAR_BYTES,
        "publisher_lfs_sha256_NOT_LOCAL_VERIFIED": UPSTREAM_LFS_SHA256_UNVERIFIED,
        "request_range": "bytes=0-511",
        "network_response_status": status,
        "tar_range_206_verified": False,
        "payload_bytes_read_max": MAX_READ_BYTES,
        "audio_files_recovered": 0,
        "no_full_archive_download_or_model_inference": True,
        "not_a_30_clip_acquisition_plan": True,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }
    if not response.geturl().startswith("https://"):
        raise ValueError("Insecure URL redirect in ranged TAR request")
    if status != 206:
        result["result"] = "RANGE_NOT_HONORED_NO_BODY_READ"
        return result
    length_header = response.headers.get("Content-Length")
    if length_header is not None and length_header != str(PROBE_BYTES):
        raise ValueError("Unexpected range Content-Length; fail closed")
    content_range = response.headers.get("Content-Range", "").strip()
    match = re.fullmatch(r"bytes 0-511/([0-9]+)", content_range)
    if not match or int(match.group(1)) != EXPECTED_TAR_BYTES:
        raise ValueError("Incorrect Content-Range or pinned TAR byte total")
    sample = response.read(MAX_READ_BYTES)
    if len(sample) != PROBE_BYTES:
        raise ValueError("206 response did not contain exactly 512 header bytes")
    try:
        member = tarfile.TarInfo.frombuf(
            sample, encoding="utf-8", errors="surrogateescape"
        )
    except (tarfile.TarError, ValueError, UnicodeError) as exc:
        raise ValueError("First 512 bytes are not a checksummed TAR header") from exc
    if not member.name:
        raise ValueError("First TAR member header lacks name")
    # Do not display member name: source paths can contain participant identity.
    result["tar_range_206_verified"] = True
    result["result"] = "FIRST_512_TAR_HEADER_VALID_REMOTE_RANDOM_RANGE_POSSIBLE"
    result["first_member_data_bytes_declared_in_tar_header"] = member.size
    result["first_member_name_displayed"] = False
    result["round_trips_to_30_selected_wavs_not_measured"] = True
    return result


def probe() -> dict:
    req = urllib.request.Request(
        TAR_URL,
        headers={
            "Range": "bytes=0-511",
            "Accept-Encoding": "identity",
            "User-Agent": "Subloka-T10-TAR-first-header-range-probe/1",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        return inspect_range_response(response)


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.parse_args()
    try:
        result = probe()
        print(json.dumps(result, ensure_ascii=False, indent=2))
        print("NO FULL TAR | NO WAV SAVED | NO MODEL DOWNLOAD | NO ADB | NO INFERENCE | CP4 BLOCKED")
        return 0 if result["tar_range_206_verified"] else 2
    except (OSError, ValueError, TypeError, UnicodeError, tarfile.TarError) as exc:
        print("ERROR: T10 Atika TAR range probe:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
