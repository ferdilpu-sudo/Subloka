# SubLoka

> Focused offline bilingual caption editor for Android (English ↔ Indonesia).

Current implementation has the **frontend demo plus local Room persistence/editor rules**. Media import/playback, speech recognition, offline translation engine, and real export are not connected yet. Demo inference/export states remain labeled and must not be interpreted as real processing.

## Product direction

`Choose video → Generate caption → Correct → Export`

Editor workspaces are deliberately limited to **Caption**, **Timing**, and **Style**. Translation is contextual state/action, not a fourth workspace.

## Toolchain baseline

- Android Gradle Plugin: 9.4.0
- Gradle Wrapper: 9.6.0
- Kotlin / Compose compiler plugin: 2.3.21
- compileSdk / targetSdk: 37
- minSdk: 26
- Compose BOM: 2026.09.00
- Activity Compose: 1.13.0
- Core KTX: 1.19.1

## Verification status

Android CI has verified the frontend scaffold on GitHub Actions:

- project guardrail validator: **PASS**
- `:app:assembleDebug`: **PASS**
- `:app:lintDebug`: **PASS**
- Gradle Wrapper 9.6.0 generation: **PASS**
- verified build evidence: [Android CI run #9](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37462634099)
- wrapper bootstrap evidence: [Bootstrap Gradle Wrapper run #1](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37463131375)

The frontend also passed the user-confirmed DEVICE-001 manual smoke test and CP3 acceptance gate. T08 persistence passed domain/Room integration tests and schema-fixture verification on Android CI run #15. T09 also proves the baseline real media path on an Android 11 emulator. This still does **not** prove offline ASR/translation quality, physical-device performance, or real export.

## Modules

- `app` — composition root, navigation state, demo fixtures.
- `core:domain` — UI-facing product models and invariants used by the demo.
- `core:designsystem` — SubLoka theme and reusable semantic UI pieces.
- `core:database` — Room v1, repository adapters, persistence facade, and schema fixture.
- `feature:projects` — Projects, New Project, offline model setup, processing states.
- `feature:editor` — Caption/Timing/Style editor workspaces and adaptive composition.
- `feature:export` — final export choices and blocked-state explanation.
- `.agents` — coding-agent source of truth: product, rules, architecture, design, plan, testing, and handoff notes.

## Coding-agent guidance

All implementation guidance and handoff notes live under [`.agents/`](.agents/README.md). Agents should start at [`.agents/AGENTS.md`](.agents/AGENTS.md) and follow the prescribed read order before changing code. Keep task status in `.agents/plan.md` and test evidence in `.agents/testing.md`; do not scatter new planning Markdown around the repository.

## Build locally

Gradle Wrapper 9.6.0 is committed to the repository. A global Gradle installation is **not required**.

Windows PowerShell:

```powershell
git pull origin main
.\gradlew.bat --version
.\gradlew.bat :app:assembleDebug :app:lintDebug
```

macOS/Linux:

```bash
git pull origin main
./gradlew --version
./gradlew :app:assembleDebug :app:lintDebug
```

The first wrapper run downloads Gradle 9.6.0 automatically, so network access is required once unless the distribution is already cached.

T04–T09 are **DONE** and CP3 is **PASS**. T09 real media pipeline passed on an Android 11 emulator. **T10 is now BLOCKED at CP4** after model/readiness smoke: the remaining gate is human-dataset quality plus physical-device RTF/RAM/thermal benchmark. T11 has not started. See `.agents/plan.md` and `.agents/testing.md`.

## T10 physical benchmark

T10 includes `tools/t10_device_benchmark.ps1` for arm64 Android evaluation of pinned Whisper tiny/base through ADB. It validates model checksums, builds whisper.cpp v1.9.4 with NDK 28.2.13676358, enforces the minimum dataset counts, and writes WER/RTF/RSS results. Synthetic/emulator smoke results are not accepted as CP4 quality evidence. Start from `tools/t10_dataset.example.json`, prepare the required human-recorded dataset, then on Windows run `./tools/t10_device_benchmark.ps1 -DatasetManifest <path-to-manifest.json>` with an arm64 Android device connected through ADB.

## T10 translation quality evaluation (prepared)

The offline ML Kit quality harness is in `engine/translation/src/androidTest/`; it reads 30 authored EN inputs and 30 authored Indonesian inputs and exports device translations for human evaluation. Review and freeze the input fixture before evaluating its outputs. This is **not** a translation quality PASS.

Run the offline benchmark on a physical Android device **only after downloading models online** with the existing `MlKitTranslationInstrumentedTest`. Switch the device to airplane mode (Wi-Fi and cellular off), then:

```powershell
.\gradlew.bat :engine:translation:connectedDebugAndroidTest '-Pandroid.testInstrumentationRunnerArguments.class=app.subloka.engine.translation.MlKitTranslationBenchmarkTest'
adb logcat -d -s 'SubLokaT10:I' '*:S'
```

Find `RESULT_PATH=` in logcat; use `adb pull` to copy the CSV. Run `python tools/t10_translation_review.py init RAW.csv REVIEW.csv`, score all 60 translations manually, and run `python tools/t10_translation_review.py report REVIEW.csv --json SUMMARY.json`. See `.agents/testing.md` for CP4 criteria and evidence limitations. The reported ID-clean ASR baseline still exceeds the 20% WER target, so CP4 remains **BLOCKED** and T11 remains **TODO**.
