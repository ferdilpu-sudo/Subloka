# Rencana Eksekusi dan Ledger

Tanggal baseline: 2026-10-06. Kondisi awal: dokumen saja; belum ada kode aplikasi. Baseline UX diperbarui ke v0.2 sebelum implementasi. Dokumen ini satu-satunya ledger task dan checkpoint. Bukti berada di testing.md.

## Status dan Definition of Done

`TODO`: belum dimulai. `IN_PROGRESS`: sedang dibuat. `IMPLEMENTED`: artefak dibuat, tes wajib belum lengkap. `VERIFIED`: semua tes task yang diwajibkan lulus, dokumentasi/penutupan mungkin belum selesai. `DONE`: kriteria selesai terpenuhi, bukti ditautkan, docs sinkron. `BLOCKED`: dependensi, akses, keputusan atau gate menghalangi; alasan wajib ada.

Status DONE tidak otomatis berarti rilis produk. Status SKIP tidak digunakan untuk melewati gate wajib. Tes FAIL/BLOCKED tidak boleh dihitung PASS. Setiap task mencatat tiga kategori: sudah dibuat, sudah diuji, belum terverifikasi.

## Task dan dependensi

| ID | Task / keluaran | Dependensi | Kriteria selesai khusus | Status |
|---|---|---|---|---|
| T00 | Paket 10 dokumen baseline + UX v0.2 | — | File lengkap, link/dependensi konsisten, interaction guardrail sinkron, pemeriksaan DOC-001/DOC-002 tercatat | DONE |
| T01 | Konfirmasi baseline produk dan perangkat uji | T00 | Scope EN/ID offline dikonfirmasi; perangkat, durasi/resolusi sampel dan batas MVP dicatat; CP0 ditinjau | DONE |
| T02 | Kontrak arsitektur dan toolchain | T01, CP0 | Pin baseline versi/SDK/ABI/native; kontrak adapter; ADR; verifikasi dokumentasi/kompatibilitas; CP1 ditinjau | DONE |
| T03 | UX & interaction specification | T02, CP1 | IA final; primary flow; wireframe compact/wide/expanded; keyboard state; Caption/Timing/Style; processing/export/error/empty/stale states; component inventory; accessibility notes; acceptance mapping; CP2 ditinjau | DONE |
| T04 | Scaffold Android dan design system | T03, CP2 | Gradle build/lint jalan; app shell mengikuti semantic tokens/component contract T03; perintah/lingkungan dicatat README | DONE |
| T05 | UI Projects, model setup, New Project | T04 | Home/recent/empty, model states, pick video + source language flow; tidak ada bottom nav; fake adapter/demo label; UI tests relevan lulus | DONE |
| T06 | UI editor Caption/Timing/Style | T05 | Caption default; bounded preview; bilingual edit; stale translation actions; timing nudge/input; style MVP; keyboard/adaptive state; undo/redo UI teruji | DONE |
| T07 | UI processing dan export | T06 | Processing sebagai project state; progress/cancel/interrupted/error; export options + blocked reasons; fake adapter; CP3 tinjauan UI selesai | DONE |
| T08 | Persistensi lokal dan aturan editor | T07, CP3 | Room/repository, revision, split/merge, autosave dan migration fixtures; unit/integration tests PASS | DONE |
| T09 | Impor/pemutar/decode audio nyata | T08 | URI/relink, orientasi/audio track, PCM benar, sumber utuh, error tanpa audio dan codec diuji | DONE |
| T10 | Evaluasi engine dan model offline | T09 | Benchmark dua bahasa/perangkat; model download/readiness; lisensi; kualitas/resource diukur; CP4 lulus atau BLOCKED | BLOCKED |
| T11 | Pipeline ASR produksi | T10, CP4 | Chunk offset/dedup/silence/cancel, timestamp valid, staging publish aman, tes ASR lulus | TODO |
| T12 | Pipeline translation produksi | T11 | EN↔ID offline, stale/manual protection, retry dan CAS teruji | TODO |
| T13 | Koordinator job dan recovery | T12 | Satu job berat; process death/cancel/low storage/retry tidak merusak data; CP5 teknis lulus | TODO |
| T14 | Renderer dan ekspor MP4/SRT | T13, CP5 | Preview/hasil sesuai, rotation/timing/audio valid, readability/overflow aman, SRT dua arah, cancel aman; tes ekspor lulus | TODO |
| T15 | Integrasi dan hardening end-to-end | T14 | Seluruh FR/NFR ditelusuri; mode pesawat, adaptive/keyboard/accessibility, kualitas, lifecycle/perangkat PASS; CP6 lulus | TODO |
| T16 | Paket rilis dan handoff | T15, CP6 | Build kandidat, checksum, petunjuk instalasi/model, known limits, sumber/lisensi, docs final; CP7 ditinjau | TODO |

