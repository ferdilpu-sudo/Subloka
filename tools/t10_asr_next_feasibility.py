#!/usr/bin/env python3
"""T10 offline Indonesian ASR candidate FEASIBILITY preflight (NO downloads).

Research only. Catalog fields are from upstream public documentation and may
change; neither source-reported WER nor Android demo is proof on Sony SO-03L.
This file never installs or runs ASR, downloads models, or promotes CP4.

Usage:
  python tools/t10_asr_next_feasibility.py
  python tools/t10_asr_next_feasibility.py --probe-device
  python tools/t10_asr_next_feasibility.py --probe-device --json .t10-benchmark/t10-asr-feasibility-1.json
"""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
from typing import Callable

ROOT = Path(__file__).resolve().parent.parent
FROZEN_ASR_REPORT = ROOT / ".agents/evidence/t10-asr-decode-final-20pairs.json"
FROZEN_SMALL_REPORT = ROOT / ".agents/evidence/t10-asr-small-model-two-pair-pilot-early-reject.json"
FROZEN_CP4_REPORT = ROOT / ".agents/evidence/t10-cp4-readiness-audit-windows-13-pass.json"

# Model-card weights are approximations, NOT measured runtime footprint or
# verified downloadable model sizes. No model URL is executable from this CLI.
CANDIDATES = (
    {
        "id": "sherpa_qwen3_asr_0_6b_int8",
        "name": "sherpa-onnx Qwen3-ASR 0.6B INT8",
        "indonesian_explicitly_supported": True,
        "android_example_listed": True,
        "published_component_weight_mib_approx": 937,
        "source": "https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html",
        "license_for_exact_converted_model_verified": False,
        "pinned_archive_sha256_verified": False,
        "host_accuracy_verified": False,
        "sony_performance_verified": False,
        "note": "Published ONNX components 42+721+174 M, plus tokenizer. "
                "Runtime RAM/storage and actual download/archive hash unknown.",
    },
    {
        "id": "wav2vec2_xlsr_large_indonesian",
        "name": "indonesian-nlp Wav2Vec2 Large XLSR Indonesian",
        "indonesian_explicitly_supported": True,
        "android_example_listed": False,
        "published_component_weight_mib_approx": 1202,
        "source": "https://huggingface.co/indonesian-nlp/wav2vec2-large-xlsr-indonesian/tree/main",
        "license_for_exact_converted_model_verified": False,
        "pinned_archive_sha256_verified": False,
        "host_accuracy_verified": False,
        "sony_performance_verified": False,
        "note": "HF pytorch_model.bin listed as 1.26 GB (decimal; ~1202 MiB). "
                "Reported 14.29% WER is from Common Voice, not T10 FLEURS. "
                "No pinned Android ONNX conversion or RAM measurement.",
    },
)

ALLOWED_QUERIES = {
    "model": ("shell", "getprop", "ro.product.model"),
    "abi": ("shell", "getprop", "ro.product.cpu.abi"),
    "mem": ("shell", "cat", "/proc/meminfo"),
    "df": ("shell", "df", "-k", "/data"),
    "battery": ("shell", "dumpsys", "battery"),
    "airplane": ("shell", "settings", "get", "global", "airplane_mode_on"),
    "wifi": ("shell", "settings", "get", "global", "wifi_on"),
}


def read_frozen_pins() -> dict[str, str]:
    out = {}
    for name, path in (("asr", FROZEN_ASR_REPORT),
                       ("small", FROZEN_SMALL_REPORT), ("cp4", FROZEN_CP4_REPORT)):
        raw = path.read_bytes()
        data = json.loads(raw.decode("utf-8-sig"))
        if name == "asr" and (
            data.get("control_errors"), data.get("paired_reference_words"),
            data.get("status")) != (105, 367, "COMPLETE_EXPERIMENT_NOT_CP4"):
            raise ValueError("Frozen 20-pair ASR evidence changed")
        if name == "small" and data.get("performance_pre_registered_rule", {}).get(
            "consequence") != "EARLY_PERFORMANCE_REJECT_P95_RTF_UNRECOVERABLE_NOT_CP4":
            raise ValueError("Small early-reject evidence changed")
        if name == "cp4" and data.get("gates", {}).get("CP4") != "BLOCKED":
            # CP4 audit evidence has a status field? Validate separately below.
            if data.get("protected_gates", {}).get("CP4") != "BLOCKED":
                raise ValueError("Prior CP4 integrity evidence changed")
        out[name] = hashlib.sha256(raw).hexdigest()
    return out


