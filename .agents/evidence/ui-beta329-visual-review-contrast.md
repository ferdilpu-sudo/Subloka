# UI-BETA329-RECORDED-REVIEW-001 — Android UI contrast and preview control overlap

Date: 2026-11-03. User-supplied screen recording reviewed locally (about 50 seconds, 1096x2560); no video frames/notification contents are uploaded to the repository. This is **user-provided visual evidence**, not an independent physical Sony model, APK signing, or engine-duration certification.

## Observations tied to recording times

- ~0–10 s: Home/Projects opens, multiple persisted project cards are shown, the persistent "Proyek baru" button stays visible. Editor opens without an obvious navigation crash. No evidence of data loss, but the recording alone does **not** prove all legacy projects/corrections/models survive.
- ~10–15 s: Editor and Style screens render; video context and caption correction card are visible. The "Caption 1 dari 3" label and the "Tampilan subtitle" heading are nearly black on dark gray. The Teks/Waktu/Gaya switcher sits adjacent to the lower preview/subtitle region and unselected areas appear to show underlying player pixels.
- ~15–47 s: Offline TranslateGemma setup transitions from model preparation to translating caption 1 of 3. Plain-text labels, titles, warnings, checkbox text, and processing status are black against a dark gray background. Model is displayed as available, but transcription/translation success, accurate output or completion time **cannot** be concluded from the clip; progress remains on caption 1 when video ends.
- At the end of the recording the user opens the notification shade; avoid interpreting notification overlay as a SubLoka layout defect.

## Source-level root cause

`SubLokaTheme.kt` specified a dark Material3 `ColorScheme` but used `MaterialTheme(content=content)` without an explicit root Surface or LocalContentColor. Plain `Text` on root-level `Column` components (`TranslationSetupScreen`, `ProcessingScreen`, editor navigation, Home headings) can inherit the platform's default black text color. A screenshot showed the unwrapped background approximately RGB #303030, making black text severely low-contrast. On the intended SubLoka palette, TextPrimary #F5F7FA on Canvas #0F1115 offers roughly 17.6:1 contrast.

The preview switcher was an unbounded segmented button row. The player's dark/video surface remained visually visible beneath inactive switcher sections.

## Patch prepared as a stacked, draft QA change

Source branch `ui/autocap-physical-review-contrast-fix` based on owner-signed preview head `ui/autocap-mobile-beta-preview@2c77287fa7176b05be7c43902add3e6f89b972be`.

- `core/designsystem/SubLokaTheme.kt`: wrap theme content in a `Surface(fillMaxSize, Canvas, TextPrimary)`. This establishes a predictable root background and inherited content color across screens. Existing palette, navigation callback, app data, and engine unchanged.
- `feature/editor/EditorScreen.kt`: use an opaque, bounded Surface around Teks/Waktu/Gaya switcher to separate it from preview/video pixels; preserve tabs, onClick, selected states.
- `app/androidTest/TranslationRecoveryUiTest.kt`: new Compose test checks offline translation screen under real `SubLokaTheme`, dark-root content color equals `TextPrimary` and title/progress remain visible.
- No change to persistence/Room, Whisper/TranslateGemma, media decoding, model files, signing, versioning, Google attribution, SRT/MP4 output or current owner-installed app.

## Verification / acceptance

Current owner-signed UI Beta #329 passed GitHub Android CI and clean emulator launch, but **this particular video indicates VISUAL UI FAIL**. The pre-patch `subloka-ui-beta.apk` artifact for #329 must NOT be treated as visually accepted.

QA patch CI: **PENDING**. After it passes, do a new owner-key signed beta preview build based on the corrected source, with versionCode strictly above 329 if that preview was already installed (or above 310 on the previous baseline). Verify contrast on the Android Sony UI under screen brightness/font size changes, preview switcher separation, long caption text, and recovery/foreground processing. Do not downgrade, uninstall, clear app data or merge to main without mobile owner acceptance.

Non-blocking followups: project cards for similarly titled files could benefit from differentiating by thumbnail/date, but the clip gives no basis for altering persistence/project names. TranslateGemma processing is potentially slow on this device, but a 50-second clip cannot establish abnormal runtime; do not change model or inference path based on this visual review.
