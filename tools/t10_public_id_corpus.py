#!/usr/bin/env python3
"""T10 public Indonesian ASR corpus triage. NOT fresh-consent private holdout.

Research dataset: Atika88/Indonesian-ASR-11-Class-Dataset, CC BY 4.0
(DOI-referenced immutable revision). Only fetches metadata, never audio, models,
ADB, benchmark predictions or permission flags. Public *speaker labels* do not
make voice recordings anonymous. The 15.6GB audio shards are NOT fetched here.
"""
from __future__ import annotations

import argparse
import csv
from collections import Counter, defaultdict
import hashlib
import json
from pathlib import Path
import re
import sys
import urllib.request

from t10_wer import normalize
from t10_id_independent_holdout import require_private_workspace

REPO_ID = "Atika88/Indonesian-ASR-11-Class-Dataset"
REVISION = "c65fe8bcff0547214c34cfbea248b4045a0d867c"
ROOT_URL = "https://huggingface.co/datasets/" + REPO_ID
METADATA_PATH = "metadata/dataset_metadata_public.csv"
METADATA_URL = f"{ROOT_URL}/resolve/{REVISION}/{METADATA_PATH}"
LICENSE = "CC-BY-4.0 (publisher metadata, not independent rights attestation)"
MAX_METADATA_BYTES = 100 * 1024 * 1024
METADATA_FILENAME = "upstream_metadata.csv"
SELECTION_FILENAME = "external_test_30_selection.json"
REQUIRED = {
    "audio_path", "split", "category", "speaker_id",
    "speaker_type", "is_synthetic", "transcript", "duration_sec",
    "sample_rate", "num_channels", "bits_per_sample", "file_size_bytes",
}
ALLOWED_CATEGORIES = re.compile(r"^[A-Za-z][A-Za-z0-9_ -]{0,70}$")


def source_info() -> dict:
    return {
        "schema_version": 1,
        "id": "T10_ATIKA_PUBLIC_EXTERNAL_DIAGNOSTIC_ONLY",
        "upstream_dataset": REPO_ID,
        "immutable_upstream_revision": REVISION,
        "upstream_metadata_url": METADATA_URL,
        "upstream_homepage": ROOT_URL,
        "doi": "10.57967/hf/10345",
        "license_metadata": LICENSE,
        "published_release_date": "2026-06-18",
        "published_total_dataset_audio_bytes_approx": 15_623_106_560,
        "metadata_only_this_script": True,
        "uses_only_test_partition": True,
        "rejects_synthetic_repair_rows": True,
        "source_is_fresh_consent_holdout": False,
        "does_not_replace_30_private_new_recording_slots": True,
        "train_disjointness_from_maleo_independently_confirmed": False,
        "test_transcripts_human_rechecked": False,
        "read_speech_not_spontaneous_generalization": True,
        "CP4": "BLOCKED",
        "T10": "ACTIVE",
        "T11": "TODO",
    }


def sha256_file(path: Path) -> str:
    sha = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            sha.update(chunk)
    return sha.hexdigest()


def fetch_metadata(workspace: Path) -> dict:
    """Bounded public metadata download; no model or WAV/TAR downloads."""
    require_private_workspace(workspace)
    target = workspace / METADATA_FILENAME
    if target.exists() or target.is_symlink():
        raise FileExistsError("Existing metadata refuses overwrite")
    workspace.mkdir(parents=True, exist_ok=True)
    length = 0
    digest = hashlib.sha256()
    try:
        req = urllib.request.Request(
            METADATA_URL,
            headers={"User-Agent": "Subloka-T10-public-metadata-research/1"},
        )
        with urllib.request.urlopen(req, timeout=30) as response, target.open("xb") as dst:
            if response.url.split(":", 1)[0] != "https":
                raise ValueError("HTTPS required for public source")
            declared = response.headers.get("Content-Length")
            if declared and int(declared) > MAX_METADATA_BYTES:
                raise ValueError("Public metadata exceeds 100MiB hard cap")
            while chunk := response.read(1024 * 1024):
                length += len(chunk)
                if length > MAX_METADATA_BYTES:
                    raise ValueError("Public metadata exceeds 100MiB hard cap")
                dst.write(chunk)
                digest.update(chunk)
        if length == 0:
            raise ValueError("Empty upstream CSV")
        with target.open("r", encoding="utf-8-sig", newline="") as f:
            header = next(csv.reader(f), [])
        if not REQUIRED.issubset(header):
            raise ValueError("Source CSV lacks required corpus columns")
    except Exception:
        # Do not preserve incomplete or unverified CSV for selection.
        if target.exists():
            target.unlink()
        raise
    return {"downloaded_metadata_bytes": length, "sha256": digest.hexdigest(),
            "local_file": str(target), "only_metadata": True, "CP4": "BLOCKED"}


