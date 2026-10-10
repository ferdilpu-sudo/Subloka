#!/usr/bin/env python3
"""T10 Atika TAR bounded HEADER-ONLY offset-chain pilot.

Uses at most 8 HTTP 512-byte Range GETs (max 4,104 body bytes read),
follows real TAR file-header size/alignment, does not retrieve WAV payloads,
does not index entire 865.7MiB archive or authenticate data provenance.
HTTP 200 (Range ignored) reads ZERO bytes and stops. No writes at all.

A successful pilot does NOT mean selected 30 test WAVs are located, useful
or verified. Separate private fresh-consent holdout is unaffected.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import tarfile
import urllib.request

from t10_atika_tar_range_probe import (
    EXPECTED_TAR_BYTES, TAR_URL, PROBE_BYTES, MAX_READ_BYTES,
)
from t10_id_independent_holdout import require_private_workspace
from t10_public_id_corpus import REVISION

MAX_HEADERS = 8
DEFAULT_HEADERS = 6
MAX_SELECTION_BYTES = 200_000
SELECTION_NAME = "external_test_30_selection.json"
PINNED_METADATA_SHA = (
    "3ba42e2261e4ef387bc15e5934ce73be8e3cf6d1700ab0d635aa9d6958f59c21"
)


class RangeNotHonored(ValueError):
    """Ranged request was ignored: server body MUST NOT be consumed."""


def load_selection(workspace: Path) -> set[str]:
    require_private_workspace(workspace)
    path = workspace / SELECTION_NAME
    if (not path.is_file() or path.is_symlink()
            or path.stat().st_size > MAX_SELECTION_BYTES):
        raise ValueError("Missing, linked or oversized frozen public selection")
    data = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(data, dict) or data.get("schema_version") != 1
            or data.get("selected_category") != "Imperative"
            or data.get("sample_count") != 30
            or data.get("source_split") != "test"
            or data.get("metadata_sha256") != PINNED_METADATA_SHA
            or not isinstance(data.get("source"), dict)
            or data["source"].get("immutable_upstream_revision") != REVISION
            or data.get("all_audio_downloaded") is not False):
        raise ValueError("Selection differs from frozen Imperative public 30 metadata")
    items = data.get("items")
    if not isinstance(items, list) or len(items) != 30:
        raise ValueError("Frozen selection requires exactly 30 metadata rows")
    audio_paths = []
    for row in items:
        if not isinstance(row, dict) or not isinstance(row.get("source_audio_tar_member"), str):
            raise ValueError("Selection item missing TAR member name")
        value = row["source_audio_tar_member"]
        if (not value.startswith("data/") or ".." in value.split("/")
                or not value.lower().endswith(".wav")):
            raise ValueError("Selection contains unsafe audio member path")
        audio_paths.append(value)
    if len(set(audio_paths)) != 30:
        raise ValueError("Duplicate selected WAV paths")
    return set(audio_paths)


def fetch_header(offset: int) -> bytes:
    if offset % PROBE_BYTES or offset < 0 or offset + PROBE_BYTES > EXPECTED_TAR_BYTES:
        raise ValueError("Header offset outside pinned aligned TAR")
    end = offset + PROBE_BYTES - 1
    req = urllib.request.Request(
        TAR_URL,
        headers={
            "Range": f"bytes={offset}-{end}",
            "Accept-Encoding": "identity",
            "User-Agent": "Subloka-T10-bounded-TAR-header-walk/1",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=30) as response:
        if not response.geturl().startswith("https://"):
            raise ValueError("Non-HTTPS final redirect")
        if response.status != 206:
            # Important: a 200 response may stream the entire multi-GB archive.
            raise RangeNotHonored("HTTP Range ignored; never read full TAR body")
        cr = response.headers.get("Content-Range", "")
        if cr != f"bytes {offset}-{end}/{EXPECTED_TAR_BYTES}":
            raise ValueError("Unexpected HTTP Content-Range or total size")
        length = response.headers.get("Content-Length")
        if length is not None and length != str(PROBE_BYTES):
            raise ValueError("Wrong 512-byte Content-Length")
        payload = response.read(MAX_READ_BYTES)
        if len(payload) != PROBE_BYTES:
            raise ValueError("Expected exactly 512 bytes, no overrun")
        return payload


def walk_headers(max_headers: int, selected: set[str]) -> dict:
    if not isinstance(max_headers, int) or not 1 <= max_headers <= MAX_HEADERS:
        raise ValueError("Maximum headers is hard capped at eight")
    if len(selected) != 30:
        raise ValueError("Expected 30 immutable selected paths")
    offset = 0
    scanned = 0
    files = 0
    recognized_pax = 0
    found = set()
    end_marker = False
    while scanned < max_headers:
        header = fetch_header(offset)
        if header == bytes(PROBE_BYTES):
            end_marker = True
            break
        try:
            info = tarfile.TarInfo.frombuf(header, encoding="utf-8",
                                           errors="surrogateescape")
        except (tarfile.TarError, ValueError, UnicodeError) as exc:
            raise ValueError("Invalid checksummed TAR header in bounded walk") from exc
        if info.size < 0:
            raise ValueError("Negative TAR member size")
        # GNU long-name and PAX headers consume archive slots as normal files.
        if info.type in (tarfile.XHDTYPE, tarfile.XGLTYPE, tarfile.GNUTYPE_LONGNAME):
            recognized_pax += 1
        if info.isfile():
            files += 1
        if info.name in selected:
            found.add(info.name)
        next_offset = offset + PROBE_BYTES + ((info.size + 511) // 512) * 512
        if next_offset <= offset or next_offset > EXPECTED_TAR_BYTES:
            raise ValueError("TAR header points outside pinned archive")
        scanned += 1
        offset = next_offset
    # DO NOT print TAR names, individual user speaker labels or transcripts.
    return {
        "schema_version": 1,
        "result": "BOUNDED_REMOTE_TAR_HEADER_WALK_ONLY",
        "headers_scanned": scanned,
        "file_headers_seen": files,
        "pax_or_longname_headers_seen": recognized_pax,
        "requested_max_headers": max_headers,
        "network_requests_max": max_headers,
        "http_body_bytes_max": max_headers * MAX_READ_BYTES,
        "archive_total_bytes_not_downloaded": EXPECTED_TAR_BYTES,
        "tar_end_marker_seen": end_marker,
        "next_header_offset_bytes": offset,
        "selected_exact_name_matches_in_scanned_headers": len(found),
        "selected_total": len(selected),
        "all_30_clip_offsets_found": False,
        "full_tar_or_wav_downloaded": False,
        "WAV_integrity_verified": False,
        "model_downloaded_or_inference_performed": False,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--workspace", type=Path, required=True)
    parser.add_argument("--max-headers", type=int, default=DEFAULT_HEADERS)
    args = parser.parse_args()
    try:
        paths = load_selection(args.workspace)
        report = walk_headers(args.max_headers, paths)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("NO WAV SAVED | NO FULL TAR | NO MODEL DOWNLOAD | NO ADB | NO INFERENCE | CP4 BLOCKED")
        return 0
    except RangeNotHonored as exc:
        print("RANGE_NOT_HONORED_NO_BODY_READ:", exc, file=sys.stderr)
        return 2
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR: T10 bounded TAR header walk:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