def adb_devices(text: str) -> str:
    matches = []
    for line in text.splitlines():
        line = line.strip()
        if line.startswith("List of devices attached") or not line:
            continue
        parts = line.split()
        if len(parts) >= 2 and parts[1] == "device" and re.fullmatch(r"[\w.:-]{4,120}", parts[0]):
            matches.append(parts[0])
        elif len(parts) >= 2:
            raise ValueError("ADB device not ready: " + parts[1])
        else:
            raise ValueError("Unexpected ADB devices output")
    if len(matches) != 1:
        raise ValueError("Need exactly one ready ADB device, not " + str(len(matches)))
    return matches[0]


def parse_mem_total(text: str) -> int:
    m = re.search(r"(?m)^MemTotal:\s*([0-9]+)\s+kB\s*$", text)
    if not m or not 256000 <= int(m.group(1)) <= 128_000_000:
        raise ValueError("Invalid /proc/meminfo MemTotal")
    return int(m.group(1))


def parse_data_free_kib(text: str) -> int:
    """Read /data Available in KiB from a single-row Android `df -k /data`.

    Android toybox uses a two-word "Mounted on" HEADER but a single
    mountpoint value (/data). Normalize the HEADER phrase first; never align
    raw header-token and row-token counts directly.
    """
    lines = [x.strip() for x in text.splitlines() if x.strip()]
    if len(lines) != 2:
        raise ValueError("Unexpected Android df -k output: expected header and one /data row")
    header = re.split(r"\s+", lines[0])
    if [part.lower() for part in header[-2:]] == ["mounted", "on"]:
        header = header[:-2] + ["Mounted_on"]
    elif header and header[-1].lower() in ("mounted_on", "mounted", "mountpoint"):
        header[-1] = "Mounted_on"
    else:
        raise ValueError("Unexpected Android df -k mount header")

    names = [item.lower() for item in header]
    if (len(names) != 6 or names[0] != "filesystem"
            or names[1] not in ("1k-blocks", "1024-blocks")
            or names[2] != "used"
            or names[3] not in ("available", "avail")
            or names[4] != "use%" or names[5] != "mounted_on"):
        raise ValueError("Unexpected Android df -k header")

    values = re.split(r"\s+", lines[1])
    if len(values) != len(header) or values[-1] != "/data":
        raise ValueError("Unexpected Android df -k row")
    if not all(re.fullmatch(r"[0-9]+", values[index]) for index in (1, 2, 3)):
        raise ValueError("Invalid Android df -k numeric fields")
    if not re.fullmatch(r"[0-9]{1,3}%", values[4]):
        raise ValueError("Invalid Android df -k capacity percentage")
    total, used, available = (int(values[i]) for i in (1, 2, 3))
    if not (0 < total < 2**48 and 0 <= used <= total and 0 <= available <= total):
        raise ValueError("Invalid Android /data capacity numbers")
    return available

def parse_battery_c(text: str) -> float:
    m = re.search(r"(?m)^\s*temperature:\s*([0-9]+)\s*$", text)
    if not m or not 100 <= int(m.group(1)) <= 600:
        raise ValueError("Missing or implausible battery temperature")
    return int(m.group(1)) / 10


def radio_setting(text: str, name: str) -> int:
    setting = text.strip()
    if setting not in ("0", "1"):
        raise ValueError("Unverified Android " + name + " setting")
    return int(setting)


def run_adb(adb: str, args: list[str], timeout: int = 12) -> str:
    p = subprocess.run([adb, *args], capture_output=True, text=True,
                       timeout=timeout, encoding="utf-8", errors="replace",
                       check=False)
    if p.returncode != 0:
        raise ValueError("ADB read-only command failed: " + " ".join(args))
    return p.stdout


