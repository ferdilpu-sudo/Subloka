# Modern Android service/notification coverage

Status: FIX IMPLEMENTED; Android CI revalidation pending. Application version 0.6.7-modern-services.

## Scope
Keep the existing API30 media/app gate. Add a separate API35 (Android15) modern-services gate for service-owned ASR, translation and MP4 lifecycle tests. Stable prototype signing depends on build, media-device and modern-services.
Tests use controlled workers and synthetic project data, never user media or real model downloads. This is service lifecycle/permission coverage, not physical native performance, codec compatibility, six-hour timeout or all newer Android versions.

## Permission phases
Install app and test APK, stop the app, grant POST_NOTIFICATIONS, then run existing AsrForegroundServiceTest, TranslationForegroundServiceTest and RenderForegroundServiceTest through am instrument.
Stop the app again, revoke notification permission and clear user flags before starting the next instrumentation process. NotificationDeniedServiceTest asserts permission is denied and notifications disabled, then tests each of three service types twice: completion after Activity stop, and cancellation through the service API after returning to foreground. No notification action is required in this phase.
Permission changes happen before instrumentation because revocation may terminate the target process. Do not apply this CI script to a user's production phone.

## Result handling and tests
Raw granted/denied logs are retained in a dedicated artifact even when the modern job fails. A fail-closed verifier requires a nonempty OK summary, successful instrumentation completion and no failure/crash marker; the denied phase must execute exactly three JUnit methods (each covers completion and cancellation).
Local parser regression tests cover accepted output, missing/empty/truncated completion, failures/crash, wrong completion code and wrong test count. Shell syntax, project guardrails and whitespace checks PASS. Emulator/Android compilation and permission behavior remain pending until CI reports.

## Primary references
- https://developer.android.com/develop/ui/compose/notifications/notification-permission
- https://developer.android.com/studio/test/command-line

## API35 startup correction
The first API35 execution failed: all 13 granted-phase cases timed out before worker entry; denied phase did not execute. Build/lint and API30 passed.
Inspection of the exact Core 1.19.1 source artifact confirms ServiceCompat.Api34Impl masks foregroundServiceType against an allowlist that omits MEDIA_PROCESSING. Passing only that flag becomes NONE, forbidden for the target SDK.
All three services now call platform startForeground directly on API35+, retaining the existing compatibility path below API35. No timeout extension or gate removal.
Tests now surface terminal session state before worker entry instead of hiding early startup failures behind a timeout. The runner uses am instrument -r so the verifier receives raw completion codes, requires exactly 13 granted and 3 denied tests, and retains emulator logcat on failure.
Source checked: https://dl.google.com/dl/android/maven2/androidx/core/core/1.19.1/core-1.19.1-sources.jar (androidx/core/app/ServiceCompat.java).
No model/schema/signing-identity change; no physical support claim or release approval.
