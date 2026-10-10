#!/usr/bin/env python3
"""Read-only CP4 readiness audit from pinned, committed T10 evidence.

Do NOT conflate historical single-segment translation CP4 scores with
the later 60-paragraph strategy A/B or host-only Argos full30 screen.
This tool NEVER promotes CP4, changes model weights, regrades a fixture,
runs network, or consumes private media/transcripts.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT = Path(__file__).resolve().parent.parent
EVIDENCE = {
    "asr": "t10-asr-decode-final-20pairs.json",
    "small": "t10-asr-small-model-two-pair-pilot-early-reject.json",
    "media": "t10-real-video-media-stage-sony-json-verified.json",
    "translation": "t10-translation-strategy-ab-review-complete.json",
    "argos": "t10-argos-full30-official-net-zero-no-promotion.json",
}
ORIGINAL_ASR_ID_ERRORS = 105
ORIGINAL_ASR_ID_WORDS = 367
ORIGINAL_TRANSLATION_ID_ACCEPT = 24
ORIGINAL_TRANSLATION_EN_ACCEPT = 27
TRANSLATION_CASES_PER_DIRECTION = 30
MAX_ASR_WER = .20
MIN_TRANSLATION_ACCEPT = .90


def _load(path: Path) -> tuple[dict, str]:
    raw = path.read_bytes()
    data = json.loads(raw.decode("utf-8-sig"))
    if not isinstance(data, dict):
        raise ValueError("T10 evidence must be JSON objects: " + path.name)
    return data, hashlib.sha256(raw).hexdigest()


def _expect(ok: bool, description: str) -> None:
    if not ok:
        raise ValueError("T10 evidence inconsistency: " + description)


def evaluate(evidence: dict[str, dict]) -> dict:
    """Fail closed on incompatible evidence; never infer missing gates as PASS."""
    _expect(set(evidence) == set(EVIDENCE), "wrong number/identity of evidence sources")
    asr, small, media = (evidence[k] for k in ("asr", "small", "media"))
    translation, argos = evidence["translation"], evidence["argos"]

    _expect(
        (asr.get("paired_samples"), asr.get("control_errors"),
         asr.get("paired_reference_words"), asr.get("beam1_errors"))
        == (20, 105, 367, 110)
        and asr.get("status") == "COMPLETE_EXPERIMENT_NOT_CP4"
        and asr.get("official_CP4", {}).get("status") == "BLOCKED",
        "frozen Indonesian clean ASR baseline or paired decoding results changed",
    )
    _expect(
        small.get("performance_pre_registered_rule", {}).get("consequence")
        == "EARLY_PERFORMANCE_REJECT_P95_RTF_UNRECOVERABLE_NOT_CP4"
        and small.get("completed_pairs") == 2
        and small.get("performance_pre_registered_rule", {})
                 .get("currently_observed_small_rtfs_strictly_over_2") == 2,
        "Small-q5_1 early performance rejection changed",
    )
    _expect(
        media.get("observed_status") == "MEDIA_STAGE_PASS_NOT_FULL_E2E"
        and media.get("validation", {}).get("all_checks_passed") is True
        and media.get("scientific_limits", []) != [],
        "one-device media stage is not a validated MEDIA-only PASS",
    )
    official = translation.get("official_gate_unchanged", {})
    _expect(
        official.get("historical_translation_ID_to_EN_ACCEPT") == "24/30"
        and official.get("historical_translation_EN_to_ID_ACCEPT") == "27/30"
        and official.get("historical_ASR_ID_clean_micro_WER") == "105/367=28.61%"
        and official.get("real_ten_minute_app_video_E2E") == "NOT_DONE",
        "historical CP4 translation/ASR/E2E gate snapshot changed",
    )
    paragraph = translation.get("experiment", {}).get("results_by_direction", {})
    _expect(
        paragraph.get("id->en", {}).get("whole_ACCEPT") == 21
        and paragraph.get("en->id", {}).get("whole_ACCEPT") == 22
        and translation.get("review_sha256")
        == "516ca5d8967aefa7046db65e53fb1788ef7267bb48f7f34ada48eb72d20018a9",
        "later paragraph ML Kit diagnostic changed; not CP4 original fixture",
    )
    aggregates = argos.get("confirmed_aggregates", {})
    all30 = aggregates.get("full30", {})
    extra20 = aggregates.get("additional_existing20", {})
    _expect(
        (all30.get("argos_accept"), all30.get("mlkit_accept"),
         all30.get("net_additional_accepted")) == (21, 21, 0)
        and (extra20.get("argos_accept"), extra20.get("mlkit_accept"),
             extra20.get("net_additional_accepted")) == (13, 15, -2)
        and argos.get("decision", {}).get("reporter_verdict")
        == "DESCRIPTIVE ONLY | INDEPENDENT HOLDOUT REQUIRED | CP4 BLOCKED",
        "official host-only Argos full30 decision changed",
    )

    # The frozen CP4 clean-ID threshold is applied to this known subset.
    # A failing mandatory subset is enough to keep CP4 blocked; passing a
    # subset could never establish a CP4 PASS.
    _expect(MAX_ASR_WER == .20 and MIN_TRANSLATION_ACCEPT == .90,
            "CP4 thresholds changed")
    max_errors = math.floor(MAX_ASR_WER * ORIGINAL_ASR_ID_WORDS)
    needed_translations = math.ceil(MIN_TRANSLATION_ACCEPT * TRANSLATION_CASES_PER_DIRECTION)
    _expect(max_errors == 73 and needed_translations == 27,
            "CP4 threshold arithmetic changed")

    return {
        "schema_version": 1,
        "type": "T10_CP4_READ_ONLY_EVIDENCE_AUDIT",
        "cp4_status": "BLOCKED",
        "t10_status": "ACTIVE",
        "t11_status": "TODO",
        "asr_clean_id": {
            "source": "20-item frozen FLEURS ID-clean device/archived benchmark",
            "base_word_errors": ORIGINAL_ASR_ID_ERRORS,
            "reference_words": ORIGINAL_ASR_ID_WORDS,
            "micro_wer": round(ORIGINAL_ASR_ID_ERRORS / ORIGINAL_ASR_ID_WORDS, 6),
            "maximum_allowed_wer": MAX_ASR_WER,
            "maximum_errors_at_frozen_length": max_errors,
            "minimum_edit_reduction_to_gate": ORIGINAL_ASR_ID_ERRORS - max_errors,
            "status": "FAIL_MANDATORY_SUBSET",
            "decoder_beam1": "REJECTED_110_EDITS_VS_105",
            "small_q5_1": "EARLY_REJECTED_RTF_GATE_UNRECOVERABLE",
            "baseline_provenance": "User-reported final device summary, not independent raw ASR run log",
        },
        "translation_original_cp4": {
            "source": "Historical 30 single-segment review per direction, not paragraph A/B",
            "required_accepted_per_direction": needed_translations,
            "id_en_accepted": ORIGINAL_TRANSLATION_ID_ACCEPT,
            "id_en_gap": needed_translations - ORIGINAL_TRANSLATION_ID_ACCEPT,
            "en_id_accepted": ORIGINAL_TRANSLATION_EN_ACCEPT,
            "en_id_gap": max(0, needed_translations - ORIGINAL_TRANSLATION_EN_ACCEPT),
            "status": "FAIL_ID_TO_EN_HISTORICAL_AI_ASSISTED_REVIEW",
            "human_independent_review": "NOT_ATTESTED",
        },
        "later_paragraph_translation_diagnostic": {
            "source": "Different 60-paragraph whole-versus-linewise dataset",
            "mlkit_id_en_whole_accepted": 21,
            "mlkit_en_id_whole_accepted": 22,
            "used_as_original_cp4": False,
        },
        "argos_host_full30": {
            "source": "Separate Indonesian-to-English 30-paragraph host-screen",
            "argos_accepted": 21,
            "mlkit_control_accepted": 21,
            "net_acceptance_gain": 0,
            "additional20_net_gain": -2,
            "independent_holdout_performed": False,
            "android_inference_performed": False,
            "recommendation": "DO_NOT_PROMOTE_ARGOS_ON_CURRENT_EVIDENCE",
        },
        "sony_real_video_media": {
            "source": "One Sony SO-03L video (734.57 s); inspect + PCM decode only",
            "status": "MEDIA_STAGE_PASS_NOT_FULL_E2E",
            "duration_seconds": media["media"]["duration_seconds"],
            "input_source_unchanged": True,
            "full_app_video_to_subtitle_export_e2e": "NOT_RUN",
        },
        "pending": [
            "Separately preregistered ASR accuracy candidate and independent validation",
            "Independently verified human bilingual QA on original CP4 translation",
            "Production ASR/translation/subtitle renderer/export pipeline is not integrated",
            "Full offline Android video-to-subtitle E2E plus resource/thermal proof",
            "User decision for any change to CP4 scope or engineering direction",
        ],
        "interpretation": (
            "At least one mandatory quality subset fails; a successful Sony media "
            "decode and exploratory host Argos outputs cannot promote CP4."
        ),
    }


def audit(root: Path) -> dict:
    data, hashes = {}, {}
    for key, filename in EVIDENCE.items():
        path = root / filename
        data[key], hashes[key] = _load(path)
    result = evaluate(data)
    result["evidence_sha256"] = hashes
    return result


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--evidence-dir", type=Path,
        default=ROOT / ".agents" / "evidence",
        help="Directory of committed T10 evidence JSON (read-only)",
    )
    parser.add_argument(
        "--json", type=Path, default=None,
        help="Optional output file in ignored local benchmark; never overwrite",
    )
    args = parser.parse_args()
    try:
        summary = audit(args.evidence_dir)
        if args.json is not None:
            if args.json.exists():
                raise FileExistsError("Refusing to overwrite CP4 audit: " + str(args.json))
            args.json.parent.mkdir(parents=True, exist_ok=True)
            args.json.write_text(
                json.dumps(summary, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
        asr = summary["asr_clean_id"]
        translation = summary["translation_original_cp4"]
        print(
            f"ASR Indonesian clean: {asr['base_word_errors']}/"
            f"{asr['reference_words']} edits, WER {asr['micro_wer']:.2%}; "
            f"requires >= {asr['minimum_edit_reduction_to_gate']} fewer errors"
        )
        print(
            "Original CP4 ID->EN accepted:", translation["id_en_accepted"],
            "/30, needs", translation["required_accepted_per_direction"],
            "/30 (gap", translation["id_en_gap"], ")"
        )
        print("Sony video 734s: MEDIA_STAGE_PASS, NOT full E2E")
        print("Argos host full30: 21/30 vs 21/30, net 0; NOT Android")
        print("T10 ACTIVE | CP4 BLOCKED | T11 TODO")
        return 0
    except (OSError, ValueError, TypeError, KeyError, json.JSONDecodeError) as error:
        print("ERROR: CP4 audit blocked: " + str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
