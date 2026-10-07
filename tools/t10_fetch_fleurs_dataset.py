#!/usr/bin/env python3
"""Fetch and materialize the T10 human ASR benchmark subset from Google FLEURS."""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import statistics
import struct
import sys
import tarfile
import urllib.request
import wave
from pathlib import Path
from typing import Iterable

FLEURS_REVISION = "4683b04af03d2d9549064c7d72060a9a94bb6046"
FLEURS_BASE = "https://huggingface.co/datasets/google/fleurs/resolve"
SAMPLE_RATE = 16_000
MAX_DURATION_SECONDS = 25.0

LANGUAGES = {
    "en": {
        "locale": "en_us",
        "archive_sha256": "2658fda72f199e12676ecac9415094667a4e14e149b146e568ea00b2a2f0954c",
    },
    "id": {
        "locale": "id_id",
        "archive_sha256": "74e5f1c8676a321dc4c34944b171846d40923dabe765a767d8dbc2f56cac3142",
    },
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Download Google FLEURS EN/ID dev audio and create the 60-sample "
            "T10 ASR manifest: 20 typical-duration clean + 10 long-utterance "
            "challenging clips per language."
        )
    )
    parser.add_argument("--manifest", default="t10-dataset.json")
    parser.add_argument("--audio-dir", default="t10-audio")
    parser.add_argument("--cache-dir", default=".t10-fleurs-cache")
    parser.add_argument(
        "--force",
        action="store_true",
        help="Allow replacing an existing non-placeholder manifest/target WAV files.",
    )
    return parser.parse_args()


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def download(url: str, destination: Path, expected_sha256: str | None = None) -> None:
    if destination.exists():
        if expected_sha256 is None or sha256_file(destination) == expected_sha256:
            print(f"Cache: {destination}")
            return
        destination.unlink()

    destination.parent.mkdir(parents=True, exist_ok=True)
    partial = destination.with_suffix(destination.suffix + ".part")
    partial.unlink(missing_ok=True)

    print(f"Download: {url}")
    request = urllib.request.Request(url, headers={"User-Agent": "SubLoka-T10/1.0"})
    with urllib.request.urlopen(request) as response, partial.open("wb") as output:
        total = int(response.headers.get("Content-Length", "0") or 0)
        received = 0
        while True:
            chunk = response.read(1024 * 1024)
            if not chunk:
                break
            output.write(chunk)
            received += len(chunk)
            if total:
                percent = received * 100 // total
                print(f"\r  {percent:3d}% ({received // (1024 * 1024)} MiB)", end="", flush=True)
        if total:
            print()

    if expected_sha256 is not None:
        actual = sha256_file(partial)
        if actual != expected_sha256:
            partial.unlink(missing_ok=True)
            raise RuntimeError(
                f"Checksum gagal untuk {destination.name}: expected={expected_sha256} actual={actual}"
            )

    partial.replace(destination)


def read_tsv(path: Path) -> list[dict]:
    rows: list[dict] = []
    with path.open("r", encoding="utf-8") as handle:
        reader = csv.reader(handle, delimiter="\t")
        for values in reader:
            if len(values) < 7:
                continue
            sample_id, filename, raw_transcription, transcription, _words, num_samples, gender = values[:7]
            try:
                frames = int(num_samples)
            except ValueError:
                continue
            if frames <= 0:
                continue
            duration = frames / SAMPLE_RATE
            rows.append(
                {
                    "source_id": sample_id,
                    "filename": filename,
                    "raw_transcription": raw_transcription.strip(),
                    "transcription": transcription.strip(),
                    "num_samples": frames,
                    "duration": duration,
                    "gender": gender.strip(),
                }
            )
    if not rows:
        raise RuntimeError(f"Tidak ada row FLEURS valid di {path}")
    return rows


def unique_by_transcription(rows: Iterable[dict]) -> list[dict]:
    seen: set[str] = set()
    unique: list[dict] = []
    for row in sorted(rows, key=lambda item: (item["duration"], item["filename"])):
        key = " ".join(row["transcription"].lower().split())
        if not key or key in seen:
            continue
        seen.add(key)
        unique.append(row)
    return unique


def select_rows(rows: list[dict]) -> tuple[list[dict], list[dict]]:
    eligible = [
        row
        for row in unique_by_transcription(rows)
        if 1.0 <= row["duration"] <= MAX_DURATION_SECONDS
    ]
    if len(eligible) < 30:
        raise RuntimeError(f"FLEURS subset hanya punya {len(eligible)} sample eligible; butuh 30.")

    challenging = sorted(
        eligible, key=lambda item: (item["duration"], item["filename"]), reverse=True
    )[:10]
    challenging_names = {row["filename"] for row in challenging}

    remaining = [row for row in eligible if row["filename"] not in challenging_names]
    median_duration = statistics.median(row["duration"] for row in remaining)
    clean = sorted(
        remaining,
        key=lambda item: (abs(item["duration"] - median_duration), item["filename"]),
    )[:20]

    return (
        sorted(clean, key=lambda item: item["filename"]),
        sorted(challenging, key=lambda item: item["filename"]),
    )