Dependensi CP pada task diperiksa selain dependensi task. Task yang menghasilkan checkpoint menyiapkan bukti dan menunggu persetujuan bila tipe checkpoint membutuhkan pengguna. Jangan memulai task dependent saat checkpoint masih menunggu. Task dokumentasi boleh mencatat rancangan fase berikutnya tanpa mengklaim fase implementasi sudah selesai.

## T03 — keluaran wajib sebelum CP2

T03 harus menghasilkan artefak yang dapat ditinjau, bukan hanya diskusi chat:

1. IA final dan navigation graph.
2. Primary flow `Home → New Project → Processing → Editor → Export`.
3. Compact portrait wireframe, termasuk video 9:16.
4. Wide/landscape compact wireframe.
5. Expanded/supporting-pane wireframe.
6. Keyboard-active state.
7. Caption workspace: list, selected edit, split/merge, source/translation role.
8. Translation states: MISSING/PENDING/CURRENT/STALE/FAILED + bulk stale summary.
9. Timing workspace: timeline contextual, direct input/nudge, invalid state.
10. Style workspace MVP + progressive disclosure.
11. Model setup/download/retry/storage state.
12. Processing: progress-known/unknown, cancel, interrupted, failure.
13. Export: source/translation/dual, blocked reasons, video/SRT.
14. Empty/loading/error/save-failure/URI-relink/long-text states.
15. Component inventory dan semantic token proposal.
16. Touch target, focus order, font scale, TalkBack, contrast/focus notes.
17. Mapping tiap screen/state ke FR/NFR dan acceptance criteria.

T03 tidak menambah feature di luar MVP. Brand/logo/icon boleh tetap placeholder.

## Checkpoint

| ID | Titik / pemilik | Syarat keluar | Status |
|---|---|---|---|
| CP0 | Baseline produk / pengguna | Scope inti dikonfirmasi; detail asumsi T01 ditinjau; tidak ada API berbayar | PASS — eksekusi diminta setelah paket agent-ready; baseline detail dicatat |
| CP1 | Arsitektur / pengguna | T02 menghasilkan desain/batas teknis konkret; risiko model belum terbukti ditandai | PASS — baseline stabil dipin; engine tetap unverified |
| CP2 | Desain / pengguna | Semua keluaran T03 tersedia; dua arah bahasa; compact/expanded/keyboard; reviewer dapat menyelesaikan user flow tanpa ambiguity | PASS — interaction contract v0.3 menjadi dasar frontend demo |
| CP3 | Frontend / pengguna | T04–T07 teruji sebagai UI demo; jelas engine belum terhubung; layout mengikuti ADR-016–021; izin lanjut engine lokal | PASS — DEVICE-001 dikonfirmasi pengguna; lanjut T08 diizinkan |
| CP4 | Kelayakan offline / teknis | T10 memenuhi gate kualitas/resource testing.md; keputusan model/perangkat dicatat | BLOCKED — smoke/readiness lulus; benchmark dataset manusia pada perangkat fisik belum dijalankan |
| CP5 | Engine lokal / teknis | T08–T13 teruji dan docs sinkron sebelum ekspor/integrasi penuh | Menunggu |
| CP6 | Kandidat rilis / teknis | T15 semua gate wajib PASS, batas dukungan berdasarkan bukti | Menunggu |
| CP7 | Delivery / pengguna | T16 artefak dan hasil uji disajikan; distribusi publik memerlukan otorisasi terpisah | Menunggu |

