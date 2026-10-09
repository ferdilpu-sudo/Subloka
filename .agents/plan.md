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


### T10-TRANSLATION-REVIEW / PROVISIONAL / 2026-10-08
- Bukti terbaru dari Sony SO-03L Android 11 (dikirim pengguna): 60 keluaran ML Kit EN↔ID, 30 per arah, kolom `error` kosong seluruhnya. Dua fase persiapan-online dan benchmark-offline telah menghasilkan CSV; mode pesawat/Wi-Fi off diperiksa oleh harness, tetapi log pemeriksaan belum diarsipkan secara terpisah.
- Review AI atas pasangan source/translation dinilai "review bagus" oleh pengguna; belum ada tanda tangan reviewer bilingual independen per baris. Evaluasi awal EN→ID: 27/30 ACCEPT (90.00%), tiga MAJOR_MEANING_ERROR; ID→EN: 25/30 ACCEPT (83.33%), lima MAJOR_MEANING_ERROR; tak ada NEGATION_ERROR atau NUMBER_OR_NAME_ERROR yang diberi label. Median latency 42.239 ms (EN→ID), 39.378 ms (ID→EN); p95 67.037 ms dan 52.802 ms. Sampel awal lebih lambat (700.778 ms dan 297.453 ms).
- Sudah dibuat: `tools/t10_translation_ai_draft.json` berisi label/catatan yang terkait digest 60 source/translation agar tidak diterapkan pada hasil inference lain. `tools/t10_translation_review.py apply-draft` merekonstruksi lembar review hanya apabila fingerprint cocok; output tetap provisional dan manual review ulang dibutuhkan bila terdapat perbedaan.
- Perbaikan CI: `.github/workflows/t10-engine-eval.yml` membatasi job translation-device pada `MlKitTranslationInstrumentedTest`; sebelumnya job tersebut mengeksekusi juga benchmark offline yang mensyaratkan model telah READY. Kegagalan CI pada run `37767746650` terjadi di translation-device sementara kedua job lainnya PASS; kemungkinan pemicunya precondition offline, tetapi XML detail kegagalan CI belum diekstrak.
- Acceptance ID→EN belum mencapai 90%; baseline ASR ID-clean 28.61% masih di atas WER 20%; review referensi ID belum lengkap, timing dan thermal/stabilitas belum selesai. **T10/CP4 tetap BLOCKED, T11 TODO.**
- Next: tarik commit baru, pulihkan review draft dari CSV perangkat lokal, verifikasi status; selanjutnya lakukan thermal/stability dan investigasi model ASR Indonesia, tanpa mengubah threshold atau referensi baseline.


### T10-ASR-STABILITY-HARNESS / IMPLEMENTED / 2026-10-08
- Scope: menambah evaluasi termal/stabilitas beban ASR berulang di perangkat Sony SO-03L; tidak mengubah engine produksi, model, threshold WER, CSV ASR baseline, atau status CP4.
- Sudah dibuat: `tools/t10_asr_stability.ps1` memakai artefak yang disiapkan oleh `tools/t10_device_benchmark.ps1` (whisper.cpp v1.9.4 arm64 + tiny/base dengan checksum pinned) serta `t10-dataset.json`. Default model `base`, bahasa `id`, durasi aktivitas inferensi 5 menit; sampel diputar berurutan/berulang. Script baru membuat folder sesi `.t10-benchmark/thermal-<UTC>-<id>` yang unik dan tidak menimpa bukti WER lama.
- Data dikumpulkan: `summary.json` (status, durasi, versi/model/hash, median/p95 RTF, puncak RSS teramati, suhu baterai awal/puncak/akhir), `runs.csv` dan `telemetry.csv` (interval sampling saat proses berjalan). Pada kegagalan, summary tetap dicoba disimpan dan status ditandai `ABORTED`.
- Pengaman: preflight arm64, perangkat tunggal, airplane mode/Wi-Fi mati, checksum model, WAV asli tersedia, suhu baterai awal <40°C, berhenti ketika ≥43°C atau suhu tak dapat dibaca berulang. Suhu baterai adalah **proxy**, bukan sensor CPU; uji ini tidak setara dengan memproses video 10 menit/ANR aplikasi. Tidak ada transcript pribadi atau audio yang di-commit.
- Sudah diuji: CI T10 revision sebelumnya `54fbffa` PASS di https://github.com/ferdilpu-sudo/Subloka/actions/runs/37772412408; perubahan harness baru hanya siap diperiksa syntax PowerShell lewat CI dan belum dijalankan pada Sony. Tidak klaim PASS thermal sebelum menerima `summary.json` perangkat.
- Acceptance untuk langkah ini: review output perangkat minimal satu sesi `base/id` 5 menit; perhatikan pemanasan, variasi RTF awal/akhir, RSS, thermal stop, crash, dan battery-power context. Jika perlu, lanjutkan tes video nyata 30 s/3 min/10 min sesuai testing.md dengan scope T10/T15 yang jelas.
- Status **T10/CP4 BLOCKED**, **T11 TODO**. Blocker utama tetap ASR ID clean 28.61% >20%, kualitas translation ID→EN 25/30 <27/30, referensi ID belum sepenuhnya diverifikasi, gate timing/thermal belum selesai. Next: jalankan preflight dan sesi stability di Sony, kirim `summary.json` dan beberapa baris `runs.csv`.


