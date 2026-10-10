#!/usr/bin/env python3
"""T10 translation human-QA handoff tied to original offline device evidence.

Prepare a 60-row sheet from a real ML Kit result CSV. Existing AI draft
labels are provisional only when exact model outputs match its digest.
Finalize requires 60 independent human decisions and bilingual attestation.
Neither command changes CP4 baseline, translation outputs or fixture.
"""
from __future__ import annotations

import argparse
import csv
from datetime import datetime, timezone
import json
from pathlib import Path
import sys

from t10_translation_review import (
    FIELDS, REQUIRED, STATUS, content_digest, fingerprint,
    load, report, verify,
)

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = ROOT / "engine/translation/src/androidTest/assets/t10_translation_fixtures.json"
DRAFT = ROOT / "tools/t10_translation_ai_draft.json"
HUMAN_COLUMNS = (*REQUIRED, "provisional_ai_status", "provisional_ai_notes",
                 "human_status", "human_notes")
SESSION_VERSION = 1


def read_fixtures(path: Path = FIXTURES) -> dict[str, dict]:
    data = json.loads(path.read_text(encoding="utf-8-sig"))
    items = data.get("samples")
    if not isinstance(items, list) or len(items) != 60:
        raise ValueError("Expected frozen 60-sample translation fixture")
    keyed = {}
    for row in items:
        sid = row["id"]
        if sid in keyed:
            raise ValueError("Duplicate translation fixture " + sid)
        keyed[sid] = row
    return keyed


def check_fixture_identity(rows: list[dict], fixture_path: Path = FIXTURES) -> None:
    verify(rows)
    expected = read_fixtures(fixture_path)
    if {row["sample"] for row in rows} != set(expected):
        raise ValueError("Raw sample IDs do not match frozen translation fixtures")
    for row in rows:
        fixture = expected[row["sample"]]
        src = fixture["language"]
        target = "id" if src == "en" else "en"
        if (row["source_language"], row["target_language"], row["source_text"]) != (
                src, target, fixture["text"]):
            raise ValueError("Fixture/source text mismatch: " + row["sample"])


def ai_projection(rows: list[dict], draft_file: Path) -> tuple[bool, dict[str, tuple[str, str]]]:
    draft = json.loads(draft_file.read_text(encoding="utf-8"))
    if draft.get("version") != 1 or draft.get("default_status") != "ACCEPT":
        raise ValueError("Unsupported translation AI draft format")
    if content_digest(rows) != draft.get("source_content_sha256"):
        return False, {r["sample"]: ("NOT_APPLICABLE", "") for r in rows}
    override = draft.get("overrides", {})
    notes = draft.get("accept_notes", {})
    ids = {r["sample"] for r in rows}
    if not isinstance(override, dict) or not isinstance(notes, dict):
        raise ValueError("Malformed AI draft")
    if not set(override).issubset(ids) or not set(notes).issubset(ids - set(override)):
        raise ValueError("Unknown draft ID")
    projection = {}
    for row in rows:
        sid = row["sample"]
        decision = override.get(sid, {})
        if not isinstance(decision, dict):
            raise ValueError("Malformed AI decision")
        status = decision.get("status", "ACCEPT")
        note = decision.get("notes", notes.get(sid, ""))
        if status not in STATUS or not isinstance(note, str):
            raise ValueError("Invalid AI draft status or notes for " + sid)
        projection[sid] = (status, note)
    return True, projection


def write_csv(path: Path, columns: tuple, rows: list[dict]) -> None:
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns, extrasaction="ignore")
        writer.writeheader()
        writer.writerows(rows)


