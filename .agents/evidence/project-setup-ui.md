# Project setup UI — 0.6.11
## Scope / 2026-10-22
User requested the next UI increment after reporting all five projects-home smoke checks PASS (metadata, persistent create action, existing project preservation, large-font/landscape layout and create/back navigation). This is bounded user-reported acceptance of 0.6.10.

Problem: New Project's Create Caption button actually navigated to model setup, selected videos had no direct replacement action, and model setup presented import/download/start choices together. Implement two explicit steps, localized labels, change-video action, a single persistent primary action and scrollable content. Source language uses saveable state and accessible single radio-row targets. Oriented dimensions determine vertical/horizontal/square labels correctly. Valid selected video remains retryable after project persistence failure; over-10-minute video cannot continue.

Model setup uses actual ready/busy flags: download when unavailable, start when ready, cancel while busy. Advanced disclosure contains model imports. Required sizes and memory tradeoff remain visible before downloading. No model readiness bypass or automatic inference/download; engine choices and callbacks unchanged. Model Back returns to projects as before.

## Validation
Local guardrails (115 Kotlin files) and diff check PASS. Added ProjectSetupUiTest to Android11 CI selection: initial pick, Indonesian selection, retry after save failure, duration rejection/change video, portrait native vertical metadata, large-font reachability, download/start/busy/cancel action gating. Tests authored, not locally executed: Android SDK/Gradle distribution unavailable locally as recorded in earlier increments.
No database migration, engine/signing/model file change. IN_PROGRESS until CI and physical acceptance. Next: verify CI, create stable-key update, test short-video import/language/model reuse/transcription and Back/Ganti video at large font.