def parse_bool(value: str) -> bool | None:
    key = str(value).strip().lower()
    if key in ("true", "1"):
        return True
    if key in ("false", "0"):
        return False
    return None


def valid_human_test(row: dict) -> bool:
    """Never infer 'not synthetic' from a missing/unknown flag."""
    try:
        duration = float(row["duration_sec"])
        sample_rate = int(row["sample_rate"].replace(",", ""))
        channels = int(row["num_channels"])
        depth = int(row["bits_per_sample"])
        size = int(row["file_size_bytes"].replace(",", ""))
    except (TypeError, ValueError, KeyError, AttributeError):
        return False
    path = row.get("audio_path", "")
    # Dataset paths are relative TAR member names, NOT URLs.
    if not isinstance(path, str) or not path.startswith("data/") or ".." in path.split("/"):
        return False
    tokens = normalize(row.get("transcript", ""))
    return (
        row.get("split") == "test"
        and row.get("speaker_type") == "human"
        and parse_bool(row.get("is_synthetic", "")) is False
        and 1 <= duration <= 30
        and sample_rate == 16000
        and channels == 1
        and depth == 16
        and 44 <= size <= 3_000_000
        and 4 <= len(tokens) <= 90
        and bool(row.get("speaker_id"))
        and bool(row.get("category"))
    )


def eligible_rows(workspace: Path) -> tuple[list[dict], str]:
    require_private_workspace(workspace)
    path = workspace / METADATA_FILENAME
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_METADATA_BYTES:
        raise ValueError("First fetch a valid small upstream CSV metadata file")
    digest = sha256_file(path)
    rows = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        if not REQUIRED.issubset(reader.fieldnames or ()):
            raise ValueError("Invalid public corpus metadata schema")
        for row in reader:
            if valid_human_test(row):
                rows.append(row)
    return rows, digest


def inspect(workspace: Path) -> dict:
    rows, sha = eligible_rows(workspace)
    grouped = defaultdict(list)
    for row in rows:
        grouped[row["category"]].append(row)
    counts = []
    for category in sorted(grouped):
        subset = grouped[category]
        counts.append({
            "category": category,
            "eligible_test_human_rows": len(subset),
            "distinct_public_speaker_labels": len({r["speaker_id"] for r in subset}),
            "total_wav_file_bytes_if_unpacked": sum(int(r["file_size_bytes"]) for r in subset),
            "tar_shard_network_bytes": "NOT MEASURED; upstream category TAR could be >1GB",
        })
    return {
        "dataset": REPO_ID,
        "revision": REVISION,
        "sha256_local_metadata": sha,
        "eligible_human_test_rows": len(rows),
        "categories": counts,
        "audio_downloaded": False,
        "safe_to_claim_independent_training_holdout": False,
        "CP4": "BLOCKED",
    }


