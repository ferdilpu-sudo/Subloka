# UX-SRT-SAVE-FIRST-001 — Prepared SRT save-first workflow

Date: 2026-11-06. Baseline: owner-signed Beta7 `0.7.0-beta.7`, versionCode **344**, [manual CI #344](https://github.com/ferdilpu-sudo/Subloka/actions/runs/41826458242) 4/4 PASS and owner-confirmed Sony correction sequence Caption 2 → word correction → zoom → Caption 3 → saved. Root owner UX audit from a 74-second recording: after BOTH export yields `7.id.srt` and `7.en.srt`, generic `Simpan file 1/2` and highlighted `Siapkan SRT lagi` invert the user's next action. This change addresses priority #2 only.

## State and safety proof

- Actual SRT documents are immutable snapshots from `SrtExport.documents`, which names files by source/target language suffix (`.id.srt` / `.en.srt`) in either ID→EN or EN→ID direction. Do not infer filename language from currently selected radio (user may change it after preparation). Unknown/legacy suffix is labeled by file index instead of guessed language.
- Existing `SrtExportViewModel` records `saved: Set<Int>` **only after actual bytes have been written, flushed and stream closed successfully**. Canceled picker leaves snapshot unsaved, failed writes never mark success, and different files remain selectable. No fake success from UI clicks.
- New pure `SrtSaveActions`: language-specific Save/Re-save labels and deterministic next unsaved file index. Original `SrtDocument` wire format and SRT text bytes remain unchanged.
- After preparation the **fixed primary action** is `Simpan SRT Indonesia` or `Simpan SRT Inggris` for the next unsaved snapshot. Other unsaved files remain individually selectable in a row; saved file has `Tersimpan` and `Simpan ulang ...`, with progress count. When all are saved, primary becomes `Selesai — kembali ke editor`.
- `Siapkan SRT lagi` becomes a secondary inline action and explains it resets prepared snapshot/status on screen, **not saved files on disk**. While there are no prepared documents, `Siapkan SRT` remains primary. All callbacks, enabled/busy/picker guards and MP4 primary/render branch unchanged.
- Existing translation provider and fidelity warnings unchanged; stale translation may block generating *new* translated output but does not block saving already prepared document snapshots. No model, Room, file writer, signing secret, app ID, target SDK or stored project changes.

## Tests / acceptance

- New domain unit tests: ID/EN filenames in both direction; legacy suffix fallback; first unsaved/only remaining/all saved selection; actual SrtExport-generated filename coverage.
- Android Compose `ExportFlowUiTest`: BOTH creates two files; correct language-specific save action; picker pending/cancel never falsely marks success; first saved updates 1/2 and promotes second; all saved offers completion instead of regeneration; no accidental `onPrepare` after saving; saved labels and alternate source direction remain stable. Existing 150% font, failed-mode blocking, Google provenance and MP4 render/save test retained.
- CI **PENDING** at creation, Sony physical SRT export acceptance NOT_RUN for this patch. No new owner-signed APK is created by this PR. Keep PR Draft on Beta7 branch, main untouched; before any preview sign-off require CI PASS and separate exact-branch owner manual-signing workflow.
- Remaining audit scope: 0-eligible offline translation vs device model readiness; project disambiguation/rename; Style bottom-guide/preview proximity; screen-reader and final exports on device.

This is a focused UX fix and does not certify CP4/CP6, translation accuracy, license/branding, or full release readiness.