### T10-ASR-STABILITY-ADB-STDERR-FIX / IMPLEMENTED / 2026-10-08
- Bukti user Sony SO-03L Windows PowerShell: `-PreflightOnly` PASS untuk Whisper `base/id` / 30 WAV / arm64 offline, suhu awal baterai 36.7°C. Saat `-RunMinutes 5`, sesi `thermal-20261008T120059Z-5a0b61` berakhir `ABORTED` dengan `completed_runs=0` setelah `adb push` berhasil mengirim binary `whisper-cli` (27,661,368 bytes). Pesan progress transfer ADB tercatat sebagai exception di Windows PowerShell sebelum inference; **tidak ada bukti suhu naik/OOM/kegagalan ASR**.
- Root cause teknis: helper `Adb-Raw` memakai `2>&1` sementara `$ErrorActionPreference="Stop"`. Windows PowerShell 5.1 dapat mempromosikan stderr native (pesan progress `adb push` sekalipun exit=0) menjadi terminating error. Perbaikan: gunakan scoped `ErrorActionPreference=Continue` saat memanggil ADB, filter ErrorRecord dari stdout, periksa exit code native, pulihkan preference, dan izinkan nonzero hanya untuk probe seperti `pidof`.
- Test regresi `tools/test_t10_asr_stability_adb.ps1`: mock batch menghasilkan stderr normal + exit 0, stderr error + exit 7, serta opsi `-AllowFailure`. CI Windows PowerShell 5.1 dan parser syntax CI tersedia; **hasil CI / uji ulang fisik belum tersedia pada saat perubahan ditulis**.
- Tidak menimpa evidence sesi ABORTED; sesi ulang akan memakai nama folder baru. **CP4 BLOCKED, T11 TODO**; next `git pull`, preflight, sesi lima menit; kirim `summary.json` + ringkasan `runs.csv`.


### T10-ASR-STABILITY-ADB-TEST-RUNNER / IN_PROGRESS / 2026-10-08
- GitHub Actions `37774711520` Windows regression menulis `PASS: native stderr on exit 0 ignored; exit 7 rejected; opt-in failure works; EAP restored.`, tetapi job exit 1 karena mock negative-test sengaja meninggalkan `$LASTEXITCODE=7` dalam host PowerShell. Ini bukan kegagalan assertion helper.
- Perbaikan hanya pada terminasi regression script: reset `$global:LASTEXITCODE=0` dan `exit 0` setelah seluruh assertion dan cleanup berhasil. CI perlu rerun; uji fisik perangkat juga belum dijalankan ulang. CP4 BLOCKED / T11 TODO.


### T10-ASR-STABILITY-EXIT-VERIFICATION / IMPLEMENTED / 2026-10-08
- Bukti Sony SO-03L Windows: `-PreflightOnly` PASS untuk `base/id`, 30 WAV, offline, suhu baterai 36.0°C. Sesi `thermal-20261008T121209Z-0766d8` berhenti `ABORTED` pada run pertama dengan `adb_exit=` (kosong), tetapi `result_exists=True` dari pemeriksaan nonempty transcript di perangkat. `completed_runs=0`; puncak baterai 36.5°C. Tidak ada bukti suhu berlebih atau engine ASR gagal; tidak pula ada cukup bukti untuk menyatakan run berhasil sepenuhnya.
- Penyebab di kode: `if ($proc.ExitCode -ne 0 -or $outputExit -ne 0)` menganggap `$null -ne 0` bernilai benar pada Windows PowerShell meskipun file hasil ada. `WaitForExit(5000)` sebelumnya juga tidak memvalidasi ketersediaan exit code.
- Fix: menunggu proses ADB selesai dengan batas tunggu dan kill fallback pada abort; cek exit code sebagai nullable; mewajibkan transcript result.txt tidak kosong; membedakan `RESULT_PRESENT_EXIT_ZERO`, `RESULT_PRESENT_EXIT_UNKNOWN`, `RESULT_PRESENT_ADB_NONZERO`. Run dengan exit tidak jelas tetap dicatat untuk metrik, tetapi summary menjadi `COLLECTED_WITH_UNVERIFIED_ADB_EXIT`, tidak dinyatakan PASS. Log stdout/stderr per-run disimpan ketika exit tidak terverifikasi atau output absen, dan dibersihkan untuk exit=0+transcript.
- Regression: `tools/test_t10_asr_stability_adb.ps1` diperluas menguji exit 0/null/nonzero dengan hasil nonempty serta abort bila transcript kosong; Windows CI harus membuktikan tes ini. Bukti sesi lama disimpan; `CP4 BLOCKED`, `T11 TODO`. Next: pull, jalankan ulang lima menit dalam kondisi offline dan perangkat diawasi, lalu periksa `summary.json` dan `runs.csv` dari sesi baru.


