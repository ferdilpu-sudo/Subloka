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

Run the benchmark in **two phases**, retaining the same installed test APK so model downloads are not removed between online preparation and offline measurement. A standalone Gradle `connectedDebugAndroidTest` run may uninstall the app and its model storage afterward.

First, keep internet connected and run:

```powershell
.\tools\t10_translation_device_benchmark.ps1 -Phase Prepare
```

After preparation passes, enable airplane mode manually and turn off Wi-Fi, then run **without reinstalling**:

```powershell
.\tools\t10_translation_device_benchmark.ps1 -Phase Benchmark
```

The benchmark phase runs instrumented inference without network and pulls its results to `.t10-benchmark/translation-results.csv`. It does not declare translation quality PASS. Review all 60 outputs:

```powershell
python tools/t10_translation_review.py init .t10-benchmark/translation-results.csv .t10-benchmark/translation-review.csv
python tools/t10_translation_review.py report .t10-benchmark/translation-review.csv --json .t10-benchmark/translation-summary.json
```

See `.agents/testing.md` for CP4 criteria and evidence limitations. The reported ID-clean ASR baseline still exceeds the 20% WER target, so CP4 remains **BLOCKED** and T11 remains **TODO**.

### Restore provisional translation review after pulling

The initial Sony SO-03L translation benchmark produced 60 rows; the AI-assisted review is acknowledged by the user but is **not an independent bilingual human sign-off**. Results: EN→ID 27/30 accepted (90.00%), ID→EN 25/30 (83.33%). All 60 translations returned without recorded engine errors. This does not close CP4.

To reproduce the draft labels from the **exact matching** raw CSV already on the PC:

```powershell
python tools/t10_translation_review.py apply-draft .t10-benchmark/translation-results.csv .t10-benchmark/translation-review-ai-draft.csv
python tools/t10_translation_review.py report .t10-benchmark/translation-review-ai-draft.csv --json .t10-benchmark/translation-summary-ai-draft.json
```

The `apply-draft` command checks an order-sensitive SHA-256 digest of the 60 input/output text pairs and refuses to reuse labels if they differ. It also refuses to overwrite an existing review. The `report` command exits with code 2 while ID→EN fails; that is the expected **quality-gate failure**, not a Python runtime error. The CI translation-device job runs *only* the model-readiness smoke test; offline 60-sample evaluation remains a separate physical-device step.


## T10 ASR thermal and stability sampling (physical device)

After running `tools/t10_device_benchmark.ps1` at least once so the arm64 binary and checksum-verified models are cached in `.t10-benchmark`, connect one physical Android arm64 device. Ensure `t10-dataset.json` and its WAV files remain available; on the phone, enable airplane mode and disable Wi-Fi.

Run the non-inference preflight, then the default 5-minute continuous repeated-utterance sampling (Whisper base / Indonesian):

```powershell
.\tools\t10_asr_stability.ps1 -PreflightOnly
.\tools\t10_asr_stability.ps1 -RunMinutes 5 -Model base -Language id
```

The script refuses to start if battery temperature is 40°C or higher, and attempts to stop inference when it reaches 43°C. It saves device-only evidence under a unique `.t10-benchmark/thermal-*/` directory: `summary.json`, `runs.csv`, `telemetry.csv`. The logged temperature is **battery temperature**, not CPU temperature, and RSS is sampled (possibly unavailable). If interrupted, treat `ABORTED` as an inconclusive result. Keep the device in a normal ventilated position, monitor it during the test, and do not treat this five-minute short-utterance loop as a ten-minute-video E2E test or a CP4 PASS. The initial Indonesian ASR quality and ID→EN translation-quality blockers remain.


### Windows PowerShell 5.1 ADB stderr fix (T10)

If an earlier stability run ended `ABORTED` after a successful `adb push` reporting `1 file pushed`, the issue was caused by handling native stderr with PowerShell `ErrorActionPreference=Stop`, not by a Whisper/thermal failure. Pull the latest `main`, rerun `-PreflightOnly` and then `-RunMinutes 5 -Model base -Language id`. The helper now uses ADB's actual native exit status. A Windows PowerShell 5.1 mock-native regression test runs in T10 Engine Evaluation CI. Preserve prior `thermal-*/` output; it must remain `ABORTED`.


