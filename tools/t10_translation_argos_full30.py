#!/usr/bin/env python3
"""Separate T10 offline host-only FULL30 screening of existing ID->EN fixtures.

`pilot` / `report` for the original 10 are UNCHANGED. This full30 screen
contains the same first ten + 20 additional existing fixtures; none of the
30 are an independent unseen holdout. Never interpret its descriptive
statistics as an Android result or CP4 promotion.
"""
from __future__ import annotations

import argparse
from contextlib import contextmanager
from datetime import datetime, timezone
import json
from pathlib import Path
import sys
import time
import uuid

from t10_translation_argos_candidate import (
    DEFAULT_WORK, local_paths, no_network, require_argos_packages,
)
from t10_translation_argos_offline_sbd import (
    ensure_offline_sbd, unwrap_local_cached_translation,
)
from t10_translation_argos_protocol import (
    MODEL_SHA256, REVIEW_SHA256, sha256, strict_review,
    validate_argos_archive, write_csv,
)
from t10_translation_argos_full30_protocol import (
    FULL30_DIAGNOSTIC, FULL30_IDS, EXTRA20_IDS,
    full30_rows, grade_full30,
)


def full30(review: Path, workdir: Path, *, translate_fn=None) -> Path:
    """Verify original frozen control and pinned model before 30 predictions."""
    control = strict_review(review)
    model, packages = local_paths(workdir)
    validate_argos_archive(model)
    if translate_fn is not None:
        return _generate_full30(
            control, review, workdir, translate_fn,
            sbd_mode="SYNTHETIC_TEST_ONLY",
        )
    with no_network():
        package = require_argos_packages(packages)
        direct_packages = [
            p for p in package.get_installed_packages()
            if p.from_code == "id" and p.to_code == "en"
        ]
        if len(direct_packages) != 1:
            raise RuntimeError("Expected exactly one installed isolated id->en package")
        from argostranslate import translate
        installed_langs = translate.get_installed_languages()
        source = [lang for lang in installed_langs if lang.code == "id"]
        target = [lang for lang in installed_langs if lang.code == "en"]
        if len(source) != 1 or len(target) != 1:
            raise RuntimeError("Expected unique isolated id/en language objects")
        cached = source[0].get_translation(target[0])
        backend = unwrap_local_cached_translation(cached, direct_packages[0])
        sbd_mode = ensure_offline_sbd(backend, packages)
        print("OFFLINE SENTENCE BOUNDARY READY:", sbd_mode)
        return _generate_full30(
            control, review, workdir, cached.translate,
            sbd_mode=sbd_mode,
        )


def _generate_full30(
    control: list, reviewed_path: Path, workdir: Path,
    translate_fn, *, sbd_mode: str,
) -> Path:
    session = (workdir.resolve() /
               ("argos-id-en-full30-" +
                datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") +
                "-" + uuid.uuid4().hex[:7]))
    session.mkdir(parents=True, exist_ok=False)
    metadata = {
        "experiment": FULL30_DIAGNOSTIC,
        "status": "PARTIAL_NO_QUALITY_VERDICT",
        "source_review_sha256": sha256(reviewed_path),
        "model_sha256": MODEL_SHA256,
        "source_sample_ids": list(FULL30_IDS),
        "pilot_overlap_first10": list(FULL30_IDS[:10]),
        "additional_existing_fixture20": list(EXTRA20_IDS),
        "note": (
            "Full30 shares 10 with pilot; additional 20 are from original "
            "ML Kit fixture, NOT independent holdout. All acceptance fields blank."
        ),
        "model": "Argos ID->EN 1.9 (Windows host, offline; NOT Android)",
        "offline_sbd_mode": sbd_mode,
        "cp4": "BLOCKED",
        "android_inference": "NOT_PERFORMED",
    }
    predictions = {}
    try:
        with no_network():
            for row in control:
                sid = row["id"]
                start = time.monotonic_ns()
                result = translate_fn(row["text"])
                latency_ms = (time.monotonic_ns() - start) / 1e6
                if not isinstance(result, str) or not result.strip():
                    raise ValueError("Argos produced empty full30 translation: " + sid)
                predictions[sid] = {
                    "translation": result.strip(),
                    "latency_ms": max(0.001, latency_ms),
                }
                print(f"{len(predictions):02d}/30 {sid} host_ms={latency_ms:.2f}")
        original_rows = full30_rows(control, predictions)
        raw = session / "full30.csv"
        write_csv(raw, original_rows)
        metadata["raw_sha256"] = sha256(raw)
        metadata["status"] = "HOST_FULL30_COMPLETE_REVIEW_PENDING_NOT_CP4"
        (session / "session.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("HOST FULL30 CSV:", raw)
        print("Review 30 outputs; first ten OVERLAP pilot. No quality labels inferred.")
        return session
    except BaseException as error:
        metadata["status"] = "HOST_FULL30_ABORTED_NO_QUALITY_VERDICT"
        metadata["successful_translations"] = len(predictions)
        metadata["error"] = f"{type(error).__name__}: {error}"[:350]
        (session / "session.json").write_text(
            json.dumps(metadata, indent=2, ensure_ascii=False) + "\n",
            encoding="utf-8",
        )
        print("FULL30 PARTIAL ABORT, NO scored CSV:", session, file=sys.stderr)
        raise


def report_full30(session: Path, review: Path) -> dict:
    metadata = json.loads((session / "session.json").read_text(encoding="utf-8"))
    result = grade_full30(session / "full30.csv", review, metadata)
    target = session / "full30-review-report.json"
    if target.exists():
        raise FileExistsError("Full30 report exists: refusing overwrite")
    target.write_text(
        json.dumps(result, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    all30 = result["full30"]
    extra20 = result["previously_unseen_fixture_extra20"]
    print(
        "FULL30 REVIEWED: Argos", all30["argos_accept"],
        "/30; ML Kit", all30["mlkit_whole_accept"],
        "/30; net", all30["net_additional_accepted"],
    )
    print(
        "ADDITIONAL 20 EXISTING FIXTURES: Argos", extra20["argos_accept"],
        "/20; ML Kit", extra20["mlkit_whole_accept"],
        "/20; net", extra20["net_additional_accepted"],
    )
    print("DESCRIPTIVE ONLY | INDEPENDENT HOLDOUT REQUIRED | CP4 BLOCKED")
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    run = sub.add_parser("run")
    run.add_argument("--review", type=Path, required=True,
                     help="Frozen original 120-row ML Kit review CSV")
    run.add_argument("--workdir", type=Path, default=DEFAULT_WORK)
    report = sub.add_parser("report")
    report.add_argument("--session", type=Path, required=True)
    report.add_argument("--review", type=Path, required=True,
                        help="Separate filled 30-case reviewed CSV")
    args = parser.parse_args()
    try:
        if args.cmd == "run":
            full30(args.review, args.workdir)
        else:
            report_full30(args.session.resolve(), args.review.resolve())
        return 0
    except (ValueError, RuntimeError, FileNotFoundError, FileExistsError,
            ImportError, KeyError, OSError) as error:
        print("ERROR:", error, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
