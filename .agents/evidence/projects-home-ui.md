# Projects home refinement — 0.6.10

## Scope / 2026-10-22
User requested the next UI increment after accepting the editor. Problem: inert Settings label, mixed language, project cards hiding source identity, create action scrolling away with long lists. Implement localized lazy project list and a persistent Proyek baru action. Cards show title, distinct source filename, language, duration, resolution and actual update timestamp. Active ASR/translation/render status derives from current matching project sessions, including stopping. Otherwise status says only Tersimpan di perangkat; it does not imply transcription, translation or export completion. Existing database updated-time ordering and open/import callbacks are retained. No new settings route or media thumbnail decoder is introduced.

ProjectSummary adds a presentation-only statusLabel with a saved-local default; database schema and persistence contracts are unchanged. Engines, model provisioning and signing are unchanged.

## Previous increment closure
For b2bb441fdbe2d11959dce01e6737637f36c839a7, CI39590536345 build/media-device/modern-services SUCCESS; stable signing skipped for PR. Manual39593326371 build119199446757, media-device119199447111, modern-services119199447136 and stable-prototype-apk119204822807 all SUCCESS, verified through job results.
User reports PASS for retained caption correction, list position, translation disclosure/stale status, portrait/landscape/keyboard reachability. Bounded physical acceptance for the editor, not all-device or full accessibility certification.

## Current verification
Local python tools/validate_project.py PASS; git diff --check PASS. Android SDK/Gradle distribution unavailable locally as established in preceding increment. ProjectsScreenTest added to Android11 CI selection: empty-state/create at 1.5 font scale and long-list opening correct project while create stays reachable. These new instrumentation tests are NOT_RUN locally; Android CI and physical review required. Static checks are not runtime acceptance.

## Status / next step
IN_PROGRESS. Run Android CI for this increment, then stable-key manual workflow and physical home review: empty/list states, long names, large font, opening the intended existing project, and New Project navigation. Preserve prior data and models during update.
