# UI-AUTOCAP-MOBILE-TOOLS-001 — Timing and Style studio hierarchy

Date: 2026-11-01. Based on stable `main@5514e1a73e0dc698ece04acd3860aba7236216c9`.
Reference: owner-provided AutoCap Desktop UI, especially section/card hierarchy and reduction of ambiguous controls. UI authored natively in Jetpack Compose; not a port of WinUI/XAML.

## Problem → rationale → adaptation
- P2 usability/consistency: Timing's two sets of identical ±10/±100 ms buttons were visually contiguous; users could confuse the **Awal** and **Akhir** targets. Keep the existing nudge behavior and constraints, but group each pair under its own bounded panel with an explicit current timestamp. Source caption goes into a selected-caption reference panel.
- P2 scan/visual hierarchy: Style's chips, 3 sliders and two toggles were a single long flat form. Group into **Bahasa dan urutan**, **Ukuran teks**, **Keterbacaan dan posisi**. Preserve all control labels, existing enum modes, initial values, slider bounds, and callbacks. Help remains below the controls.
- P1 accessibility: keep textual status/section names and existing semantic descriptions on timing nudge and style sliders/switches. Avoid relying on card color to identify actions.

## Files, limits and acceptance
- `feature/editor/TimingWorkspace.kt`: 3 visually bounded sections including source caption, start, end; retains microsecond nudge and neighbor boundary guards verbatim.
- `feature/editor/StyleWorkspace.kt`: groups existing controls into tonal sections; no supported rendering styles added/removed.
- `app/src/androidTest/EditorLayoutTest.kt`: added compact 320×480 dp / 150% font UI tests: at t=0 negative starting nudge disabled and ±10ms callback semantics unchanged; style section visibility and background-toggle callback.
- **No changes** to data schema, model files, inference, translation, video preview/render, SRT/MP4 export, signing, versionCode, or user projects.
- PR #2 touches export screen (attribution) and remains independent. PR #3 (Home) and PR #4 (Editor shell) remain separate, already CI PASS, still draft. This tools PR builds independently on main to avoid accidental merge of those branches.

## Verification
- Implementation and tests committed to `ui/autocap-mobile-tools-v1`; CI Android build/instrumentation **NOT_RUN at writing**.
- Existing EditorLayoutTest boundary/landscape/save assertions must remain PASS.
- Physical Sony SO-03L 320–360dp touch/scroll/landscape/large font/TalkBack **NOT_RUN**. Do not merge on appearance alone.
- CP4, CP6, source/license obligations and paused model benchmark remain open.

## Subsequent UI work
- Export screen can receive the same visual hierarchy once the PR #2 attribution changes are reconciled. Keep export mode/eligibility logic and offline destination picker unchanged. Avoid directly copying the desktop sidebar.