def parse_wav(raw: bytes) -> tuple[int, int, int, int, bytes]:
    if len(raw) < 12 or raw[:4] != b"RIFF" or raw[8:12] != b"WAVE":
        raise RuntimeError("File bukan RIFF/WAVE.")

    offset = 12
    fmt: tuple[int, int, int, int] | None = None
    audio_data: bytes | None = None

    while offset + 8 <= len(raw):
        chunk_id = raw[offset : offset + 4]
        chunk_size = struct.unpack_from("<I", raw, offset + 4)[0]
        start = offset + 8
        end = start + chunk_size
        if end > len(raw):
            raise RuntimeError("Chunk WAV terpotong.")

        if chunk_id == b"fmt ":
            if chunk_size < 16:
                raise RuntimeError("fmt WAV terlalu pendek.")
            format_tag, channels, sample_rate, _byte_rate, block_align, bits = struct.unpack_from(
                "<HHIIHH", raw, start
            )
            if format_tag == 0xFFFE and chunk_size >= 40:
                # WAVE_FORMAT_EXTENSIBLE: first 16 bits of SubFormat GUID identify PCM/IEEE float.
                format_tag = struct.unpack_from("<H", raw, start + 24)[0]
            fmt = (format_tag, channels, sample_rate, bits)
            if block_align <= 0:
                raise RuntimeError("blockAlign WAV invalid.")
        elif chunk_id == b"data":
            audio_data = raw[start:end]

        offset = end + (chunk_size & 1)

    if fmt is None or audio_data is None:
        raise RuntimeError("WAV tidak memiliki fmt/data chunk.")

    return (*fmt, audio_data)


def decode_sample(data: bytes, offset: int, format_tag: int, bits: int) -> float:
    if format_tag == 1:
        if bits == 16:
            return struct.unpack_from("<h", data, offset)[0] / 32768.0
        if bits == 24:
            value = int.from_bytes(data[offset : offset + 3], "little", signed=False)
            if value & 0x800000:
                value -= 1 << 24
            return value / 8388608.0
        if bits == 32:
            return struct.unpack_from("<i", data, offset)[0] / 2147483648.0
    elif format_tag == 3:
        if bits == 32:
            return float(struct.unpack_from("<f", data, offset)[0])
        if bits == 64:
            return float(struct.unpack_from("<d", data, offset)[0])
    raise RuntimeError(f"Format WAV tidak didukung: format={format_tag} bits={bits}")


def convert_to_pcm16_mono_16k(raw: bytes, destination: Path) -> float:
    format_tag, channels, sample_rate, bits, audio_data = parse_wav(raw)
    if sample_rate != SAMPLE_RATE:
        raise RuntimeError(f"FLEURS WAV bukan 16 kHz: {sample_rate}")
    if channels < 1:
        raise RuntimeError(f"Jumlah channel invalid: {channels}")

    bytes_per_sample = bits // 8
    if bytes_per_sample <= 0:
        raise RuntimeError(f"bitsPerSample invalid: {bits}")
    frame_size = bytes_per_sample * channels
    frame_count = len(audio_data) // frame_size

    pcm = bytearray(frame_count * 2)
    for frame_index in range(frame_count):
        frame_offset = frame_index * frame_size
        total = 0.0
        for channel in range(channels):
            total += decode_sample(
                audio_data,
                frame_offset + channel * bytes_per_sample,
                format_tag,
                bits,
            )
        value = max(-1.0, min(1.0, total / channels))
        signed = int(round(value * 32767.0))
        struct.pack_into("<h", pcm, frame_index * 2, signed)

    destination.parent.mkdir(parents=True, exist_ok=True)
    with wave.open(str(destination), "wb") as output:
        output.setnchannels(1)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        output.writeframes(bytes(pcm))

    return frame_count / SAMPLE_RATE


def placeholder_manifest(path: Path) -> bool:
    if not path.exists():
        return True
    try:
        payload = json.loads(path.read_text(encoding="utf-8-sig"))
        samples = payload.get("samples", [])
        return bool(samples) and all(
            str(sample.get("reference", "")).startswith("__FILL_")
            and float(sample.get("durationSeconds", 0)) <= 0
            for sample in samples
        )
    except (OSError, ValueError, TypeError, json.JSONDecodeError):
        return False


