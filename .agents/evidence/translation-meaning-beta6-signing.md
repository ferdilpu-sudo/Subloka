# QA-TRANSLATION-MEANING-BETA6-PREVIEW-001 — Owner-signed review hints
Date: 2026-11-04

## Provenance

- **QA review hints PR #13**: `qa/translation-meaning-review-v1@e937ac2f4281f1f7447a7577e353ef1507ad4752`; corrected [Android CI #337](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41603555682) **SUCCESS**, build/domain and Android11/Android15 jobs 3/3 PASS.
- Historical owner-signed Beta5 build `0.7.0-beta.5`, versionCode **335**, [manual CI #335](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41597729628), 4/4 PASS. Owner screenshot confirmed larger 9:16 preview with dual subtitles but revealed ambiguous referent in one machine-generated English translation. No screenshot or user/private caption content is committed here.
- This branch `qa/translation-meaning-beta6-preview` starts **exactly at PR #13's green head**, and contains packaging/version/branch gating only. No source changes to translation prompts, model inference, ASR, Room, caption editing or export payload from PR #13.

## Release package / signing boundaries

- VersionName `0.7.0-beta.6`, generated versionCode `github.run_number`, **strictly >335** even when installed Beta5 is present. Package ID stays `app.subloka.caption`, native engine ABIs stay `arm64-v8a` and `x86_64`.
- The `ui-beta-preview` job can read the owner's signing secret *only* for repository-maintainer `workflow_dispatch` on the **exact branch** `refs/heads/qa/translation-meaning-beta6-preview`. It requires same-run `build`, `media-device`, and `modern-services` PASS before signing. The branch is not main; pull_request events do not sign.
- Existing signer certificate SHA256 pin `295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325` retained. Signed APK must satisfy non-debug, launcher, package, version, ABI/engine verification and clean Android11 emulator launch; never treat a debug/unsigned CI artifact as an update.
- Existing owner-installed Beta5, model files, source videos, project DB and manual caption corrections are **not** modified by creating this branch.

## Verification and next actions

- At branch creation, a **fresh PR CI is PENDING**. A new owner-signed APK **does not yet exist**. Once PR CI passes, owner may manually run **Actions → Android CI → Run workflow → branch `qa/translation-meaning-beta6-preview`**. Only after all four manual workflow jobs PASS and signed metadata is verified may the owner update the Sony SO-03L via `adb install -r`, never uninstall/clear/downgrade.
- On device verify the machine-only meaning reminder in Caption Editor; manual correction still saves with MANUAL origin and suppresses reminder; source-only Export has no translation warning, BOTH and translation have a warning while preserving original Google attribution notices. Also reopen old projects/corrections, reuse model offline, translate/recover and export bilingual SRT/MP4.
- This feature **does not automatically fix a wrong English referent**, measure improved model accuracy, or close CP4/CP6. Future real accuracy changes require pre-registered unseen EN↔ID samples, human bilingual review, memory/latency measurements and device testing. Keep all stacked PRs Draft and stable main untouched.
