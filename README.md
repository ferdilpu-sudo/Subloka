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


### T10 listening review final and gain-only diagnostic

Six priority Indonesian clean WAVs were human-reviewed: `id-clean-07`, `id-clean-12`, `id-clean-02`, `id-clean-17`, and `id-clean-19` are `AUDIO_AMBIGUOUS`; `id-clean-08` is `REF_MATCHES_AUDIO`. The decisions are archived in `.agents/evidence/t10-asr-listening-review-final.json`. **The official FLEURS reference text and 20-sample Indonesian clean baseline are not changed**; Whisper Base ID-clean WER remains 28.61% against the 20% CP4 target.

An **optional, non-gating** diagnostic compares amplitude-only WAV gain with each original for the two low-level clips `id-clean-02` and `id-clean-12`, one trial of each condition per sample. It uses the existing pinned Whisper Base model/binary and checks Android offline mode and battery temperature before running. It needs original WAVs in `t10-audio/id-clean/`, plus cached artifacts from the prior benchmark.

```powershell
git pull origin main
python tools/t10_asr_gain_ab.py --preflight-only
python tools/t10_asr_gain_ab.py
```

The four diagnostic runs write `.t10-benchmark/gain-ab-<timestamp>/summary.json` and `runs.csv`. Reported WER is labeled against a **listener-ambiguous reference**, never official CP4. No new baseline, no dataset edits, no sample exclusions, and no claim that volume gain improves SNR or ASR quality without further evidence.


### T10 gain-only result (Sony, diagnostic only)

On Sony SO-03L (Android 11, offline), four A/B Whisper Base inference runs completed with **both Android Whisper exit 0 and ADB host exit 0**, without reaching the 43°C battery thermal threshold (37.7→38.5°C). The two listener-ambiguous samples did **not** show a WER benefit from changing volume alone: `id-clean-02` 44.44% → 44.44% at +17.2 dB; `id-clean-12` 66.67% → 73.33% at +8.453 dB (worse). Hypotheses changed in both pairs. See `.agents/evidence/t10-asr-gain-ab-sonyoct08.json` for provenance and run metrics. These tiny one-shot comparisons cannot establish population-level effects, and gain-only does not improve SNR. **No model, preprocessing, dataset, baseline, or gate changes have been made.** Next focus: controlled whole-set ASR quality experiments against the unchanged 20-clip benchmark, not additional gain-only trials.


### T10 full-set decoding A/B (frozen Indonesian clean, diagnostic)

The gain-only experiment did not improve either of its two ambiguous clips, so the next T10 step evaluates **decoder beam size only** with the same cached Whisper Base model, unchanged CLI control settings and **all 20 original** FLEURS Indonesian clean WAVs, including clips marked `AUDIO_AMBIGUOUS`. The control uses exactly `-nt -ng -nfa -otxt -of result` and the candidate adds `-bs 1`. Order alternates AB/BA across samples to reduce sequential device-temperature bias. The tool pins the original manifest and CSV baseline hashes, and refuses altered audio/model/CLI on resume.

First run a non-inference preflight and a **3-pair pilot (6 inferences)** on the physical offline Sony, then review `summary.json`. Only if the pilot behaves correctly and the phone is cool, resume the same unique session to finish all 20 paired samples:

```powershell
git pull origin main
python tools/t10_asr_decode_ab.py --preflight-only
python tools/t10_asr_decode_ab.py --max-pairs 3
# Copy the decode-ab-* directory shown by the pilot; replace the example below:
python tools/t10_asr_decode_ab.py --resume ".\.t10-benchmark\decode-ab-YYYYMMDDTHHMMSSZ-XXXXXX"
```

The script checks offline/arm64/battery conditions, attempts safe interruption at battery >=43°C, and writes `summary.json`, `runs.csv`, stderr/stdout logs to `.t10-benchmark/decode-ab-*`. `PARTIAL_EXPERIMENT_NOT_CP4` is expected for the short pilot; `COMPLETE_EXPERIMENT_NOT_CP4` indicates data collected across 20 pairs, **not an official gate pass**. Frozen official Base ID clean remains 105/367 errors (28.61% WER); CP4 BLOCKED and T11 TODO. Do not infer accuracy improvement before comparing complete paired WER and inspecting transcripts.