### Pertanyaan review wajib CP2

CP2 belum lulus bila reviewer belum dapat menjawab dengan jelas:

- Bagaimana membuat project baru?
- Bagaimana mengetahui source language dan output bilingual?
- Bagaimana memperbaiki source caption dan translation?
- Bagaimana mengetahui translation stale dan memperbaruinya?
- Bagaimana mengatur timing presisi tanpa bergantung hanya pada drag?
- Bagaimana mengubah style tanpa keluar dari scope caption editor?
- Bagaimana export source-only/translation/dual dan kenapa opsi bisa blocked?
- Apa yang terjadi saat processing gagal/terputus/cancel?
- Apa yang terjadi ketika keyboard aktif?
- Apa yang terjadi pada video 9:16, wide screen, font scale besar, dan expanded window?

Tidak meminta persetujuan ulang untuk hal yang telah diotorisasi. Gate teknis gagal berarti laporkan hasil serta opsi; jangan menurunkan ambang atau mengganti offline dengan cloud diam-diam.

## Format catatan per task

```text
Task / status / tanggal:
Dependensi dan checkpoint terpenuhi:
Sudah dibuat (path):
Sudah diuji (ID evidence + hasil):
Belum terverifikasi (alasan / dampak):
Acceptance criteria terpenuhi / belum:
Dokumen diperbarui (file + perubahan):
Blocker / risiko:
Next task:
```

## Ledger awal — T00

- Sudah dibuat: README.md, AGENTS.md, rules.md, prd.md, design.md, architecture.md, schema.md, plan.md, testing.md, decisions.md.
- Baseline awal diuji: DOC-001 PASS — paket v0.1, 10 file, link lokal, task DAG tanpa siklus, aturan status/docs update.
- Pembaruan UX v0.2: interaction model difokuskan menjadi Caption/Timing/Style; translation menjadi state/action; import/process/export menjadi flow/state; adaptive/keyboard/readability dan severity audit ditambahkan.
- Sudah diuji: DOC-002 — lihat testing.md untuk hasil pemeriksaan paket v0.2.
- Belum terverifikasi: seluruh build, runtime, UI usability pada device, model, kualitas translation, performa, ekspor, dan dukungan perangkat.
- Dokumen diperbarui: seluruh paket disinkronkan agar requirement, ADR, task, testing, dan architecture mengikuti arah UX v0.2.
- Status penutupan: DONE untuk paket dokumentasi saja; tidak ada kode aplikasi.
- Next task: T01; seluruh implementasi tetap TODO.

## Handoff awal untuk agent

Mulai dari T01. Jangan membuat project Android lalu langsung mengimprovisasi editor. T03/CP2 adalah kontrak interaction sebelum UI produksi.

Guardrail yang tidak boleh dilanggar tanpa ADR baru:

```text
Caption      = hero
Video        = context
Timeline     = contextual
Translation  = state/action
Style        = secondary tool
Export       = final action
No bottom navigation on MVP
```

Nama produk, perangkat target, toolchain, model, benchmark, profil codec, breakpoint final, dan batas durasi perlu dibuktikan/ditetapkan melalui task, bukan diasumsikan dari rancangan.


## Ledger eksekusi 2026-10-06 — T01 sampai T07