def diagnostic_df_lines(text: str) -> list[str]:
    """Format Android df stdout for diagnosis; mask block device names.

    Do not expose ADB serials; never parse numbers here as evidence of
    capacity or deem the actual device probe successful.
    """
    lines = text.splitlines()
    if not lines or len(lines) > 24 or len(text) > 4000:
        raise ValueError("Unexpected df diagnostic length")
    result = []
    for number, line in enumerate(lines):
        # Block device path is not needed to diagnose header/token alignment.
        safe_line = re.sub(r"^([ \\t]*)/dev/[^ \\t]+",
                           r"\\1<filesystem-redacted>", line)
        result.append(f"line[{number}] token_count={len(line.split())} text={safe_line!r}")
    return result


def diagnose_device_df(adb: str, query: Callable[[str, list[str]], str] = run_adb) -> list[str]:
    """Query ONLY ADB device list and df -k /data; no state changes."""
    serial = adb_devices(query(adb, ["devices", "-l"]))
    raw = query(adb, ["-s", serial, *ALLOWED_QUERIES["df"]])
    return diagnostic_df_lines(raw)


def probe_device(adb: str, query: Callable[[str, list[str]], str] = run_adb) -> dict:
    serial = adb_devices(query(adb, ["devices", "-l"]))
    values = {
        field: query(adb, ["-s", serial, *args])
        for field, args in ALLOWED_QUERIES.items()
    }
    model = values["model"].strip()
    abi = values["abi"].strip()
    if not re.fullmatch(r"[A-Za-z0-9_.-]{2,60}", model):
        raise ValueError("Unexpected Android device model")
    if abi not in ("arm64-v8a", "armeabi-v7a", "x86_64"):
        raise ValueError("Unsupported Android ABI for candidate feasibility")
    ram = parse_mem_total(values["mem"])
    try:
        data = parse_data_free_kib(values["df"])
    except ValueError as exc:
        raise ValueError(str(exc) + "; run --diagnose-df for sanitized read-only output") from exc
    battery = parse_battery_c(values["battery"])
    airplane = radio_setting(values["airplane"], "airplane_mode_on")
    wifi = radio_setting(values["wifi"], "wifi_on")
    return {
        "device_model": model,
        "device_serial_sha256_prefix": hashlib.sha256(serial.encode()).hexdigest()[:12],
        "abi": abi,
        "mem_total_kib": ram,
        "free_data_kib": data,
        "battery_c": battery,
        "battery_is_not_cpu_temperature": True,
        "airplane_mode_on": airplane,
        "wifi_on": wifi,
        "probe_methods": list(ALLOWED_QUERIES),
        "note": "Read-only ADB snapshot, not runtime RAM headroom, free heap, "
                "actual model memory footprint, or ASR inference.",
    }


