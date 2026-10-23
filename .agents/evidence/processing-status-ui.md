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