### T10 decoding A/B pilot (3 of 20 pairs)

First physical Sony pilot returned six ASR runs (3 paired samples) with exact frozen-control transcript reproduction **3/3**. On 53 reference words, Whisper Base control had **15 edits (28.30% micro-WER)** versus `-bs 1` with **17 edits (32.08%)**, or **+2 edits/+3.77 percentage points worse** in this small subset. All three hypotheses differed, but no sample improved (deltas 0, +1, +1). Per-sample RTF moved in both directions. Evidence: `.agents/evidence/t10-asr-decode-pilot-3pairs.json`. This is too small for a conclusion about all 20 clips; no decoding change is promoted. Baseline stays 105/367 (28.61%) and CP4 remains BLOCKED.

**Before continuing**, inspect the original session's `summary.json` for `status`, `stop_reason`, `battery_last_c` and events; this user-provided excerpt included only the `analysis` object, not the thermal/session outcome. If safely `PARTIAL_EXPERIMENT_NOT_CP4` with no stop reason and device cool, continue the **same** session in stages with e.g. `python tools/t10_asr_decode_ab.py --resume ".\.t10-benchmark\decode-ab-<actual-session>" --max-pairs 4`. Do not create a new session or delete previous pilot evidence. CI for harness commit `b3fda1c` passed: Android CI and T10 Engine Evaluation.


### T10 decoding A/B after seven paired samples

After resuming the same Sony session for four more sample pairs, **control and `-bs 1` tied on 7/20 Indonesian clean clips: 32 word edits each across 129 reference words (24.81% micro-WER each)**. The additional four recovered the two-edit disadvantage from the original three-pair pilot (additional control 17 edits, beam1 15). Evidence: `.agents/evidence/t10-asr-decode-7pairs.json`. The user supplied aggregate `analysis` only, not updated session status/temperature or raw run logs, so confirm `status=PARTIAL_EXPERIMENT_NOT_CP4`, empty `stop_reason`, and battery safely cooled before another short staged resume. Do not infer a stable decoding advantage or change engine defaults, dataset or baseline. Official CP4 remains BLOCKED with 105/367 baseline edits.


### T10 decoding A/B — 11/20 pairs completed on Sony

Another four pairs (`id-clean-08` to `11`) were collected in the **same** `decode-ab-20261008T145942Z-10430e` session. Cumulative results: default 48 edits, `-bs 1` 47 edits out of **203 reference words** (23.65% vs 23.15% diagnostic micro-WER, only **one** edit difference); 22/40 inference runs completed. Latest stage passed offline preflight (battery 30.2°C), ended with battery 31.0°C and `PARTIAL_EXPERIMENT_NOT_CP4` / empty stop reason. Details: `.agents/evidence/t10-asr-decode-11pairs.json`. This tiny numerical advantage cannot establish a production improvement. After a fresh device preflight/cooldown, resume the existing session with `--max-pairs 4` for clips 12–15, and inspect status plus paired WER. **Official** Base ID-clean WER 105/367=28.61%, CP4 BLOCKED.


### T10 decoding A/B — progress 15/20

The latest Sony session summary reports default decoder 72/270 edits (**26.67%**) versus `-bs 1` 73/270 edits (**27.04%**) on **15 paired Indonesian-clean clips**, with `PARTIAL_EXPERIMENT_NOT_CP4`, empty stop reason, battery last 30.2°C. Only one edit separates them; do not promote either candidate from a partial set. See `.agents/evidence/t10-asr-decode-15pairs.json` (user-reported excerpt). After a new cool/offline preflight, **resume the same session** using `--max-pairs 5` for clips `id-clean-16` through `20`. The frozen CP4 official baseline is unchanged at 105/367=28.61%, CP4 BLOCKED.

### T10 decoding A/B — final 20-pair outcome

The physical Sony experiment completed all **20 paired original Indonesian-clean FLEURS recordings**. Whisper Base default matched archived transcripts **20/20** and had **105/367 word edits (28.61%)**; `-bs 1` had **110/367 edits (29.97%)**, five additional errors (**+1.36 percentage points worse**). Session ended with `COMPLETE_EXPERIMENT_NOT_CP4`, no reported stop reason and final battery **30.7°C**. The user-provided evidence excerpt is archived in `.agents/evidence/t10-asr-decode-final-20pairs.json`; full local logs not independently inspected. **Do not switch v1 to `-bs 1`.** The frozen CP4 baseline remains 28.61% vs 20% target, CP4 BLOCKED; other translation and 10-minute app E2E gates remain open. Do not rerun this completed A/B unnecessarily; continue other T10 blockers or use a new, predefined ASR evaluation plan.