### T01 / DONE / 2026-10-06
- Dependensi/checkpoint: T00 DONE; CP0 ditinjau melalui instruksi pengguna untuk mengeksekusi paket agent-ready tanpa mengubah requirement inti.
- Sudah dibuat: baseline nama kerja SubLoka; scope tetap Android/offline/EN↔ID; fixture benchmark minimum dicatat 30 detik, 2 menit, 10 menit pada 720p/1080p portrait+landscape; Sony SO-03L Android 11 dicatat sebagai perangkat primer yang pernah tersedia.
- Sudah diuji: konsistensi baseline terhadap README/prd/rules/architecture/decisions diperiksa oleh validator proyek `tools/validate_project.py` bersama guardrail frontend.
- Belum terverifikasi: koneksi perangkat, RAM aktual, profil video pengguna paling umum.
- Acceptance: terpenuhi untuk baseline planning; klaim performa tidak dibuat.
- Dokumen: README, architecture, decisions, plan.

### T02 / DONE / 2026-10-06
- Dependensi/checkpoint: T01 + CP0 terpenuhi.
- Sudah dibuat: AGP 9.4.0; Gradle 9.6.0; Kotlin/Compose compiler 2.3.21; Compose BOM 2026.09.00; minSdk 26; compile/target 37; Media3 1.11.1; Room 2.8.5; ML Kit Translate 17.0.3; whisper.cpp v1.9.4 kandidat evaluasi.
- Sudah diuji: kompatibilitas versi diperiksa terhadap dokumentasi resmi Android/Google dan release upstream; tidak ada dependency dinamis di scaffold.
- Belum terverifikasi: resolution Gradle artifact secara lokal, NDK/JNI, ABI benchmark, ML Kit model readiness dan kualitas translation.
- Acceptance: kontrak dan risk boundary terpenuhi; CP1 PASS.
- Dokumen: architecture, decisions, README.

### T03 / DONE / 2026-10-06
- Dependensi/checkpoint: T02 + CP1 terpenuhi.
- Sudah dibuat: navigation graph, primary flow, compact/expanded/keyboard wireframe, Caption/Timing/Style contract, translation states, model/processing/export/error states, component inventory, accessibility notes, mapping requirements di `design.md §22`.
- Sudah diuji: review statis memastikan no bottom navigation, hanya Caption/Timing/Style, translation state/action, export final action, demo disclosure, adaptive breakpoint, dan blocked export behavior terwakili.
- Belum terverifikasi: usability pengguna nyata, TalkBack, font scale, contrast screenshot, IME behavior pada device.
- Acceptance: artefak T03 tersedia; CP2 PASS sebagai interaction contract frontend.
- Dokumen: design, decisions, plan, testing.

### T04 / DONE / 2026-10-06
- Dependensi/checkpoint: T03 + CP2 terpenuhi.
- Sudah dibuat: Gradle multi-module scaffold, `app`, `core:domain`, `core:designsystem`, feature modules, theme graphite/soft-indigo, semantic actions, manifest privacy baseline, target build commands, dan workflow `.github/workflows/android-ci.yml`.
- Sudah diuji: `STATIC-001` PASS; `DOMAIN-001` PASS; `DOC-003` PASS; `BUILD-001` PASS pada GitHub Actions; `BUILD-002` PASS pada Windows lokal menggunakan `gradlew.bat` dengan hasil `BUILD SUCCESSFUL in 3m 46s`.
- Belum terverifikasi: install/runtime pada emulator atau perangkat fisik, interaction smoke test, TalkBack/font scale/IME.
- Acceptance: build/lint dan scaffold terpenuhi; T04 ditutup DONE. T05–T07 tetap IMPLEMENTED sampai UI smoke/instrumented test dan CP3 review selesai.

### T05 / DONE / 2026-10-06
- Sudah dibuat: Projects recent/empty structure, New Project one-primary-action flow, source language EN/ID with automatic target, model setup states, permanent DEMO disclosure.
- Sudah diuji: static guardrail validator PASS.
- Sudah diuji: DEVICE-001 PASS berdasarkan smoke test manual pengguna pada perangkat; flow UI demo T05 tercakup dalam CP3.
- Belum terverifikasi: document picker integration nyata dan actual model download tetap belum ada karena masih demo.
- Acceptance: UI demo dan runtime gate T05 terpenuhi untuk CP3; engine nyata tetap di luar scope task ini.

