# Export flow UI — 0.6.12

## Scope / 2026-10-22
Project-setup 0.6.11: user reported all five physical checks PASS. Manual CI 39746130975 verified all four jobs successful, including stable-key APK. Acceptance is bounded to those checks.

P1 usability: initial BOTH selection blocks projects without a complete translation; SRT prepare/save and MP4 render/save actions compete in one scrolling page. Implement format selection, SOURCE default, accessible language radio group, and a persistent contextual primary action. Keep prepared SRT file names and individual save actions together. Explain that changed language selection applies only to newly prepared/rendered output. Ready MP4 retains save action even if a new selection cannot be rendered; render again explains replacement of temporary output. Reattached render selects MP4 so progress/cancel/save remain discoverable.

## Validation
Local validate_project.py PASS (116 Kotlin files); diff whitespace check PASS. ExportFlowUiTest authored and selected in Android11 CI: stale translation blocks new translated SRT/MP4; SOURCE callbacks preserved; prepared SRT can still be saved; render cancellation reachable with large font; ready MP4 save remains enabled for existing result, disabled while picker pending, available again after cancellation. Instrumentation not executed locally (Android environment unavailable); CI pending. Physical portrait/landscape, dual-file save and render/save retry acceptance pending.

Existing services, storage, validation, render quality, signing and models unchanged. No database migration. Status IN_PROGRESS until CI and physical acceptance. Next: stable-key update after CI, then scoped export smoke test.