### T10 — independent bilingual translation QA handoff

The initial Sony offline ML Kit translation output has an **AI-assisted, provisional** review only (EN→ID 27/30, ID→EN 25/30). This is **not independent bilingual human verification**. The new QA handoff leaves all 60 AI suggestions visible only as provisional hints and never pre-fills a human decision; it verifies the original device CSV against the frozen 60-input fixture, captures source hashes, and refuses to overwrite final reports or reinterpret newer inference output using stale AI labels.

With the **original** local `.t10-benchmark/translation-results.csv` available, run:

```powershell
git pull origin main
python tools/t10_translation_human_qa.py prepare .t10-benchmark/translation-results.csv .t10-benchmark/translation-human-qa-01
```

A bilingual reviewer must inspect every row in `.t10-benchmark/translation-human-qa-01/human-review.csv`, fill all 60 `human_status` decisions (`ACCEPT`, `MAJOR_MEANING_ERROR`, `NEGATION_ERROR`, `NUMBER_OR_NAME_ERROR`), and justify every rejection and disagreement with provisional AI assessment in `human_notes`. Do not change any other columns, model outputs, or sample IDs. The separate `REVIEW_INSTRUCTIONS.md` generated in the session summarizes flagged rows. **Do not mark entries ACCEPT just to meet 90%.** For a new device run that does not match the previous AI-draft content hash, the AI labels are marked `NOT_APPLICABLE`, not copied.

After review, finalize with an attested bilingual reviewer identity (the script records a declaration; it cannot authenticate reviewer independence):

```powershell
python tools/t10_translation_human_qa.py finalize .t10-benchmark/translation-results.csv .t10-benchmark/translation-human-qa-01 --reviewer "Bilingual Reviewer" --attest-independent-bilingual-review
```

This creates `human-reviewed.csv`, `human-quality-report.json`, and `human-signoff.json`. The quality report uses the unchanged threshold logic in `tools/t10_translation_review.py` (>=27/30 accepted per direction, no negation or number/name error). Share the reviewed files for analysis; **CP4 remains BLOCKED** independently because Indonesian ASR WER is 28.61% (>20%) and 10-minute app/video E2E resource gate has not been completed.


### T10 AI audit — a readable 60-row translation report

The user's exact 60 source/output pairs were found in an archived conversation file and rechecked by AI using the same canonical source+output digest from `tools/t10_translation_ai_draft.json` (`2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c`). The resulting **AI-provisional** assessment is **EN→ID 27/30**, **ID→EN 24/30**, with 9 major meaning issues, 15 accepted with caution and 36 accepted without identified material concerns. One status changed from the original AI draft: `id-17`, where the untranslated Indonesian word `Peron` makes the English rail-platform sentence unclear for an English-only reader. Audit provenance and exception IDs are recorded in `.agents/evidence/t10-translation-ai-provisional-recheck-60.json`. A readable local HTML (filterable cards) and XLSX (dashboard, nine issues, both directions) were provided as conversation attachments, not repo inputs.

This is **not independent human signoff**. It never fills `human-review.csv`, never calls `finalize`, and never changes `translation-results.csv`, the ML Kit engine, original benchmarks or CP4 acceptance. The archived CSV uses different byte serialization from the original Sony CSV; only the canonical source/output text digest was verified. A bilingual human reviewer is required for human-certified quality, and CP4 remains blocked by translation, ASR and 10-minute real in-app video resource testing.

### T10 user acknowledgement of translation AI audit

The user reported reviewing the readable AI audit and agreeing with its judgments (`sudah saya review. review saya sama dengan review ai`). Recorded in `.agents/evidence/t10-translation-user-acknowledgement.json` while preserving the original provisional 27/30 EN→ID and revised provisional 24/30 ID→EN results. This confirmation is **not** a machine-verified signed independent bilingual 60-row review: exact per-row coverage / reviewer independence were not established, and `human-review.csv` remains without generated signoff. **No scores, device outputs, fixtures, or CP4 gates were changed.** Next technical work should focus on actual ID→EN translation improvements or a real 10-minute Android app E2E run. CP4 BLOCKED.

