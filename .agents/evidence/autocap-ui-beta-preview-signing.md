# UI-AUTOCAP-PREVIEW-SIGN-001 — Safe owner-key beta preview preparation

Date: 2026-11-03. Based on combined UI QA [PR #7](https://github.com/ferdilpu-sudo/Subloka/pull/7) head `4b67493c619bd9ef13180bdc2aa9a8100dcea299` and on its already successful [CI #41326384859](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41326384859) (build/media-device/modern-services 3/3 PASS). Stable `main@5514e1a`, owner-installed signed Beta #310 (0.7.0-beta.2), and user projects remain unchanged.

## Reason and implementation

The prior owner-held certificate signing job in `.github/workflows/android-ci.yml` is accessible only for explicit `workflow_dispatch` on `codex/t11-offline-asr-prototype`. This cannot create an owner-key release APK from an unmerged combined UX branch. Downloading and directly installing PR debug APK on the Sony SO-03L would risk a signing incompatibility or data loss.

This stacked preparation branch `ui/autocap-mobile-beta-preview` changes **only** release-preview version metadata, package-verifier regressions, the Android CI workflow and this documentation:

- `app/build.gradle.kts` sets `versionName=0.7.0-beta.3`, with `versionCode` still generated from `github.run_number` during CI. No signing key, package ID, engine, model, Room schema, media pipeline or user content changes.
- `tools/verify_beta_package.py` and `tools/test_verify_beta_package.py` require the beta.3 version name and `versionCode > 310`; existing non-debug, app ID, launcher, and native ABI/engine validations remain unchanged.
- A new independent job `ui-beta-preview` in `.github/workflows/android-ci.yml` runs **only** when an authorized repository user manually dispatches `Android CI` on the exact branch `ui/autocap-mobile-beta-preview`. It requires success of build, media-device and modern-services jobs on the **same run**, downloads the release-unsigned APK from that tested run, uses the existing private `SUBLOKA_PROTOTYPE_SIGNING` secret, verifies APK contents/version and pins the signing certificate SHA-256 to the **known installed Beta #310 fingerprint** `295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325`, launches it on a **clean Android 11 emulator only**, then publishes `subloka-ui-beta-preview-apk`.
- Signing cannot run on PR or push events; the pre-existing prototype-only signing job is **unchanged**. Never print or share owner-held keystores, passwords or base64 bundles.

## Device review gate (not performed)

After this stacked PR itself passes CI, a repository maintainer can manually trigger **Actions → Android CI → Run workflow → branch `ui/autocap-mobile-beta-preview`**. The signed preview APK is downloadable *only if* the manual run and all its required jobs pass. Download from `subloka-ui-beta-preview-apk` and inspect `package-info.txt` / `signing-info.txt`.

Before testing on Sony SO-03L: preserve original installation, do NOT run `adb uninstall`, `pm clear`, use APK with a different certificate, install a debug PR artifact, downgrade, or overwrite models. Check actual installed `versionCode=310`, fingerprint and update package details; only install the owner-signed preview with `adb install -r`. Verify old projects/corrections/models; offline transcription/translation; editor portrait/landscape, large font and keyboard; SRT/MP4; NOTICE accessibility and TalkBack.

**No installer should be delivered or installed based on a successful PR CI alone.** PR remains Draft until UI owner-acceptance. No public release, merge or CP4/CP6 sign-off; complete license/Google branding audits remain OPEN.

## Verification
- This source change is prepared; build, version-verifier regressions, Android 11/15 tests and manual signing/clean emulator preview launch: **NOT_RUN at writing**, pending GitHub CI and a separate owner manual run.
- Prior combined UX PR #7 CI: [#41326384859](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41326384859) SUCCESS, not proof of this signing preparation.

## Failed manual run #321 — SDK archive download; root cause and mitigation

Owner-dispatched [Android CI #321, run 41571806271](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41571806271), based on initial preview source `ebae541a787efe680bf73c5645c634249ae8a861`, reported **build FAILURE** during the `Install Android 17 SDK` step, before any Gradle compilation:

```
Warning: An error occurred while preparing SDK package NDK (Side by side)
28.2.13676358: Error on ZipFile unknown archive.
Process completed with exit code 1.
```

The job's downloaded `android-ndk-r28c-linux` archive was not accepted by sdkmanager; this is evidence of an SDK download/archive error, **not proof of an app or engine regression**. Prior PR [CI #320](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41561129960) was 3/3 SUCCESS for the exact original preview commit.

Mitigation prepared on the **same preview branch**, not on main:
- New `tools/retry_android_sdk_install.sh` wraps each sdkmanager installation in **at most three attempts**, using a short delay between transient failures; persistent failure exits nonzero. No bypass, no ignored exit code and no fallback to a different NDK revision.
- Applied to commandline-tools and platform-tools/platforms/build-tools/NDK/CMake installs for build, Android 11 `media-device` and Android 15 `modern-services` jobs. The new preview signing job also retries its build-tools installation. The old prototype-only signing job remains untouched.
- Added offline `tools/test_retry_android_sdk_install.py` checking first-attempt success, recovery on third attempt, and persistent fail-closed behavior; wired to CI build.

**Verification of mitigation:** New PR CI is pending. Run #321 on the old commit cannot validate the changed workflow. After new CI succeeds, a new owner manual `workflow_dispatch` run on the updated preview branch is required to produce an eligible signed UI preview artifact. An old failed run or an unsigned PR artifact must **not** be installed on Sony SO-03L. All model/data/engine/API/signing gates remain as above.