def prepare(raw: Path, outdir: Path, fixture_path: Path = FIXTURES,
            draft_file: Path = DRAFT) -> dict:
    rows = load(raw)
    check_fixture_identity(rows, fixture_path)
    ai_matches, projected = ai_projection(rows, draft_file)
    if outdir.exists():
        raise FileExistsError("Session directory exists; create a new folder: " + str(outdir))
    metadata = {
        "version": SESSION_VERSION,
        "evidence_type": "T10 HUMAN_REVIEW_HANDOFF; not CP4 gate",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": fingerprint(raw),
        "raw_content_digest": content_digest(rows),
        "fixture_sha256": fingerprint(fixture_path),
        "ai_draft_sha256": fingerprint(draft_file),
        "ai_draft_exact_output_match": ai_matches,
        "sample_count": 60,
        "human_review_completed": False,
        "instructions": "Human statuses start blank; independently review all 60. AI labels are hints only.",
    }
    sheet = [
        {
            **{key: row[key] for key in REQUIRED},
            "provisional_ai_status": projected[row["sample"]][0],
            "provisional_ai_notes": projected[row["sample"]][1],
            "human_status": "",
            "human_notes": "",
        }
        for row in rows
    ]
    outdir.mkdir(parents=True)
    write_csv(outdir / "human-review.csv", HUMAN_COLUMNS, sheet)
    (outdir / "review-session.json").write_text(
        json.dumps(metadata, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    flagged = [r["sample"] for r in sheet if r["provisional_ai_status"] not in
               ("ACCEPT", "NOT_APPLICABLE")]
    notes = [
        "# T10 translation bilingual human QA", "",
        "**Independent human review, NOT another AI re-scoring.**",
        "Fill all 60 human_status cells; leave no unreviewed row.",
        "Allowed statuses: " + ", ".join(sorted(STATUS)),
        "For every rejection, explain the concrete translation defect in human_notes.",
        "When overriding a provisional AI label, explain the disagreement in human_notes.",
        "Never edit original source, translation, timing, sample ID or AI columns.",
        "Never replace actual ML Kit outputs with a suggested correction.",
        "",
        "Draft: " + ("exact device output match" if ai_matches else
                     "NOT_APPLICABLE: model outputs differ; previous AI judgments cannot be reused"),
        "Provisional flagged IDs: " + (", ".join(flagged) if flagged else "none"),
        "Review 60 outputs, including modal force, tense, gender, numbers, names and negation.",
        "",
        "After manual bilingual review, run finalize with an explicit reviewer attestation.",
        "Finalize produces quality-threshold evidence only: CP4 stays blocked until every gate passes.",
    ]
    (outdir / "REVIEW_INSTRUCTIONS.md").write_text("\n".join(notes) + "\n", encoding="utf-8")
    print("Human-QA session created:", outdir)
    print("Raw SHA256:", metadata["raw_sha256"])
    print("AI draft exact-output match:", ai_matches)
    print("All 60 human_status cells must be filled; AI labels are NOT human decisions.")
    return metadata


def validate_human_sheet(raw_rows: list[dict], sheet_path: Path, draft_file: Path) -> list[dict]:
    with sheet_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if set(reader.fieldnames or ()) != set(HUMAN_COLUMNS) or len(reader.fieldnames or ()) != len(HUMAN_COLUMNS):
            raise ValueError("Reviewer columns changed; restore original sheet schema")
        sheet = list(reader)
    if len(sheet) != 60 or len({r["sample"] for r in sheet}) != 60:
        raise ValueError("Reviewer sheet must have exactly 60 unique original sample IDs")
    by_id = {r["sample"]: r for r in raw_rows}
    if {r["sample"] for r in sheet} != set(by_id):
        raise ValueError("Reviewer sheet IDs differ from device raw CSV")
    _, ai = ai_projection(raw_rows, draft_file)
    output = []
    for row in sheet:
        sid = row["sample"]
        old = by_id[sid]
        if any(row[key] != old[key] for key in REQUIRED):
            raise ValueError("Original model evidence edited in review sheet: " + sid)
        if (row["provisional_ai_status"], row["provisional_ai_notes"]) != ai[sid]:
            raise ValueError("Provisional AI labels were edited: " + sid)
        status, notes = row["human_status"].strip(), row["human_notes"].strip()
        if status not in STATUS:
            raise ValueError("Missing/invalid human decision: " + sid)
        if status != "ACCEPT" and not notes:
            raise ValueError("Rejected output needs human meaning explanation: " + sid)
        if ai[sid][0] != "NOT_APPLICABLE" and status != ai[sid][0] and not notes:
            raise ValueError("Disagreement with provisional AI label needs explanation: " + sid)
        output.append({**old, "status": status, "notes": notes})
    return output



def check_review(raw: Path, outdir: Path, review_file: Path,
                 fixture_path: Path = FIXTURES, draft_file: Path = DRAFT) -> dict:
    """Read-only external 60-case sheet preflight; NOT an attestation or CP4 PASS.

    Unlike finalize(), this checks the supplied external CSV without copying
    it into the original session or writing any graded/signoff artifacts.
    """
    session = json.loads((outdir / "review-session.json").read_text(encoding="utf-8"))
    if session.get("version") != SESSION_VERSION or session.get("sample_count") != 60:
        raise ValueError("Unsupported human-QA session")
    originals = load(raw)
    check_fixture_identity(originals, fixture_path)
    if session["raw_sha256"] != fingerprint(raw) or session["raw_content_digest"] != content_digest(originals):
        raise ValueError("Original raw CSV changed since QA sheet preparation")
    if session["fixture_sha256"] != fingerprint(fixture_path):
        raise ValueError("Frozen original translation fixture changed")
    if session["ai_draft_sha256"] != fingerprint(draft_file):
        raise ValueError("Provisional AI draft changed since QA sheet preparation")

    # Give reviewer all missing disagreement-note IDs at once, while keeping
    # the original validator as authoritative for the remaining field checks.
    with review_file.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        fields = reader.fieldnames
        rated = list(reader)
    if fields != list(HUMAN_COLUMNS) or len(rated) != 60:
        raise ValueError("External reviewer CSV requires exact 60-row original schema/order")
    missing = [
        row.get("sample", "<missing>")
        for row in rated
        if row.get("human_status") in STATUS
        and row.get("provisional_ai_status") not in ("NOT_APPLICABLE", row.get("human_status"))
        and not (row.get("human_notes") or "").strip()
    ]
    if missing:
        raise ValueError("Missing reviewer rationale for changed AI decisions: " + ", ".join(missing))
    completed = validate_human_sheet(originals, review_file, draft_file)
    en_accepted = sum(row["source_language"] == "en" and row["status"] == "ACCEPT"
                      for row in completed)
    id_accepted = sum(row["source_language"] == "id" and row["status"] == "ACCEPT"
                      for row in completed)
    result = {
        "status": "EXTERNAL_SHEET_INTEGRITY_PASS_NOT_HUMAN_ATTESTED_NOT_CP4",
        "sample_count": len(completed),
        "en_to_id_accepted": en_accepted,
        "id_to_en_accepted": id_accepted,
        "review_sha256": fingerprint(review_file),
        "raw_sha256": fingerprint(raw),
        "human_review_independence_verified": False,
        "cp4_status": "BLOCKED",
    }
    print("REVIEW INTEGRITY PASS: 60/60 labels, original evidence unchanged")
    print(f"EN->ID {en_accepted}/30; ID->EN {id_accepted}/30")
    print("NOT HUMAN-ATTESTED | CP4 BLOCKED | no files changed")
    return result


def finalize(raw: Path, outdir: Path, reviewer: str, attested: bool,
             fixture_path: Path = FIXTURES, draft_file: Path = DRAFT) -> dict:
    if not reviewer.strip() or not attested:
        raise ValueError("Require named reviewer and --attest-independent-bilingual-review")
    session = json.loads((outdir / "review-session.json").read_text(encoding="utf-8"))
    if session.get("version") != SESSION_VERSION or session.get("sample_count") != 60:
        raise ValueError("Unsupported human-QA session")
    originals = load(raw)
    check_fixture_identity(originals, fixture_path)
    if session["raw_sha256"] != fingerprint(raw) or session["raw_content_digest"] != content_digest(originals):
        raise ValueError("Original raw CSV changed since QA sheet generation")
    if session["fixture_sha256"] != fingerprint(fixture_path):
        raise ValueError("Frozen fixture changed since session preparation")
    if session["ai_draft_sha256"] != fingerprint(draft_file):
        raise ValueError("AI draft changed since session preparation")
    completed = validate_human_sheet(originals, outdir / "human-review.csv", draft_file)
    paths = [outdir / name for name in
             ("human-reviewed.csv", "human-quality-report.json", "human-signoff.json")]
    if any(p.exists() for p in paths):
        raise FileExistsError("Finalized review already exists; refusing overwrite")
    write_csv(paths[0], FIELDS, completed)
    quality_threshold_met = report(paths[0], paths[1])
    report_data = json.loads(paths[1].read_text(encoding="utf-8"))
    signed = {
        "evidence_type": "T10 DECLARED HUMAN BILINGUAL REVIEW; not automatic CP4 pass",
        "reviewer_name": reviewer.strip(),
        "attestation": "Reviewer declares independent bilingual judgment of all 60 actual ML Kit outputs",
        "signed_utc": datetime.now(timezone.utc).isoformat(),
        "raw_sha256": fingerprint(raw),
        "human_review_sheet_sha256": fingerprint(outdir / "human-review.csv"),
        "human_reviewed_csv_sha256": fingerprint(paths[0]),
        "human_quality_report_sha256": fingerprint(paths[1]),
        "ai_draft_exact_output_match": session["ai_draft_exact_output_match"],
        "reviewed_all_60": True,
        "both_directions_quality_threshold_met_from_labels": quality_threshold_met,
        "quality_directions": report_data["directions"],
        "offline_and_reviewer_validity": "External audit required; reviewer identity is not authenticated",
        "cp4_status": "BLOCKED",
        "baseline_and_model_output_unchanged": True,
    }
    paths[2].write_text(json.dumps(signed, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Human bilingual QA report:", paths[2])
    print("CP4 remains BLOCKED; quality labels do not override ASR/E2E gates.")
    return signed


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="cmd", required=True)
    prep = sub.add_parser("prepare", help="Make 60-row human QA sheet from original device raw CSV")
    prep.add_argument("raw", type=Path)
    prep.add_argument("session_dir", type=Path)
    check = sub.add_parser("check", help="Read-only validate external completed sheet before human signoff")
    check.add_argument("raw", type=Path)
    check.add_argument("session_dir", type=Path)
    check.add_argument("--review", type=Path, required=True)
    finish = sub.add_parser("finalize", help="Check complete independent review and export signed report")
    finish.add_argument("raw", type=Path)
    finish.add_argument("session_dir", type=Path)
    finish.add_argument("--reviewer", required=True)
    finish.add_argument("--attest-independent-bilingual-review", action="store_true")
    args = parser.parse_args()
    try:
        if args.cmd == "prepare":
            prepare(args.raw, args.session_dir)
        elif args.cmd == "check":
            check_review(args.raw, args.session_dir, args.review)
        else:
            finalize(args.raw, args.session_dir, args.reviewer, args.attest_independent_bilingual_review)
        return 0
    except (ValueError, KeyError, FileNotFoundError, FileExistsError, csv.Error, json.JSONDecodeError) as exc:
        print("ERROR:", exc, file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
