#!/usr/bin/env python3
"""T10 private Indonesian ASR holdout intake: no network, ADB or inference.

Checks metadata declarations and exact original audio bytes. Does NOT
authenticate consent, independence from training, or a human reviewer.
Never promotes CP4, alters frozen FLEURS evidence, or downloads models.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timedelta, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys
import wave

from t10_wer import normalize
from t10_asr_next_feasibility import read_frozen_pins
from t10_asr_id_compact_protocol import CANDIDATES

SCHEMA_VERSION = 1
MIN_COUNTS = {"clean": 20, "challenging": 10}
MIN_SPEAKERS = 5
MIN_CLEAN_WORDS = 250  # New research robustness rule; NOT CP4 gate revision.
MAX_WAV_BYTES = 3_000_000
MAX_MANIFEST_BYTES = 128_000
FIELDS = {
    "id", "category", "language", "audio", "audio_sha256", "reference",
    "speaker_id", "recorded_utc", "consent_scope", "consent_declared",
    "human_reference_reviewed", "reference_reviewed_by", "origin",
}
ID = re.compile(r"^id-(clean|challenging)-[0-9]{2}$")
PSEUDONYM = re.compile(r"^(spk|rev)-[a-z0-9][a-z0-9_-]{1,30}$")
HEX64 = re.compile(r"^[0-9a-f]{64}$")
ORIGIN = "fresh_consented_recording_not_public_corpus"
CONSENT = "offline_asr_evaluation_only"


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def parse_recorded_utc(value: object) -> None:
    if not isinstance(value, str):
        raise ValueError("Recorded date must be ISO8601 string")
    try:
        stamp = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as e:
        raise ValueError("Invalid recorded_utc") from e
    if stamp.tzinfo is None or stamp.utcoffset() is None:
        raise ValueError("recorded_utc requires explicit timezone")
    utc = stamp.astimezone(timezone.utc)
    if utc < datetime(2026, 1, 1, tzinfo=timezone.utc) or utc > datetime.now(timezone.utc) + timedelta(days=1):
        raise ValueError("recorded_utc outside acceptable range")


def load_manifest(workspace: Path) -> tuple[dict, bytes]:
    if workspace.is_symlink():
        raise ValueError("Workspace symlink prohibited")
    path = workspace / "manifest.json"
    if not path.is_file() or path.is_symlink() or path.stat().st_size > MAX_MANIFEST_BYTES:
        raise ValueError("Missing/linked/oversized manifest")
    raw = path.read_bytes()
    try:
        manifest = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeError, json.JSONDecodeError) as e:
        raise ValueError("Invalid UTF-8 manifest") from e
    if (not isinstance(manifest, dict) or set(manifest) != {"schema_version", "purpose", "samples"}
            or manifest["schema_version"] != SCHEMA_VERSION
            or manifest["purpose"] != "independent_id_asr_holdout"
            or not isinstance(manifest["samples"], list)):
        raise ValueError("Unsupported private holdout manifest")
    return manifest, raw


def validate_audio_path(workspace: Path, relative: object) -> Path:
    if not isinstance(relative, str) or "\\" in relative:
        raise ValueError("Unsafe audio path")
    part = PurePosixPath(relative)
    if (part.is_absolute() or len(part.parts) != 2 or part.parts[0] != "audio"
            or not re.fullmatch(r"[A-Za-z0-9_-]+\.wav", part.parts[1])):
        raise ValueError("Audio must be audio/<safe-name>.wav inside workspace")
    folder = workspace / "audio"
    file = workspace / str(part)
    if folder.is_symlink() or file.is_symlink() or not file.is_file():
        raise ValueError("Missing WAV or symlinked private audio")
    if file.resolve().parent != folder.resolve():
        raise ValueError("WAV escapes private workspace")
    return file


def audit(workspace: Path) -> dict:
    manifest, original = load_manifest(workspace)
    samples = manifest["samples"]
    if len(samples) != 30:
        raise ValueError("Exactly 20 clean + 10 challenging real recordings required")
    counts: Counter[str] = Counter()
    speakers: set[str] = set()
    wav_hashes: set[str] = set()
    normalized_texts: set[str] = set()
    clean_words = 0
    assets: list[dict] = []
    for row in samples:
        if not isinstance(row, dict) or set(row) != FIELDS:
            raise ValueError("Sample has missing or unknown fields")
        kind = row["category"]
        sid = row["id"]
        if (kind not in MIN_COUNTS or not isinstance(sid, str)
                or not ID.fullmatch(sid)
                or sid != f"id-{kind}-{counts[kind] + 1:02d}"
                or row["language"] != "id"):
            raise ValueError("Unexpected sample ID/order/language")
        counts[kind] += 1
        if counts[kind] > MIN_COUNTS[kind]:
            raise ValueError("More items than frozen category slots")
        speaker, reviewer = row["speaker_id"], row["reference_reviewed_by"]
        if (not isinstance(speaker, str) or not PSEUDONYM.fullmatch(speaker)
                or not speaker.startswith("spk-")
                or not isinstance(reviewer, str) or not PSEUDONYM.fullmatch(reviewer)
                or not reviewer.startswith("rev-")):
            raise ValueError("Only pseudonymous speaker/reviewer IDs permitted")
        speakers.add(speaker)
        if row["origin"] != ORIGIN:
            raise ValueError("Not a fresh independent source declaration")
        if row["consent_scope"] != CONSENT or row["consent_declared"] is not True:
            raise ValueError("Real recording permission must be obtained before declaration")
        if row["human_reference_reviewed"] is not True:
            raise ValueError("Reference requires actual human listening review")
        parse_recorded_utc(row["recorded_utc"])
        reference = row["reference"]
        if not isinstance(reference, str) or not reference.strip() or len(reference) > 1600:
            raise ValueError("Invalid human-reviewed transcript")
        tokens = normalize(reference)
        if not 4 <= len(tokens) <= 90:
            raise ValueError("Unreasonable reference word count")
        normalized = " ".join(tokens)
        if normalized in normalized_texts:
            raise ValueError("Duplicate normalized reference")
        normalized_texts.add(normalized)
        if kind == "clean":
            clean_words += len(tokens)
        expected_sha = row["audio_sha256"]
        if not isinstance(expected_sha, str) or not HEX64.fullmatch(expected_sha):
            raise ValueError("Missing exact WAV SHA256")
        path = validate_audio_path(workspace, row["audio"])
        if not 44 <= path.stat().st_size <= MAX_WAV_BYTES:
            raise ValueError("Empty or oversized original WAV")
        actual_sha = sha256_file(path)
        if expected_sha != actual_sha or actual_sha in wav_hashes:
            raise ValueError("WAV bytes changed or audio recording duplicated")
        wav_hashes.add(actual_sha)
        try:
            with wave.open(str(path), "rb") as wav:
                if (wav.getnchannels(), wav.getsampwidth(), wav.getframerate(), wav.getcomptype()) != (1, 2, 16000, "NONE"):
                    raise ValueError("Must be mono PCM16 16kHz WAV")
                duration = wav.getnframes() / 16000
        except (wave.Error, EOFError) as e:
            raise ValueError("Unreadable WAV") from e
        if not 1 <= duration <= 30:
            raise ValueError("WAV must be 1-30 seconds")
        assets.append({
            "id": sid, "category": kind, "audio_sha256": actual_sha,
            "reference_sha256": hashlib.sha256(reference.encode("utf-8")).hexdigest(),
            "words": len(tokens), "duration_seconds": round(duration, 3),
        })
    if counts != MIN_COUNTS or len(speakers) < MIN_SPEAKERS or clean_words < MIN_CLEAN_WORDS:
        raise ValueError("Holdout must have 20 clean, 10 challenging, >=5 speakers, >=250 clean words")
    return {
        "schema_version": SCHEMA_VERSION,
        "status": "FILE_AND_DECLARATION_AUDIT_NOT_INDEPENDENCE_ATTESTED",
        "manifest_sha256": hashlib.sha256(original).hexdigest(),
        "clean_samples": counts["clean"], "challenging_samples": counts["challenging"],
        "pseudonymous_speakers": len(speakers), "clean_reference_words": clean_words,
        "assets": assets,
        "baseline_evidence_sha256": read_frozen_pins(),
        "candidate_upstream_artifact_sha256": {k: v["sha256"] for k, v in CANDIDATES.items()},
        "real_consent_and_human_independence_authenticated": False,
        "training_overlap_independently_excluded": False,
        "inference_performed": False,
        "CP4": "BLOCKED", "T10": "ACTIVE", "T11": "TODO",
    }


def init(workspace: Path) -> None:
    if workspace.is_symlink() or (workspace / "manifest.json").exists():
        raise FileExistsError("Private manifest already exists; refusing overwrite")
    workspace.mkdir(parents=True, exist_ok=True)
    (workspace / "audio").mkdir(exist_ok=True)
    template = {"schema_version": 1, "purpose": "independent_id_asr_holdout", "samples": []}
    with (workspace / "manifest.json").open("x", encoding="utf-8") as file:
        json.dump(template, file, ensure_ascii=False, indent=2)
        file.write("\n")
    print("PRIVATE EMPTY HOLDOUT INITIALIZED:", workspace)
    print("NO REAL AUDIO, TRANSCRIPT OR CONSENT HAS BEEN VERIFIED")


def seal(workspace: Path) -> dict:
    path = workspace / "manifest.lock.json"
    if path.exists() or path.is_symlink():
        raise FileExistsError("Frozen holdout lock exists; cannot overwrite")
    report = audit(workspace)
    lock = {
        "schema_version": 1,
        "kind": "BYTE_LOCK_NOT_INDEPENDENCE_ATTESTATION",
        "sealed_utc": datetime.now(timezone.utc).isoformat(),
        "audit": report,
        "CP4": "BLOCKED",
    }
    with path.open("x", encoding="utf-8") as file:
        json.dump(lock, file, ensure_ascii=False, indent=2)
        file.write("\n")
    return lock


def verify(workspace: Path) -> dict:
    path = workspace / "manifest.lock.json"
    if not path.is_file() or path.is_symlink():
        raise ValueError("Missing immutable holdout lock")
    lock = json.loads(path.read_text(encoding="utf-8"))
    if (not isinstance(lock, dict) or lock.get("schema_version") != 1
            or lock.get("kind") != "BYTE_LOCK_NOT_INDEPENDENCE_ATTESTATION"
            or lock.get("CP4") != "BLOCKED"):
        raise ValueError("Invalid lock schema")
    report = audit(workspace)
    if lock.get("audit") != report:
        raise ValueError("Locked manifest/reference/audio/pins changed")
    return report


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for command in ("init", "audit", "seal", "verify"):
        parser = sub.add_parser(command)
        parser.add_argument("--workspace", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "init":
            init(args.workspace)
        elif args.command == "audit":
            report = audit(args.workspace)
            print("HOLDOUT FILE AUDIT PASS:", report["clean_samples"], "clean,",
                  report["challenging_samples"], "challenging;", report["clean_reference_words"], "clean words")
        elif args.command == "seal":
            print("HOLDOUT BYTE LOCK SEALED:", seal(args.workspace)["audit"]["manifest_sha256"])
        else:
            print("HOLDOUT LOCK VERIFY PASS:", verify(args.workspace)["manifest_sha256"])
        print("HUMAN INDEPENDENCE NOT AUTHENTICATED | NO DOWNLOAD | NO ADB | NO INFERENCE | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR: T10 private ID holdout:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
