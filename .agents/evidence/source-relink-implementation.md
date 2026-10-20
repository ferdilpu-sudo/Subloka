# Verified source relink — implementation handoff

Status: IMPLEMENTED, Android CI and physical document-picker acceptance pending.
Version: 0.6.6-source-relink. User explicitly authorized the missing-source relink increment.

## Problem and scoped decision
P1 usability/data-safety gap: core media had a relink verifier but the application did not expose recovery for a lost source URI. Requiring a new project would lose the connection to existing caption work.
The editor now offers Tautkan ulang video when source access fails, including playback failures; empty-caption real projects also offer recovery. Access is checked on project load and Activity resume without hashing the entire source. A dedicated scrollable screen explains original-file selection, verification progress and rejection/retry. Back and another pick are disabled during verification. Canceling the picker leaves the project untouched.
Before entering recovery, existing editor edits pass through the persistence queue/flush barrier. The picker callback is bound to the original project ID.

## Identity and persistence contract
A candidate must be readable by the media probe, include audio/video, and have a full SHA-256 matching the persisted original fingerprint. Duration, width, height, rotation and known file size must also match. Missing/invalid original fingerprint fails closed; visually similar, re-encoded or edited media is not accepted. A persistent read grant must be retained before commit.
ProjectRepository.relinkSource rechecks original URI/fingerprint and candidate identity within a Room transaction. It changes only URI, display name, known size and update time; project identity, caption content, timing, style, languages and content revision remain unchanged. Keeping the content revision is deliberate because same-file URI repair does not change content and must not invalidate pending translation work. No Room schema change.
The editor/player is recreated after successful relink even for the same URI, so restored permission actually reloads playback. Models and signing identity are unchanged.

## Verification
- Added Room regression cases: preserve manual source/translation, style, content revision and pending translation checkpoint through database reopen; reject fingerprint/metadata/size mismatch, stale URI and missing original fingerprint without caption mutation.
- Added SourceRelinkUiTest: recovery available with empty captions, controls blocked while verifying, rejection permits retry/back.
- Existing media probe/verifier tests remain configured. UI tests added to Android CI class list.
- Local project guardrails and whitespace checks PASS.
- Android compilation/lint/unit/emulator: pending. No physical relink success claimed.

## Acceptance after CI
Use a disposable project and a duplicate original video. Make its old URI unavailable without deleting the only original. Open the existing project, choose Tautkan ulang video; cancel once, try an unrelated video (must be rejected without caption changes), then choose the exact original copy. Verify playback and saved corrections/style, close/reopen and confirm persistent access. No model download or new project generation is needed.
Do not ask users to uninstall, remove their only source, or reset app data.
CP4/full CP5/CP6/CP7 remain open; no merge or public release.
