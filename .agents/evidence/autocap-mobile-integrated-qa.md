# UI-AUTOCAP-INTEGRATION-001 — Integrated AutoCap-inspired SubLoka mobile UX QA

Date: 2026-11-01.
Protected stable baseline: `main@5514e1a73e0dc698ece04acd3860aba7236216c9`, owner-verified signed Android Beta #310.
Integration branch: `ui/autocap-mobile-integrated-qa` based on stacked Export [PR #6](https://github.com/ferdilpu-sudo/Subloka/pull/6) head `f0ff22843f1f07df3605af3e8e61167ab9e81d1b`, which incorporates legacy attribution [PR #2](https://github.com/ferdilpu-sudo/Subloka/pull/2). Additional source/test UI content is copied from the exact independently green [Home PR #3](https://github.com/ferdilpu-sudo/Subloka/pull/3), [Editor PR #4](https://github.com/ferdilpu-sudo/Subloka/pull/4) and [Timing/Style PR #5](https://github.com/ferdilpu-sudo/Subloka/pull/5).

## Matrix / sources

| Area | Sources | Separate CI |
|---|---|---|
| Legacy translation provider notice | `core/domain/TranslationOrigins.kt`, domain tests, Export test from PR #2 | [#41153737370](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41153737370) SUCCESS |
| Home / Projects | `feature/projects/ProjectsScreen.kt`, `app/androidTest/ProjectsScreenTest.kt` from PR #3 | [#41317926635](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41317926635) SUCCESS |
| Editor shell and selected caption | `feature/editor/EditorScreen.kt`, `CaptionWorkspace.kt` from PR #4 | [#41319407955](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41319407955) SUCCESS |
| Timing / Style | `feature/editor/TimingWorkspace.kt`, `StyleWorkspace.kt` from PR #5 | [#41321309552](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41321309552) SUCCESS |
| Export UI | `feature/export/ExportScreen.kt`, `app/androidTest/ExportFlowUiTest.kt` from PR #6 | [#41324291453](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41324291453) SUCCESS |

`EditorLayoutTest.kt` was changed by two independent PRs #4 and #5. The integration branch deliberately combines both regression sets into a **single** suite. This avoids one branch's version silently replacing tests from the other. The PR #6 Export test remains untouched and inherits PR #2's provenance tests.

## Acceptance scope
- A single combined PR to **main as a Draft only** is appropriate to run CI with all five change sets. It is not merge authorization.
- Existing UI callback contracts, project persistence, Room schema, model files, engine code, media/export pipeline, version and certificate are unchanged. No in-place install, no forced app downgrade, no data wipe, no public release.
- GitHub CI of each individual PR is not proof of integration. At writing: combined Android CI **NOT_RUN**, physical Sony SO-03L UX (portrait, landscape, large font 150%, TalkBack, keyboard, existing projects/manual corrections, SRT/MP4) **NOT_RUN**.
- Ensure checked-in Kotlin sources build and all emulator instrumented tests pass. Then prepare a signed, higher-versionCode *controlled* UI beta using owner-managed key and update-in-place only after confirming same package/signature. Do **not** install a GitHub debug APK over Beta #310 or uninstall/clear data.
- Google branding/NOTICE distribution audit, CP4 quality/resources, CP6 release qualification and paused 30-case ASR benchmark remain separate gates.

## UX target
Autocap-inspired information hierarchy without recreating WinUI's desktop rail on a phone: Home import emphasis and recent projects, editor save/export header, Teks/Waktu/Gaya switching, selected caption contrast, Timing start/end groupings, Style panels and export format/language/output groups including legacy-provider warnings. **Caption is hero, video is context**; no new video-effects editor or bottom navigation.
