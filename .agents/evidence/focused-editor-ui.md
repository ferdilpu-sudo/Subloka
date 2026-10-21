# Focused editor refinement — 0.6.9

## Scope and decision
User approved the charcoal/teal editor mockup and its implementation, then explicitly authorized this short repository note on 2026-10-21. This file records only this increment; no historical planning documents or private media are included.

Implemented in 33b852f74c5a87d3d38f3dc956f383f335d6f2c3, with constrained-layout test follow-up 2d83810feebaaaabaad7aa4d4fc751d4dffd9567:
- Teks / Waktu / Gaya labels and teal accent; export remains blocked on save failure.
- Previous/next caption navigation in text and timing workspaces.
- Independent caption-list scroll state; compact windows toggle list/correction, larger workspaces show both.
- Collapsible translation field with visible status and existing manual-edit protection.
- Explicit midpoint split label; unavailable merge and timing nudges disabled.
- Keyboard preview depends on remaining space; landscape keeps supporting panes.

Problem: selection previously reset the shared list to its top, and unavailable controls silently did nothing. Acceptance: retain list position, preserve edits through selection, expose stale translation while collapsed, and keep fields/tools reachable in constrained layouts. Schema, engines, model files and signing configuration are unchanged.

## Evidence
Revision: 2d83810feebaaaabaad7aa4d4fc751d4dffd9567.
Android CI: https://github.com/ferdilpu-sudo/Subloka/actions/runs/39587666007
- build 119180503720: SUCCESS, including unit tests, Android test compilation, assembly and lint.
- media-device 119180503378: SUCCESS on Android 11; configured app instrumentation includes EditorLayoutTest, with correction/navigation/boundary/stale-state and list-position regressions.
- modern-services 119180503626: FAILURE. Granted-permission phase ran 13 tests, with 2 failures: cancellationAcknowledgedWhileWorkerIsStillStopping in AsrForegroundServiceTest and TranslationForegroundServiceTest. Both reported NoSuchElementException. Root cause is not established by this note; do not dismiss as flakiness. Denied-permission coverage is not established by this failed run.
- stable-prototype-apk: SKIPPED; this run does not provide a validated stable-key update.

Local guardrail and diff checks passed. Checked opaque UI text/background token contrast pairs exceed 4.5:1; this is not full accessibility or subtitle-on-video certification.

## Status / next step
IMPLEMENTED, validation incomplete. Investigate the two Android 15 service-test failures and rerun the required CI gate before producing the stable-key update. Physical portrait/landscape/keyboard usability and correction/reopen acceptance for this version remain NOT_RUN. No release-readiness claim.


## Notification synchronization follow-up / 2026-10-21
Inspection found notification-action tests read activeNotifications immediately after controlled worker entry. Worker entry is not notification-publication synchronization; the failing calls use first(predicate), which throws when the ID is absent. Test fixtures now await the expected notification ID and Hentikan action with a 15-second deadline and diagnostic failure, then send the actual PendingIntent. The same unsafe reads in render tests are covered. Existing stopping, single-job ownership, cancellation and post-commit assertions remain unchanged. Permission-denied tests are separate and unchanged. No production service or engine changes.
Local guardrails/diff checks and all four instrumentation-log verifier regressions PASS. Android build and both permission phases require fresh CI; no claim yet that this fixes every Android 15 failure. Physical editor acceptance remains pending.