### T06 / DONE / 2026-10-06
- Sudah dibuat: bounded preview, Caption default, bilingual source/translation editor, source edit → STALE, manual translation origin, stale summary/retranslate demo, contextual Timing with direct values+nudge, Style MVP, compact/expanded composition, IME-driven preview compaction.
- Sudah diuji: static guardrail validator PASS.
- Sudah diuji: DEVICE-001 PASS dan CP3 PASS berdasarkan smoke test manual pengguna; editor Caption/Timing/Style dapat dijalankan pada perangkat.
- Belum terverifikasi: behavior produksi yang belum diimplementasikan seperti real seek, timing mutation penuh, persistence, dan engine lokal.
- Acceptance: UI demo/runtime T06 diterima untuk CP3; behavior engine/data tetap task lanjutan.

### T07 / DONE / 2026-10-06
- Sudah dibuat: processing stage UI with honest indeterminate semantics, cancel/demo-complete path, Export screen, source-only fallback, bilingual/translation blocked on non-CURRENT translation, explicit fake-export disclosure.
- Sudah diuji: static validator PASS; source code inspection confirms no output file is written by demo actions.
- Sudah diuji: DEVICE-001 PASS dan CP3 PASS berdasarkan smoke test manual pengguna; flow Processing → Editor → Export diterima sebagai UI demo.
- Belum terverifikasi: interrupted/error variants produksi dan export engine/progress/cancel nyata.
- Acceptance: T07 selesai sebagai UI demo; real export tetap T14.

### T08 / DONE / 2026-10-07
- Dependensi/checkpoint: T07 DONE; CP3 PASS.
- Sudah dibuat: `core:database` Room v1; repository project/caption; UUID string segment ID; project/source revision; optimistic compare-and-set translation; split/merge; timing validation; style persistence; editor autosave queue; flush sebelum Back/Export; persistence facade; schema export v1.
- Sudah diuji: `DATA-001` PASS pada Android CI run #15, revision `deb5b1ebfe87254535a5a5845fa368cb6e6c8829`; domain unit tests, Room integration tests, schema fixture verification, assembleDebug, dan lintDebug seluruhnya PASS.
- Belum terverifikasi: migrasi antarversi belum dapat diuji karena schema saat ini baru version 1; fixture `1.json` menjadi baseline wajib untuk migration test saat version 2 dibuat. Persistence proyek/media nyata selain fixture demo juga menunggu T09+.
- Acceptance: Room/repository, revision monotonic, split/merge, autosave/reopen, manual-translation protection, dan schema fixture terpenuhi. T08 ditutup DONE.
- Dokumen diperbarui: plan, testing, architecture, schema, README, `.agents/README.md`, FILELIST.
- Blocker/risiko: tidak ada blocker T08. Jangan menganggap Room PASS sebagai bukti URI/media pipeline.
- Next task: T09 — impor/pemutar/decode audio nyata.

### T09 / DONE / 2026-10-07
- Dependensi/checkpoint: T08 DONE.
- Sudah dibuat: `core:media`; OpenDocument `content://` flow; persistable read permission; SHA-256 fingerprint; metadata/orientation/audio-track discovery; Media3 playback; MediaExtractor/MediaCodec PCM decode; relink verification; structured media errors.
- Sudah diuji: `MEDIA-001` PASS pada GitHub Actions run #31, revision `900d7af443d0e4c61a39f96eaef27aca49d51b77`; Android 11 emulator menjalankan media pipeline lewat `content://`.
- Bukti perilaku: rotated MP4 dibaca; AAC 16 kHz mono didekode menjadi PCM; source bytes tetap identik; duplicate URI dengan fingerprint sama diterima untuk relink; no-audio ditolak; unsupported codec ditolak; Media3 player mencapai `STATE_READY`.
- Belum terverifikasi: variasi codec/perangkat di luar fixture gate, VFR edge case, multi-audio selection UX, dan performa decode video panjang pada perangkat fisik. Ini tidak menghalangi T09 karena kontrak dasar media telah terbukti; coverage luas masuk T15.
- Acceptance: seluruh kriteria T09 terpenuhi untuk baseline media.
- Next task: T10 — evaluasi engine/model offline dan CP4.