### T10-ASR-STABILITY-EXIT-PARSER / IMPLEMENTED / 2026-10-08
- CI pertama untuk patch exit verification (commit `cc994ce`) melaporkan parse failure PowerShell pada `tools/t10_asr_stability.ps1`: `Variable reference is not valid. ':' was not followed by a valid variable name character`. Penyebab: string log `"$RunNumber:"` dalam helper baru.
- Hotfix mengganti interpolasi dengan `"${RunNumber}:"`, tidak mengubah parameter, model, durasi, atau logic klasifikasi inference.
- Perubahan belum diklaim PASS hingga parser dan Windows regression CI rerun. Perangkat fisik juga belum diuji ulang; T10/CP4 BLOCKED, T11 TODO.


### T10-ASR-STABILITY-5MIN-EVIDENCE / COLLECTED-PROVISIONAL / 2026-10-08
- Pengguna menyerahkan isi `summary.json` Sony SO-03L Android 11, serial tidak dicatat ulang dalam laporan publik; whisper.cpp v1.9.4 model Base multilingual Indonesian (SHA-256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`), dataset manifest SHA-256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`. Offline preflight airplane=1/Wi-Fi=0; USB power aktif.
- Hasil: 300.06 detik sesi, 23 run menghasilkan file transkripsi, 23/23 `unverified_adb_exit_runs` karena Windows PowerShell `Start-Process.ExitCode` null, status `COLLECTED_WITH_UNVERIFIED_ADB_EXIT`, `stop_reason=null`. Median RTF 1.0539, p95 RTF nearest-rank 1.2304; sampled peak RSS 378888 KiB (~370 MiB); suhu baterai 36.5°C awal, 39.2°C puncak/akhir (+2.7°C), tidak mencapai stop 43°C.
- Ini bukti beban *repeated short utterances*, bukan E2E video 10 menit, CPU thermal, network audit, atau aplikasi bebas crash/ANR; jangan menyatakan 23 run fully verified karena seluruh exit code lokal masih unknown. RTF>1 berarti beban ini sedikit lebih lambat dari waktu nyata. Suhu dipengaruhi pengisian USB.
- Improvement harness: shell Android sekarang menyimpan kode keluar Whisper di `result.exit` per run; setiap run juga mensyaratkan `result.txt` nonempty, menyimpan remote vs Windows ADB exit masing-masing, melabeli ketidakpastian, menyimpan evidence lokal, dan tetap menghentikan run jika remote Whisper exit nonzero. Tes regresi PowerShell Windows + eksekusi shell POSIX mock ditambahkan ke CI. **Status fix: IMPLEMENTED / CI PENDING / PHYSICAL RECHECK NOT_RUN.**
- Next: cek CI, lakukan uji 2 menit validasi remote exit marker, kemudian jika sukses pertimbangkan 5 menit lagi. CP4 **BLOCKED** dan T11 **TODO** karena ASR ID clean WER 28.61% >20%, translation ID→EN 25/30 <27/30, peninjauan referensi ID/timing serta E2E thermal belum selesai.


### T10-ASR-REMOTE-EXIT-PARSER / IMPLEMENTED / 2026-10-08
- Run CI `37778559881` untuk commit `ea65032`: job Windows regression dan Android benchmark binary berhenti pada parser PowerShell `InvalidVariableReferenceWithDrive` dari pesan baru `run=$LastRun:`. Parse fail sebelum model/device, bukan kegagalan inference; koreksi memakai format string `-f` agar tidak ada interpolasi `$var:` lagi. Tunggu CI commit berikutnya; uji Sony belum diulang, CP4 tetap BLOCKED.


### T10-ASR-STABILITY-REMOTE-VERIFICATION / DEVICE VERIFIED (limited scope) / 2026-10-08
- Physical device Sony SO-03L Android 11, whisper.cpp v1.9.4 Base multilingual (`base/id`), manifest SHA-256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`, model SHA-256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`. Laporan JSON berasal dari pengguna, belum diinspeksi bersama `runs.csv`/`telemetry.csv`.
- Device retest `-RunMinutes 2`: actual `elapsed_session_s=132.86`; **9/9 remote Whisper exits explicitly 0** via `result.exit`; `unverified_remote_whisper_exit_runs=0`; 9/9 Windows ADB exits masih tidak tersedia. Status `COLLECTED_REMOTE_VERIFIED_ADB_UNVERIFIED`, `stop_reason=null`. Berhasil memverifikasi **penyelesaian proses CLI di Android** untuk 9 run, bukan exit proses ADB host.
- Median RTF 0.7021; p95 nearest-rank RTF 1.118. Peak sampled VmRSS 378764 KiB (≈369.9 MiB). Battery temp 38.5°C awal, 39.0°C puncak/akhir (+0.5°C), USB powered=true; tidak mencapai batas berhenti 43°C. Preflight airplane mode=1 dan Wi-Fi=0. Durasi 132.86 detik >120 detik karena run terakhir diselesaikan sebelum loop berhenti.
- Perbandingan dengan 300.06 detik / 23 run sebelumnya tidak sepadan langsung karena jumlah/subset sampel dan starting thermal context berbeda. Tidak menetapkan bahwa RTF membaik signifikan atau CPU tidak throttle. Hasil dua menit ini belum memenuhi video E2E 30s/3min/10min dan tidak membuktikan Android app bebas ANR/OOM.
- CI commit `163cbc8`: Android CI **PASS** https://github.com/ferdilpu-sudo/Subloka/actions/runs/37778750189 dan T10 Engine Evaluation **PASS** https://github.com/ferdilpu-sudo/Subloka/actions/runs/37778750212. Remote-exit harness sudah terverifikasi pada CI mock Windows+POSIX dan runtime fisik pengguna dengan batas di atas.
- Next T10 prioritas kualitas: review 20 clean ID terhadap human reference/audio karena WER base clean 28.61% >20%, lalu investigasi model/normalisasi dan error khusus; translation ID→EN masih 25/30 ACCEPT (83.33%) <27/30. Thermal 5 menit remote-exit verified dan video E2E tetap **belum dijalankan** jika dibutuhkan gate resource.
- **T10/CP4 BLOCKED, T11 TODO**. Jangan ubah target WER, terjemahan, atau klaim CP4 PASS berdasarkan uji pendek ini.


### T10-ASR-ID-CLEAN-WER-TEXT-AUDIT / COMPLETE-TEXT / AUDIO-REVIEW-PENDING / 2026-10-08
- Input evidence dari unggahan pengguna: `asr-results.csv` 120 hasil (Tiny dan Base × 2 bahasa × 20 clean + 10 challenging), SHA256 `39a9570cd621d81c9607332c34a068fa83c48c4c142f3594d3243144eab08daa`; `t10-dataset.json` 60 fixture, SHA256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`. Tidak ada WAV yang diunggah; kualitas referensi berdasarkan audio belum boleh diklaim.
- Normalizer identik `tools/t10_wer.py` (lowercase, non-word punctuation→spasi; split whitespace), dengan DP Levenshtein. Baseline **ID clean Base 105 edit /367 kata referensi = WER micro 28.6104%**, 82 substitutions /7 deletions /16 insertions; mean per-sample WER macro 28.07%. ID clean Tiny 162/367 = 44.14%; Base lebih baik 15/20 sampel, sama 3, lebih buruk 2. Base EN clean 42/429 = 9.79%. Semua keputusan gate memakai WER micro baseline yang tidak diubah.
- Agar mencapai **WER <=20%** pada referensi tetap 367 kata, total edit <=73; minimal **32 edit** harus hilang, bukan mengganti score/threshold. 6 audio prioritas `id-clean-07` (14 errors), `id-clean-12` (10), `id-clean-02` (8), `id-clean-08` (8), `id-clean-17` (8), `id-clean-19` (8): gabungan 56/105 error (53.3%). `id-clean-19` kasus angka: reference `21-20` menjadi `0.1.220`; `id-clean-12` nama Aristarchus rusak; `id-clean-07` banyak kata dan angka terpotong. Referensi `id-clean-01` dan `id-clean-14` terdengar janggal secara tekstual, **belum boleh dikoreksi tanpa mendengar WAV**.
- Integrity: 119 dari 120 WER tersimpan sesuai hasil hitung ulang (toleransi rounding 0.000051). Satu exception **Base/en-challenging-06**: CSV WER=0.2326 tetapi teks CSV+manifest yang diunggah menghitung 9/43=0.2093; audit source/provenance perlu dicek, jangan menulis ulang evidence historis. **Tidak memengaruhi ID clean baseline.**
- Reproducibility: `tools/t10_asr_error_audit.py` memvalidasi ID/kategori, menghitung edit per sampel, membuat `asr-error-summary.json` dan review ID-clean yang seluruhnya bertanda `UNREVIEWED`; script tidak membaca audio atau mengubah baseline. Uji unit terintegrasi ke CI; **status test CI pending saat commit**.
- NEXT: pemeriksaan manusia terhadap enam WAV asli dari `t10-audio/id-clean/` (07,12,02,08,17,19), cocokkan kata per kata dengan referensi FLEURS dan model output; kategorikan noise/ucapan, kesalahan fonetik, angka, nama, ejaan terpisah. Setelah referensi benar, eksperimen terkontrol parameter decoding/model boleh dipertimbangkan dengan fixture dan metrik dibekukan. **CP4 BLOCKED / T11 TODO.**


### T10-ASR-PRIORITY-WAV-ACOUSTIC-AUDIT / SIGNAL INSPECTED, HUMAN LISTENING PENDING / 2026-10-08
- Pengguna mengirim `id-clean-priority-audio.zip` yang berisi tepat enam WAV ID-clean (07, 12, 02, 08, 17, 19). SHA-256 ZIP: `c7eba760822a4cb9ae5db41a9a15df8925c4495d708725e25d93c13ae05f6533`. Rekaman terverifikasi PCM 16-bit mono 16 kHz, durasi sesuai `t10-dataset.json` hingga ±0.01 s, dan **0 sample digital clipping** pada semuanya.
- RMS dBFS / peak dBFS / durasi detik: `id-clean-07 -24.1/-7.7/10.86`; `id-clean-12 -35.0/-9.5/10.62`; `id-clean-02 -41.2/-24.2/10.98`; `id-clean-08 -22.4/-5.8/10.44`; `id-clean-17 -24.0/-4.3/9.90`; `id-clean-19 -23.5/-4.8/10.02`. Audio `02` paling pelan; `12` juga pelan. Level audio rendah **tidak membuktikan** noise/SNR buruk atau salah referensi.
- Hasil model tetap asli, termasuk `id-clean-07` 56% WER, `12` 66.67%, `02` 44.44%, `08` 44.44%, `17` 34.78%, `19` 44.44% (Whisper Base), dengan masalah kandidat angka `21-20`, nama `Aristarchus`, pemisahan kata. Tiny malah lebih rendah daripada Base pada `id-clean-08` (33.33% vs 44.44%), sehingga penyebab tidak dapat disederhanakan hanya pada ukuran model.
- Artifact privat dibuat dalam chat: halaman HTML offline berisi enam audio asli, dua versi *gain only* (`02` +17.2 dB; `12` +8.5 dB, peak dibatasi hingga -1 dBFS), referensi, hipotesis Tiny/Base, pilihan status `UNREVIEWED/REF_MATCHES_AUDIO/REF_NEEDS_CORRECTION/AUDIO_AMBIGUOUS`, ekspor CSV; serta CSV template yang default semua `UNREVIEWED`. Tidak ada file WAV/raw transcript pengguna yang ditambahkan ke Git. Gain adalah eksperimen mendengar, bukan hasil ASR baru atau perbaikan SNR.
- Batasan penting: **belum ada transkripsi pendengaran independen** dari keenam WAV. Audit ini berdasarkan format/file, pengukuran sinyal, dan teks dataset/model; tidak membenarkan koreksi reference atau reinterpretasi WER. Next: reviewer mendengar WAV satu per satu via halaman offline, ekspor CSV, kemudian baru lakukan paired ASR A/B original vs gain atau perbaikan dataset bila terbukti oleh rekaman.
- T10 / CP4 **BLOCKED**, T11 TODO. Baseline clean Indonesia tetap 105/367 error (28.61% WER).


### T10-ASR-LISTENING-REVIEW-USER-001 / REVIEW PARTIALLY FINALIZED / 2026-10-08
- Input pengguna: `subloka-t10-six-wav-listening-review.csv`, SHA-256 `88df1defbbf4d3a3f2b86dbc84980921617d18ac29464531afdc6e67a4464576`, enam baris, semuanya cocok dengan enam prioritas WAV `id-clean-{07,12,02,08,17,19}`; tidak ada `corrected_reference` yang diisi. Dokumen ini merangkum hasil penilaian pengguna, bukan verifikasi transkripsi audio independen oleh asisten.
- Status eksplisit di CSV: `id-clean-08=REF_MATCHES_AUDIO` (1/6), `id-clean-07` dan `id-clean-12=AUDIO_AMBIGUOUS` (2/6), `id-clean-02`, `id-clean-17`, `id-clean-19=UNREVIEWED` (3/6). Tiga status UNREVIEWED **tidak** diubah sepihak walaupun `listening_notes` ketiganya menyebut ucapan ambigu/tidak jelas dan menyarankan tidak digunakan.
- Reviewer memberi alasan eksplisit pada `07` "cara berbicara tidak jelas"; `12` "cara mengucapkan kata tidak jelas". Catatan `02`, `17`, `19` mengindikasikan pengucapan tidak jelas/ambigu tetapi status belum finalized. Hanya `08` yang secara eksplisit dinilai referensi cocok dengan audio. Tidak ada satu pun referensi yang disetujui untuk diubah.
- **Jangan drop atau mengganti referensi** keenam sample dari baseline resmi hanya berdasar review pasca-hoc; FLEURS `clean` pada manifest T10 dipilih sebagai klip durasi terdekat ke median, bukan audit kejernihan akustik. Audit audio quality bisa menjadi penelitian tambahan atau benchmark baru dengan protokol pre-registered, dataset & checksum terpisah, tanpa menimpa baseline.
- Next: minta konfirmasi pengguna apakah `02`, `17`, `19` memang mau di-finalisasi `AUDIO_AMBIGUOUS`; jika ya, catat status review (tanpa mengubah baseline). Jika review dianggap final, lakukan eksperimen pasangan (original vs gain untuk 02/12) di set diagnostik terpisah, bukan penyesuaian angka CP4. T10/CP4 **BLOCKED**, T11 TODO; ASR Base ID-clean WER 105/367 =28.61% >20%.


### T10-ASR-LISTENING-FINAL + GAIN-AB-DIAGNOSTIC / IMPLEMENTED / 2026-10-08
- Pengguna memberi konfirmasi eksplisit: `id-clean-02`, `id-clean-17`, `id-clean-19` ditetapkan sebagai `AUDIO_AMBIGUOUS` sesuai catatan review sebelumnya. Status final enam klip: `AUDIO_AMBIGUOUS` = 07, 12, 02, 17, 19 (5/6); `REF_MATCHES_AUDIO` = 08 (1/6); `UNREVIEWED` = 0. Tidak ada `REF_NEEDS_CORRECTION` atau teks `corrected_reference` yang disetujui.
- Provenance review: original CSV SHA256 `88df1defbbf4d3a3f2b86dbc84980921617d18ac29464531afdc6e67a4464576`; CSV final yang menyimpan seluruh 12 kolom asli SHA256 `ed4eb43e80db1b699a2af56f0cafef6daa6981592545e54c21d5fdaafd4af0aa`; keputusan status dan provenance di-rekam tanpa audio/transkrip asli pada `.agents/evidence/t10-asr-listening-review-final.json`.
- **FROZEN CP4**: referensi FLEURS dan 20 sampel ID-clean tetap utuh; ASR Base ID-clean 105/367 kesalahan kata / WER 28.61% (>20% target), tidak berkurang setelah review. Teks review menyatakan ucapan tidak jelas pada lima klip, tetapi menghapus sampel setelah melihat WER akan menghasilkan bias seleksi; jika diinginkan, revisi dataset perlu protokol baru dan baseline versi terpisah.
- Workstream berikutnya: `tools/t10_asr_gain_ab.py` (diagnostik non-gating) membandingkan Whisper Base input WAV asli vs penguatan amplitudo saja pada dua WAV paling pelan: `id-clean-02 +17.2 dB`, `id-clean-12 +8.5 dB`. Checksum WAV/model/manifest pinned, PCM16 mono 16k, peak <= -1 dBFS, perangkat arm64 offline, suhu baterai awal <40°C dan berhenti >=43°C, sampel dijalankan dalam urutan tetap original 02, gain 12, original 12, gain 02. Result `.t10-benchmark/gain-ab-*/summary.json`, `runs.csv`, hipotesis+stderr lokal; **tidak menulis ulang asr-results.csv/t10-dataset.json** dan WER output hanyalah diagnostik terhadap referensi yang kini ditandai ambigu.
- CI: `tools/test_t10_asr_gain_ab.py` mencakup invariansi audio asli, headroom, validasi format WAV, marker remote, scope dan status review final; GitHub Actions menjalankan unit test. **Status tool IMPLEMENTED / CI PENDING / SONY A/B NOT_RUN** hingga hasil verifikasi diterima.
- Next: pastikan CI selesai, lalu jalankan `python tools/t10_asr_gain_ab.py --preflight-only`, selanjutnya `python tools/t10_asr_gain_ab.py` hanya jika siap; kirim ringkasan lokal untuk melihat apakah perubahan gain mengubah hipotesis dalam dua pasangan. Jangan infer peningkatan WER resmi dari 4 inference saja. **CP4 BLOCKED / T11 TODO**; kualitas terjemahan ID→EN tetap 25/30 di bawah 90%.


### T10-ASR-GAIN-AB-SONY / DIAGNOSTIC DONE / 2026-10-08
- Input pengguna: `summary.json` (body disampaikan di chat) untuk `tools/t10_asr_gain_ab.py`; Sony SO-03L Android 11, offline_preflight=true, Whisper Base multilingual pinned SHA `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`, manifest frozen SHA `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`. Asisten belum memeriksa berkas lokal `runs.csv` atau log perangkat secara terpisah. Hasil ringkas tanpa transkrip tersimpan dalam `.agents/evidence/t10-asr-gain-ab-sonyoct08.json`.
- Actual status `DIAGNOSTIC_COLLECTED_NOT_CP4`, `stop_reason=null`. **4/4 Whisper Android exit=0 dan 4/4 host ADB exit=0** (berbeda dari tes stability sebelumnya). Suhu baterai 37.7°C→38.5°C, stop threshold 43°C tidak tercapai, USB berpotensi aktif.
- Perbandingan diagnostik frozen-reference: `id-clean-02` original 44.44%, gain +17.2 dB 44.44% (Δ=0 pp); `id-clean-12` original 66.67%, gain +8.453 dB 73.33% (Δ≈+6.66 pp, lebih buruk). Kedua hipotesis asli-vs-gain berubah, tetapi tidak menghasilkan perbaikan WER. RTF (orig→gain): `02` 0.8154→0.8822; `12` 0.8578→0.8239. Bukan eksperimen power/timing terkontrol.
- **Kesimpulan scoped**: penguatan amplitudo saja **tidak terbukti memperbaiki** Whisper Base pada kedua klip ini. Keduanya `AUDIO_AMBIGUOUS` menurut review pengguna; jumlah n=2 dan tanpa pengulangan/randomization, WER diagnostik tidak layak menyimpulkan apakah gain bermanfaat pada dataset lain. Gain saja bukan penambah SNR atau pembersih artikulasi.
- **Next T10**: jangan mempromosikan gain-only sebagai fix engine; prioritaskan kontrol variabel decoding / model alternatif melalui pengujian seluruh frozen 20 ID-clean, pertahankan semua 20 reference dan bandingkan WER mikro secara berpasangan; tambahkan evaluasi nyata audio/kejelasan sebagai benchmark **baru terpisah** dengan protokol yang ditetapkan sebelum run, bukan menghapus sampel yang tidak disukai sesudah melihat baseline.
- Gate **CP4 BLOCKED**, T10 aktif, T11 TODO. Baseline resmi ID-clean Base 105/367 edits = 28.61% (>20%). Kualitas translation ID→EN 25/30 ACCEPT (83.33% <90%) tetap blocker lain. E2E video/thermal gate belum lengkap.


### T10-ASR-FROZEN-DECODE-A/B-HARNESS / IMPLEMENTED, DEVICE NOT_RUN / 2026-10-08
- T10 next diagnostic prepared: `tools/t10_asr_decode_ab.py` on Sony SO-03L Android arm64 offline; Whisper Base pinned SHA256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`; original 20 Indonesian FLEURS clean WAVs (manifest SHA `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`) and immutable original CSV SHA `39a9570cd621d81c9607332c34a068fa83c48c4c142f3594d3243144eab08daa`.
- Exactly one decoding variable differs: control uses prior CLI flags `-nt -ng -nfa -otxt -of result`, candidate adds `-bs 1` to narrow beam size; no new model, gain, denoising, prompt, language, preprocessing, clip dropping, or reference normalization. Default option is left unspecified in control exactly as prior harness. Fixed sorted ID schedule with alternate control/candidate ordering (AB/BA) per clip; **20 full pairs = 40 inference runs** when completed. Five reviewer-ambiguous samples remain in the 20.
- The independent script checks frozen input hashes and baseline 105 edits/367 words, original 16kHz mono PCM16 WAV shape, model and CLI cache presence, airplane_mode_on=1/Wi-Fi=0, arm64 device, initial battery <40°C. It monitors battery every ~2s while ASR runs, attempts targeted kill at >=43°C using remote PID, checks Android `result.exit=0` and host ADB `exit=0`, and saves transcripts/per-pair metrics only in a unique ignored `.t10-benchmark/decode-ab-*` folder.
- **Safe staged usage**: `python tools/t10_asr_decode_ab.py --preflight-only`, then `python tools/t10_asr_decode_ab.py --max-pairs 3`; after a cool-down if needed, `python tools/t10_asr_decode_ab.py --resume .\.t10-benchmark\decode-ab-<session>` for remaining 17 pairs. Persistent per-run `summary.json` and `runs.csv` allow resumption without replaying completed runs; resume is refused if model, compiled binary, audio WAVs, serial, original baseline, or manifest fingerprints differ.
- Analysis reports current-control vs beam1 micro WER and individual word-edit deltas **for completed paired subset only**, archived baseline held separately as 105/367=28.61%; control-to-archived hypothesis equality also shown to flag any CLI-run drift. A lower diagnostic WER does **not** pass CP4 without whole-set verification and other gates.
- Tests `tools/test_t10_asr_decode_ab.py` verify 20 unique pairs, AB/BA order, no cherry-picked fixtures, fixed command flags, safe remote command/PID marker, frozen-hash guard, analysis, and no gate promotion. GitHub Actions `T10 Engine Evaluation` runs tests. **Status at commit: CI PENDING and Sony decoding A/B NOT_RUN**; previous gain-only test n=2 showed no WER benefit.
- CP4/T10 **BLOCKED**, T11 TODO. Indonesian Base official clean WER 28.61% vs <=20%; translation ID→EN ACCEPT 25/30 (83.33%) vs >=90%; E2E resource/video, reference validation remain. Do not update engine or CP4 baseline unless a full controlled experiment supports it.


### T10-ASR-DECODING-PILOT-3PAIRS / DEVICE RESULTS RECORDED, NO CP4 PROMOTION / 2026-10-08
- Evidence user: output `analysis` dari `tools/t10_asr_decode_ab.py --max-pairs 3` pada perangkat fisik Sony; 6 inference, 3 full pairs (`id-clean-01/02/03`), 53 reference words. Full `summary.json` metadata (`status`, `stop_reason`, `battery_last_c`, `events`) dan `runs.csv` **belum diserahkan dalam turn ini**. Structured result saved in `.agents/evidence/t10-asr-decode-pilot-3pairs.json`.
- Frozen control default: 15/53 edits, micro-WER 28.3019%; `beam1`: 17/53 edits, micro-WER 32.0755%; Δ beam1 minus default = **+2 edits / +3.7736 poin persentase (worse)**. Sample deltas: `id-clean-01 +0` (4→4); `id-clean-02 +1` (8→9); `id-clean-03 +1` (3→4). 3/3 hypotheses changed; 3/3 control hypotheses equal archived baseline exact text. Five listener-ambiguous clips including 02 remain part of full dataset; no cherry-picking.
- RTF control→beam1: `01 1.2004→1.1973`; `02 1.1327→1.3249`; `03 1.2877→1.0674`. Mixed per-sample timing; do not infer beam1 is faster or slower universally. Piloting subset n=3, one run per config per clip, cannot establish decoding candidate inferiority on all 20.
- CI commit `b3fda1c`: [T10 Engine Evaluation](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37796038607) **PASS** and [Android CI](https://github.com/ferdilpu-sudo/Subloka/actions/runs/37796038850) **PASS**. Device pilot is real user-supplied analysis; thermal/aborted status unverified without full summary.
- Decision: no production change to beam size and no baseline edits. Request `summary.json` metadata before resuming. If session `PARTIAL_EXPERIMENT_NOT_CP4`, stop_reason null and cool/healthy phone, may continue **same session** in stages (`--resume PATH --max-pairs 4`), not a separate 20-sample baseline. If thermal or runtime issue, stop and diagnose first.
- Official frozen Base ID-clean WER 105/367 = 28.61% (>20% gate), translation ID→EN 25/30 ACCEPT (83.33%), CP4 BLOCKED, T11 TODO; E2E video resource gate open.


### T10-ASR-DECODE-7PAIRS-SONY / PARTIAL DIAGNOSTIC TIE / 2026-10-08
- User after resume four additional pairs submitted `summary.analysis` excerpt: `paired_samples=7`, `control_errors=32`, `beam1_errors=32`, `control_micro_wer=beam1_micro_wer=0.2480620155`, `beam1_minus_control_micro_wer=0`. These counts imply **129 reference words** across paired `id-clean-01` to `id-clean-07`; no complete session summary or `runs.csv` supplied in the same turn. Preserved at `.agents/evidence/t10-asr-decode-7pairs.json`.
- Relative to pilot first 3 (`15 vs 17` on 53 words), subsequent four samples contribute default `17` vs beam1 `15` edits over remaining 76 words (derived from aggregate differences). Candidate regained initial 2-edit disadvantage, now **32 vs 32** on 7 pairs. This is not evidence of improvement or equivalence for whole 20 samples.
- User's latest output lacks session `status`, `stop_reason`, `battery_last_c` and events. Previously submitted 3-pair pilot `battery_last_c=39.2` and `PARTIAL_EXPERIMENT_NOT_CP4`, but **do not carry it forward** as proof the resumed 7-pair session is thermal safe. Before resuming check current session metadata and current device temperature (<40°C), airplane mode/Wi-Fi off.
- If new session metadata healthy, resume **same decode-ab session** next four pairs (08–11) via `python tools/t10_asr_decode_ab.py --resume "$($session.FullName)" --max-pairs 4`, then re-review paired WER. Do not automatically update any engine setting. CP4 BLOCKED, T11 TODO, historical 20-sample baseline 105/367=28.61%.


### T10-ASR-DECODE-11PAIRS-SONY / PARTIAL DIAGNOSTIC BEAM1 -1 EDIT / 2026-10-09
- User posted original resumed session `decode-ab-20261008T145942Z-10430e` console log after `--max-pairs 4` and `summary.analysis`. Current `paired_samples=11`, `control_errors=48`, `beam1_errors=47` on 203 reference words; control micro-WER **23.6453%**, beam1 **23.1527%**, delta beam1-control **-1 edit / -0.4926 percentage points**. Difference is small and partial, NOT a verified full-set improvement. Evidence stored in `.agents/evidence/t10-asr-decode-11pairs.json`.
- Newly completed `id-clean-08/09/10/11` results, control→beam1 errors: `08 8→7` (18 words); `09 7→6` (20); `10 1→2` (19); `11 0→0` (17). New four contributed 16 control vs 15 candidate edits over 74 words; 7-pair prior baseline 32 vs 32 over 129 words. Total now 22/40 inference and 9 pairs remain.
- Latest operational evidence: `status=PARTIAL_EXPERIMENT_NOT_CP4`, `stop_reason=null`, battery temp after prior 7-pair stage 37.7°C; new offline preflight SO-03L PASS at battery 30.2°C, after last run 31.0°C; stop threshold 43°C not reached. Note that the checked sensor is **battery**, not CPU, and USB/device/environmental conditions vary. Actual 8 logged run results successful according to harness output; raw log files weren't independently inspected.
- Decision: **continue controlled A/B**, do not change decoding default yet. Next stage should run `--resume "$($session.FullName)" --max-pairs 4` on **id-clean-12–15** if new preflight safe/cool/offline; inspect session metadata & micro-WER afterward. Keep all 20 original samples, archived WER 105/367=28.61%, reference texts, original WAV/model checksums and CP4 criteria unchanged. CP4 BLOCKED, T11 TODO.


### T10-ASR-DECODE-15PAIRS-SONY / PARTIAL DIAGNOSTIC 2026-10-09
- User reports same original resumed session `decode-ab-20261008T145942Z-10430e` now at **15/20 paired samples (30/40 inferences)**. Control default 72 edits/270 reference words = **26.6667%** diagnostic micro WER; beam1 73/270 = **27.0370%**, delta beam1-control **+1 edit / +0.37037 pp**. Previous 11-pair results were 48/203 control and 47/203 beam1, hence newly completed 12–15 account for 24 control and 26 beam1 errors in 67 words. No individual 12–15 transcripts or RTF shown.
- Summary `status=PARTIAL_EXPERIMENT_NOT_CP4`, `stop_reason` empty, battery sensor last 30.2°C (stop threshold 43°C). Battery != CPU temperature; operational health only at report time. Evidence: `.agents/evidence/t10-asr-decode-15pairs.json`.
- Remaining **5 pairs (id-clean-16–20)**. If new device preflight confirms offline arm64 Sony, battery below 40°C and no new issue, resume **same session** with `--max-pairs 5`; script checks battery during inference, stops at 43°C. Do not infer candidate inferiority from 15 pairs or promote decoder. All 20 frozen clips including listener-ambiguous remain in evaluation. Historical official baseline still 105/367=28.61%; **T10 ACTIVE, CP4 BLOCKED, T11 TODO**.
