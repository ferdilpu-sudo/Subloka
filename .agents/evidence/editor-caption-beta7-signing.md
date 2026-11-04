# UX-EDITOR-CAPTION-BETA7-001 — Owner-signed preview gate

Date: 2026-11-04

## Verified source and UX scope

- [PR #15](https://github.com/ferdilpu-sudo/Subloka/pull/15) on `ux/editor-caption-focus-v1` is the **exact base** of this packaging branch, commit `dd8568b5f522f6baf44b14b2d1da57ae9d92e466`.
- Integrated [Android CI #342](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41817771431) **PASS 3/3** at the exact base head: `build`, Android11 `media-device` (including Editor Compose correction/navigation tests), Android15 `modern-services`. The owner signing job was appropriately skipped for the PR.
- UX fix: no-scroll Caption n/N navigation outside Teks and Waktu scroll views; selecting next scrolls correction to top/returns from open list; preview compact by default in Teks/Waktu and user-expandable; Style uses large preview; model management moved below correction; normal header stays focused on title, save and Export. Previous 9:16 aspect fix retained. No media, translation engine, model, DB, SRT/MP4 payload, or signing secret changes.

## Beta7 package guard

- `versionName=0.7.0-beta.7`, `applicationId=app.subloka.caption`, generated `versionCode=github.run_number` which **must exceed owner-signed Beta6 #339**, including if Beta6 is already installed.
- `tools/verify_beta_package.py` keeps strict package ID/launcher/icon/non-debug/testOnly/arm64-v8a+x86_64 native offline engine checks and now requires beta.7 / versionCode >339.
- `tools/test_verify_beta_package.py` tests rejecting versionCode 339 and earlier, beta.6 and older labels, altered package identity, missing launcher/native artifacts.
- `ui-beta-preview` in Android CI can access `SUBLOKA_PROTOTYPE_SIGNING` only on an explicit maintainer `workflow_dispatch` with the **exact ref** `refs/heads/ux/editor-caption-beta7-preview` and `needs: [build, media-device, modern-services]`. Ordinary PR events skip signing; legacy prototype-only signer remains separate.
- Pinned owner cert SHA256 `295b1bbcebb8419c8361b077e41b913410207ee3ecb3bc0da3acf150c8e1c325` and clean Android11 signed release launch smoke remain required.

## Acceptance states

At creation: **Beta7 PR CI NOT_RUN, owner signing NOT_RUN, physical Sony QA NOT_RUN**. Opening a PR creates no installable signed APK. First require same-head PR CI PASS. Then owner may manually trigger Actions → Android CI → Run workflow on `ux/editor-caption-beta7-preview`. Verify all 4/4 jobs PASS and resulting `subloka-ui-beta-preview-apk` signature/version/metadata before any Sony update. Use only `adb install -r`, no uninstall/clear/downgrade, and preserve existing projects/models/manual translations.

Field acceptance: on portrait 9:16 video select Caption 2 of 4, correct word, inspect larger preview, select Caption 3 **without scrolling the navigation row or losing correction**; confirm Timing navigation, Style large preview, keyboard and large font, saved source/translation persistence and bilingual MP4/SRT. Screen-reader/touch-size, CP4/CP6, NOTICE/legal and release qualification remain open. Keep `main` and old owner Beta6 unchanged.

Audit followups (separate PRs): named SRT save actions with saved/pending priority, clear zero-eligible Translation vs model state, duplicate Projects rename/thumbnail/snippet, Style bottom-position live guide. No approval for these to be released under beta7 yet.