### T10 / BLOCKED / 2026-10-07
- Dependensi/checkpoint: T09 DONE.
- Sudah dibuat: `tools/t10_fetch_fleurs_dataset.py` untuk mematerialisasi 60 fixture manusia Google FLEURS EN/ID secara deterministik;  kontrak ModelReadiness/OfflineTranslator; `engine:asr` model catalog/store untuk Whisper multilingual tiny/base dengan SHA-256 pinned dan atomic install; `engine:translation` ML Kit EN↔ID readiness/translate; WER tool; synthetic bilingual smoke; arm64 physical-device benchmark harness via ADB.
- Sudah diuji: `MODEL-001` PASS untuk download+checksum tiny/base; `TRANS-SMOKE-001` PASS untuk download model ML Kit dan translate EN↔ID pada Android 11 emulator; `ASR-SMOKE-001` PASS untuk whisper.cpp v1.9.4 tiny/base mengeksekusi EN/ID synthetic; `ASR-ANDROID-BUILD-001` PASS untuk cross-compile `whisper-cli` arm64 dengan NDK 28.2.13676358; Android CI revision `729dc64` PASS setelah model-store test diperbaiki.
- Temuan synthetic: WER smoke tiny EN 0.50, tiny ID 0.75, base EN 0.50, base ID 1.50 pada espeak-ng. Angka ini tidak dipakai sebagai quality gate karena synthetic TTS bukan dataset manusia dan karakteristiknya tidak mewakili rekaman target.
- Sudah dibuat/diuji tambahan: harness Windows telah melewati syntax parse CI dan binary benchmark whisper.cpp arm64 telah berhasil di-cross-compile dengan NDK pinned.
- Belum terverifikasi/blocker: dataset manusia minimum 30 ujaran EN + 30 ID (20 clean + 10 challenging), review translation 30 segmen per arah, dan benchmark RTF/RAM/thermal pada perangkat fisik belum tersedia/dijalankan dari sesi ini.
- Acceptance: readiness, integrity, build harness, dan functional smoke terpenuhi; quality/resource gate T10 belum terpenuhi. Status BLOCKED, bukan FAIL.
- CP4: BLOCKED sampai hasil benchmark fisik + review kualitas memenuhi `testing.md`.
- Next task: tetap T10. Jangan mulai T11.

### Handoff saat ini
T10 infrastructure/readiness smoke telah selesai, tetapi **T10 dan CP4 BLOCKED** pada benchmark dataset manusia + perangkat fisik. Gunakan `tools/t10_device_benchmark.ps1` untuk tiny/base setelah manifest dataset memenuhi 20 clean + 10 challenging per bahasa. T11 tetap TODO dan dilarang dimulai sebelum CP4 diselesaikan.

### Handoff repository — 2026-10-06
- Tujuan: menyiapkan source tree untuk repository `ferdilpu-sudo/Subloka` dan menjadikan `.agents/` satu-satunya lokasi catatan coding-agent Markdown.
- Sudah dibuat: `.agents/README.md`, `.agents/AGENTS.md`, serta seluruh pedoman product/rules/architecture/schema/design/plan/testing/decisions di `.agents/`; root `README.md` tetap human-facing.
- Sudah diuji: `STATIC-001` PASS setelah path validator diperbarui; `DOC-004` PASS untuk struktur/link `.agents`; `DOMAIN-001` kembali PASS dengan `kotlinc`.
- Sudah diuji setelah handoff: `BUILD-001` PASS pada GitHub Actions dan `BUILD-002` PASS pada Windows lokal; validator, assembleDebug, dan lintDebug seluruhnya sukses.
- Sudah diuji: `DEVICE-001` PASS berdasarkan smoke test manual pengguna; CP3 PASS dan T05–T07 ditutup DONE sebagai frontend demo.
- Aturan handoff: jangan membuat catatan planning Markdown baru di root; perbarui source of truth yang relevan di `.agents/`.
- Task berikutnya: T09 impor/pemutar/decode audio nyata; T08 sudah DONE.

