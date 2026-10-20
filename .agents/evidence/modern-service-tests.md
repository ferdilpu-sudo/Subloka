# Modern Android service/notification coverage

Status: IMPLEMENTED; Android CI execution pending. Test-only increment, application version remains 0.6.6-source-relink.

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

No app behavior/model/schema/signing-identity change; no physical support claim or release approval.
