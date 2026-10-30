# Background MP4 implementation and validation handoff

Status: bounded background MP4 increment accepted; CI PASS and user-reported physical smoke PASS. Full release gates remain open.
Version: 0.6.5-background-mp4. User authorized background MP4 after successful background translation and stop/resume trials.

## Decision and scope
RenderForegroundService owns the Media3 coroutine, bounded partial wake lock, progress and cancel notification. RenderSession carries an immutable project/caption/style request and exposes an output only after existing video/audio/duration validation. Transformer calls remain on Main; cancellation unwinds Transformer and deletes partial staging. Screen stop and ViewModel destruction do not cancel the service. A completion notification opens export for explicit document-picker saving. ASR, translation and rendering reservations exclude each other. Caption engines, signing identity and database schema are unchanged.

VideoExportViewModel observes the session and does not clean live/ready staging on recreation. Fresh process without a session cleans orphan staging; there is no process-death resume guarantee. Final copying to a selected document remains UI-owned and retains existing cancellation/partial-document cleanup. MP4 encoding settings and source/translation/manual-edit rules are unchanged.

## Verification
Local project guardrails and diff checks PASS. Added controlled-worker instrumentation for Activity stop/destruction/reopen, notification cancellation, delayed cancellation acknowledgement, commit/cancel ordering and ready-output survival across recreation. Synthetic output in ownership test is explicitly not codec evidence. Existing real media exporter tests remain configured in CI. Compile/lint/emulator and user-reported background/cancel acceptance are recorded below; remaining release coverage is separate.

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
| Accepted smoke / FR12, FR05 | Explicit airplane-mode E2E in both directions now user-reported PASS; see OFFLINE-E2E-002/003 below. | Do not repeat without regression. Traffic audit and quantitative quality remain separate. |
| High / FR11, NFR01 | Saved edits and translation checkpoint after OS process death; safe interrupted ASR/render and retry. Home/screen-off is not process death. | Use a disposable test project; preserve saved edits, interrupt the process, reopen and inspect results before retry. ASR/render currently restart from the beginning; no chunk resume claim. |
| High / FR01, FR09, FR11 | Low-storage and document-provider write failures, partial-output cleanup, failed model setup/retry. | Controlled test fixture or emulator fault injection before physical destructive storage scenarios. Do not fill the user's phone or remove prepared models. |
| Accepted / FR03 | Verified same-file relink UI implemented, CI PASS and physical flow user-reported PASS. | See source-relink-implementation.md, RELINK-CI-001 and RELINK-DEVICE-001. No repeat required without regression. |
| Required / NFR03, CP4 | Current Turbo/Gemma quantitative quality/timing and resource gates remain unclosed. Historical Base/older-translation failures are not measurements of the current models. | Define model-specific evidence gaps; retain completed external-30 evidence, do not rerun it automatically or lower thresholds. |
| Required / NFR05, CP6 | Keyboard/font scale/TalkBack/adaptive layout and additional supported device/API coverage. | Targeted remaining cases; existing main-flow PASS remains valid within its scope. |
| Delivery / T16, CP7 | Candidate checksums, licenses/model terms, installation/known limits, supported format/device scope and final approval. | Prepare after technical gates; no merge, tag or public release now. |

CP4 remains BLOCKED; full T13/CP5, T15/CP6 and T16/CP7 are not closed by these smoke results. Bounded background MP4 acceptance is complete. Latest follow-up below supersedes the earlier next-test proposal; no APK rebuild is required for documentation-only updates.


## Follow-up acceptance and source/test audit — 2026-10-20
Application baseline remains 1a8ef2f38be7ca601c0b0c895d1c10cf6539bb5b; no newer APK was requested between these reports. Installed revision was not independently read from the device.

| Evidence | Reported result | Scope and limits |
|---|---|---|
| OFFLINE-E2E-002 | PASS for the selected airplane-mode, Wi-Fi-off English-source transcription, Indonesian translation, SRT/MP4 export, close/reopen and saved-correction check. | User-reported functional offline smoke; not a packet capture or quantitative quality benchmark. |
| OFFLINE-E2E-003 | PASS for Indonesian-to-English following the instruction to repeat the same offline flow. | User-reported second-direction smoke in the conversation context; no separate output artifacts or resource metrics supplied. |
| RECOVERY-DEVICE-002 | PASS for the selected force-stop recovery test using a disposable project. | Exact interruption stage and stop method were not provided. This supports bounded user acceptance, not every OS kill, active copy, ASR, render or durable checkpoint scenario. |
| MP4-SAVE-DEVICE-002 | PASS for render complete, open save picker, Back/cancel, then save again. | User-reported cancel/retry flow; it does not exercise a provider write/close/delete failure or full disk. |

