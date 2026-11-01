# UI-AUTOCAP-MOBILE-EXPORT-001 — Export UX structured without changing media

Date: 2026-11-01.

## Provenance and dependency

The user requested an AutoCap Desktop-inspired UX adaptation of the working SubLoka Android app. This export-only patch branches from `feat/legacy-translation-export-notices@09fce45c0dc7dd4b2bd9f571fa39bc864c1b774e` (Draft PR #2), NOT directly from main. The inherited PR #2 domain utility `TranslationOrigins.exportWarnings` and its attribution behavior are a **functional prerequisite**. The intended PR target is PR #2's branch, so a reviewer sees only this UI patch. Once PR #2 is merged, retarget export PR to main after verifying the compare diff. Do not cherry-pick this branch onto stable main before its dependency.

## UX problem → solution

- **P2 usability/consistency:** flat vertically scrolling format/language/output content was harder to scan on a narrow phone than the same categories in AutoCap Desktop. Group these existing controls into three understated Material3 outlined/tonal sections: `Format hasil`, `Bahasa caption`, and conditional `File SRT` / `Hasil video`.
- **P1 attribution clarity:** existing PR #2 shows inherited historical Google Translate (ML Kit) or unknown machine-origin warnings only for translation/BOTH modes. Present these notices in a subdued bordered `Asal terjemahan` section, visually separate from choices. Do **not** infer Google attribution from Gemma/manual/unknown origins or claim full compliance.
- **P1 task continuity:** keep a single footer action visible independently of scrolling the controls, preserve the SRT-vs-MP4 and original-vs-translation selection, export eligibility, prepared SRT snapshot, pending document picker, post-render saved MP4, cancellation and ready-state behavior.

## Source changes

- `feature/export/src/main/java/app/subloka/feature/export/ExportScreen.kt`: simple local `ExportSection` composable and layout-only groupings. Current messages, buttons, eligibility booleans, origin warnings, callbacks and snapshots all remain unchanged.
- `app/src/androidTest/java/app/subloka/ExportFlowUiTest.kt`: adds compact 320x480dp and 150% font test for section accessibility, ML Kit and unknown warnings shown for translated output, source-only suppression, SRT and MP4 actions.
- Does not modify Whisper, Silero, TranslateGemma, Room schema, media/rendering, SRT cue contents, document writer, file picker, signing keys, or previously saved projects.

## Verification evidence / limits

- PR #2 baseline Android CI [#41153737370](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41153737370) completed success. This is **parent code evidence**, not proof of this patch.
- Source and test changes are committed on `ui/autocap-mobile-export-v1`. Android CI compile, static checks and Compose device tests: **PENDING** for this new PR.
- Sony SO-03L on-device UI/large-font and TalkBack acceptance: **NOT_RUN**. No APK produced or installed for this patch.
- Existing `ExportFlowUiTest` must still pass: stale translations block translation but not original, SRT save snapshot stays available, foreground MP4 cancellation, ready state, and PR #2 origin warnings. New test must also PASS.
- Requirement for Google branding/graphic/disclaimer and full third-party notices remains OPEN; visual warning does not equal distribution compliance. CP4/CP6 remain open.
- Independent UI PRs #3 (Home), #4 (Editor), #5 (Timing/Style) may be integrated separately after CI and physical acceptance. Do not merge to main or publish a release based on this PR alone.