### Stability diagnostic: transcript exists but ADB exit code is blank

On some Windows PowerShell 5.1 sessions, `Start-Process -PassThru` can expose no usable `ExitCode` after the remote Whisper transcript is written. The stability harness now requires a nonempty remote result but records the ADB result as `RESULT_PRESENT_EXIT_UNKNOWN` (or `RESULT_PRESENT_ADB_NONZERO` when applicable), without falsely claiming an exit-zero PASS. `summary.json` contains `unverified_adb_exit_runs`; `runs.csv` contains `completion_evidence` and `adb_exit_code`. Logs for unverified or failed runs stay under the private, git-ignored `thermal-*/` directory for local diagnostics. A run with no nonempty transcript still aborts. Old `ABORTED` sessions are never overwritten.


### T10 five-minute Sony stability result (provisional)

Physical Sony SO-03L (Android 11), Whisper Base/Indonesian, airplane mode/Wi-Fi off, USB connected: **300.06 s, 23 runs, median RTF 1.0539, p95 RTF 1.2304, observed peak process RSS 378888 KiB (~370 MiB), battery 36.5 to 39.2°C (+2.7°C)**, no 43°C thermal stop. All 23 local Windows ADB process exit codes were unavailable, so this is **performance evidence only, not fully verified inference success or a 10-minute video test**.

To avoid another five-minute session before the exit marker is validated, the updated harness writes a `result.exit` marker on the **Android shell itself** and checks it separately from the Windows ADB exit. The CI suite exercises marker writing with a POSIX `sh` stub and Windows PowerShell regression. The follow-up physical Sony run has now confirmed **9/9 remote Whisper exit=0** over **132.86 s** (median RTF 0.7021, p95 1.118, observed RSS peak 378764 KiB, battery 38.5→39.0°C). Windows ADB ExitCode remained unavailable on 9/9, so the session is reported as `COLLECTED_REMOTE_VERIFIED_ADB_UNVERIFIED`; do not claim the host transport was verified. New `summary.json` fields distinguish verified remote exit-zero runs from unavailable host ADB codes. Do not relabel the older five-minute run. **CP4 remains BLOCKED**: ID clean ASR WER and ID→EN quality still miss their thresholds, and full video-E2E/timing/resource gates are incomplete. Prioritize review of Indonesian ASR reference/hypothesis errors next.


### T10 ASR Indonesian error audit from cached benchmark

User-provided FLEURS `asr-results.csv` + `t10-dataset.json` contain 120 results across two Whisper models. For 20 Indonesian clean samples, Whisper Base makes **105 word edits over 367 reference words (28.61% micro WER)** versus Tiny's 162/367 (44.14%). The Base errors include 82 substitutions, 7 deletions, and 16 insertions. Reaching the frozen 20% WER gate requires reducing errors by **at least 32**. The six highest-error recordings `id-clean-{07,12,02,08,17,19}` account for **56/105** Base errors, so listen to those original WAVs first before revising references or tuning decoding parameters.

Generate a reproducible, **text-only** diagnostic review without changing source data:

```powershell
python tools/t10_asr_error_audit.py .t10-benchmark/asr-results.csv t10-dataset.json .t10-benchmark/asr-audit-v1
```

The generated `asr-error-summary.json` reports micro/macro WER, edit counts and original SHA-256s; `id-clean-base-audio-review.csv` starts with `UNREVIEWED` for every clip. Outputs refuse to overwrite a nonempty destination folder. **Audio is NOT read** by this script: references, especially odd-sounding FLEURS translations, must be verified by listening to the original WAV before correction. Recomputed WER matches 119/120 archived rows; the one `base/en-challenging-06` row differs (archived 0.2326 versus recomputed 0.2093), not affecting the Indonesian clean baseline. Do not silently fix archived evidence or game the metric. CP4 remains BLOCKED.

