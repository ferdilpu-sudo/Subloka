# UX-EDITOR-CAPTION-FOCUS-001 — Video-first editor to caption-first correction

Date: 2026-11-04. Source: owner-supplied 74-second Android UX audit identifying excessive content before active-caption controls. No private recording, frames, notifications, filenames or caption strings are committed.

## Problem and priority

The existing mobile Editor stacked project header, explanatory hint, model button, 9:16 video preview and tab switcher above caption navigation *inside* the scrolled caption panel. User's primary correction path — caption 2 → edit one word → check in preview → caption 3 — forced repetitive scrolling. The same scrolling issue affected Timing. Owner's highest priority is editor; later concerns (save-specific SRT actions, offline-model gating, duplicate project cards, Style positioning guides) are separately scoped, **NOT delivered by this patch**.

## Implemented, no backend/persistence changes

1. The top of Editor keeps **Project title + local save status + Export** only for ordinary projects. Existing relink warning still appears if the source is unavailable; Demo remains explicitly labelled.
2. Removed redundant "Periksa teks, waktu..." helper and moved "Model / lanjutkan terjemahan" below the selected caption correction controls inside the scrollable Teks workspace. All callback and model readiness behavior retained.
3. **Caption navigation is now one fixed shared `‹ Caption n dari N ›` control directly above the active workspace panel for BOTH Teks and Waktu**. No longer nested inside the selected-caption scroll. It remains adjacent to edit/timing tools on narrow portrait and on expanded two-column layouts; Style does not duplicate this navigator. The former internal navigator is suppressed by `showNavigation=false` when hosted in EditorScreen; standalone callers retain the default behavior.
4. When active caption changes, the selected-caption scroll resets to the top, so next caption's source field is immediately accessible. The existing selection callback still seeks the actual video start. No caption text/revision/timing change logic altered.
5. On narrow phones, Teks/Waktu preview defaults to **compact** up to 152dp or 22% of available height. The labeled **Perbesar/Ringkas** action expands it back to prior fully bounded portrait size (<=288dp and <=32% of height). Style automatically uses the larger preview to inspect visual settings. Playback, SubtitlePainter and output frame ratios remain unchanged. Preview hides when the keyboard is open. The Sembunyikan/Tampilkan toggle remains accessible with short visual labels plus descriptive talkback semantics.
6. Smaller vertical gap between top-level controls (12dp→8dp) to preserve the editing viewport. No new app route/tab, no camera/renderer change, no model download/data migration.

## Test plan / evidence

`EditorLayoutTest.kt` adds Android Compose automated tests:
- A 4-caption portrait correction flow: caption 2 selection, source edit, caption 3 selection, source preserved, Waktu navigator immediately above timing controls and previous caption still accessible — without scrolling the navigation row.
- Preview size assertions for compact → expanded → compact and naturally larger Style default, while export and bottom-position controls remain reachable.
- Model management action follows correction fields and still calls the same model/translation callback.
- Existing navigation tests updated to target the new *fixed* controls rather than asking to scroll them into view.

CI status at writing: **PENDING**. This is a Draft PR stacked on owner-signed Beta6 PR #14; it must pass build, Android11 UI/media, Android15 foreground tests before any signing path is considered. A new signed APK requires separately approved owner-manual dispatch and versionCode >339 if installed. Do NOT install debug/unsigned CI APK, uninstall, clear app data, or merge to main before field acceptance. Keep Whisper/TranslateGemma, model files, Room, user projects, SRT/MP4 outputs and owner signing cert unchanged.

## Backlog, intentionally out of scope

1. **Export SRT**: localize per-document save actions using actual language/document info; when results exist, prioritize pending saves over "Siapkan SRT lagi" and visibly mark saved.
2. **Offline translation**: separate project eligibility state from model readiness; zero eligible due to all translated must offer "Kembali ke editor" rather than prominently advertise a multi-GB download.
3. **Projects**: visible snippet or thumbnail + owner-controlled rename; compact startup guidance for non-empty lists.
4. **Style**: enlarged preview near active style controls and bottom-position guide while sliding.
5. Additional accessibility verification at 150% font and TalkBack; ten-minute full offline video E2E and export file playback must be field-tested.

This is an Editor UX experiment, not a claim of product release readiness. PRs remain Draft; `main` remains unchanged; CP4/CP6 and complete third-party NOTICE/brand audit remain open.
