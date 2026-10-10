#!/usr/bin/env python3
"""T10 private, topic-based Indonesian holdout collection plan and progress.

Plans *topics*, not exact speech or reference transcripts. Real adults/volunteers
choose their own words with informed consent. This script never records speech,
sets consent/review flags, collects PII, hashes model files, or runs inference.
Use only a pre-existing gitignored T10 private holdout workspace.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from t10_id_independent_holdout import (
    MIN_COUNTS, load_manifest, require_private_workspace,
)

# Themes, NOT target transcripts. Actual words must be spoken naturally and
# independently checked from the actual recordings before ASR prediction.
CLEAN_TOPICS = (
    "Ceritakan kegiatan pertama yang biasa dilakukan pada pagi hari.",
    "Jelaskan kegiatan ringan di rumah pada waktu senggang.",
    "Ceritakan cara menyiapkan makanan sederhana dengan bahasa sendiri.",
    "Jelaskan suasana ketika membeli kebutuhan di pasar.",
    "Ceritakan rencana perjalanan singkat dengan kendaraan umum.",
    "Jelaskan apa yang disukai dari membaca buku atau majalah.",
    "Ceritakan aktivitas belajar sesuatu yang baru.",
    "Jelaskan cara merawat tanaman di halaman atau dalam pot.",
    "Ceritakan keadaan cuaca yang baru saja diamati.",
    "Jelaskan cara menyusun daftar barang yang akan dibeli.",
    "Ceritakan pengalaman berkunjung ke taman kota.",
    "Jelaskan kegiatan sehari-hari dalam kelompok belajar.",
    "Ceritakan persiapan menyambut tamu di rumah.",
    "Jelaskan cara menata meja atau ruangan agar nyaman.",
    "Ceritakan pengalaman mendapatkan paket atau kiriman.",
    "Jelaskan bagaimana memilih buah yang segar.",
    "Ceritakan kegiatan menjaga kebersihan lingkungan sekitar.",
    "Jelaskan cara mempersiapkan perlengkapan bepergian.",
    "Ceritakan sebuah kebiasaan sederhana pada sore hari.",
    "Jelaskan rencana kegiatan esok hari dengan kalimat alami.",
)
CHALLENGING_TOPICS = (
    "Jelaskan dua perubahan jadwal dan sebutkan beberapa waktu dengan jelas.",
    "Ceritakan beberapa jumlah barang yang berbeda dengan tempo alami.",
    "Jelaskan urutan tiga tempat umum yang pernah atau ingin dikunjungi.",
    "Ceritakan kegiatan sambil sesekali berhenti berpikir secara alami.",
    "Jelaskan arah ke tempat fiktif tanpa menyebut alamat pribadi.",
    "Ceritakan dua pilihan kegiatan dengan koreksi kecil yang alami.",
    "Jelaskan nama benda yang mirip bunyi tanpa membacanya dari daftar.",
    "Ceritakan pengalaman singkat dengan suara ruangan normal yang agak bergema.",
    "Jelaskan rencana kelompok dalam suasana dalam ruangan dengan bunyi latar rendah.",
    "Ceritakan sesuatu secara spontan dengan laju bicara pribadi yang wajar.",
)
PLAN_FILENAME = "collection_plan.json"


def expected_ids() -> list[str]:
    return [
        f"id-{category}-{index:02d}"
        for category, count in MIN_COUNTS.items()
        for index in range(1, count + 1)
    ]


def check_template(workspace: Path) -> dict:
    obj, _ = load_manifest(workspace)  # Also enforces gitignored private area.
    rows = obj["samples"]
    if len(rows) != 30 or [r.get("id") if isinstance(r, dict) else None for r in rows] != expected_ids():
        raise ValueError("Existing private manifest sample IDs are not the original 30 ordered slots")
    if any(row.get("language") != "id" or row.get("category") != sid.split("-")[1]
           for row, sid in zip(rows, expected_ids())):
        raise ValueError("Existing private manifest category/language altered")
    return obj


def plan_payload() -> dict:
    if len(CLEAN_TOPICS) != 20 or len(CHALLENGING_TOPICS) != 10:
        raise ValueError("The pre-registered research topic count changed")
    items = []
    for category, topics in (("clean", CLEAN_TOPICS), ("challenging", CHALLENGING_TOPICS)):
        for index, topic in enumerate(topics, start=1):
            items.append({
                "id": f"id-{category}-{index:02d}",
                "category": category,
                "suggested_speaker_id": f"spk-{(index - 1) % 5 + 1:02d}",
                "topic_cue_not_reference_transcript": topic,
                "suggested_setting": (
                    "Ruang tenang, suara alami, jarak mikrofon nyaman."
                    if category == "clean" else
                    "Berbicara alami dalam suasana aman, dengan jeda atau variasi "
                    "angka/tempo dan suara latar rendah bila memang ada."
                ),
            })
    if len({row["topic_cue_not_reference_transcript"] for row in items}) != 30:
        raise ValueError("Duplicate topic cues")
    return {
        "schema_version": 1,
        "type": "PRIVATE_ID_HOLDOUT_TOPIC_PLAN_NOT_HUMAN_REFERENCE_OR_CONSENT",
        "sample_count": 30,
        "speaker_plan": "5 consenting speakers; each: 4 clean + 2 challenging",
        "recommended_utterance": "Kata-kata spontan sendiri, sekitar 15-20 kata per klip; 1-30 detik.",
        "prompt_is_not_reference": True,
        "require_actual_permission_before_recording": True,
        "minor_participant_extra_permission_if_required": True,
        "suggested_speakers_not_real_identity_or_consent": True,
        "record_real_audio": False,
        "review_real_audio_before_model_prediction": True,
        "do_not_fill_reference_from_topic_cue": True,
        "do_not_share_private_audio_transcripts_or_identity": True,
        "CP4": "BLOCKED",
        "items": items,
    }


def create_plan(workspace: Path) -> Path:
    require_private_workspace(workspace)
    check_template(workspace)
    lock = workspace / "manifest.lock.json"
    if lock.exists() or lock.is_symlink():
        raise ValueError("Holdout already sealed; collection planning may no longer change")
    output = workspace / PLAN_FILENAME
    if output.exists() or output.is_symlink():
        raise FileExistsError("Private collection plan exists; refusing overwrite")
    with output.open("x", encoding="utf-8") as handle:
        json.dump(plan_payload(), handle, ensure_ascii=False, indent=2)
        handle.write("\n")
    return output


def progress(workspace: Path) -> dict:
    manifest = check_template(workspace)
    rows = manifest["samples"]
    folder = workspace / "audio"
    if folder.is_symlink():
        raise ValueError("Audio folder symlink not permitted")
    result = {
        "total_slots": len(rows),
        "clean_slots": 20,
        "challenging_slots": 10,
        "wav_present_not_verified": 0,
        "reference_filled_not_verified": 0,
        "audio_hash_entered_not_verified": 0,
        "permission_declared_not_authenticated": 0,
        "review_declared_not_authenticated": 0,
        "speaker_id_filled_not_verified": 0,
        "recorded_date_filled_not_verified": 0,
        "rows_with_all_declarations_not_audited": 0,
        "consent_authenticated_by_this_tool": False,
        "independent_dataset_ready": False,
        "CP4": "BLOCKED",
    }
    for row in rows:
        candidate = folder / f"{row['id']}.wav"
        if candidate.is_file() and not candidate.is_symlink():
            result["wav_present_not_verified"] += 1
        for field, key in (
            ("reference", "reference_filled_not_verified"),
            ("audio_sha256", "audio_hash_entered_not_verified"),
            ("speaker_id", "speaker_id_filled_not_verified"),
            ("recorded_utc", "recorded_date_filled_not_verified"),
        ):
            if isinstance(row.get(field), str) and row[field].strip():
                result[key] += 1
        if row.get("consent_declared") is True:
            result["permission_declared_not_authenticated"] += 1
        if row.get("human_reference_reviewed") is True:
            result["review_declared_not_authenticated"] += 1
        if all(row.get(k) for k in ("reference", "audio_sha256", "speaker_id", "recorded_utc")) and (
            row.get("consent_declared") is True and row.get("human_reference_reviewed") is True
        ):
            result["rows_with_all_declarations_not_audited"] += 1
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="command", required=True)
    for action in ("create", "status"):
        command = sub.add_parser(action)
        command.add_argument("--workspace", type=Path, required=True)
    args = p.parse_args()
    try:
        if args.command == "create":
            created = create_plan(args.workspace)
            print("PRIVATE 30-TOPIC COLLECTION PLAN CREATED:", created)
            print("NO RECORDINGS, REAL CONSENT OR HUMAN TRANSCRIPTS CREATED")
        else:
            report = progress(args.workspace)
            print("PRIVATE HOLDOUT STATUS (COUNTS ONLY, NOT VERIFIED):")
            for key in (
                "total_slots", "clean_slots", "challenging_slots",
                "wav_present_not_verified", "reference_filled_not_verified",
                "audio_hash_entered_not_verified", "permission_declared_not_authenticated",
                "review_declared_not_authenticated",
                "rows_with_all_declarations_not_audited",
            ):
                print(key + ":", report[key])
        print("NO MODEL DOWNLOAD | NO ADB | NO INFERENCE | T10 ACTIVE | CP4 BLOCKED")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as exc:
        print("ERROR: T10 private collection kit:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
