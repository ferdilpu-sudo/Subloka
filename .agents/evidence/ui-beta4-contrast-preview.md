# UI-BETA4-CONTRAST-PREVIEW-001 — Owner-key device preview for recorded UI fixes

Date: 2026-11-03.

## Origin and prerequisites
- Signed Beta #329 (`0.7.0-beta.3`, versionCode 329) workflow [#329](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41577493041): build, Android 11 media, Android 15 service, signed clean-emulator launch **4/4 PASS**. Artifact `subloka-ui-beta-preview-apk` SHA256 of ZIP `323356405da63a1fea1557687a96fd743a0ccf8e30b277c43752ef283e62f988`. Physical user recording identified visual contrast and switcher separation defects; functional CI did not cover visual accessibility adequately.
- Contrast fix [PR #9](https://github.com/ferdilpu-sudo/Subloka/pull/9) source `c18a7f3dd18c898a4d638dceb26463cd87236988` passed [Android CI #330](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41584977920): 3/3 PASS. It wraps dark-theme root content in an explicit Surface with light LocalContentColor, bounds Teks/Waktu/Gaya switcher in an opaque card, and adds a translation status contrast instrumentation assertion.
- This branch `ui/autocap-contrast-beta4-preview` starts from **exact PR #9 green head**; it is a separate signing/packaging gate and does not replace or merge PR #9. Original stable main remains `5514e1a`; source code, models, Room, media pipeline, existing installed data untouched.

## Safe beta4 signing changes
- `app/build.gradle.kts`: versionName `0.7.0-beta.4` while retaining package ID `app.subloka.caption` and CI run-number-derived versionCode.
- `tools/verify_beta_package.py` and unit tests: signed release requires beta4 and **versionCode >329** so installation upgrades both known Beta #310 and the newest Beta #329. Existing nondebug/launcher/native-ABI/engine verification is still required.
- `.github/workflows/android-ci.yml`: owner-key `ui-beta-preview` job now available exclusively after repository maintainer `workflow_dispatch` on exact ref `refs/heads/ui/autocap-contrast-beta4-preview` and `build`, `media-device`, `modern-services` all pass on same manual run. All `pull_request` runs remain secret-free, with preview signing job SKIPPED. Preexisting legacy prototype job untouched.
- `tools/test_ui_beta_preview_workflow.py`: requires the same fixed branch as the manual signing-only job; checks owner cert fingerprint gate `295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325`.
- Existing finite SDK installer retries remain in place (max 3; persistent failure aborts). No manual signing triggered by merely opening this PR.

## Verification and next steps
- This beta4 package/restriction patch and test sources are prepared; a fresh integrated PR Android CI run is required. **Status at writing: NOT_RUN for beta4 changes**. No signed beta4 APK created or installed yet.
- If PR CI passes, maintainer manually triggers **Actions → Android CI → Run workflow → branch `ui/autocap-contrast-beta4-preview`**. Signed APK is valid for Sony only after all 4 jobs PASS, release metadata + signer fingerprint verified, and clean Android 11 emulator launch PASS; select only `subloka-ui-beta-preview-apk`, never unsigned/debug artifacts.
- Before installing, inspect `adb shell dumpsys package app.subloka.caption` versionCode and versionName, ensure target package ID/fingerprint and preview versionCode > installed; preserve and back up important project files if possible, install with `adb install -r` **only**. Never `adb uninstall`, `pm clear`, downgrade or overwrite models.
- On Sony SO-03L, first test root text contrast on TranslationSetup screen and editor CaptionNavigation, tab switcher separation from player/subtitle, 150% font and landscape, then old projects, corrected captions, reuse Whisper/Gemma, completion/recovery, SRT/MP4, and offline airplane mode. Physical device signoff PENDING.
- PR #7/#8/#9 remain Draft; no main merge, public release, CP4/CP6 closure or unverified legal compliance claim.