def materialize_language(
    language: str,
    config: dict,
    cache_dir: Path,
    audio_dir: Path,
    force: bool,
) -> list[dict]:
    locale = config["locale"]
    base = f"{FLEURS_BASE}/{FLEURS_REVISION}/data/{locale}"
    archive = cache_dir / f"{locale}-dev.tar.gz"
    metadata = cache_dir / f"{locale}-dev.tsv"

    download(
        f"{base}/audio/dev.tar.gz?download=true",
        archive,
        expected_sha256=config["archive_sha256"],
    )
    download(f"{base}/dev.tsv?download=true", metadata)

    clean_rows, challenging_rows = select_rows(read_tsv(metadata))
    selected = [
        ("clean", index + 1, row) for index, row in enumerate(clean_rows)
    ] + [
        ("challenging", index + 1, row) for index, row in enumerate(challenging_rows)
    ]

    by_filename = {row["filename"]: (category, index, row) for category, index, row in selected}
    found: set[str] = set()
    manifest_samples: list[dict] = []

    with tarfile.open(archive, "r:gz") as source:
        for member in source:
            filename = Path(member.name).name
            if filename not in by_filename or not member.isfile():
                continue

            category, index, row = by_filename[filename]
            sample_id = f"{language}-{category}-{index:02d}"
            destination = audio_dir / f"{language}-{category}" / f"{sample_id}.wav"
            if destination.exists() and not force:
                raise RuntimeError(
                    f"Target sudah ada: {destination}. Gunakan --force jika memang boleh ditimpa."
                )

            extracted = source.extractfile(member)
            if extracted is None:
                raise RuntimeError(f"Gagal membaca {member.name} dari archive.")
            duration = convert_to_pcm16_mono_16k(extracted.read(), destination)
            found.add(filename)

            manifest_samples.append(
                {
                    "id": sample_id,
                    "language": language,
                    "category": category,
                    "audio": destination.as_posix(),
                    "reference": row["raw_transcription"] or row["transcription"],
                    "durationSeconds": round(duration, 4),
                    "sourceSample": filename,
                    "sourceGender": row["gender"],
                }
            )

    missing = sorted(set(by_filename) - found)
    if missing:
        raise RuntimeError(f"{len(missing)} file terpilih tidak ditemukan di archive: {missing[:3]}")

    return sorted(manifest_samples, key=lambda item: item["id"])


def main() -> int:
    args = parse_args()
    repo_root = Path(__file__).resolve().parent.parent
    manifest = (repo_root / args.manifest).resolve()
    audio_dir = (repo_root / args.audio_dir).resolve()
    cache_dir = (repo_root / args.cache_dir).resolve()

    if manifest.exists() and not args.force and not placeholder_manifest(manifest):
        raise RuntimeError(
            f"Manifest {manifest} sudah berisi data non-placeholder. "
            "Gunakan --force hanya jika penggantian memang disengaja."
        )

    samples: list[dict] = []
    for language, config in LANGUAGES.items():
        print(f"\n== FLEURS {config['locale']} ==")
        samples.extend(
            materialize_language(language, config, cache_dir, audio_dir, args.force)
        )

    if len(samples) != 60:
        raise RuntimeError(f"Expected 60 sample, actual {len(samples)}.")

    manifest_payload = {
        "version": 1,
        "source": {
            "dataset": "Google FLEURS",
            "revision": FLEURS_REVISION,
            "split": "dev",
            "license": "CC-BY-4.0",
            "homepage": "https://huggingface.co/datasets/google/fleurs",
            "selection": (
                "Per language: 20 unique-transcript clips nearest the median duration as clean; "
                "10 longest unique-transcript clips at <=25 s as challenging long-utterance subset."
            ),
            "limitation": (
                "challenging measures long-utterance/linguistic load; it does not by itself "
                "prove robustness to natural background noise, overlap, or accent diversity."
            ),
        },
        "samples": samples,
    }
    manifest.write_text(
        json.dumps(manifest_payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print("\nDataset FLEURS T10 siap.")
    print(f"  Manifest : {manifest}")
    print(f"  Audio    : {audio_dir}")
    print(f"  Samples  : {len(samples)}")
    print("  Format   : WAV PCM signed 16-bit, mono, 16 kHz")
    print("\nCatatan: reference berasal dari metadata FLEURS. Review dengar-manusia lokal")
    print("tetap perlu dicatat sebelum CP4 diklaim PASS.")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print("\nDibatalkan.", file=sys.stderr)
        raise SystemExit(130)
    except Exception as error:
        print(f"\nERROR: {error}", file=sys.stderr)
        raise SystemExit(1)
