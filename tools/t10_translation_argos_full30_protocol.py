"""T10 host-only Argos ID->EN full-30 descriptive screen.

This is NOT the previously preregistered ten-case pilot and is NOT an
independent unseen holdout. The first ten samples OVERLAP the pilot.
No new thirty-case promotion threshold is invented here.
"""
from __future__ import annotations

import math

from t10_translation_argos_protocol import (
    MODEL_SHA256, OUTPUT_COLUMNS, PILOT_IDS, REVIEW_SHA256, sha256,
)
from t10_translation_strategy_ab_review import STATUS, read_csv

FULL30_IDS = tuple(f"id-ab-{i:02d}" for i in range(1, 31))
EXTRA20_IDS = FULL30_IDS[10:]
FULL30_DIAGNOSTIC = "T10_ARGOS_ID_EN_HOST_FULL30_DESCRIPTIVE_NOT_HOLDOUT_NOT_CP4"


def full30_rows(reviewed: list[dict], translated: dict) -> list[dict]:
    """Generate unchanged source/ML Kit control fields with EMPTY candidate QA."""
    if len(reviewed) != 30 or tuple(row["id"] for row in reviewed) != FULL30_IDS:
        raise ValueError("Full30 must use all 30 frozen Indonesian source fixtures")
    if tuple(translated) != FULL30_IDS:
        raise ValueError("Full30 inference must contain exactly 30 pinned sample IDs in order")
    result = []
    for row in reviewed:
        sid = row["id"]
        value = translated[sid]
        if (not isinstance(value, dict)
                or not isinstance(value.get("translation"), str)
                or not value["translation"].strip()
                or not isinstance(value.get("latency_ms"), (int, float))
                or isinstance(value["latency_ms"], bool)
                or not math.isfinite(value["latency_ms"])
                or value["latency_ms"] <= 0):
            raise ValueError("Invalid full30 candidate translation/latency: " + sid)
        control = row["mlkit"]
        result.append({
            "sample": sid,
            "source_text": row["text"],
            "risk_tag": row["risk_tag"],
            "mlkit_whole_translation": control["translation"],
            "mlkit_whole_status": control["status"],
            "mlkit_whole_notes": control["notes"],
            "argos_translation": value["translation"].strip(),
            "argos_latency_ms": f'{value["latency_ms"]:.3f}',
            "error": "",
            "candidate_review_status": "",
            "candidate_notes": "",
        })
    return result


def grade_full30(raw, review, session: dict) -> dict:
    """Describe all 30 + disjoint 20-extra subset without CP4/promotion claims."""
    if session.get("experiment") != FULL30_DIAGNOSTIC:
        raise ValueError("Expected dedicated full30 host session")
    if session.get("status") != "HOST_FULL30_COMPLETE_REVIEW_PENDING_NOT_CP4":
        raise ValueError("Full30 session is not complete")
    if session.get("source_review_sha256") != REVIEW_SHA256:
        raise ValueError("Frozen ML Kit review SHA does not match")
    if session.get("model_sha256") != MODEL_SHA256:
        raise ValueError("Pinned Argos model SHA does not match")
    if session.get("source_sample_ids") != list(FULL30_IDS):
        raise ValueError("Full30 fixture order is not pinned")
    if session.get("raw_sha256") != sha256(raw):
        raise ValueError("Full30 raw evidence hash does not match session")

    original = read_csv(raw, OUTPUT_COLUMNS)
    revised = read_csv(review, OUTPUT_COLUMNS)
    if (len(original) != 30 or len(revised) != 30
            or tuple(r["sample"] for r in original) != FULL30_IDS
            or tuple(r["sample"] for r in revised) != FULL30_IDS):
        raise ValueError("Full30 review must cover the same 30 fixtures in order")

    per_case = []
    for initial, rated in zip(original, revised):
        if any(initial[k] != rated[k] for k in OUTPUT_COLUMNS[:-2]):
            raise ValueError("Full30 reviewer altered immutable raw/control fields")
        if initial["candidate_review_status"] or initial["candidate_notes"]:
            raise ValueError("Full30 original is not an unreviewed output")
        if (not initial["argos_translation"].strip() or
                not initial["mlkit_whole_translation"].strip() or
                initial["error"].strip()):
            raise ValueError("Missing full30 candidate or frozen ML Kit output")
        if rated["candidate_review_status"] not in STATUS:
            raise ValueError("Missing/invalid full30 reviewer status")
        if (rated["candidate_review_status"] != "ACCEPT"
                and not rated["candidate_notes"].strip()):
            raise ValueError("Full30 rejection must include reviewer explanation")

        baseline = initial["mlkit_whole_status"]
        candidate = rated["candidate_review_status"]
        if baseline not in STATUS:
            raise ValueError("Unknown frozen ML Kit review status")
        per_case.append({
            "sample": initial["sample"],
            "mlkit_accepted": baseline == "ACCEPT",
            "argos_accepted": candidate == "ACCEPT",
            "new_critical": (
                candidate in ("NEGATION_ERROR", "NUMBER_OR_NAME_ERROR")
                and baseline not in ("NEGATION_ERROR", "NUMBER_OR_NAME_ERROR")
            ),
        })

    def count(rows: list[dict]) -> dict:
        wins = sum(r["argos_accepted"] and not r["mlkit_accepted"] for r in rows)
        losses = sum(r["mlkit_accepted"] and not r["argos_accepted"] for r in rows)
        return {
            "sample_count": len(rows),
            "mlkit_whole_accept": sum(r["mlkit_accepted"] for r in rows),
            "argos_accept": sum(r["argos_accepted"] for r in rows),
            "wins": wins,
            "losses": losses,
            "net_additional_accepted": wins - losses,
            "new_critical_errors": [r["sample"] for r in rows if r["new_critical"]],
        }

    return {
        "experiment": FULL30_DIAGNOSTIC,
        "source_review_sha256": REVIEW_SHA256,
        "model_sha256": MODEL_SHA256,
        "raw_sha256": session["raw_sha256"],
        "review_sha256": sha256(review),
        "full30": count(per_case),
        "pilot_overlap_first10": count(per_case[:10]),
        "previously_unseen_fixture_extra20": count(per_case[10:]),
        "extra20_sample_ids": list(EXTRA20_IDS),
        "independent_holdout": "NOT_PERFORMED (all 30 are existing frozen fixtures)",
        "verdict": "DESCRIPTIVE_FULL30_ONLY_INDEPENDENT_HOLDOUT_REQUIRED",
        "performance": "Host Windows CPU only; not Android latency",
        "android_engine": "NOT_INTEGRATED_OR_TESTED",
        "cp4": "BLOCKED",
    }
