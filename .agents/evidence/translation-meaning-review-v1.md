# QA-TRANSLATION-MEANING-REVIEW-001 — Beta5 referent error: reviewer warning, not model improvement

Date: 2026-11-03. Baseline: owner-signed Beta5 `0.7.0-beta.5`, `versionCode=335`, build [#335](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41597729628), [PR #12](https://github.com/ferdilpu-sudo/Subloka/pull/12) Draft. User-provided screenshot showed a well-rendered 9:16 preview but a machine translation with a referent/recipient ambiguity. No private screenshot or exact user dialogue is stored in source control.

## Findings
- TranslateGemma's native `GemmaSession.translate(text, fromId)` currently receives a single caption; no adjacent-caption contextual coreference. Its prompt requests accurate nuanced translation but cannot guarantee speaker/recipient identity.
- Existing `TranslationFidelityGuard` is a static conservative diagnostic (numbers, negation, prohibition, tense, gender, terms); it neither measures semantic equivalence nor reliably identifies shifted agents/recipients. Historical guard evidence states 4/9 material reviewer findings flagged with several false positives, and historical CP4 remains BLOCKED. Do not reinterpret heuristic flags as independent bilingual acceptance.
- `TranslationStatus.CURRENT` signifies same source revision, not verified meaning. `TranslationOrigins` already persists provenance, and `TranslationEligibility` protects manually corrected translations from automatic replacement.

## Patch (safe, UI-only signaling)
- Added `TranslationOrigins.isCurrentMachineTranslation(segment)` to identify *fresh* MACHINE/MACHINE_GEMMA/MACHINE_MLKIT captions only, not MANUAL, NONE, stale, missing, or outputs with unmatched revision.
- In Caption Editor show a small non-blocking, clearly worded warning for fresh machine output: inspect who acts/receives an action, pronouns, and negation. The warning is **not** a scoring system or machine self-correction; it disappears after a manual correction changes origin to MANUAL.
- Export warning surface already appears only for Translation and Both, never Original-only. Add a generic model-agnostic meaning-review advisory for current machine outputs alongside existing provider/licensing notices. Do not relabel legacy ML Kit as Gemma or change Google attribution.
- New domain unit and Android Compose tests check machine-only warning, stale/manual suppression, before/after explicit manual edit, SOURCE-only export warning absence, and translation export advisory presence.
- No edits to C++ prompts, inference, model files, model downloads, auto-replacement eligibility, Room schema, caption persistence, render behavior, timings, export payloads, signing, privacy, or stable `main`.

## Verification and limitations
At creation: new PR CI **NOT_RUN**, no new signed APK, no new on-device QA. Preserve installed Beta5 #335 and all corrections. Compare warning clarity and manual-edit protection on Sony only after CI PASS and a separately approved owner-signed versionCode >335 preview.

Accuracy improvement **NOT CLAIMED**. Do not change legacy frozen 60-case acceptance baseline; evaluate any future Gemma prompt/model/context candidate with *new preregistered, unseen* dual-direction samples, independent human review, timing and memory checks on Sony. CP4/CP6, legal notices, long-video E2E and complete release gates still OPEN.