def assess(pins: dict[str, str], device: dict | None) -> dict:
    if set(pins) != {"asr", "small", "cp4"} or any(
        not re.fullmatch(r"[0-9a-f]{64}", x) for x in pins.values()
    ):
        raise ValueError("Missing or unverified frozen evidence pins")
    if device is not None and (device["mem_total_kib"] <= 0 or device["free_data_kib"] < 0):
        raise ValueError("Invalid device physical capacity")
    catalog = []
    for candidate in CANDIDATES:
        weight = candidate["published_component_weight_mib_approx"]
        item = dict(candidate)
        item["ready_for_model_download"] = False
        item["ready_for_sony_inference"] = False
        item["ready_for_cp4_promotion"] = False
        item["requirements_before_download"] = [
            "Get exact immutable model revision, verified SHA256 per artifact",
            "Verify model+conversion/runtime redistributable license",
            "Obtain user opt-in for GB-scale network/storage consumption",
            "Review Android ABI and model input/output/timestamp integration",
            "Pre-register run order, identical decoder parameters where comparable, "
            "independent holdout protocol and stop gates before inference",
        ]
        if device is not None:
            item["published_weight_over_total_ram_ratio_approx"] = round(
                weight * 1024 / device["mem_total_kib"], 3
            )
            item["free_data_over_weight_ratio_approx"] = round(
                device["free_data_kib"] / (weight * 1024), 3
            )
            item["rough_two_copies_of_weights_fit_data"] = (
                device["free_data_kib"] >= weight * 1024 * 2
            )
        catalog.append(item)
    return {
        "schema_version": 1,
        "type": "T10_NEW_ID_ASR_READ_ONLY_FEASIBILITY_NOT_A_BENCHMARK",
        "status": "RESEARCH_ONLY_NO_MODEL_SELECTED",
        "T10": "ACTIVE",
        "CP4": "BLOCKED",
        "T11": "TODO",
        "baseline_id_clean_wer": "105/367=28.61% (target <=20%)",
        "historical_small_and_beam1": "REJECTED_DO_NOT_REPLAY",
        "previous_evidence_sha256": pins,
        "device_probe": device,
        "candidates": catalog,
        "limitations": [
            "Published weight sizes approximate and do not represent runtime memory",
            "Common Voice WER is not comparable to T10 FLEURS WER",
            "Models not downloaded, independently evaluated, verified or integrated",
            "Before any inference, genuinely separate held-out speech needs frozen references/manifest",
            "No phone benchmark, production integration, translation or CP4 PASS",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--probe-device", action="store_true",
                        help="Read-only ADB device snapshot (no transfers or inference)")
    parser.add_argument("--diagnose-df", action="store_true",
                        help="Print sanitized df -k /data output shape only; no probe PASS")
    parser.add_argument("--adb", default=None,
                        help="ADB executable path; default searches PATH")
    parser.add_argument("--json", type=Path, default=None,
                        help="Write a new report exactly once; never overwrite")
    args = parser.parse_args()
    try:
        pins = read_frozen_pins()
        device = None
        if args.diagnose_df and (args.probe_device or args.json is not None):
            raise ValueError("--diagnose-df is diagnostic-only; do not combine with --probe-device or --json")
        if args.probe_device or args.diagnose_df:
            adb = args.adb or shutil.which("adb")
            if not adb and sys.platform == "win32":
                import os
                sdk = os.environ.get("ANDROID_SDK_ROOT") or os.environ.get("ANDROID_HOME")
                candidates = [
                    Path(sdk) / "platform-tools" / "adb.exe"
                ] if sdk else []
                candidates.append(
                    Path.home() / "AppData" / "Local" / "Android" / "Sdk"
                    / "platform-tools" / "adb.exe"
                )
                adb = next((str(p) for p in candidates if p.is_file()), None)
            if not adb:
                raise ValueError("ADB unavailable; add Android SDK platform-tools to PATH")
            if args.diagnose_df:
                print("ANDROID DF DIAGNOSTIC ONLY (block-device source redacted, NOT preflight PASS):")
                for line in diagnose_device_df(adb):
                    print(line)
                print("NO DOWNLOAD | NO INFERENCE | CP4 BLOCKED")
                return 0
            device = probe_device(adb)
        result = assess(pins, device)
        if args.json is not None:
            if args.json.exists():
                raise FileExistsError("Refusing to overwrite feasibility evidence: " + str(args.json))
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
            )
        if device:
            print("DEVICE SNAPSHOT:", device["device_model"], device["abi"],
                  "RAM total MiB", round(device["mem_total_kib"] / 1024),
                  "free /data MiB", round(device["free_data_kib"] / 1024),
                  "battery C", device["battery_c"])
        else:
            print("DEVICE SNAPSHOT: NOT RUN")
        for x in result["candidates"]:
            print("RESEARCH:", x["id"], "weights ~",
                  x["published_component_weight_mib_approx"], "MiB; "
                  "ARTIFACT SHA/LICENSE/SONY QA NOT VERIFIED")
        print("NO DOWNLOAD | NO INFERENCE | T10 ACTIVE | CP4 BLOCKED | T11 TODO")
        return 0
    except (OSError, ValueError, TypeError, KeyError,
            subprocess.TimeoutExpired, json.JSONDecodeError) as exc:
        print("ERROR: T10 feasibility preflight failed:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
