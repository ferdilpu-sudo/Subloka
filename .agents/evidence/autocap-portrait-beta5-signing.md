# UI-AUTOCAP-PORTRAIT-BETA5-001 — Signed portrait preview gate

Date: 2026-11-03. This **Draft/stacked** beta5 packaging branch `ui/autocap-portrait-beta5-preview` is based on the exact green [portrait 9:16 UI PR #11](https://github.com/ferdilpu-sudo/Subloka/pull/11) source `f74596c44bc0cb8bc663bacafd61ef343e3cccad`. [Android CI #333](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41594079993) completed **SUCCESS 3/3** (build, Android11 media-device, Android15 modern-services). No signing job ran for the PR.

## Controlled differences from PR #11

1. `app/build.gradle.kts`: label new APK as `0.7.0-beta.5`, retain `applicationId=app.subloka.caption`; versionCode remains CI `github.run_number`.
2. `tools/verify_beta_package.py`: enforce `versionCode > 332` even if latest owner-signed Beta4 #332 already installed; reject versionName other than `0.7.0-beta.5`. Non-debug, launcher, source ABIs and Whisper/TranslateGemma engine packaging assertions unchanged.
3. `tools/test_verify_beta_package.py`: extend downgrade regression for #332 and Beta4 label, retain wrong package and ABI/engine tests.
4. `tools/test_ui_beta_preview_workflow.py` + `.github/workflows/android-ci.yml`: sign only if maintainer manually `workflow_dispatch`es `Android CI` on **exact** branch `refs/heads/ui/autocap-portrait-beta5-preview`, after build, media-device and modern-services jobs PASS **on that manual run**. All PR/push workflows remain secret-free; legacy prototype-only signing job unchanged. Existing release signing fingerprint pin `295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325` (Beta #310/#329/#332 owner certificate) and clean Android11 emulator smoke retained.
5. Model, offline engines, inference timing, Room, SRT/MP4, user projects, signing secret, source files, tests for responsive portrait and landscape playback are not altered.

## QA gate / what is NOT done yet

- **Beta5 branch CI:** pending, do not claim success before checking final head.
- **Owner-signed Beta5 artifact:** not built at creation, requires separate owner manual run after PR CI PASS. A PR debug/unsigned artifact is NOT an installable in-place upgrade.
- **Physical Sony acceptance:** pending. Confirm installed versionCode 310/329/332 or other known value, app ID and certificate. Only use owner-signed beta5 with versionCode greater than currently installed; install with `adb install -r` and **never** uninstall, clear storage, overwrite model files or downgrade.
- Verify user-recorded problem is resolved: a 9:16 project uses a taller, visibly wider centered preview; subtitles are legible; Teks/Waktu/Gaya and Ekspor remain reachable at 150% font; 16:9 and landscape/keyboard remain usable; reopen old project, manual captions, offline translation, and export to bilingual MP4.
- `main@5514e1a73e0dc698ece04acd3860aba7236216c9`, PRs #7–#11 and owner-installed Beta4 unchanged. No merge, public release or full legal/NOTICE/CP4/CP6 signoff.
