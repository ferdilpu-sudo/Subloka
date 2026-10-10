#!/usr/bin/env python3
"""T10 host-only Indonesian->English Argos model screening, NEVER CP4.

No Argos/PyTorch dependencies are required for this command's --help or tests.
Install argostranslate==1.11.0 explicitly in a dedicated Python environment
before --prepare. No paid API/cloud inference; model download happens only in
--prepare, while --pilot blocks outgoing socket connections and reads the
already-reviewed fixed ML Kit 120-row CSV as an unchanged control.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import socket
import sys
import time
import uuid
from urllib.error import HTTPError, URLError
from urllib.request import urlopen

from t10_translation_argos_offline_sbd import ensure_offline_sbd
from t10_translation_argos_protocol import (
    ROOT, MODEL_URL, MODEL_FILENAME, MODEL_SHA256, MODEL_BYTES_MIN,
    MODEL_BYTES_MAX, REVIEW_SHA256, PILOT_IDS, DIAGNOSTIC,
    sha256, strict_review, validate_argos_archive, pilot_rows,
    write_csv, grade,
)

DEFAULT_WORK = ROOT / ".t10-benchmark"
PACKAGE_SUBDIR = "argos-id-en-host"
TIMEOUT = 75


def local_paths(workdir: Path) -> tuple[Path, Path]:
    root = workdir.resolve() / PACKAGE_SUBDIR
    return root / MODEL_FILENAME, root / "packages"


def isolated_argos_env(packages: Path) -> None:
    root = packages.parent.resolve()
    # Argos settings are imported once. Assign all variables BEFORE any Argos
    # import. Avoid touching global model storage and force local CPU.
    if any(key == "argostranslate" or key.startswith("argostranslate.") for key in sys.modules):
        raise RuntimeError("Argos was loaded before isolated package settings")
    os.environ["ARGOS_PACKAGES_DIR"] = str(packages)
    os.environ["XDG_DATA_HOME"] = str(root / "data")
    os.environ["XDG_CACHE_HOME"] = str(root / "cache")
    os.environ["XDG_CONFIG_HOME"] = str(root / "config")
    os.environ["ARGOS_DEVICE_TYPE"] = "cpu"
    os.environ["ARGOS_CHUNK_TYPE"] = "ARGOSTRANSLATE"
    os.environ["ARGOS_INTER_THREADS"] = "1"
    os.environ["HF_HUB_OFFLINE"] = "1"
    os.environ["TRANSFORMERS_OFFLINE"] = "1"
    packages.mkdir(parents=True, exist_ok=True)


def require_argos_packages(packages: Path):
    isolated_argos_env(packages)
    try:
        import argostranslate.package as package
    except ImportError as error:
        raise RuntimeError(
            "Missing Argos dependencies. In an opt-in Python environment run "
            "'python -m pip install argostranslate==1.11.0' first."
        ) from error
    return package


@contextmanager
def no_network():
    original_connect = socket.socket.connect
    original_connect_ex = socket.socket.connect_ex
    original_create = socket.create_connection

    def block(*args, **kwargs):
        raise RuntimeError("Outgoing network is forbidden in offline T10 candidate inference")

    socket.socket.connect = block
    socket.socket.connect_ex = block
    socket.create_connection = block
    try:
        yield
    finally:
        socket.socket.connect = original_connect
        socket.socket.connect_ex = original_connect_ex
        socket.create_connection = original_create


def prepare(model: Path, packages: Path) -> None:
    if model.exists():
        validate_argos_archive(model)
        print("Argos ID->EN model archive already SHA256-verified:", model)
    else:
        model.parent.mkdir(parents=True, exist_ok=True)
        tmp = model.with_name(model.name + "." + uuid.uuid4().hex[:12] + ".partial")
        count = 0
        try:
            try:
                with urlopen(MODEL_URL, timeout=TIMEOUT) as response, tmp.open("xb") as out:
                    if response.geturl().split(":", 1)[0].lower() != "https":
                        raise ValueError("Model download redirected to non-HTTPS")
                    while True:
                        piece = response.read(1024 * 1024)
                        if not piece:
                            break
                        count += len(piece)
                        if count > MODEL_BYTES_MAX:
                            raise ValueError("Candidate download exceeds pinned size bound")
                        out.write(piece)
            except HTTPError as exc:
                raise RuntimeError(f"Argos pinned model download failed HTTP {exc.code}; not a device test") from exc
            except URLError as exc:
                raise RuntimeError(f"Argos model download network failure: {exc.reason}") from exc
            if count < MODEL_BYTES_MIN:
                raise ValueError("Model download is suspiciously small")
            validate_argos_archive(tmp)
            if model.exists():
                raise FileExistsError("Model destination appeared during download; refuse overwrite")
            tmp.replace(model)
        finally:
            if tmp.exists():
                tmp.unlink()
        print("Verified Argos ID->EN archive:", model, "bytes:", model.stat().st_size)
    pkg = require_argos_packages(packages)
    from argostranslate import translate
    candidates = [p for p in pkg.get_installed_packages()
                  if p.from_code == "id" and p.to_code == "en"]
    if not candidates:
        pkg.install_from_path(model)
        candidates = [p for p in pkg.get_installed_packages()
                      if p.from_code == "id" and p.to_code == "en"]
    if len(candidates) != 1:
        raise RuntimeError("Expected exactly one isolated Argos ID->EN package")
    print("PREPARE COMPLETE (local Windows host, NOT Android):", candidates[0])


def pilot(review: Path, workdir: Path, *, translate_fn=None) -> Path:
    # Do not install/download/modify any model during this phase.
    control = strict_review(review)
    model, packages = local_paths(workdir)
    validate_argos_archive(model)
    if translate_fn is None:
        with no_network():
            package = require_argos_packages(packages)
            packages_id_en = [p for p in package.get_installed_packages()
                              if p.from_code == "id" and p.to_code == "en"]
            if len(packages_id_en) != 1:
                raise RuntimeError("Isolated model not installed; run prepare online first")
            from argostranslate import translate
            # Obtain a direct id->en adapter. No pivot and no additional packages.
            languages = translate.get_installed_languages()
            sources = [x for x in languages if x.code == "id"]
            targets = [x for x in languages if x.code == "en"]
            if len(sources) != 1 or len(targets) != 1:
                raise RuntimeError("Expected isolated Indonesian and English language objects")
            direct = sources[0].get_translation(targets[0])
            # Argos lazily constructs Stanza.Pipeline with its default
            # DOWNLOAD_RESOURCES option at first translate(). Pin the SAME
            # bundled SBD resources to strictly local files before inference.
            # Keep the no_network guard for ALL initialization and inference.
            sbd_mode = ensure_offline_sbd(direct, packages)
            print("OFFLINE SENTENCE BOUNDARY READY:", sbd_mode)
            def offline_translate(sentence: str) -> str:
                return direct.translate(sentence)
            # Hold network guard through all subsequent model inference.
            return _generate_pilot(control, review, model, workdir, offline_translate,
                                   enforce_offline=True, sbd_mode=sbd_mode)
    return _generate_pilot(control, review, model, workdir, translate_fn,
                           enforce_offline=True)


def _generate_pilot(control: list, reviewed_path: Path, model: Path,
                    workdir: Path, translate_fn, *, enforce_offline: bool,
                    sbd_mode: str = "SYNTHETIC_TEST_ONLY") -> Path:
    session = (
        workdir.resolve() / (
            "argos-id-en-pilot-" +
            datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") +
            "-" + uuid.uuid4().hex[:7]
        )
    )
    session.mkdir(parents=True, exist_ok=False)
    predictions: dict[str, dict] = {}
    raw_path = session / "pilot.csv"
    metadata = {
        "experiment": DIAGNOSTIC,
        "status": "PARTIAL_NO_QUALITY_VERDICT",
        "source_review_sha256": sha256(reviewed_path),
        "model_sha256": MODEL_SHA256,
        "source_sample_ids": list(PILOT_IDS),
        "model": "Argos ID->EN 1.9 (host-only offline; NOT Android)",
        "preregistered_pilot_rule": (
            "At least two previously rejected ML Kit translations fixed, net >=2 "
            "accepted over 10, zero new negation/number/name errors. "
            "Passing is PROMISING only; then screen all 30, independent unseen "
            "holdout and physical-device integration/performance separately."
        ),
        "candidate_statuses": "ALL BLANK pending human/AI-assisted review",
        "cp4": "BLOCKED",
        "android_inference": "NOT_PERFORMED",
        "offline_sbd_mode": sbd_mode,
    }
    try:
        with no_network() if enforce_offline else _no_op():
            for source in control[:10]:
                sid = source["id"]
                start = time.monotonic_ns()
                candidate = translate_fn(source["text"])
                ms = (time.monotonic_ns() - start) / 1e6
                if not isinstance(candidate, str) or not candidate.strip():
                    raise ValueError("Argos produced blank or invalid output for " + sid)
                predictions[sid] = {"translation": candidate.strip(),
                                    "latency_ms": max(ms, 0.001)}
                print(f"{len(predictions):02d}/10 {sid} host_ms={ms:.2f}")
        rows = pilot_rows(control, predictions)
        write_csv(raw_path, rows)
        metadata["raw_sha256"] = sha256(raw_path)
        metadata["status"] = "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4"
        (session / "session.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("HOST PILOT CSV:", raw_path)
        print("No candidate acceptance labels inferred. Upload CSV to review.")
        return session
    except BaseException as error:
        metadata["status"] = "HOST_PILOT_ABORTED_NO_QUALITY_VERDICT"
        metadata["successful_translations"] = len(predictions)
        metadata["error"] = f"{type(error).__name__}: {error}"[:350]
        (session / "session.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
        )
        print("PARTIAL ABORT, NO scored CSV:", session, file=sys.stderr)
        raise


@contextmanager
def _no_op():
    yield


def report(session: Path, completed_review: Path) -> dict:
    raw = session / "pilot.csv"
    meta = json.loads((session / "session.json").read_text(encoding="utf-8"))
    if meta.get("status") != "HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4":
        raise ValueError("Host pilot is not a complete ten-output session")
    result = grade(raw, completed_review, meta)
    output = session / "review-report.json"
    if output.exists():
        raise FileExistsError("Refusing overwrite of existing graded report")
    output.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n", encoding="utf-8")
    print("Candidate reviewed:", result["argos_accept"], "/10; whole ML Kit:",
          result["baseline_accept"], "/10; net", result["net_additional_accepted"])
    print("VERDICT:", result["verdict"], "| CP4 BLOCKED")
    return result


def main() -> int:
    p = argparse.ArgumentParser(description=__doc__)
    sub = p.add_subparsers(dest="cmd", required=True)
    prepare_cmd = sub.add_parser("prepare")
    prepare_cmd.add_argument("--workdir", type=Path, default=DEFAULT_WORK)
    pilot_cmd = sub.add_parser("pilot")
    pilot_cmd.add_argument("--review", type=Path, required=True,
                           help="Exact original 120-row translation-strategy-ab-review.csv")
    pilot_cmd.add_argument("--workdir", type=Path, default=DEFAULT_WORK)
    done = sub.add_parser("report")
    done.add_argument("--session", type=Path, required=True)
    done.add_argument("--review", type=Path, required=True,
                      help="Editable copy of pilot.csv with candidate_review_status filled")
    args = p.parse_args()
    try:
        if args.cmd == "prepare":
            model, packages = local_paths(args.workdir)
            prepare(model, packages)
        elif args.cmd == "pilot":
            pilot(args.review, args.workdir)
        else:
            report(args.session.resolve(), args.review.resolve())
        return 0
    except (ValueError, RuntimeError, FileNotFoundError, FileExistsError,
            ImportError, KeyError, OSError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
