# UI-AUTOCAP-PORTRAIT-PREVIEW-001 — Adapted video preview (9:16 / 16:9)

Date: 2026-11-03. Scope: bounded responsive video preview in SubLoka Android Editor only. This feature is based on user-feedback from Sony SO-03L signed Beta #332 and the earlier ~67-second owner screen recording: the portrait video occupied only a tiny centered vertical sliver within a fixed 16:9, 112dp-high preview box.

## Stable precondition

- Stacked base: `ui/autocap-contrast-beta4-preview@21012a46f72107ea86b56817eddbe42567be6054` ([PR #10](https://github.com/ferdilpu-sudo/Subloka/pull/10)). Beta4 owner-signed [manual CI #332](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41588777077) **4/4 PASS**, owner-reported translation completion, caption persistence and Indonesian/English MP4 playback PASS.
- No problem was found in the underlying ASR/TranslateGemma engines, output files, Room persistence, signed keys or rendering pipeline. Do not modify those areas to fix this preview issue.

## Root cause and patch

- Previous `feature/editor/VideoPreview.kt`: preview container enforced `aspectRatio(16f/9f)` regardless of oriented source dimensions, and compact Editor always passed `compactHeight=true`, limiting the frame to 112dp. With portrait 9:16 footage, native video playback fitted an approximately **63dp-wide** rectangle within the preview.
- `VideoPreview` now uses source metadata `videoWidth / videoHeight` (already oriented for rotation in `SubLokaApp`) to calculate actual on-screen frame width and height. The frame is centered and bounded by both the available width and a caller-supplied maximum height. Invalid metadata falls back to 16:9 for layout; renderer errors still use the existing validation.
- `EditorScreen` sets a portrait-specific compact height budget of `min(288dp, 32% of available editor height)`, yielding a portrait frame roughly 2–2.5x wider than the previous 112dp strip on taller phones. For landscape videos, the existing 112dp compact cap remains; expanded normal cap remains 248dp. Expanded portrait gets up to 288dp (or 58% of available editor height).
- Selection, playback, overlay `SubtitlePainter`, source/translation text, caption timings, style, export, model inference and navigation callbacks are not changed. Preview remains collapsible on compact screens and automatically hidden when IME/keyboard is active.
- A semantics tag `video-preview-frame` is attached to the visible frame for Android layout tests, without touching media state.

## Test sources / gates

`app/src/androidTest/java/app/subloka/EditorLayoutTest.kt` adds:
1. `videoPreviewUsesActualPortraitAndLandscapeAspectWithoutOversizing`: asserts correct 9:16 and 16:9 geometry and that portrait footage receives more height without exceeding compact width.
2. `tallPortraitVideoKeepsWorkspaceAndExportReachableAtLargeFont`: under 150% text scaling, checks portrait framing, separation from editor switcher, reachability of source correction field, Waktu, Gaya and Ekspor callbacks.

Existing narrow short screen, landscape supporting pane, caption saving and interruption tests must remain passing.

## Status and release gate

**Code prepared. New branch CI, signed APK and physical Sony visual confirmation: NOT_RUN at writing.** Open a Draft PR stacked onto PR #10 rather than `main`. Require GitHub build/Android11 media/Android15 services PASS before advancing. New APK needs a separate owner-authorized workflow and signing under the established certificate, with versionCode strictly higher than the installed one (at least >332 if signed Beta4 is installed). Do not install PR debug artifacts or clear any app data.

Release CP4/CP6, complete licensing notices/Google branding and extended 150%/TalkBack/airplane-mode stress remain separately OPEN.