def archive_sizes(workspace: Path) -> dict:
    """Read tiny pinned HF repository tree JSON; NEVER fetch TAR or WAV bytes."""
    local = inspect(workspace)  # Requires already downloaded CSV in gitignored root
    expected = {x["category"] for x in local["categories"]}
    url = (
        f"https://huggingface.co/api/datasets/{REPO_ID}/tree/{REVISION}"
        "/data/audio_shards/by_category"
    )
    request = urllib.request.Request(
        url, headers={"User-Agent": "Subloka-T10-public-archive-preflight/1"}
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        if not response.url.startswith("https://huggingface.co/"):
            raise ValueError("Archive size metadata must be fetched from HTTPS huggingface.co")
        raw = response.read(1_000_001)
    if len(raw) > 1_000_000:
        raise ValueError("Archive metadata API unexpectedly exceeded 1MB")
    try:
        entries = json.loads(raw.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise ValueError("Malformed HF archive metadata JSON") from exc
    if not isinstance(entries, list):
        raise ValueError("HF archive metadata is not a list")
    shards: dict[str, dict] = {}
    for item in entries:
        if not isinstance(item, dict) or item.get("type") != "file":
            continue
        archive_path = item.get("path")
        if (not isinstance(archive_path, str)
                or not re.fullmatch(r"data/audio_shards/by_category/[A-Za-z]+\.tar", archive_path)):
            continue
        category = Path(archive_path).stem
        size = item.get("size")
        if category in shards or type(size) is not int or not 1_000_000 <= size <= 5_000_000_000:
            raise ValueError("Duplicate archive, missing size or implausible TAR bytes")
        lfs = item.get("lfs")
        lfs_sha = lfs.get("oid") if isinstance(lfs, dict) else None
        if lfs_sha is not None and not re.fullmatch(r"[a-f0-9]{64}", str(lfs_sha)):
            raise ValueError("Unexpected upstream LFS object digest")
        shards[category] = {
            "category": category,
            "archive_bytes_publisher_api": size,
            "archive_mib_publisher_api": round(size / (1024 * 1024), 1),
            "pinned_tar_url_NOT_DOWNLOADED": (
                f"{ROOT_URL}/resolve/{REVISION}/{archive_path}"
            ),
            "lfs_sha256_upstream_metadata_unverified": lfs_sha,
            "local_archive_exists_or_verified": False,
            "approved_for_download": False,
        }
    if set(shards) != expected or len(shards) != 11:
        raise ValueError("Remote TAR category listing mismatch with locally pinned metadata")
    ordered = sorted(shards.values(), key=lambda x: (x["archive_bytes_publisher_api"], x["category"]))
    return {
        "source_revision": REVISION,
        "metadata_csv_sha256": local["sha256_local_metadata"],
        "archive_api_url": url,
        "archive_size_evidence": "Published HF repository tree metadata only; no download",
        "archive_count": len(ordered),
        "total_archive_bytes_publisher_api": sum(s["archive_bytes_publisher_api"] for s in ordered),
        "categories_by_archive_size": ordered,
        "tar_or_wav_downloaded": False,
        "model_downloaded_or_inference_performed": False,
        "CP4": "BLOCKED",
    }


def choose_samples(workspace: Path, category: str, limit: int = 30) -> dict:
    if not ALLOWED_CATEGORIES.fullmatch(category):
        raise ValueError("Category must be an exact reasonable upstream category label")
    rows, digest = eligible_rows(workspace)
    candidates = [x for x in rows if x["category"] == category]
    if len(candidates) < limit:
        raise ValueError("Insufficient human test rows in chosen category")
    # Stable content-agnostic rotation across public speaker labels.
    by_speaker: dict[str, list] = defaultdict(list)
    for r in candidates:
        by_speaker[r["speaker_id"]].append(r)
    if len(by_speaker) < 2:
        raise ValueError("Need multiple distinct test speakers for public diagnostic")
    for key, group in by_speaker.items():
        group.sort(key=lambda r: hashlib.sha256(
            (REVISION + "|" + key + "|" + r["audio_path"]).encode("utf-8")
        ).hexdigest())
    selected = []
    seen_audio_paths = set()
    unique_references = set()
    while len(selected) < limit:
        progressed = False
        for speaker in sorted(by_speaker):
            while by_speaker[speaker]:
                row = by_speaker[speaker].pop(0)
                if row["audio_path"] in seen_audio_paths:
                    continue
                selected.append(row)
                seen_audio_paths.add(row["audio_path"])
                unique_references.add(" ".join(normalize(row["transcript"])))
                progressed = True
                break
            if len(selected) >= limit:
                break
        if not progressed:
            raise ValueError("Insufficient distinct audio paths in chosen category")
    # Author documents only ~19 distinct sentence prompts per category;
    # speaker-disjoint audio often repeats text. Report repetitions honestly,
    # rather than pretending the external subset tests unseen vocabulary.
    total_words = sum(len(normalize(x["transcript"])) for x in selected)
    if total_words < 180:
        raise ValueError("Selected external diagnostic has too few normalized words")
    return {
        "schema_version": 1,
        "type": "T10_PUBLIC_EXTERNAL_ID_ASR_TEST_SAMPLING_NOT_PRIVATE_HOLDOUT",
        "source": source_info(),
        "metadata_sha256": digest,
        "source_split": "test",
        "selected_category": category,
        "source_category_tar_url_not_downloaded": (
            f"{ROOT_URL}/resolve/{REVISION}/data/audio_shards/by_category/{category}.tar"
        ),
        "source_archive_sha256_not_locally_verified": True,
        "tar_archive_size_not_preflighted": True,
        "sample_count": len(selected),
        "distinct_audio_paths": len(seen_audio_paths),
        "distinct_reference_prompts": len(unique_references),
        "repeated_reference_prompts": len(selected) - len(unique_references),
        "reference_texts_may_repeat_across_speakers": True,
        "not_unseen_prompt_or_open_vocabulary_benchmark": True,
        "normalized_reference_words": total_words,
        "public_speaker_label_count": len({r["speaker_id"] for r in selected}),
        "all_audio_downloaded": False,
        "audio_bytes_locally_verified": False,
        "test_transcripts_human_rechecked": False,
        "model_inference_done": False,
        "evaluation_pass": False,
        "CP4": "BLOCKED",
        "items": [{
            "source_audio_tar_member": r["audio_path"],
            "speaker_label": r["speaker_id"],
            "reference_from_publisher_not_rechecked": r["transcript"],
            "audio_expected_bytes_from_publisher": int(r["file_size_bytes"]),
            "duration_seconds_from_publisher": float(r["duration_sec"]),
        } for r in selected],
    }


def select(workspace: Path, category: str) -> dict:
    require_private_workspace(workspace)
    path = workspace / SELECTION_FILENAME
    if path.exists() or path.is_symlink():
        raise FileExistsError("Frozen public sample selection exists; refuse overwrite")
    report = choose_samples(workspace, category)
    with path.open("x", encoding="utf-8") as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
        f.write("\n")
    return {
        "selection_file": str(path),
        "sample_count": report["sample_count"],
        "public_speaker_label_count": report["public_speaker_label_count"],
        "source_split": report["source_split"],
        "actual_audio_downloaded": False,
        "CP4": "BLOCKED",
    }


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("source", help="Show researched source without network")
    for cmd in ("fetch-metadata", "inspect", "archive-sizes", "select"):
        pp = sub.add_parser(cmd)
        pp.add_argument("--workspace", type=Path, required=True)
        if cmd == "select":
            pp.add_argument("--category", required=True)
    args = p.parse_args()
    try:
        if args.command == "source":
            report = source_info()
        elif args.command == "fetch-metadata":
            report = fetch_metadata(args.workspace)
        elif args.command == "inspect":
            report = inspect(args.workspace)
        elif args.command == "archive-sizes":
            report = archive_sizes(args.workspace)
        else:
            report = select(args.workspace, args.category)
        print(json.dumps(report, ensure_ascii=False, indent=2))
        print("NO AUDIO SHARD DOWNLOAD | NO MODEL DOWNLOAD | NO ADB | NO INFERENCE | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, csv.Error, UnicodeError) as exc:
        print("ERROR: T10 external public ID corpus triage:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