### Translation 60/60 review coverage confirmed by user

The user clarified **"saya review 60"**, after saying their judgments agree with the readable AI audit. The repository records **all 60 translation pairs reviewed according to the user's explicit confirmation** in `.agents/evidence/t10-translation-user-acknowledgement.json`; the previous uncertainty about number reviewed is resolved. This is AI-assisted review agreement, not a generated formal `human-signoff.json` or separately verified independent bilingual-review credential. Confirmed numerical outcomes remain EN→ID 27/30 and ID→EN 24/30, so ID→EN still fails the acceptance threshold. Frozen device/model data and CP4 remain unchanged.


### T10 translation fidelity diagnostic (warnings only)

A new pure-Kotlin helper, `engine/translation/src/main/java/app/subloka/engine/translation/TranslationFidelityGuard.kt`, inspects bilingual `sourceText` and `translatedText` for six **possible** fidelity risks: digit changes, missing negation, weakened prohibitions, contradicting time references, ungrounded gender assumptions, and untranslated Indonesian transport/administrative terminology. This helper is **not a translator or automatic corrector**. It never touches ML Kit outputs, does not score translation correctness or repair the nine reviewer-reported semantic failures, and is not yet wired to the editor; a future T12 integration would show non-blocking warnings subject to user review.

Reproducible unit testing (after pull):

```powershell
.\gradlew.bat :engine:translation:testDebugUnitTest
```

Android CI was updated to run the Gradle unit tests (15 Kotlin regression scenarios) automatically. A standalone Kotlin compiler with local JUnit stubs passed these 15 before the commit; check GitHub Actions for the **actual** Gradle outcome after push. On archived 60 Sony outputs, the diagnostic flagged seven pairs (four previously confirmed as major problems, three acceptable but cautionary); five other material problems were missed. This is **not independent validation**, and a zero-warning output does not equal ACCEPT. Full diagnostic provenance and limitations: `.agents/evidence/t10-translation-fidelity-guard-static.json`. **No demonstrated translation quality improvement:** EN→ID 27/30, ID→EN 24/30, CP4 BLOCKED. Genuine quality gains require a predeclared separate engine/translation candidate and previously unseen held-out QA inputs; do not memorize fixes for the frozen 60 samples.


### T10 — NEW offline paired paragraph translation diagnostic (not the frozen CP4 gate)

A separate, **pre-registered 60-paragraph A/B experiment** compares two strategies using the **same** existing ML Kit English–Indonesian offline models: `whole` translates two sentences in one call, while `linewise` translates each sentence separately and concatenates them (two calls). This tests a possible segmentation benefit, **not an alternative neural model**. Input fixture: `engine/translation/src/androidTest/assets/t10_translation_strategy_ab_fixtures.json`; 30 new Indonesian and 30 new English two-sentence paragraphs. The original 60 single-sentence CP4 inputs and all previous output/review evidence are untouched. No production `MlKitOfflineTranslator` change.

On Sony SO-03L / Windows PowerShell 5.1 after `git pull --ff-only origin main`, **prepare the installed model online first** (this is not the offline inference phase):

```powershell
.\tools\t10_translation_device_benchmark.ps1 -Phase Prepare
```

Then enable airplane mode, turn off Wi-Fi, ensure battery temperature below 40°C and continue with **ONLY** the new Strategy diagnostic:

```powershell
.\tools\t10_translation_device_benchmark.ps1 -Phase Strategy
```

Offline preflight checks airplane-mode/Wi-Fi state; test stops at battery >=43°C or wall time >=10 minutes. Battery reading is not SoC die temperature. The new raw file is `.t10-benchmark/translation-strategy-ab-results.csv` and must **not overwrite** the original `.t10-benchmark/translation-results.csv`. 60 matched sources yield 120 variant outputs across 180 ML Kit calls; order alternates within source.

Prepare a **readable offline browser review** instead of editing multiline CSV manually:

