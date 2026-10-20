# Background MP4 implementation and validation handoff

Status: bounded background MP4 increment accepted; CI PASS and user-reported physical smoke PASS. Full release gates remain open.
Version: 0.6.5-background-mp4. User authorized background MP4 after successful background translation and stop/resume trials.

## Decision and scope
RenderForegroundService owns the Media3 coroutine, bounded partial wake lock, progress and cancel notification. RenderSession carries an immutable project/caption/style request and exposes an output only after existing video/audio/duration validation. Transformer calls remain on Main; cancellation unwinds Transformer and deletes partial staging. Screen stop and ViewModel destruction do not cancel the service. A completion notification opens export for explicit document-picker saving. ASR, translation and rendering reservations exclude each other. Caption engines, signing identity and database schema are unchanged.

VideoExportViewModel observes the session and does not clean live/ready staging on recreation. Fresh process without a session cleans orphan staging; there is no process-death resume guarantee. Final copying to a selected document remains UI-owned and retains existing cancellation/partial-document cleanup. MP4 encoding settings and source/translation/manual-edit rules are unchanged.

## Verification
Local project guardrails and diff checks PASS. Added controlled-worker instrumentation for Activity stop/destruction/reopen, notification cancellation, delayed cancellation acknowledgement, commit/cancel ordering and ready-output survival across recreation. Synthetic output in ownership test is explicitly not codec evidence. Existing real media exporter tests remain configured in CI. New revision Android compile/lint/emulator results and real-device screen-off render/cancel/save must be recorded before declaring completion.

## Next steps
Use the acceptance and release-gap review below. Do not repeat the accepted basic background/cancel or full-flow smoke without a concrete regression. Keep the existing stable-key installation and prepared models.

## CI compilation repair (2026-10-19)
Run 39278053473 failed in both build and media-device at :app:compileDebugKotlin. In the completion notification inside scope.launch, bare this resolved to CoroutineScope instead of Android Context. Qualified the three notification/intent context arguments with this@RenderForegroundService. No render behavior, engine, schema or signing changes. Stable APK job was skipped. Guardrail and whitespace validation must pass locally; Android compile/lint and instrumentation remain pending on the repair revision. Physical MP4 background tests remain NOT_RUN.


## Acceptance and release-gap review — 2026-10-20
Tested code baseline: 1a8ef2f38be7ca601c0b0c895d1c10cf6539bb5b, version 0.6.5-background-mp4.
This section supersedes the pending status in the historical compilation-repair entry.

| Evidence | Actual result | Boundary |
|---|---|---|
| MP4-SERVICE-CI-003 | Run 39283814636: build 118164052501, media-device 118164053041 and stable-prototype-apk 118168134087 all SUCCESS, verified through GitHub jobs API. Compile, lint, configured unit/instrumentation and signing verification passed. | Emulator/service fixtures do not establish all physical codec/device support. |
| MP4-SERVICE-DEVICE-001 | User explicitly reported PASS for short render across Home/screen-off, completion notification, save/playback with picture/audio/subtitle/duration checks, and stop then restart. | User-reported smoke on existing test device; no independent frame measurement or process-death evidence. |
| E2E-DEVICE-001 | User explicitly reported PASS for import, transcription, correction, translation, SRT and MP4 export. | Language direction, airplane mode, clip metadata and measured timing/resource values were not specified. Do not infer them. |

Existing background ASR and translation acceptance remains recorded in prior history. No engine, schema, signing identity or application code changes in this documentation increment.

### Remaining release gates
This is a review of existing PRD/testing requirements, not new product scope or a release approval.

| Priority / requirement | Remaining evidence or behavior | Next bounded action |
|---|---|---|
| First / FR12, FR05 | Explicit airplane-mode E2E with prepared models, including both EN-to-ID and ID-to-EN. General E2E PASS does not establish network state or both directions. | Start with one short English-source clip in airplane mode, translate to Indonesian, export and reopen; then cover the other direction if not explicitly documented. |
| High / FR11, NFR01 | Saved edits and translation checkpoint after OS process death; safe interrupted ASR/render and retry. Home/screen-off is not process death. | Use a disposable test project; preserve saved edits, interrupt the process, reopen and inspect results before retry. ASR/render currently restart from the beginning; no chunk resume claim. |
| High / FR01, FR09, FR11 | Low-storage and document-provider write failures, partial-output cleanup, failed model setup/retry. | Controlled test fixture or emulator fault injection before physical destructive storage scenarios. Do not fill the user's phone or remove prepared models. |
| High / FR03 | Lost source URI recovery usability. Earlier permission workaround is not acceptance of a discoverable relink flow. | Inspect current UI and repository relink wiring, then test with a disposable source. |
| Required / NFR03, CP4 | Current Turbo/Gemma quantitative quality/timing and resource gates remain unclosed. Historical Base/older-translation failures are not measurements of the current models. | Define model-specific evidence gaps; retain completed external-30 evidence, do not rerun it automatically or lower thresholds. |
| Required / NFR05, CP6 | Keyboard/font scale/TalkBack/adaptive layout and additional supported device/API coverage. | Targeted remaining cases; existing main-flow PASS remains valid within its scope. |
| Delivery / T16, CP7 | Candidate checksums, licenses/model terms, installation/known limits, supported format/device scope and final approval. | Prepare after technical gates; no merge, tag or public release now. |

CP4 remains BLOCKED; full T13/CP5, T15/CP6 and T16/CP7 are not closed by these smoke results. Bounded background MP4 acceptance is complete. Next user-facing test is explicit offline English-to-Indonesian E2E; no APK rebuild is required for this documentation-only update.