### T10-TRANSLATION-HARNESS / PREPARED / 2026-10-08
- Tujuan: membuat evaluator ML Kit EN↔ID 30 segmen per arah tanpa mengubah engine produksi.
- Sudah dibuat (commit ini): test `MlKitTranslationBenchmarkTest`, fixture 60 sumber kalimat, generator review CSV dan report acceptance/latensi, serta 5 unit test evaluator.
- Bukti lokal saat persiapan patch: `python -m unittest discover -s tools -p test_t10_translation_review.py` mengembalikan 5 test PASS pada paket pengembangan; suite Android belum dijalankan dengan patch repo ini.
- Baseline ASR yang dilaporkan pengguna di Sony SO-03L Android 11 (arm64): corpus WER Base EN-clean 9.79%, ID-clean 28.61%; Tiny EN-clean 12.35%, ID-clean 44.14%. Audit manual ID-clean: 7 jelas, 13 kurang jelas; corpus WER Base subset jelas 13.22%, kurang jelas 36.18%. Mean RTF Base ID jelas 1.026, kurang jelas 1.071. Ini evidence yang dilaporkan pengguna, belum ada file mentah perangkat pada repository.
- File evidence lokal pengguna: `.t10-benchmark/asr-results.csv`, `asr-summary.csv`, `device.json`, `id-clean-audit.csv`, dan `evidence-hashes.csv`. Jangan commit media pribadi atau file mentah tanpa review privasi.
- Batas: 14 referensi ID-clean diverifikasi, 4 belum dinilai, 2 belum dapat dipastikan; baseline ID clean 28.61% masih FAIL terhadap target 20%. Translation quality offline, thermal, timing, dan total resource produksi belum diverifikasi.
- CP4 tetap BLOCKED; T11 TODO. Setelah `git pull`, jalankan instrumented test pada Sony dalam mode pesawat (sesudah download model online), review 60 output secara manusia, lalu selesaikan gate lain. Tidak mengklaim perubahan ini membuat CP4 PASS.


### T10-TRANSLATION-DEVICE-FIX / PREPARED / 2026-10-08
- Bukti kegagalan dari Sony SO-03L: `MlKitTranslationBenchmarkTest.kt:54` menghasilkan `expected READY but was NOT_READY`; tidak ada CSV/RESULT_PATH. Ini **FAIL precondition**, bukan hasil kualitas translation.
- Hipotesis yang relevan: Gradle `connectedDebugAndroidTest` dapat mencopot APK dan menghapus storage model ML Kit di antara smoke test online dan benchmark offline. Penyebab pasti penghapusan model pada perangkat belum dibuktikan secara langsung.
- Perbaikan disiapkan: `tools/t10_translation_device_benchmark.ps1` dua fase menggunakan `adb install -r -t` sekali saat `Prepare`, menjalankan smoke test melalui `adb shell am instrument`, lalu `Benchmark` tanpa reinstall/clear app data setelah mode pesawat+Wi-Fi off. Script mengambil hasil via `adb pull`.
- Pengujian: syntax PowerShell + unit test reviewer ditambahkan pada T10 Engine Evaluation CI; hasil CI dan percobaan perangkat fisik harus diverifikasi sebelum klaim PASS.
- CP4 tetap BLOCKED, T11 TODO; baseline ASR tidak diubah. Next: pull commit, `-Phase Prepare` dengan koneksi internet, `-Phase Benchmark` setelah perangkat offline, lakukan review translation manusia.