### Source and configured-test audit
Read VideoExportViewModel.kt, RenderTask.kt, RenderForegroundServiceTest.kt, SrtDocumentWriterTest.kt, TranslationRecoveryUiTest.kt, translation recovery startup and the explicit Android CI instrumentation class list.

- MP4 picker cancellation preserves the rendered source and clears pending; a later save copies from staging. RenderForegroundServiceTest also covers ready output across Activity recreation and save(null). The new physical report covers the requested picker cancel/retry flow.
- MP4 copying catches errors, attempts destination deletion under NonCancellable IO and warns when cleanup cannot be confirmed. This is source inspection only. No dedicated MP4 destination failure tests were found in the configured app suite. SRT tests cover null stream, write and close failure but do not prove the MP4 ViewModel path.
- RenderTask checks a 64 MiB initial free-space floor and deletes unpublished staging in finally. This is not a full output-size reservation or evidence that disk exhaustion during encoding/copy is handled on all providers.
- Translation startup calls recoverInterrupted only when no live TranslationSession is running. Existing UI test checks resume and explicit discard controls; it does not itself terminate an Android process.
- MediaRelinkVerifier and AndroidMediaSource.verifyRelink exist in core/media. No relink reference/action was found in app/src/main/java. Existing domain/media verification must not be described as a complete discoverable application relink flow.

### Prioritized next implementation
1. Add controlled MP4 destination failure coverage (null/open/write/flush/close failures; delete success/failure; cancellation during copy; retained staging and successful retry). Use synthetic files and a test provider or injected destination adapter; never fill the user's device.
2. Wire a source-missing/relink action after inspecting the existing repository contract. Validate the chosen replacement before updating the source; keep caption edits and refuse incompatible media. This remains a separate scoped code increment.
3. Continue remaining release evidence: modern API/device behavior, accessibility/adaptive cases, current-model quantitative quality/resource and provider/storage matrix.

Audit outcome: documentation and gap review complete. No application code changed and no new automated test execution is claimed. Main-flow user PASS results remain accepted; full CP4/CP5/CP6/CP7 remain open. No additional manual test is requested in this handoff.


## MP4 destination failure coverage / 2026-10-20
Status: IMPLEMENTED; Android compile and emulator execution pending.
Added Mp4Destination/AndroidMp4Destination as a per-ViewModel test seam for the existing ContentResolver openOutputStream(uri, "wt") and DocumentsContract.deleteDocument calls. Existing save lifecycle, cancellation, staging retention and UI messages remain unchanged.
VideoExportSaveTest exercises the real ViewModel with synthetic 150000-byte source data: null/open failure; failure on second write after partial output; flush/close failure; delete returning false or throwing; byte-exact retry using retained staging; blocked close preventing premature success; ViewModelStore.clear during blocked copy followed by NonCancellable cleanup. No actual codec, physical full-disk or external document-provider claim.
Configured the new class in the existing CI emulator class list. Local tools/validate_project.py and git diff --check PASS. No local Android SDK/Gradle distribution available; do not mark new tests PASS until CI confirms.
No new user device test requested. Application version name/model/database/signing unchanged. Next: inspect automatic PR CI, repair failures if any; stable manual APK is only needed if a subsequent behavior fix requires device verification.


## MP4-SAVE-CI-001 — verification and closure / 2026-10-20
Tested revision: 667a7452a138ac75283210afdb9ca1494d7a1ede.
Run39355767643 verified through GitHub jobs API: build118410061915 SUCCESS (including compilation, unit suites, schema fixture and lint); media-device118410062222 SUCCESS. Emulator log explicitly invokes VideoExportSaveTest alongside existing app suites and reports BUILD SUCCESSFUL. Stable-prototype-apk was correctly skipped for this PR-triggered run; no owner-signed installation artifact is claimed.
Result: PASS for configured Android11 emulator failure-injection suite. Bounded MP4 destination failure coverage increment DONE. The earlier IMPLEMENTED/pending status is superseded by this result.
This covers synthetic stream open/write/flush/close/delete errors, retained staging/byte-exact retry, delayed close and ViewModel destruction cancellation. It does not prove every external document provider, real full-disk behavior or arbitrary OS process termination.
Documentation/guardrail checks PASS. Application behavior, models, schema and signing identity remain unchanged. No new physical test or APK update is required for the test seam. No merge/release performed.
Next ready scoped increment: missing-source UI and verified relink, preserving saved captions and refusing incompatible replacements. Full CP4/CP5/CP6/CP7 remain open.


## Source recovery closure / 2026-10-20
The earlier missing-app-relink finding is resolved by d393b63. [Source relink implementation and acceptance](source-relink-implementation.md) records CI and physical PASS. Remaining release scope is modern API/device and accessibility/resource/provider coverage, not repetition of accepted main-flow smoke.
