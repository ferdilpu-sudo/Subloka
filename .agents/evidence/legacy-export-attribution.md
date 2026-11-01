# EXPORT-PROVENANCE-001 — 2026-10-31

## Scope
Post-merge Beta #310 development change, based on `main` merge commit `5514e1a73e0dc698ece04acd3860aba7236216c9`. Show a limited historical translation-provider notice before preparing SRT/MP4 in modes **Terjemahan** / **Keduanya**. No new Google ML Kit SDK, inference, model setup, schema, origin migration or change to encoded/exported media. Preserve owner signing and device data.

## Source and requirements checked
- Official ML Kit on-device translation usage guidelines: https://developers.google.com/ml-kit/language/translation/translation-terms — point to Google Cloud Translation API attribution obligations insofar as applicable to apps.
- Official Cloud Translation attribution: https://docs.cloud.google.com/translate/attribution — includes Google result attribution/brand placement, disclaimer and related rules. **This patch does not claim to satisfy every requirement** or authorize public distribution.
- Existing `TranslationOrigins` only attributes a recognized saved `MACHINE_MLKIT` origin to historical Google output. `MACHINE` is unknown, and `MACHINE_GEMMA` and `MANUAL` are never assigned Google provenance by fallback inference.

## Implementation
- `core/domain/TranslationOrigins.exportWarnings` counts only current, nonblank translation results matching the source revision. Returns one advisory for known ML Kit output and another for unknown legacy machine origins, if present.
- `feature/export/ExportScreen` shows the notices only when translation text is selected, not in SOURCE mode. Neither export payload nor player subtitles are altered. It directs users to the existing in-app **Privasi dan lisensi** information.
- Pure domain regressions cover mixed ML Kit/Gemma/manual/unknown origins and exclude stale, failed or pending rows; Compose screen regression covers translation/source selection visibility.

## Status and limits
- Source change and test cases committed on dedicated branch `feat/legacy-translation-export-notices`; Kotlin tests and Android UI instrumentation pending GitHub CI verification.
- This is **scoped export-user-awareness**, not complete Google branding compliance: official Google graphic placement, exact disclaimer, export downstream attribution, and ambiguous legacy source handling require separate product/legal review.
- Full source-level native/vendor/resource copyright and NOTICE inventory still OPEN; `source-notice-audit.json` remains `complete_distribution_audit: false`.
- No rerun of paused 30-sample Turbo research benchmark; CP4/CP6 remain open. Do not merge or label public-release-ready before review and CI.
