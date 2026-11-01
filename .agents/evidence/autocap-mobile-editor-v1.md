# UI-AUTOCAP-MOBILE-EDITOR-001 — Mobile studio editor polish

Date: 2026-11-01. Baseline: `main@5514e1a73e0dc698ece04acd3860aba7236216c9`, SubLoka Beta #310 development baseline.

## Problem → rationale → solution

- P2 visual consistency: editor project header, save status and export control lacked a bounded studio surface; AutoCap Desktop's editor organizes the active project and state together. Use one restrained tonal, outlined header without changing the callback chain.
- P2 navigation clarity: existing Compose Tab children in a bare Row lack a consistently bounded visual group. Replace only that editor-level switcher with the same Material3 segmented-control pattern used by SubLoka's export screen. Keep exact labels `Teks`, `Waktu`, `Gaya`, the `EditorWorkspace` enum, and all click handlers.
- P2 selected-caption identification: use a subtle outline around selected-caption correction and the active caption card, plus a small correction label; do not move the caption editor behind a new page or modal.
- P1 regression guards: existing viewport tests cover 320x480dp at 150% font and 640x320dp landscape; preserve header export reachability, status/retry behavior, editing persistence, caption navigation, and preview placement. Add a Compose navigation/edit persistence regression.

## Scope

Changed only:
- `feature/editor/src/main/java/app/subloka/feature/editor/EditorScreen.kt`: tonal header + segmented workspace navigation.
- `feature/editor/src/main/java/app/subloka/feature/editor/CaptionWorkspace.kt`: active caption and correction-panel emphasis.
- `app/src/androidTest/java/app/subloka/EditorLayoutTest.kt`: selected workspace state, editing continuity and export visibility.

**Explicitly unchanged:** Whisper, Silero, TranslateGemma, Room, model catalog, project and caption persistence, ASR/translation/render foreground service lifecycle, video preview/render engine and encoding contract, signing, versioning, SRT/MP4 semantics, existing UI callback contracts.

## Verification

- Source transformations and changed-file review prepared on `ui/autocap-mobile-editor-v1`.
- Android compilation/Compose instrumentation: **NOT_RUN pending GitHub CI**.
- Sony SO-03L on-device UI/keyboard/TalkBack checks: **NOT_RUN**; no visual acceptance claim.
- Existing CI assertions that must pass: `EditorLayoutTest` tests for narrow screen, long title/export no overlap, editable caption, 40-caption list position, short landscape preview and timing/style reachability, save-failure/retry. New test `studioSwitcherClearlySelectsCaptionTimingAndStyleWithoutLosingEdits`.

## Next

Compare layout on a real 360dp-class device before adopting further AutoCap desktop patterns. Keep the mobile interaction contract: caption=hero; video=context; no desktop sidebar or bottom navigation. PR #3 separately handles Home/Projects and PR #2 handles translation attribution. Do not merge this editor PR or create a beta APK until CI and UI review; CP4/CP6/public release remain open.