```powershell
python tools/t10_translation_strategy_ab_review.py init .t10-benchmark/translation-strategy-ab-results.csv .t10-benchmark/translation-strategy-ab-qa-01
Invoke-Item .\.t10-benchmark\translation-strategy-ab-qa-01\review.html
```

Browser cards show each paragraph and the two outputs side by side as Output 1/2, with status selection and explanatory notes. Export the CSV to keep progress; later you may reimport it into the browser. Grading is **not auto-filled**. After both variants of every source have been assessed (120 decisions), export `translation-strategy-ab-review.csv` to Downloads and run:

```powershell
python tools/t10_translation_strategy_ab_review.py report .t10-benchmark/translation-strategy-ab-results.csv .t10-benchmark/translation-strategy-ab-qa-01 "$HOME\Downloads\translation-strategy-ab-review.csv" --json .t10-benchmark/translation-strategy-ab-qa-01/paired-report.json
```

The script enforces original raw/fixture hashes and all complete paired judgments; reports per-language accepted samples, wins/losses, median/p95 latency and critical regression counts. **Pre-registered diagnostic success** requires the candidate achieve >=27/30 ACCEPT per direction, >=3 **net** additional accepted compared with control in each direction, no added negation/number/name errors, and p95 latency <=2.5x control. Even then, results are merely PROMISING and require independent confirmation with truly unseen sources before any production change. This two-sentence diagnostic **cannot replace or regrade the frozen CP4 single-sentence benchmark**. ASR Indonesian clean 28.61% WER and translation ID→EN 24/30 reported baseline still BLOCKED; real 10-minute in-app video E2E remains undone.


### T10 paragraph strategy A/B physical CSV captured — scoring pending

On Sony SO-03L the user reports an **instrumentation PASS** (`OK (1 test)`, `INSTRUMENTATION_CODE: -1`) and successful retrieval of the new `.t10-benchmark/translation-strategy-ab-results.csv`, **27,616 bytes**, SHA256 **`50e612ec7ec41d37de1e520650f1c5f90343267856bfe0c6f44ae0d27991353f`**. This evidence is retained in `.agents/evidence/t10-translation-strategy-ab-device-captured.json`; raw device CSV is gitignored and was **not** seen by the assistant. The required next action is the `tools/t10_translation_strategy_ab_review.py init` check for exact complete 120 A/B variant rows, then upload original raw CSV for AI-assisted paired semantic review. Neither strategy has yet been established superior and this new paragraph fixture does not replace any CP4 evaluation. Android CI and T10 Engine Evaluation for commit `251f9cb` passed. CP4 remains BLOCKED.


### T10 paragraph translation A/B result — linewise rejected

The user uploaded a **complete 120-row labelled review CSV** for the new two-sentence paragraph A/B, SHA256 `516ca5d8967aefa7046db65e53fb1788ef7267bb48f7f34ada48eb72d20018a9`. Comparing matched judgments: **whole vs linewise** ID→EN **21/30 vs 21/30** and EN→ID **22/30 vs 22/30**, both zero net gain. **58 of 60 source pairs produced exactly equal translations**; only `id-ab-17` and `en-ab-17` changed text without changing ACCEPT status. The candidate was slower in **56/60** source pairs; median ID→EN **58.31 vs 76.93ms**, EN→ID **52.12 vs 68.85ms**, and p95 also slower in both directions. No introduced critical errors, but the original number/name error and negation error remain in both configurations.

Pre-registered acceptance-improvement criteria were **NOT MET** (required >=27/30 ACCEPT and >=+3 net accepted per direction). **Decision: retain whole strategy; do not promote linewise to the production engine**. This experiment uses the same on-device ML Kit models and NEW 2-sentence paragraphs: it cannot improve, regrade, or replace the frozen original CP4 test outcomes. Original raw Sony CSV hash remains user-reported (not byte-verified here); uploaded file was the graded CSV. Complete scoped results and provenance: `.agents/evidence/t10-translation-strategy-ab-review-complete.json`; browser-viewable 60-card HTML, 3-tab XLSX and full JSON analysis are available as separate conversation artifacts. Reviewer identity/independence not externally verified. Gate still **T10 ACTIVE, CP4 BLOCKED, T11 TODO** due original ID→EN 24/30, ASR Base clean Indonesian WER 28.61%, and unperformed real 10-minute in-app video E2E.

