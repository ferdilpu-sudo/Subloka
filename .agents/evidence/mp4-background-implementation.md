# Background MP4 implementation and validation handoff

Status: IN_PROGRESS; Android CI and physical codec/background testing pending.
Version: 0.6.5-background-mp4. User authorized background MP4 after successful background translation and stop/resume trials.

## Decision and scope
RenderForegroundService owns the Media3 coroutine, bounded partial wake lock, progress and cancel notification. RenderSession carries an immutable project/caption/style request and exposes an output only after existing video/audio/duration validation. Transformer calls remain on Main; cancellation unwinds Transformer and deletes partial staging. Screen stop and ViewModel destruction do not cancel the service. A completion notification opens export for explicit document-picker saving. ASR, translation and rendering reservations exclude each other. Caption engines, signing identity and database schema are unchanged.

VideoExportViewModel observes the session and does not clean live/ready staging on recreation. Fresh process without a session cleans orphan staging; there is no process-death resume guarantee. Final copying to a selected document remains UI-owned and retains existing cancellation/partial-document cleanup. MP4 encoding settings and source/translation/manual-edit rules are unchanged.

## Verification
Local project guardrails and diff checks PASS. Added controlled-worker instrumentation for Activity stop/destruction/reopen, notification cancellation, delayed cancellation acknowledgement, commit/cancel ordering and ready-output survival across recreation. Synthetic output in ownership test is explicitly not codec evidence. Existing real media exporter tests remain configured in CI. New revision Android compile/lint/emulator results and real-device screen-off render/cancel/save must be recorded before declaring completion.

## Next steps
Run Android CI, repair any failures, then build the stable-key artifact with workflow_dispatch. Install in place. Render a short video, switch Home and turn screen off, reopen completion notification, save and play output checking subtitle/audio/duration. Separately cancel while rendering and retry. Do not uninstall or re-download caption models.
