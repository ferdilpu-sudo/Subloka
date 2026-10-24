# Processing status UI — 0.6.13

## Scope / 2026-10-23
User reported export 0.6.12 physical checks PASS: original and dual SRT, MP4 save-picker cancellation/retry, render cancel/restart, large font/landscape, translated export blocked after original edits while SOURCE remains available.

P1 usability: stop/resume controls scroll out of view on long processing/setup pages. Add persistent primary footer to transcription and translation; show actual stage and error near the top, distinguish model setup from background translation, and consume explicit session stopping flags to disable repeated cancel requests. Preserve resume versus new translation eligibility, Gemma consent, explicit recovery discard confirmation and engine callbacks. ASR completed leads to editor; interrupted/error leads to retry model setup. Stack model choices for narrow/large-font layouts.

## Validation
Local validate_project.py PASS (117 Kotlin files), diff whitespace check PASS. New ProcessingStatusUiTest covers large-font stop/stopping/retry/completed callbacks. TranslationRecoveryUiTest retains resume/discard assertions and adds compact-landscape stop/stopping coverage. CI selection updated. Android compilation/instrumentation and physical checks pending; no local Android SDK test claim.

No database, model, service or signing changes. IN_PROGRESS pending CI and scoped physical acceptance. Next: stable-key update after CI, test persistent stop and resume with large font/landscape and existing short-video workflow.

## Render notification follow-up / 2026-10-23
Run 39883320630: build and Android11 PASS; Android15 granted suite 13 tests, one failure. The existing exact-ready-title assertion timed out with no active notifications. Denied suite not reached. Device logcat reports missing enqueued record for notification 4003 immediately after render stop. Source removed the foreground notification then immediately posted the ready notification using the same ID: a cancellation/publication race is consistent with these observations.

Change success transition to STOP_FOREGROUND_DETACH before updating the notification, preserving its slot independently of service destruction. Failed/cancelled renders without a saved result and notification-denied paths retain REMOVE. Android API contract: https://developer.android.com/reference/android/app/Service#STOP_FOREGROUND_DETACH . Retain bounded exact-title/content-intent/no-stop-action regression; no timeout increase, retry or skipped test. Local guardrail and whitespace checks PASS. Android CI rerun and physical notification verification pending; root-cause resolution is not yet confirmed by rerun.

## Translation stage diagnostics / 2026-10-24 / 0.6.14
Separate verification, native loading and caption inference status. Emit local SubLokaTranslation start/end events using monotonic duration, an ephemeral translator-session identifier, attempt index and returned/failed/cancelled outcome. No caption text, source paths, project identifiers or exception payloads are logged. Returned indicates a stage returned, not database publication or successful model readiness. Existing pipeline publication, checksum validation, model/prompt, signing and cleanup remain intact. Cancellation is checked again after native open before inference.

Local validate_project.py PASS (117 Kotlin files); git diff --check PASS. Android compilation/lint and real-weight device timing remain pending. This is measurement and status correction, not a demonstrated speed improvement. After stable-key installation, capture `adb logcat -v time -s SubLokaTranslation:I '*:S'` during a fresh short-project translation; inspect verify/load/caption durations and confirm saved output plus cancellation/resume still work.

## Native phase diagnostics / 2026-10-24 / 0.6.15
Manual CI40052474784 for0.6.14: build, Android11 media-device, Android15 modern-services and stable-prototype-apk verified SUCCESS. Native phase measurement now separates prefill (KV clear and prompt/input decode) from generation (sampling and output decode), with processed prompt-token and emitted output-token counts. Scope exit records partial time on exceptions as interrupted_or_failed; returned is not a database publication claim. Logs remain local metadata only under SubLokaTranslation. Model, prompt, greedy sampling, token caps, CPU configuration and cancellation callback unchanged. This increment does not claim a speedup.

Validation: host C++17 compiler with warnings-as-errors and success/exception-unwind timing smoke PASS. Android logging branch syntax checked with declaration stub, not an Android build. Project guardrails117 Kotlin files and git diff --check PASS. Full native Android compilation and real model timing pending CI/device. Capture the same log tag for1–2 captions, compare prefill/generation durations and output token count; no full-project rerun needed.
