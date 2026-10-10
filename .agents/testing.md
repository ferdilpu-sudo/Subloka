# Pengujian, Gate, dan Bukti

Dokumen ini membedakan strategi yang belum dijalankan dari bukti aktual. Tanggal baseline 2026-10-06. Build dan lint Android frontend telah berhasil dijalankan melalui GitHub Actions dan Windows lokal; smoke test runtime perangkat untuk frontend demo telah dikonfirmasi PASS oleh pengguna. T08 persistence/domain juga telah lulus unit/integration test serta verifikasi Room schema fixture pada CI. Pemeriksaan statis lokal tetap dicatat terpisah agar bukti compile tidak disamakan dengan bukti usability/runtime.

## Klasifikasi hasil

PASS = langkah dijalankan dan actual memenuhi expected. FAIL = dijalankan tetapi berbeda. BLOCKED = tidak dapat dijalankan, alasan disebut. NOT_RUN = belum dijalankan. “Sudah diuji” harus selalu disertai hasil, bukan sinonim lulus. Semua hasil terikat revision, versi model, environment dan fixture; perubahan signifikan dapat membatalkan relevansinya.

## Matriks pengujian

| Suite | Requirement | Skenario penting | Jenis / task |
|---|---|---|---|
| DOC | Pedoman | 10 file, tautan lokal, task DAG, checkpoint, status, UX guardrail, handoff | Pemeriksaan dokumen / T00 |
| UX-SPEC | FR02–FR09, NFR05,NFR07 | IA, Caption/Timing/Style, keyboard, adaptive, 9:16, stale translation, error/empty/export blocking | Review/prototype walkthrough / T03, CP2 |
| UI | FR01–FR12, NFR05,NFR07 | Navigasi, bilingual, keyboard, font scale, TalkBack, touch target, timeline contextual, no bottom nav | UI/instrumented/manual / T04–T07 |
| DATA | FR02, FR06–FR08, FR11, NFR01 | CRUD, transaksi, autosave/reopen, migration, revision monotonic, split/merge/undo | Unit + Room integration / T08 |
| MEDIA | FR03 | URI revoke/relink, rotation, tanpa audio, stereo, sample rate berbeda, VFR, unsupported input | Integration/perangkat / T09 |
| MODEL | FR01, FR12 | Unduhan parsial, checksum ASR, readiness SDK, ruang habis, delete/re-download, mode pesawat | Perangkat / T10 |
| ASR | FR04, NFR02–04 | EN/ID, silence, musik, slang, overlap, chunk boundaries, offset absolut, cancel | Engine/perangkat / T10–T11 |
| TRANS | FR05 | Kedua arah, negasi/nama/angka, stale source, edit manual saat job, retry | Unit + engine + penilaian manusia / T10,T12 |
| JOB | FR04, FR09, FR11, NFR01–04 | Process death, cancel, single-job, background, input revision berubah, storage penuh | Integration/perangkat / T13 |
| EXPORT | FR08–FR10, NFR06 | MP4 playback/audio/style, SRT Unicode/timestamp, frame boundary, rotation, cancel, overwrite prevention | Golden/integration/perangkat / T14 |
| E2E | Semua FR/NFR | Pick video→generate→Caption→Timing/Style→translate→export→reopen offline dua arah | Perangkat fisik / T15 |
| RELEASE | Delivery | Install/update, data tetap ada, model siap, lisensi, checksum, README benar | Smoke/manual / T16 |

Tes domain minimal: interval start/end invalid, overlap, boundary start inclusive/end exclusive, stale translation, CAS menolak hasil lama, edit manual tidak tertimpa, SRT rounding durasi nol, undo revision monotonik. Jangan hanya menguji getter atau memantulkan implementasi.

## Gate UX T03 / CP2

CP2 menggunakan walkthrough berbasis task. Prototype/wireframe tidak harus terhubung engine, tetapi semua state kritis harus dapat ditinjau.

### Task walkthrough wajib

1. Dari empty Home, buat project baru.
2. Pilih video 9:16 dan source English; pahami bahwa target Indonesia otomatis.
3. Hadapi model belum siap → download → retry failure → ready.
4. Mulai generation; bandingkan progress known vs unknown; cancel dan interrupted.
5. Masuk Editor/Caption; pilih segment, play/seek, edit source, lihat translation menjadi stale.
6. Retranslate satu segment dan bulk stale; lindungi translation manual dari overwrite tanpa konfirmasi.
7. Split/merge selected caption.
8. Buka Timing; ubah start/end dengan metode non-drag dan periksa invalid/overlap behavior.
9. Buka Style; ubah dual/source/translation, order, size/color/outline/background/position tanpa menemukan tool video editing di luar scope.
10. Aktifkan keyboard saat edit video portrait; selected field/action tetap terlihat.
11. Tinjau compact wide/landscape dan expanded/supporting pane; task utama tetap sama.
12. Tinjau long text/readability warning dan tindakan split/perkecil size.
13. Export source-only ketika translation stale; pastikan dual blocked dengan alasan; export dual setelah current.
14. Simulasikan save failure dan URI missing/relink.

### Kriteria CP2

PASS hanya jika:

- reviewer dapat menyelesaikan task tanpa ambiguity fundamental;
- satu primary action terlihat pada tiap state utama;
- Caption adalah default editor;
- Timeline detail tidak memonopoli Caption workspace;
- Translation tidak menjadi tab utama;
- tidak ada bottom navigation MVP;
- preview 9:16 bounded sehingga editor usable;
- keyboard tidak menutup task utama;
- compact dan expanded memiliki information hierarchy konsisten;
- error/empty/loading/stale/disabled states menjelaskan recovery;
- setiap status penting punya label/icon/text selain warna;
- touch target/focus/font-scale/TalkBack notes tersedia untuk T04;
- mapping ke FR/NFR lengkap.

Temuan dicatat P0–P3. CP2 tidak boleh ditutup bila ada P0/P1 unresolved tanpa keputusan eksplisit.

## Fixture dan perangkat

Gunakan fixture yang legal/disetujui: ucapan EN bersih, ID bersih, dialog informal, musik latar, silence, audio tumpang tindih; video portrait/landscape/rotated; klip tanpa audio dan file rusak. Dataset kualitas baseline: sekurangnya 30 ujaran per bahasa, terdiri dari 20 bersih dan 10 menantang, dengan transkrip acuan yang ditinjau manusia.

Untuk UI/UX, fixture minimum mencakup:

- video 9:16 portrait;
- video 16:9 landscape;
- source/translation pendek;
- long source + long translation;
- translation MISSING, CURRENT, STALE, FAILED;
- project kosong, recent list, processing known/unknown;
- keyboard aktif;
- font scale besar;
- compact width dan expanded/window besar.

Perangkat target harus ditetapkan T01. Minimum gate rilis: satu HP fisik mewakili kelas bawah dari target dukungan dan satu perangkat/API lebih baru. Emulator membantu UI tetapi tidak menggantikan benchmark native/codec/thermal. Sony Android 11 adalah calon bila tersedia; belum ada perangkat yang diklaim diuji.

Video uji performa: 30 detik, 3 menit, dan satu video 10 menit pada perangkat sasaran, jika cukup ruang. Catat codec, resolusi, fps, jumlah audio channel, sample rate, versi OS, RAM, chipset, temperatur bila tersedia, model, thread count, waktu proses, peak memory, ruang sementara dan crash. Dukungan durasi lebih panjang tidak boleh disimpulkan tanpa uji.

## Protokol evaluasi T10 / CP4

Kandidat ASR adalah whisper.cpp v1.9.4 multilingual dengan model `tiny` dan `base`. Artifact model dipin ke revision Hugging Face `80da2d8bfee42b0e836fc3a9890373e5defc00a6`; SHA-256 `tiny` = `be07e048e1e599ad46341c8d2a135645097a538221678b7acdd1b1919c6e1b21`, `base` = `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`. Synthetic speech hanya smoke test fungsi dan **tidak** masuk dataset kualitas CP4.

Translation candidate adalah ML Kit on-device Translation 17.0.3, hanya pair EN↔ID. Model dikelola SDK melalui `RemoteModelManager`; aplikasi tidak mengarang path/hash internal model ML Kit.

Dataset CP4 minimum tetap 30 ujaran per bahasa untuk ASR (20 clean + 10 challenging) dan 30 segmen per arah untuk translation. Perangkat fisik wajib untuk angka RTF/RAM/thermal. Emulator hanya membuktikan API/readiness/smoke.

Fixture ASR T10 dapat dimaterialisasi dari Google FLEURS `dev` split pada revision `4683b04af03d2d9549064c7d72060a9a94bb6046` melalui `tools/t10_fetch_fleurs_dataset.py`. Per bahasa dipilih 20 ujaran unik berdurasi tipikal di sekitar median sebagai `clean` dan 10 ujaran unik terpanjang dengan durasi maksimal 25 detik sebagai `challenging` long-utterance. Seluruh audio tetap suara manusia dan dikonversi ke WAV PCM signed 16-bit mono 16 kHz. Subset challenging ini menguji beban utterance panjang/linguistik, bukan bukti robustness terhadap noise alami, overlap, atau variasi aksen. Reference berasal dari metadata FLEURS dan review dengar-manusia lokal tetap harus dicatat sebelum CP4 ditutup.

Pengukuran ASR per model/perangkat: WER per bahasa, RTF, thread count, wall time, peak memory bila stabil, crash/OOM/ANR, thermal bila tersedia. Translation: ACCEPT/MAJOR_MEANING_ERROR/NEGATION_ERROR/NUMBER_OR_NAME_ERROR, median/p95 latency setelah model siap.

CP4 tidak boleh PASS dari model checksum, build native, synthetic TTS, atau emulator saja. T11 tetap tertahan sampai benchmark fisik + review kualitas memenuhi gate atau keputusan eksplisit setelah FAIL/BLOCKED.

## Gate kualitas baseline (target, belum hasil)

- Transkripsi bersih: WER agregat per bahasa ≤20% pada dataset acuan; normalisasi case/punctuation harus ditetapkan sebelum uji. Laporkan juga hasil slang/noise, jangan mencampurnya untuk menutupi kelemahan satu bahasa.
- Translation: ≥90% segmen dataset diterima reviewer bilingual tanpa kesalahan makna besar; tidak ada pembalikan negasi atau perubahan angka/nama yang material pada sampel gate. Laporkan jumlah sampel dan kegagalan.
- Timing: ≥95% batas segmen pada sampel clean berada dalam toleransi ±300 ms terhadap anotasi manusia; tidak ada segmen invalid atau overlap.
- Render: transisi subtitle sesuai timestamp dengan toleransi maksimal satu frame output; preview/export tidak memotong teks dan mematuhi style/urutan.
- UI: tidak ada P0/P1 unresolved pada alur utama; 9:16 + keyboard + font scale + expanded tidak menghilangkan task utama; touch target/focus/TalkBack memenuhi acceptance yang ditetapkan T03/T04.
- Resource: tidak ada OOM/ANR pada video gate dan satu job; pembatalan diproses pada kesempatan aman engine. T10 menetapkan target latensi cancel, RTF, RAM dan durasi maksimum berdasarkan pengukuran lalu membekukannya sebelum CP4.
- Data: nol kehilangan perubahan yang sudah bertanda saved dalam tes restart/process death; file sumber checksum tetap sama.
- Offline: seluruh E2E lulus mode pesawat setelah setup, tidak memerlukan login/biaya; audit dependency dan observasi trafik ketika online dilakukan terpisah untuk klaim tidak mengunggah konten.

Ambang kualitas adalah baseline rancangan. Perubahan wajib dijelaskan sebagai ADR, ditinjau pengguna jika mengurangi kualitas/dukungan, dan tidak dilakukan setelah melihat kegagalan hanya supaya gate terlihat lulus.

## Contoh perintah setelah scaffold tersedia

```bash
./gradlew testDebugUnitTest
./gradlew lintDebug
./gradlew assembleDebug
./gradlew connectedDebugAndroidTest
```

Ini contoh, belum pernah dijalankan untuk proyek ini. T04 harus menggantinya dengan task Gradle yang benar-benar tersedia pada struktur modul aktual. Bukti menyertakan exit code dan ringkasan, bukan sekadar menempel command.

## Format evidence

```text
Evidence ID / task / tanggal:
Revision atau identitas artefak yang diuji:
Lingkungan: OS, SDK, perangkat, toolchain, engine/model version
Fixture dan hash bila relevan:
Perintah atau langkah manual:
Expected:
Actual:
Result: PASS / FAIL / BLOCKED / NOT_RUN
Artefak bukti: path log/report/frame/video, bila ada
Batas: apa yang tidak dibuktikan pengujian ini
Dokumen/task yang diperbarui:
```

## Bukti aktual

### DOC-001 — Baseline dokumen v0.1

- Task: T00.
- Tanggal: 2026-10-06. Identitas: paket dokumen baseline v0.1; tidak ada revision kode aplikasi.
- Lingkungan: Python 3 pada workspace Linux; tidak menggunakan Android SDK/perangkat.
- Result: PASS.
- Expected: tepat 10 Markdown, tautan relatif valid, task/dependency dikenal dan tidak siklik, aturan status/docs update ada.
- Actual: baseline v0.1 memenuhi pemeriksaan saat pembuatan.
- Batas: pemeriksaan dokumen tidak membuktikan implementasi atau kelayakan engine Android.

### DOC-002 — Sinkronisasi UX v0.2

- Task: T00.
- Tanggal: 2026-10-06.
- Revision/artefak: paket `offline-caption-project-docs-v0.2-agent-ready.zip`.
- Lingkungan: Python 3 / shell pada workspace Linux; tidak menggunakan Android SDK/perangkat.
- Langkah aktual: pemeriksaan jumlah file, tautan Markdown lokal, task DAG/checkpoint references, code fence, presence guardrail ADR-016–021, Caption/Timing/Style, no-bottom-nav rule, T03 outputs, CP2 questions, dan cross-document terminology.
- Result: **PASS**.
- Expected: 10 Markdown; tidak ada tautan lokal rusak; 17 task tanpa siklus; 8 checkpoint; arah UX v0.2 konsisten antara README/rules/prd/design/decisions/architecture/plan/testing.
- Actual: 10 Markdown; 0 tautan lokal rusak; 17 task; 8 checkpoint; task DAG acyclic; code fence berpasangan; ADR-016–021 tersedia; guardrail Caption/Timing/Style, no-bottom-nav, adaptive/keyboard, T03 outputs, dan CP2 review questions terdeteksi konsisten.
- Batas: pemeriksaan dokumentasi tidak membuktikan usability pada pengguna, Compose runtime, aksesibilitas aktual, engine, performa, atau export.

### APP-BASELINE — Implementasi frontend demo

- Result: **PASS untuk compile/lint baseline** melalui BUILD-001.
- Actual: source Android multi-module tersedia dan berhasil melewati `:app:assembleDebug` serta `:app:lintDebug` pada GitHub Actions.
- Belum terverifikasi: install/runtime, usability nyata, accessibility runtime, akurasi engine, resource, codec, privacy trafik SDK, dan hasil ekspor nyata.


### STATIC-001 — Scaffold/frontend guardrail validation

- Task: T03–T07.
- Tanggal: 2026-10-06.
- Revision/artefak: folder `SubLoka/` hasil eksekusi lokal.
- Lingkungan: Python 3 / shell Linux; tanpa Android SDK dan tanpa Gradle runtime.
- Perintah: `python tools/validate_project.py`.
- Expected: module/file inti ada; tidak ada bottom navigation; workspace Caption/Timing/Style tersedia; disclosure DEMO ada; `allowBackup=false` dipertahankan.
- Actual: PASS; validator melaporkan seluruh guardrail tersebut terpenuhi pada source tree.
- Result: **PASS**.
- Batas: tidak mem-parsing/compile Kotlin dan tidak membuktikan rendering Compose, click behavior, accessibility, lifecycle, media, inference, persistence, atau export.

### TOOLCHAIN-001 — Verifikasi baseline versi dari sumber resmi

- Task: T02.
- Tanggal: 2026-10-06.
- Lingkungan: dokumentasi web resmi Android/Google + upstream whisper.cpp release.
- Expected: baseline stable dan kompatibel secara dokumentasi, tanpa versi dinamis.
- Actual: AGP 9.4.0 mendukung API 37 dan memerlukan Gradle 9.6.0; Compose BOM stable 2026.09.00; Material3 stable 1.4.0; Media3 1.11.1; Room 2.8.5; ML Kit Translate 17.0.3 dengan min API 23; whisper.cpp v1.9.4 tersedia sebagai release upstream.
- Result: **PASS** untuk pemilihan baseline dokumentasi.
- Batas: tidak membuktikan dependency resolution/build pada repository ini dan tidak membuktikan kualitas/resource engine.

### DOMAIN-001 — Kompilasi model domain Kotlin

- Task: T04 sebagai verifikasi parsial scaffold/core.
- Tanggal: 2026-10-06.
- Perintah aktual: `kotlinc core/domain/src/main/java/app/subloka/core/domain/*.kt -d /tmp/subloka-kotlinc/domain.jar`.
- Expected: seluruh model/domain murni Kotlin dapat dikompilasi tanpa Android/Compose runtime.
- Actual: compiler selesai dengan exit code 0 dan menghasilkan `domain.jar` sementara.
- Result: **PASS**.
- Batas: hanya membuktikan syntax/type-check modul `core:domain`; tidak membuktikan Compose, Android resources, Gradle graph, app install, atau runtime behavior.

### DOC-003 — Validasi tautan dokumen pasca-eksekusi

- Task: T01–T07 documentation update.
- Tanggal: 2026-10-06.
- Langkah aktual: parser lokal memeriksa seluruh tautan Markdown relatif di `.agents/*.md`.
- Expected: tidak ada referensi file lokal yang putus setelah dokumen diperbarui.
- Actual: seluruh tautan lokal resolvable.
- Result: **PASS**.
- Batas: tidak menilai isi tautan eksternal atau kebenaran implementasi aplikasi.

### BUILD-001 — Android assemble/lint frontend

- Task: T04–T07.
- Tanggal: 2026-10-06.
- Revision: `d01f1fcdd0f8ce7da16c9148551f9a06f06ac702`.
- Lingkungan: GitHub Actions `ubuntu-latest`; Temurin JDK 21; Android 17 SDK platform package `platforms;android-37.0`; Build Tools 37.0.0; Gradle 9.6.0; AGP 9.4.0.
- Workflow run: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37461629333
- Langkah aktual: setup Android SDK → setup Gradle → `python3 tools/validate_project.py` → `gradle --stacktrace :app:assembleDebug` → `gradle --stacktrace :app:lintDebug`.
- Expected: toolchain siap, guardrail lulus, app dapat dikompilasi dan lint tanpa error yang menghentikan build.
- Actual: seluruh langkah selesai dengan conclusion `success`; assembleDebug PASS dan lintDebug PASS.
- Result: **PASS**.
- Dampak: T04 dapat ditutup DONE setelah docs sinkron. T05–T07 tetap `IMPLEMENTED` karena compile/lint tidak membuktikan interaction runtime.
- Batas: tidak membuktikan install APK, startup Activity, click navigation, IME behavior, adaptive layout, TalkBack/font-scale, playback/media, inference, persistence, atau export nyata.

### DEVICE-001 — Android device frontend smoke test

- Task: T04–T07 / CP3.
- Tanggal: 2026-10-06.
- Lingkungan: perangkat Android pengguna; eksekusi manual dari build lokal Windows.
- Expected: install debug APK; flow Projects → New Project → Model Setup → Processing → Editor → Export; state STALE; blocked dual export; back behavior; no crash pada alur demo utama.
- Actual: pengguna mengonfirmasi secara eksplisit `DEVICE-001 PASS + CP3`.
- Result: **PASS**.
- Dampak: gate frontend CP3 ditutup; T05–T07 dapat ditutup DONE sebagai UI demo dan T08 boleh dimulai.
- Batas: evidence ini adalah konfirmasi smoke test manual pengguna, bukan log instrumented test. Engine inference, persistence, media pipeline, dan real export belum dibuktikan.

### DOC-004 — Reorganisasi pedoman coding agent ke `.agents/`

- Task: repository handoff / dokumentasi agent.
- Tanggal: 2026-10-06.
- Revision/artefak: working tree sumber yang dipublikasikan ke `ferdilpu-sudo/Subloka`.
- Langkah aktual: seluruh Markdown pedoman agent dipindahkan dari `docs/` ke `.agents/`; referensi pada root README, validator, FILELIST, dan dokumen terkait diperbarui; parser lokal memeriksa tautan Markdown relatif; `python tools/validate_project.py` dijalankan kembali.
- Expected: hanya root `README.md` yang tetap human-facing; seluruh catatan planning/rules/architecture/design/schema/testing/handoff agent berada di `.agents/`; tidak ada tautan `docs/...` lama yang rusak.
- Actual: `MARKDOWN_LINKS_PASS`; validator proyek `PASS`; pencarian referensi `docs/*.md` lama tidak menemukan stale path.
- Result: **PASS**.
- Batas: reorganisasi dokumentasi tidak membuktikan Android build/runtime dan tidak mengubah status T04–T07.


### CI-SETUP-001 — Koreksi Android 17 CI

- Task: T04 verification infrastructure.
- Tanggal: 2026-10-06.
- Result: **PASS** setelah iterasi setup.
- Temuan: runner awal membawa command-line tools lama; Android 17 package tersedia sebagai `platforms;android-37.0`, bukan `platforms;android-37`.
- Perbaikan: workflow memperbarui command-line tools melalui channel 3 dan memasang package API 37.0 + Build Tools 37.0.0.
- Batas: ini bukti kesiapan CI, bukan requirement produk.


### WRAPPER-001 — Gradle Wrapper 9.6.0

- Task: T04 local reproducibility.
- Tanggal: 2026-10-06.
- Revision bootstrap: `54498b135494eb42d37e55f866c21c0c3a12cdef`.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37463131375
- Expected: repository memiliki `gradlew`, `gradlew.bat`, `gradle/wrapper/gradle-wrapper.jar`, dan properties yang mengunci Gradle 9.6.0.
- Actual: workflow bootstrap selesai SUCCESS; seluruh file wrapper tersedia pada branch main; `distributionUrl` mengarah ke `gradle-9.6.0-bin.zip`.
- Result: **PASS**.
- Dampak: developer Windows tidak perlu memasang Gradle global; gunakan `.\\gradlew.bat`.
- Batas: wrapper availability tidak membuktikan Android SDK lokal tersedia atau device runtime lulus.


### BUILD-002 — Windows local assemble/lint

- Task: T04 local reproducibility.
- Tanggal: 2026-10-06.
- Lingkungan: Windows PowerShell, repository lokal `C:\\Users\\FLYONZ\\Documents\\GitHub\\Subloka`, Gradle Wrapper 9.6.0.
- Perintah: `.\\gradlew.bat :app:assembleDebug :app:lintDebug`.
- Expected: build dan lint selesai tanpa error.
- Actual: user melaporkan `BUILD SUCCESSFUL in 3m 46s`; 236 actionable tasks, 218 executed, 18 from cache.
- Result: **PASS**.
- Dampak: build frontend kini terbukti berhasil baik di GitHub Actions maupun Windows lokal menggunakan Gradle Wrapper.
- Batas: belum membuktikan install APK, startup Activity, navigation/click behavior, IME/adaptive layout, accessibility, atau device runtime.


### CP3-001 — Frontend acceptance

- Task: T04–T07.
- Tanggal: 2026-10-06.
- Pemilik gate: pengguna.
- Prasyarat: BUILD-001 PASS, BUILD-002 PASS, DEVICE-001 PASS.
- Actual: pengguna menyatakan secara eksplisit `DEVICE-001 PASS + CP3`.
- Result: **PASS**.
- Dampak: frontend demo diterima untuk melanjutkan ke T08. Status ini tidak menyatakan engine lokal, persistence, media decode, ASR, translation, atau export nyata sudah tersedia.


### DATA-001 — T08 persistence dan editor rules

- Task: T08.
- Tanggal: 2026-10-07.
- Revision: `deb5b1ebfe87254535a5a5845fa368cb6e6c8829`.
- Lingkungan: GitHub Actions `ubuntu-latest`; JDK 21; Android SDK API 37.0; Gradle Wrapper 9.6.0; Room 2.8.5; Robolectric integration test.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37469858314
- Langkah aktual: validator → `:core:domain:testDebugUnitTest` → `:core:database:testDebugUnitTest` → verifikasi tidak ada drift pada `core/database/schemas` → `:app:assembleDebug` → `:app:lintDebug`.
- Expected: invariant timeline diuji; source edit membuat translation stale dan revision naik; data tetap ada setelah reopen database; overlap ditolak tanpa mutasi; split/merge menghasilkan ID baru dan translation stale; machine translation CAS menolak revision lama dan melindungi manual edit; style tersimpan; restore/undo-style snapshot tetap menaikkan project revision; schema v1 tersimpan di version control.
- Actual: seluruh step CI selesai `success`; domain tests PASS, Room integration tests PASS, Room schema fixture PASS, assemble PASS, lint PASS.
- Result: **PASS**.
- Artefak bukti: `core/database/schemas/app.subloka.core.database.SubLokaDatabase/1.json`.
- Batas: schema saat ini baru version 1 sehingga belum ada jalur migrasi antarversi yang dapat diuji. Fixture v1 ini menjadi input wajib untuk migration test ketika version 2 diperkenalkan. T08 juga tidak membuktikan URI/media decode, ASR, translation engine, atau real export.
- Dampak: T08 dapat ditutup DONE; T09 menjadi task berikutnya.


### MEDIA-001 — T09 real media pipeline

- Task: T09.
- Tanggal: 2026-10-07.
- Revision: `900d7af443d0e4c61a39f96eaef27aca49d51b77`.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37560614944
- Lingkungan: GitHub Actions; build job + Android 11/API 30 x86_64 emulator; Media3 1.11.1; Android MediaExtractor/MediaCodec.
- Fixture: MP4 H.264 + AAC 16 kHz mono dengan rotation metadata; duplicate fixture melalui URI berbeda; MP4 tanpa audio; synthetic unsupported audio format.
- Langkah: unit test relink; compile androidTest; instrumented media test via `content://`; inspect metadata; decode AAC→PCM dengan byte cap; compare source bytes sebelum/sesudah; verify relink; reject no-audio/unsupported codec; prepare Media3 playback sampai `Player.STATE_READY`; assemble/lint.
- Expected: metadata/orientasi/audio track valid; PCM non-empty dengan sample rate/channel benar; source tidak dimodifikasi; relink hanya menerima fingerprint sama; error domain benar; player dapat prepare URI.
- Actual: seluruh build job dan `media-device` job PASS. Media3 mencapai READY; PCM decode menghasilkan data; source fixture tetap byte-identik.
- Result: **PASS**.
- Batas: emulator tidak membuktikan thermal/performance perangkat fisik atau seluruh codec OEM/VFR. Multi-track selection UX belum menjadi coverage gate. Coverage kompatibilitas luas tetap T15.
- Dampak: T09 DONE; T10 boleh dimulai.


### MODEL-001 — Whisper model integrity

- Task: T10.
- Tanggal: 2026-10-07.
- Candidate: whisper.cpp v1.9.4; multilingual `tiny` dan `base`.
- Model source revision: `80da2d8bfee42b0e836fc3a9890373e5defc00a6`.
- Workflow evidence: T10 Engine Evaluation run #1/#2, termasuk https://github.com/ferdilpu-sudo/Subloka/actions/runs/37563052224.
- Expected: model aktual dapat diunduh dari source pinned dan SHA-256 sesuai katalog aplikasi.
- Actual: `ggml-tiny.bin` checksum `be07e048...c6e1b21` PASS; `ggml-base.bin` checksum `60ed5bc3...fba2efe` PASS.
- Result: **PASS**.
- Batas: integrity artifact tidak membuktikan akurasi atau resource perangkat.

### TRANS-SMOKE-001 — ML Kit EN↔ID readiness

- Task: T10.
- Tanggal: 2026-10-07.
- Engine: ML Kit on-device Translation 17.0.3.
- Environment: Android 11/API 30 Google APIs emulator.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37563052224
- Expected: model EN dan ID dapat diunduh via RemoteModelManager, readiness menjadi READY, translation dua arah menghasilkan output non-empty dan mempertahankan fixture nama/angka.
- Actual: `connectedDebugAndroidTest` PASS; model download/readiness PASS; EN→ID dan ID→EN smoke PASS untuk nama `Rina` dan angka 3/7.
- Result: **PASS** untuk readiness/functional smoke.
- Batas: bukan review kualitas 30 segmen per arah dan bukan bukti traffic-free ketika online.

### ASR-SMOKE-001 — whisper.cpp bilingual synthetic smoke

- Task: T10.
- Tanggal: 2026-10-07.
- Engine/model: whisper.cpp v1.9.4; tiny/base multilingual.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37563052224
- Fixture: espeak-ng synthetic EN/ID, 16 kHz mono WAV.
- Actual: engine berhasil build dan menjalankan seluruh kombinasi model/language. WER smoke: tiny EN 0.5000; tiny ID 0.7500; base EN 0.5000; base ID 1.5000. Host max RSS teramati sekitar 180 MB tiny dan 291 MB base pada fixture ini.
- Result: **PASS** hanya untuk functional smoke.
- Batas: synthetic TTS dan host Linux tidak boleh digunakan sebagai quality/resource CP4. WER ini sengaja tidak dipakai untuk memilih model.

### ASR-ANDROID-BUILD-001 — benchmark binary arm64

- Task: T10.
- Tanggal: 2026-10-07.
- Workflow: T10 Engine Evaluation run https://github.com/ferdilpu-sudo/Subloka/actions/runs/37563402825
- Toolchain: whisper.cpp v1.9.4, NDK 28.2.13676358, Android platform 26, ABI arm64-v8a.
- Expected: `whisper-cli` dapat di-cross-compile untuk Android arm64 tanpa mengintegrasikan JNI produksi T11.
- Actual: job `android-benchmark-binary` PASS.
- Result: **PASS**.
- Dampak: `tools/t10_device_benchmark.ps1` dapat digunakan untuk benchmark fisik tiny/base melalui ADB.

### CP4-001 — Offline engine feasibility gate

- Task: T10 / CP4.
- Tanggal: 2026-10-07.
- Result: **BLOCKED**.
- Sudah tersedia: model integrity, atomic model store, ML Kit readiness/functional smoke, whisper bilingual functional smoke, arm64 benchmark binary/harness.
- Blocker: belum ada hasil dataset manusia 30 ujaran per bahasa + 30 translation segment per arah dan belum ada RTF/RAM/thermal dari perangkat fisik.
- Syarat buka: jalankan physical benchmark dan review kualitas sesuai gate; jangan mengganti threshold setelah melihat hasil.
- Dampak: T11 tetap TODO.


### T10-HARNESS-001 — Physical benchmark harness

- Task: T10 / CP4 preparation.
- Tanggal: 2026-10-07.
- Revision harness fix: `47641fe2533f16be664ada284787c9db7c66e86d`.
- Workflow: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37563671752
- Sudah diuji: PowerShell parser CI PASS untuk `tools/t10_device_benchmark.ps1`. Cross-compile arm64 whisper-cli sebelumnya PASS pada T10 Engine Evaluation run `37563402825` dengan NDK 28.2.13676358.
- Sudah dibuat: benchmark script Windows/ADB, pinned tiny/base download+SHA-256, dataset count enforcement, device metadata capture, WER/RTF dan sampled peak RSS output.
- Belum terverifikasi: script belum dieksekusi end-to-end pada Windows + perangkat fisik pengguna dengan dataset gate manusia.
- Result: **PASS untuk syntax/build harness; BLOCKED untuk benchmark fisik**.
- Dampak: CP4 tetap BLOCKED dan T11 tetap TODO.

### T10-TRANSLATION-HARNESS-001 — Persiapan evaluasi 60 segmen
- Task: T10 / CP4; tanggal: 2026-10-08.
- Dibuat: `engine/translation/src/androidTest/java/app/subloka/engine/translation/MlKitTranslationBenchmarkTest.kt`, `engine/translation/src/androidTest/assets/t10_translation_fixtures.json`, `tools/t10_translation_review.py`, `tools/test_t10_translation_review.py`.
- Expected: 30 EN→ID + 30 ID→EN, tidak mengunduh model selama benchmark offline, ekspor CSV mentah, manual review, acceptance ≥27/30 tiap arah, nol error negasi/angka/nama material, serta median/p95 latency.
- Sudah diuji saat pembuatan paket: Python unittest `python -m unittest discover -s tools -p test_t10_translation_review.py`: 5 test PASS; parsing fixture: 60 ID unik, masing-masing 30 per bahasa. Hasil adalah pemeriksaan harness lokal, **bukan** hasil kualitas model.
- Belum diuji: kompilasi instrumented test pada repository/CI, inference pada perangkat fisik dengan mode pesawat, review manusia 60 output, hasil latensi/thermal.
- Eksekusi: unduh model dengan test `MlKitTranslationInstrumentedTest` secara online, aktifkan mode pesawat secara manual, lalu jalankan `MlKitTranslationBenchmarkTest`. Cari `RESULT_PATH=` pada log `SubLokaT10`; `adb pull` CSV ke `.t10-benchmark`. Buat review via `python tools/t10_translation_review.py init RAW.csv REVIEW.csv`, nilai semua status, lalu `python tools/t10_translation_review.py report REVIEW.csv --json SUMMARY.json`.
- Nilai audit ASR yang dilaporkan pengguna: Sony SO-03L/Android 11, corpus WER Base EN-clean 9.79%, ID-clean 28.61%, Tiny EN-clean 12.35%, ID-clean 44.14%; ID-clean 7 jelas/13 kurang jelas; Base jelas 13.22%, kurang jelas 36.18%; RTF Base rata-rata ID 1.026/1.071. Referensi 14 verified, 4 not reviewed, 2 uncertain. File mentah dan hash hanya berada di mesin pengguna; angka belum diverifikasi dari artefak mentah dalam repository.
- Result: **PREPARED** untuk evaluasi translation; CP4 **BLOCKED**, T11 **TODO**.


### T10-TRANSLATION-DEVICE-001 — Diagnostik readiness dan alur dua fase
- Task: T10/CP4; tanggal: 2026-10-08.
- Environment: Sony SO-03L, Android 11, PowerShell Windows, physical test user.
- Actual: `:engine:translation:connectedDebugAndroidTest` gagal di `MlKitTranslationBenchmarkTest.kt:54` dengan `expected:<READY> but was:<NOT_READY>`; `RESULT_PATH` tidak muncul karena test abort sebelum mengisi CSV. Error protobuf `sun.misc.Unsafe` hanya warning dependency.
- Interpretation: model translation belum siap pada saat tes dijalankan. Gradle connected test dapat uninstall APK selesai tes; ML Kit downloaded models pada instalasi lokal dapat terhapus saat uninstall. Penyebab kondisi user belum dipastikan, sehingga digunakan workflow yang tidak uninstall antarfase.
- Perbaikan yang disiapkan: `tools/t10_translation_device_benchmark.ps1` (`-Phase Prepare` saat online: build/install sekali + online readiness/smoke; `-Phase Benchmark` saat airplane+Wi-Fi off: run instrumented benchmark tanpa reinstall dan adb pull CSV). Hilangnya test APK atau ketidaksiapan model dilaporkan sebagai error, bukan inference PASS.
- Belum terverifikasi: eksekusi dua fase pada Sony, offline output 60 segmen, review acceptance, thermal; CI syntax/unit test perlu diperiksa pada workflow setelah push.
- Result: **FAIL** untuk benchmark instrumentasi sebelumnya (prasyarat NOT_READY), **PREPARED** untuk harness dua fase; CP4 tetap **BLOCKED**.


### T10-TRANS-DEVICE-RESULT-001 — 60 keluaran translation perangkat fisik (review provisional)
- Task: T10/CP4; tanggal: 2026-10-08; environment: Sony SO-03L Android 11/arm64, ML Kit Translation 17.0.3.
- Evidence: pengguna mengirim seluruh 60 baris CSV output perangkat (30 EN→ID, 30 ID→EN), 0 error engine tercatat. Precondition READY melewati alur dua fase setelah error `NOT_READY` sebelumnya. Trace perangkat/rekaman airplane-mode tidak diunggah; harness benchmark telah memeriksa `airplane_mode_on=1` dan `wifi_on=0` sebelum menjalankan test, berdasarkan skrip yang dipakai.
- Evaluasi AI *provisional* (pengguna merespons "review bagus", bukan sign-off tiap baris): EN→ID 27 ACCEPT, 3 MAJOR_MEANING_ERROR, 90.00%; ID→EN 25 ACCEPT, 5 MAJOR_MEANING_ERROR, 83.33%; 0 label NEGATION_ERROR/NUMBER_OR_NAME_ERROR pada kedua arah. Sampel bermasalah: `en-08, en-24, en-27, id-02, id-05, id-10, id-26, id-30`; contoh date/terminology `id-08` masih perlu tinjauan manusia.
- Device translation latency: median EN→ID 42.239 ms, p95 67.037 ms, first 700.778 ms; ID→EN median 39.378 ms, p95 52.802 ms, first 297.453 ms. P95 nearest-rank dan semua sampel termasuk warm-up; hasil tidak dapat diekstrapolasi langsung ke total durasi video atau thermal.
- Reproducibility: `tools/t10_translation_ai_draft.json` berisi digest kanonik dari source+translation 60 baris (`2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c`) serta delapan label error dan catatan ACCEPT. `python tools/t10_translation_review.py apply-draft .t10-benchmark/translation-results.csv .t10-benchmark/translation-review-ai-draft.csv` menolak dataset/prediksi berbeda, output yang sudah ada, dan engine error. Bukti data mentah tetap pada PC pengguna di `.t10-benchmark`; bukan commit repo.
- Evaluator lokal: 7 unit test PASS dan perbandingan hasil `apply-draft` dengan CSV review sebelumnya identik pada seluruh 60 baris; uji dilakukan di lingkungan Python pengembangan, bukan Android. Hasil laporan lokal `report` per arah: EN→ID PASS untuk kriteria angka *provisional*; ID→EN NOT_PASS.
- CI issue: T10 Engine Evaluation run `37767746650` memperlihatkan job `translation-device` FAIL, jobs `whisper-artifacts` dan `android-benchmark-binary` PASS. Workflow memanggil semua androidTest, termasuk quality benchmark yang hanya valid setelah model tersedia; workflow dipersempit ke smoke test. Fix butuh CI run berikutnya untuk verifikasi.
- Result: **Bukti inferensi translation 60/60 diterima sebagai laporan pengguna; kualitas ID→EN NOT_PASS, EN→ID PASS provisional; CP4 tetap BLOCKED**. Belum ada bukti review bilingual independen, ASR ID clean masih gagal, timestamp gate serta thermal/stabilitas belum diuji penuh.


### T10-ASR-STABILITY-001 — Android thermal / performance telemetry (harness disiapkan)
- Task: T10 / CP4; tanggal: 2026-10-08.
- Revision: commit yang menambahkan `tools/t10_asr_stability.ps1` (lihat riwayat GitHub); engine `whisper.cpp v1.9.4`, model `tiny/base` pinned SHA-256 dari `testing.md`.
- Expected: menjalankan `base` dalam bahasa Indonesia secara offline pada Sony SO-03L dalam pengukuran berulang sekitar 5 menit, tanpa menimpa baseline; menangkap `runs.csv`, `telemetry.csv` dan `summary.json` per sesi; sensor baterai dan sampled process RSS diberi label benar. Gagal aman jika perangkat/network/sensor/model tidak siap atau terlalu panas.
- Menunggu pelaksanaan di perangkat: `powershell -NoProfile -File tools/t10_asr_stability.ps1 -PreflightOnly` (pemeriksaan tanpa inference), kemudian `.\tools\t10_asr_stability.ps1 -RunMinutes 5 -Model base -Language id`. Pastikan baterai tidak panas sebelumnya, jaringan benar-benar mati, dan perangkat berada di permukaan berventilasi; hentikan bila muncul peringatan thermal.
- Output target: `.t10-benchmark/thermal-<timestamp>-<id>/summary.json`, `runs.csv`, `telemetry.csv`; semuanya diabaikan `.gitignore` dan tidak dipublikasikan otomatis.
- Acceptance evidence ini: kumpulkan actual per-run dan trend RTF serta suhu, identifikasi apakah terjadi thermal stop/performance degradation. Observasi suhu berasal dari `adb shell dumpsys battery` dalam °C; **bukan CPU/SoC die temperature**. RSS diperoleh melalui `pidof`/`/proc/<pid>/status`, bisa tidak tersedia/terlewat; jika kosong jangan klaim pengukuran RAM.
- Batas: ini *repeated short utterances*, bukan 10-minute video end-to-end. `COLLECTED_NOT_GATE_PASS` berarti file berhasil dikumpulkan, bukan aplikasi bebas OOM/ANR atau CP4 PASS. CI memeriksa syntax/script tanpa menjalankan perangkat; belum ada thermal actual dari Sony.
- Result: **IMPLEMENTED / DEVICE NOT_RUN**, gate CP4 tetap **BLOCKED**; tidak memulai T11.


### T10-ASR-STABILITY-ADB-001 — Windows native stderr regression
- Task: T10 / CP4; date: 2026-10-08; revision: commit yang menerapkan perbaikan native ADB stderr.
- Environment user: Windows PowerShell, physical Sony SO-03L Android 11 arm64; device airplane/Wi-Fi-off preflight. Model Whisper base Indonesian multilingual v1.9.4.
- Actual preflight: PASS, 30 WAV, battery 36.7°C. Actual benchmark: **ABORTED** setelah `whisper-cli: 1 file pushed, 0 skipped. 117.3 MB/s (27661368 bytes in 0.225s)`; `completed_runs=0`; output lokal `.t10-benchmark/thermal-20261008T120059Z-5a0b61/summary.json`. Tidak ada thermal/performance result yang dapat dinilai. Ini bukan crash engine atau threshold thermal.
- Penyebab kode: `Adb-Raw` menangkap stderr native memakai `2>&1` ketika `ErrorActionPreference=Stop`; pada Windows PowerShell 5.1 pesan transfer sukses dapat menjadi terminating ErrorRecord sebelum exit code diperiksa. Pembaruan memisahkan pesan stderr dari keberhasilan yang didasarkan pada exit code, melindungi probe `pidof` yang normalnya mengembalikan nonzero saat idle, dan tetap mempertahankan error native sesungguhnya.
- Sudah dibuat: regression script `tools/test_t10_asr_stability_adb.ps1` dengan mock Windows `.cmd` untuk ADB stderr exit 0/7 dan opsi `-AllowFailure`. Ditambahkan job CI khusus `windows-latest` menjalankan `shell: powershell`; parser PowerShell existing tetap berjalan.
- Actual hasil tes regresi: **NOT_RUN / CI PENDING** saat commit; pengujian fisik perbaikan juga **NOT_RUN** sampai hasil berikutnya diberikan. Jangan menyebut PASS sebelum workflow dan sesi perangkat berhasil.
- Next: cek job `asr-adb-windows-regression`, lalu jalankan kembali preflight dan benchmark 5 menit. Output lama disimpan terpisah; `CP4=BLOCKED`, `T11=TODO`.


### T10-ASR-STABILITY-ADB-002 — First Windows regression run, test-host exit issue
- Tanggal: 2026-10-08. Run: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37774711520.
- Actual Windows PowerShell 5.1 stdout: `PASS: native stderr on exit 0 ignored; exit 7 rejected; opt-in failure works; EAP restored.` setelah tiga assertion mock. GitHub Actions step tetap `failure` dengan exit 1, karena `$LASTEXITCODE` dari mock exit=7 dibiarkan tersimpan walaupun assertion berhasil.
- Koreksi: reset last native exit status dan `exit 0` di akhir regression test script setelah cleanup. **Perubahan koreksi belum diverifikasi CI hingga run berikutnya.** Harness perangkat utama tidak berubah pada koreksi ini.
- Result: regression assertions menghasilkan PASS text, workflow FAIL sebelum koreksi; tetap tidak boleh klaim full CI PASS. Sony thermal run tetap NOT_RUN setelah fix ADB. CP4 BLOCKED.


### T10-ASR-STABILITY-EXIT-001 — Run-1 transcript present / ADB ExitCode unavailable
- Task: T10/CP4. User device: Sony SO-03L Android 11 arm64, Windows PowerShell; tanggal 2026-10-08.
- Expected: 5 menit ASR repeated-utterance `base/id` offline, sampled RAM/suhu, status per-run jelas.
- Actual: `-PreflightOnly` PASS (`base/id`, 30 WAV, 36.0°C), setelah model+CLI ditransfer script menampilkan `Inference FAIL run=1, adb_exit=, result_exists=True`. Sesi `.t10-benchmark/thermal-20261008T121209Z-0766d8/summary.json` berstatus `ABORTED`, `completed_runs=0`, peak battery 36.5°C. Hasil inference `result.txt` nonempty di perangkat tetapi native ADB exit code tidak tersedia melalui ekspresi lama. Tidak ada bukti hasil RTF/RSS sesi ini atau thermal failure.
- Diagnosis kode: cabang fail membandingkan `$null -ne 0` dan menganggap exit tak tersedia sebagai kegagalan tanpa memisahkannya dari kasus transcript kosong.
- Perbaikan disiapkan: `Resolve-T10InferenceCompletion` dengan label `RESULT_PRESENT_EXIT_ZERO`, `RESULT_PRESENT_EXIT_UNKNOWN`, `RESULT_PRESENT_ADB_NONZERO`; wajib transcript nonempty untuk mencatat run; wait proses secara bounded, simpan log lokal saat hasil ambigu; tambahkan `unverified_adb_exit_runs` dan `completion_evidence` ke CSV/JSON. Status sesi `COLLECTED_WITH_UNVERIFIED_ADB_EXIT` bersifat diagnostik, **bukan PASS engine penuh**.
- Pengujian setelah patch: Windows mock regression CLI perlu berjalan di CI; Sony physical retest **NOT_RUN** hingga output baru diterima. Jangan menyimpulkan kestabilan thermal dari dua sesi ABORTED.
- CP4 masih BLOCKED; T11 TODO.


### T10-ASR-STABILITY-EXIT-002 — Parser regresi patch klasifikasi proses
- Run: https://github.com/ferdilpu-sudo/Subloka/actions/runs/37775966597, T10 Engine Evaluation; `android-benchmark-binary` FAIL sebelum build native karena PowerShell parser membaca `$RunNumber:` sebagai variable reference tidak valid.
- Diagnosis: bug format pesan helper baru, bukan kerusakan binary, model, dataset atau ketidakstabilan perangkat.
- Koreksi: gunakan `${RunNumber}:` dalam dua pesan `Write-Warning`. Hasil CI setelah koreksi: NOT_RUN pada saat pencatatan; tunggu run berikutnya. CP4 tetap BLOCKED.


### T10-ASR-STABILITY-5MIN-001 — Physical five-minute repeated-utterance evaluation
- Task: T10/CP4; tanggal: 2026-10-08; user-provided JSON `summary.json` lokal `.t10-benchmark/thermal-*/` pada Sony SO-03L Android 11, offline mode verified by scripted preflight (airplane=1/Wi-Fi=0), USB powered=true.
- Revision pengumpulan: script sebelum penambahan `result.exit` remote marker; engine whisper.cpp v1.9.4, Base multilingual SHA-256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`, manifest hash `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`.
- Expected: 5 menit ASR workload di fisik, data RTF/RSS/suhu dan status exit yang dapat diverifikasi.
- Actual: `elapsed_session_s=300.06`, `completed_runs=23`, `unverified_adb_exit_runs=23`, `stop_reason=null`, `status=COLLECTED_WITH_UNVERIFIED_ADB_EXIT`; median RTF=1.0539, p95 nearest-rank RTF=1.2304, peak observed RSS 378888 KiB (≈370 MiB). Temperatur baterai 36.5°C→39.2°C (puncak/akhir), +2.7°C; ambang 43°C tidak tercapai. Tidak ada thermal stop tercatat, tetapi tidak dapat menyimpulkan tidak ada throttle CPU tanpa metrik tambahan.
- Bukti: user-provided summary JSON in chat; CSV run/telemetry dan device/system log belum diinspeksi independen. `result.txt` nonempty pada tiap run menurut harness, tetapi `Start-Process.ExitCode` blank pada seluruh 23, sehingga verification kernel/ADB process completion belum tersedia. Jangan mengubah label menjadi PASS.
- Penafsiran: median RTF >1 berarti pipeline uji lebih lambat daripada realtime, termasuk startup binary/model per-run, ADB overhead dan sampling; tidak langsung membuktikan runtime end-user app. Sampled RSS bisa kehilangan peak; suhu baterai bukan suhu CPU dan USB power bisa memengaruhi pemanasan.
- Fix **dibuat tetapi belum diuji perangkat**: `New-T10RemoteInferenceCommand` menjalankan Whisper melalui Android sh dan menulis `result.exit` (nilai shell `$?`) yang dibaca kembali lewat ADB. Status `RESULT_PRESENT_REMOTE_EXIT_ZERO_ADB_UNKNOWN`, `RESULT_PRESENT_REMOTE_EXIT_UNKNOWN`, `RESULT_PRESENT_REMOTE_NONZERO` dibedakan; nonzero remote menghentikan sesi, selalu menuntut transcript nonempty. `summary.json` baru mencantumkan `verified_remote_whisper_exit_zero_runs` dan `unverified_remote_whisper_exit_runs`; unit/regression tests Windows dan POSIX shell menutupi nilai 0, nonzero, missing, malformed. Tidak memalsukan ADB exit status host.
- Result: **PERFORMANCE/THERMAL EVIDENCE COLLECTED, PROCESS EXIT UNVERIFIED; CP4 BLOCKED**. Next: CI parser/regression results lalu validasi singkat 2 menit sebelum uji lima menit terverifikasi.


### T10-ASR-REMOTE-EXIT-002 — Parser failure sebelum regression
- GitHub Actions https://github.com/ferdilpu-sudo/Subloka/actions/runs/37778559881; Windows job `asr-adb-windows-regression` FAIL pada parse `$LastRun:`, dan `android-benchmark-binary` FAIL pada validation syntax; tidak menyiratkan engine gagal.
- Koreksi: `throw ("Inference FAIL run={0}: ..." -f $LastRun, $remoteExit, $stderr)`, no engine/data changes. **Device retest NOT_RUN**, CI setelah koreksi belum diuji pada saat patch. Status CP4 BLOCKED.


### T10-ASR-STABILITY-REMOTE-001 — Remote Whisper inference exit 0 verified on Sony
- Date: 2026-10-08. Evidence type: user-supplied `summary.json` body from latest thermal run, not an independently retrieved device artifact. Physical Sony SO-03L Android 11 arm64; USB connected; airplane mode=1/Wi-Fi=0 as checked by harness.
- Revision: `163cbc8`; whisper.cpp v1.9.4 Base multilingual pinned model SHA256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`; dataset manifest SHA256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`.
- Command: `.\tools\t10_asr_stability.ps1 -RunMinutes 2 -Model base -Language id`. Actual: `duration_requested_minutes=2`, `elapsed_session_s=132.86`, 9 completed runs, `verified_remote_whisper_exit_zero_runs=9`, `unverified_remote_whisper_exit_runs=0`, `unverified_adb_exit_runs=9`, `stop_reason=null`, session status `COLLECTED_REMOTE_VERIFIED_ADB_UNVERIFIED`.
- Performance: median RTF 0.7021, p95 nearest-rank RTF 1.118, sampled peak VmRSS 378764 KiB (~369.9 MiB); battery 38.5°C initial, 39.0°C peak/last, rise 0.5°C, threshold 43°C never triggered; USB powered=true. Battery is not CPU temperature, RSS samples can miss short peaks.
- Expected verification: nonempty `result.txt` and on-device `result.exit=0` on each run. Actual according to harness JSON: **9/9 remote exits verified**, no missing markers. Windows ADB host process ExitCode unverified on all runs and must not be labeled as passing. This addresses the earlier `23/23` ambiguous exit statuses without retrospectively rewriting their evidence.
- Relevant CI commit `163cbc8`: T10 Engine Evaluation success https://github.com/ferdilpu-sudo/Subloka/actions/runs/37778750212, Android CI success https://github.com/ferdilpu-sudo/Subloka/actions/runs/37778750189.
- Limitations: only repeated short Indonesian utterances over 132.86s; not a sustained 5-minute remote-verified run, not a 10-minute video E2E, not direct CPU thermal or ANR test. RTF shift versus previous 5-minute run is **not paired or controlled**, so not evidence of performance improvement. Raw `runs.csv` and `telemetry.csv` not yet examined in this assessment.
- Result: **PASS: remote CLI exit-code verification for 9/9 runs; evidence collected for performance and battery-temperature proxy. CP4 remains BLOCKED** by Indonesian ASR WER 28.61%, translation ID→EN acceptance 83.33%, timing/resource/E2E and review remaining.


### T10-ASR-ERROR-AUDIT-001 — Indonesian clean reference/hypothesis text audit
- Date 2026-10-08; input CSV SHA256 `39a9570cd621d81c9607332c34a068fa83c48c4c142f3594d3243144eab08daa`, manifest SHA256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`; 120 paired Tiny/Base benchmark rows, 60 FLEURS dev fixtures. Original files uploaded by user; no WAV inspection in this step.
- Evaluator `tools/t10_wer.py` normalization reimplemented with exact Levenshtein alignment (tie-breaking only affects split S/D/I, not total WER). Check: Base ID clean **105/367=0.2861 micro WER**, 20 samples, errors S=82/D=7/I=16; Tiny ID clean 162/367=0.4414; Base EN clean 42/429=0.0979. Macro (mean segment WER) Base ID clean 28.07%, distinguish from micro WER 28.61% used by gate. ID Base wins 15 cases, ties 3, loses 2 against Tiny.
- Top 6 ID Base clean errors (by absolute word errors): `id-clean-07` 14; `id-clean-12` 10; `id-clean-02` 8; `id-clean-08` 8; `id-clean-17` 8; `id-clean-19` 8. Combined 56/105 errors (53.3%). Example `id-clean-19`: `21-20` misrecognized `0.1.220`. Other errors include distorted Aristarchus and omitted/mangled spoken phrases.
- Data integrity: 119 of 120 stored WER values match recalculation up to 4-decimal rounding. `base/en-challenging-06` exception: stored 0.2326 (10/43), recomputed 0.2093 (9/43) for provided reference/hypothesis text pair; audit why before any baseline amendment. Indonesian clean unaffected.
- Threshold: 367 tokens ×20%=73.4; maximum 73 edits; must remove at least 32 of 105 with frozen source set; no post-hoc reference edits or benchmark-only substitution/normalization allowed.
- Deliverable in chat: audit Excel (four sheets with 120 result rows) and CSV human review template (20 Indonesian clean) generated from uploaded artifacts. Review status initially `UNREVIEWED`; notes are heuristic, not audio evidence. New CLI helper `tools/t10_asr_error_audit.py` generates machine-readable summary and human-review CSV from unchanged inputs; new tests `tools/test_t10_asr_error_audit.py`, CI step added. Script and tests **not yet verified by GitHub Actions** at the time of writing.
- Missing evidence: 6 original WAVs `t10-audio/id-clean/id-clean-{07,12,02,08,17,19}.wav`; no phonetic/reference correctness judgement can be final until listened to. Actual audio not included in upload, no reason to assert mislabeled files.
- Result: **ASR quality NO PASS (28.61% >20%); error-priority audit ready; audio validation PENDING; CP4 remains BLOCKED**.


### T10-ASR-PRIORITY-WAV-001 — Audio signal check and human-listening handoff
- Source: user-uploaded ZIP `id-clean-priority-audio.zip` (SHA256 `c7eba760822a4cb9ae5db41a9a15df8925c4495d708725e25d93c13ae05f6533`), references `t10-dataset.json`, hypotheses `asr-results.csv`. Six files: `id-clean-{07,12,02,08,17,19}.wav`; WAV 16 kHz / mono / 16-bit PCM; durations match manifest within 0.01 s; none clip digitally.
- Acoustic RMS dBFS: 07=-24.1, 12=-35.0, 02=-41.2, 08=-22.4, 17=-24.0, 19=-23.5. Peak dBFS: 07=-7.7, 12=-9.5, 02=-24.2, 08=-5.8, 17=-4.3, 19=-4.8. Sample `02` anomalously quiet relative to this small selected set, not proof of low SNR. Sample `12` relatively quiet too.
- Manual-listening handoff artifact: self-contained offline HTML with 6 embedded WAV players, references and Tiny/Base hypotheses, reviewer statuses default `UNREVIEWED`, corrected-reference field, and CSV export; two listening-only gain versions +17.2 dB (02), +8.5 dB (12) with peak ≤−1 dBFS. A separate template CSV of 6 rows also starts `UNREVIEWED`. No external hosting or WAV added to repo. Audio words were **NOT verified by direct independent hearing** at this stage.
- The comparison is **diagnostic**, not CP4 pass: do not silently alter FLEURS labels/normalization/ASR or infer that gain will reduce WER. Next decision requires completed human listening statuses + exact corrected-reference evidence; if all 6 reference texts match, plan paired test original vs gain before modifying production pipeline.
- Baseline quality remains `base/id/clean` WER 28.61% >20%; CP4 BLOCKED, T11 TODO.


### T10-ASR-LISTENING-USER-001 — Signed-off listening statuses? Partial CSV reviewed, not full approval
- Date: 2026-10-08; source: user-uploaded CSV `subloka-t10-six-wav-listening-review.csv` (SHA256 `88df1defbbf4d3a3f2b86dbc84980921617d18ac29464531afdc6e67a4464576`), not an independently retrieved WAV transcription. CSV schema includes sample/review_status/corrected_reference/listening_notes/reference_fleurs/hypothesis_base/hypothesis_tiny/wer/rms/gain/wav_sha256.
- Exact status: `id-clean-07=AUDIO_AMBIGUOUS`, note "cara berbicara tidak jelas, tidak baiknya jangan dipakai"; `id-clean-12=AUDIO_AMBIGUOUS`, note "cara mengucapkan kata tidak jelas, sebaiknya jangan dipakai"; `id-clean-08=REF_MATCHES_AUDIO` with no proposed reference correction. Remaining `id-clean-02`, `id-clean-17`, `id-clean-19` are **UNREVIEWED**, despite accompanying notes respectively "pengucapanya tidak jelas, sebaiknya jangan dipakai", "pengucapan ambigu, sebaiknya jangan dipakai", and "pengucapan tidak jelas, sebaiknya jangan dipakai".
- Summary status: 2/6 AUDIO_AMBIGUOUS, 1/6 REF_MATCHES_AUDIO, 3/6 UNREVIEWED, 0/6 REF_NEEDS_CORRECTION; `corrected_reference` blank for all six. There is **no justification to edit golden reference**. The user's intention to exclude clips is a recommendation for future dataset-quality assessment, NOT a change to the frozen benchmark. Only finalized status is authoritative for review counts.
- Benchmark provenance: current FLEURS clean subset was selected by closeness to **median clip duration**; this criterion does not guarantee clarity. Post-hoc exclusion of WER-heavy recordings would bias CP4 benchmark. Retain original unmodified model outputs and samples; archive any future cleaner, predeclared benchmark as a separate version and label noncomparable.
- Scope: listener status reviewed; six WAVs/CSV previously inspected for waveform and format only. No subsequent independent listening or changed model evaluation is implied.
- Result: **USER LISTENING REVIEW PARTIALLY FINALIZED; BENCHMARK BASELINE UNCHANGED; CP4 BLOCKED/T11 TODO**. Next: ask explicit status decision for three UNREVIEWED rows; paired original/gain A/B remains diagnostic and should be recorded separately.


### T10-ASR-LISTENING-FINAL-001 — User-confirmed status update (no post-hoc gate edits)
- Source: user-uploaded `subloka-t10-six-wav-listening-review.csv` SHA256 `88df1defbbf4d3a3f2b86dbc84980921617d18ac29464531afdc6e67a4464576`; explicit chat confirmation dated 2026-10-08 that `id-clean-02, id-clean-17, id-clean-19` are `AUDIO_AMBIGUOUS`. Final preserving original CSV schema SHA256 `ed4eb43e80db1b699a2af56f0cafef6daa6981592545e54c21d5fdaafd4af0aa`.
- Final six statuses: AUDIO_AMBIGUOUS `07,12,02,17,19` (5); REF_MATCHES_AUDIO `08` (1); UNREVIEWED 0; corrected_reference all empty. `.agents/evidence/t10-asr-listening-review-final.json` is versioned decision evidence, **not** a new gold transcription.
- Explicit separation: **5 listener-ambiguous examples remain in frozen baseline**, including all 20 Indonesian clean entries and the existing hypotheses. Official Base ID-clean WER remains 105 errors / 367 reference words = 0.2861; CP4 still BLOCKED.
- Gain-only A/B test harness created for low-amplitude `02` and `12` (both user-labeled ambiguous): pinned waveform hashes and no overwrite of original WAV, gain +17.2/+8.5 dB respectively, 1 dBFS peak headroom. Runs 4 inference trials with same Whisper Base and immutable reference; Android code verified via file `result.exit`. Each run records hypothesis, measured runtime, battery temp, diagnostic WER, and exit statuses into a unique git-ignored session folder.
- Planned interpretation: paired hypothesis differences are indications for further experiments, not evidence that model reliably improves across unseen Indonesian speech; fixed sample-set is just TWO recordings and review marks reference reliability limited. No filters/noise reduction or hidden sample exclusion applied.
- Current phase **TOOL ADDED, CI RUN PENDING, PHYSICAL DEVICE NOT_RUN**. Next: verify CI; user may run preflight + device A/B and share `summary.json` to continue T10 ASR WER strategy.


### T10-ASR-GAIN-AB-SONY-001 — Paired amplitude-only diagnostic (user-reported result)
- Date: 2026-10-08; input: JSON body from Sony SO-03L experiment in chat; machine-readable **aggregate without hypotheses** archived in `.agents/evidence/t10-asr-gain-ab-sonyoct08.json`. Not an official CP4 dataset update; raw device-generated `summary.json`/`runs.csv` remain on user's workstation.
- Device and engine: SO-03L Android 11, offline_verified=true; Whisper Base pinned SHA256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`; frozen manifest SHA256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`; volume-adjusted WAV hashes are separately recorded in JSON evidence.
- Execution evidence: 4 runs completed, `remote_whisper_exit=0` and `host_adb_exit=0` for all four, status `DIAGNOSTIC_COLLECTED_NOT_CP4`, stop_reason null; battery 37.7°C initial, 38.5°C final, no thermal stop.
- id-clean-02: original WER 0.4444 vs gain +17.2 dB WER 0.4444, different hypothesis, Δ=0.0000; RTF original 0.8154, gain 0.8822.
- id-clean-12: original WER 0.6667 vs gain +8.453 dB WER 0.7333, different hypothesis, Δ=+0.0666 (gain worse); RTF original 0.8578, gain 0.8239.
- Note `WER` above is evaluated against **original immutable but reviewer-AUDIO_AMBIGUOUS references**; should not be interpreted as true accuracy of these 2 recordings or as a full-sample benchmark. No randomized repetitions, n=2, performance timing confounded by sequence and startup.
- Outcome: **NO OBSERVED ACCURACY BENEFIT FROM GAIN-ONLY** for this narrowly defined comparison; do not introduce automatic gain into engine as a proven WER fix. Freeze `asr-results.csv`, `t10-dataset.json`, original audio and CP4 thresholds. Full official ID-clean Base 105/367=28.61% WER and translation ID→EN 83.33% remain NOT_PASS. CP4 BLOCKED/T11 TODO.


### T10-ASR-DECODE-AB-001 — Full frozen ID-clean beam search comparison (harness only)
- Task: T10; date: 2026-10-08. Planned device: physical Sony SO-03L Android 11 arm64, airplane mode with Wi-Fi off. Input: 20 original FLEURS Indonesian clean WAVs (manifest SHA256 `9c5da3a324a23c3097fe72a1eb6683cee63d19a6ddad5d527f22ccdd5ad9e444`), previously measured original `asr-results.csv` SHA256 `39a9570cd621d81c9607332c34a068fa83c48c4c142f3594d3243144eab08daa`, Base model pinned SHA256 `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe`.
- Hypothesis: changing only Whisper CLI beam size via `-bs 1` might change accuracy/runtime relative to previous default. **Not an established improvement**. Both control and variant use `-m model.bin -f input.wav -l id -nt -ng -nfa -otxt -of result`; experiment alone adds `-bs 1`. All 20 samples in sorted order, within-sample AB/BA counterbalance, 40 inference runs total if completed.
- Safety/integrity: preflight model & source/baseline hashes, 20 exact IDs, WAV format; no reference edits / normalization edits / gain; device arm64, airplane/Wi-Fi-off, battery initial below 40°C. Per-inference battery monitoring every ~2s; at >=43°C attempt to terminate only the recorded whisper CLI PID, halt and preserve partial diagnostic evidence; no "PASS" when a run cannot verify both remote CLI and host ADB exit 0 and nonempty transcript.
- Operator commands: `python tools/t10_asr_decode_ab.py --preflight-only`; pilot `python tools/t10_asr_decode_ab.py --max-pairs 3`; after cooling/resumption `python tools/t10_asr_decode_ab.py --resume .\.t10-benchmark\decode-ab-<id>` to finish. New directory `.t10-benchmark/decode-ab-<utc>-<nonce>/summary.json`, `runs.csv`. Data not committed or uploaded automatically; no hidden file overwrite. A resumed session refuses mismatched dataset, audio, model, CLI binary, or device serial.
- Summary labels `PARTIAL_EXPERIMENT_NOT_CP4`, `COMPLETE_EXPERIMENT_NOT_CP4`, or `ABORTED_RESUMABLE`; even if candidate diagnostic micro-WER <=20% the official frozen 105/367=28.61% baseline remains unchanged. Report pair count and control comparisons, changes in hypothesis, run RTF and battery. The existing five user-marked `AUDIO_AMBIGUOUS` clean clips remain in scoring; do not use this test to remove them after the fact.
- Tests: Python pure unit regression `tools/test_t10_asr_decode_ab.py` integrated into GitHub Actions. **Actual result: NOT_RUN (CI and physical tests pending)** at code submission. Do not claim beam size 1 is better or gate passed without independent device results.
- Outcome T10 CP4: **BLOCKED**; translation ID→EN 83.33% still misses target >=90%, full video E2E and thermal gates outstanding; T11 TODO.


### T10-ASR-DECODE-PILOT-001 — Device pilot negative accuracy delta, operational metadata pending
- User reported `analysis` only: `paired_samples=3`, `runs_collected=6`, `paired_reference_words=53`, control word errors 15 vs candidate -bs 1 errors 17, delta +2/53=3.7736 percentage points. Control micro-WER 0.2830188679, candidate 0.3207547170.
- Per-clip errors control→beam1: `id-clean-01 4→4`, `id-clean-02 8→9`, `id-clean-03 3→4`. 3/3 text hypotheses differ, 3/3 control exactly match archived baseline hypotheses. Control RTF 1.2004/1.1327/1.2877; beam1 RTF 1.1973/1.3249/1.0674 (order listed 01/02/03). Variance prohibits robust runtime conclusions.
- Actual user text did not include `summary.status`, `stop_reason`, `battery_last_c`, `events`, or raw `runs.csv`. Six recorded runs alone do NOT prove thermal condition or no exception at session end. Need metadata to decide safe resume; no thermal check claimed PASS from missing data.
- Existing code tests from `b3fda1c`: GitHub Actions T10 Engine Evaluation PASS https://github.com/ferdilpu-sudo/Subloka/actions/runs/37796038607; Android CI PASS https://github.com/ferdilpu-sudo/Subloka/actions/runs/37796038850. No code changed in this evidence-only commit.
- Result: 3-pair **diagnostic pilot shows NO improvement from beam1**; remain underpowered to reject variant for entire 20-sample dataset. Never trim ambiguity-marked ID-clean clips to improve gate. No production decoding change or CP4 gate PASS. Next: full summary status, thermal and stop_reason; if safe, resume same session in stages (`--max-pairs 4`). CP4 BLOCKED / T11 TODO.


### T10-ASR-DECODE-7PAIRS-001 — Paired accuracy tie, metadata not available
- 2026-10-08, user transcript via PowerShell `summary.analysis` with seven matched pairs after `--resume --max-pairs 4` (new four inferred from prior 3-pair aggregate): control 32 errors, beam1 32 errors, micro-WER 0.24806201550387597 each (129 reference words), delta 0. Relative to first 3: additional 4 pairs add 17 control edits and 15 beam1 edits over 76 reference words. No hypothesis/per-clip values for those four submitted.
- Evidence committed as `.agents/evidence/t10-asr-decode-7pairs.json` (provenance: user-provided excerpt, not independently pulled device `runs.csv`). Do not interpret seven-pair 24.81% as official CP4 full-set baseline (still 105/367 edits, 28.61%) or statistically justified engine change.
- Remaining tests: 13 pairs / 26 runs. Operational blocker to resume safely: missing latest `summary.status`, `summary.stop_reason`, `summary.battery_last_c`, `summary.events`. Require healthy partial status, null stop reason, and cooldown before next staged 4-pair device run. Previous 3-pair 39.2°C end is stale for this session.
- Result: diagnostic **TIE 32/129 vs 32/129**; T10 active; CP4 BLOCKED; T11 TODO.


### T10-ASR-DECODE-11PAIRS-001 — Continued Sony decoding A/B, limited result
- Source: user PowerShell output showing `PARTIAL_EXPERIMENT_NOT_CP4`, empty stop reason, preflight SO-03L offline battery 30.2°C, 8 additional run lines (`id-clean-08`–`id-clean-11` each default and beam1), post-stage battery 31.0°C, stop threshold 43°C. Device-produced original `summary.json`, `runs.csv` were not uploaded; evidence is the pasted console excerpts only. Machine-readable transcription of claims: `.agents/evidence/t10-asr-decode-11pairs.json`.
- New pairs errors default/beam1 by sample: `08=8/7` (18 reference words), `09=7/6` (20), `10=1/2` (19), `11=0/0` (17), total 16 vs 15 over 74 words. Per-condition RTF original default/beam1: `08 .991/.790`, `09 1.029/.822`, `10 1.016/.814`, `11 .963/.768`; don't overgeneralize timing across runs/thermal circumstances.
- Cumulated 11 pairs (22 inference): 203 reference words, default 48 edits (23.6453%), beam1 47 (23.1527%), delta -1/203 = -0.4926 percentage points. Still 9/20 pairs untested, no generalizable beam1 WER superiority from partial evidence; do not promote candidate.
- Safety: session partial/not aborted, stop_reason empty, battery last 31.0°C, 43°C threshold not reached; **battery proxy is not CPU temperature**. Recheck device fresh before stage 12–15. If new preflight fails or phone is hot, pause; use no assumption that past 31°C guarantees current conditions.
- Official gate remains unchanged: 20-sample frozen Base Indonesian clean WER 105/367=28.61% >20%; translation ID→EN 25/30 <27/30; E2E gates not finished; CP4 BLOCKED and T11 TODO.


### T10-ASR-DECODE-15PAIRS-001 — User 15-pair aggregate, 5 pairs pending
- Sony terminal excerpt: `PARTIAL_EXPERIMENT_NOT_CP4`, no stop reason, last battery 30.2°C. Analysis: `paired_samples=15`, `paired_reference_words=270`, default `control_errors=72` and `control_micro_wer=0.2666666667`, candidate `beam1_errors=73` and `beam1_micro_wer=0.2703703704`, delta `+0.0037037037` (beam1 0.37 percentage points worse). User-pasted aggregate, NOT independent raw CSV review; machine-readable copy and provenance: `.agents/evidence/t10-asr-decode-15pairs.json`.
- Against 11 pairs (48/47 edits over 203 words), the subsequent 4 pairs (id-clean-12–15) account for **24 default vs 26 beam1 edits over 67 words** (derived, not per-sample observation). 30/40 inferences implied by complete 15 pairs; 10 inferences/5 pairs remain.
- Latest recorded battery reading is a proxy, not CPU thermal gate. Run fresh preflight and use same session resume `--max-pairs 5` only while device cool/offline; do not claim new script run until user provides result. No production decoder change, no sample exclusion or reference editing. Official CP4 Base ID-clean WER remains 105/367=28.61% >20%; CP4 BLOCKED.

### T10-ASR-DECODE-20PAIRS-001 — Complete paired frozen subset result (user report)
- Final user terminal excerpt: `status=COMPLETE_EXPERIMENT_NOT_CP4`, empty stop reason, `battery_last_c=30.7`; `paired_samples=20`, `paired_reference_words=367`, `control_errors=105`, `beam1_errors=110`, default WER `0.28610354223433243`, beam1 WER `0.2997275204359673`, `beam1_minus_control_micro_wer=0.013623978201634877`, `control_matches_archived_hypothesis=20`. Evidence summary: `.agents/evidence/t10-asr-decode-final-20pairs.json` (user supplied excerpt; full session JSON/CSV not uploaded).
- Reproducibility: all 20 default hypotheses match archived baseline text exactly; beam1 5 extra word errors on same 367-word, 20-clip frozen clean-ID set. This is **+1.3624 percentage points worse** for beam1, not a gain. Compared to 15-pair data, remaining 5 yielded default +33 and candidate +37 errors in 97 ref words (aggregate subtraction). No per-run thermal, RTF, or hypotheses from last five were provided, so no speed or CPU-temperature conclusion.
- Final scoped verdict: **-bs 1 NOT SELECTED for v1 ASR accuracy**, keep default. All five listener-ambiguous recordings remain in benchmark. Results come from single paired trials and frozen references, not independently established general-population accuracy. Original CP4 Base ID-clean WER remains 105/367=28.61%, target <=20%, thus **FAIL/BLOCKED**. Translation and 10-minute app E2E gates also outstanding; T11 TODO.
- Follow-up: if needed request local `runs.csv` and complete `summary.json` for audit or timing; do not require rerunning completed 20-pair experiment. Prioritize translation reviewer gate, E2E performance and a predeclared separate ASR improvement plan, not endless decoding tuning on the same frozen set.


### T10-TRANSLATION-HUMAN-QA-001 — Authentic device output and independent bilingual decision handoff
- New testable tool `tools/t10_translation_human_qa.py`, whose canonical thresholds/status vocabulary remain in `tools/t10_translation_review.py`. It does **not** relabel/replace the original model outputs. Workflow: `prepare` from original local offline ML Kit CSV -> 60-row handoff with blank `human_status`, locked device output columns, provisional AI labels **only when output digest matches** `tools/t10_translation_ai_draft.json`; `finalize` after every bilingual reviewer decision, with attestation, evidence SHA hashes and original data integrity checks. Raw session remains local/gitignored.
- Controls: reject missing/mismatched fixture IDs or original source_text, broken 30+30 directions, changed raw CSV, tampered source/translation/latency/error rows, changed AI labels, incomplete review, absent notes on rejection or disagreement, no named reviewer/attestation, or any overwrite of finalized evidence. Outputs signed self-attestation and direction quality report; no hidden acceptance adjustments. Guardrail: declared reviewer identity **not authenticated by script**, human judgment still requires external verification, and this result alone cannot pass CP4.
- Unit tests `tools/test_t10_translation_human_qa.py` include 9 regression scenarios; GitHub Actions T10 Engine Evaluation automatically runs them. Real human review / physical translation model rerun **NOT PERFORMED in this step**. AI-only provisional 27/30 EN→ID, 25/30 ID→EN is not human-certified and remains NOT_PASS for ID→EN.
- Scope: diagnostic quality-only handoff, no source fixture edits, ML Kit code edits, model change, benchmark threshold edit, ASR beam experiment change, or E2E gate override. CP4 BLOCKED / T11 TODO.


### T10-TRANSLATION-AI-RECHECK-60 / USER-REQUESTED READABLE REVIEW (NOT HUMAN)
- Source: full 60-row archived Sony ML Kit output in prior conversation; model output/source canonical digest confirmed `2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c` in raw archive and AI-labelled review. Local mounted raw CSV SHA `2a12e1aa07a5126f44e168522d147908c08b25121e6ce468491e4e9143038818` differs from **user reported device raw CSV SHA** `f135ec8bf749d0609197137e54691170047d3336b2d246a9f89dd0689cb5de6a`, so only **canonical source+translation identity** is verified; no exact raw-byte equivalence claim. Source model text is not overwritten.
- 60 AI-audited pairs: 27/30 accepted EN→ID; 24/30 accepted ID→EN (vs prior AI draft 25/30). Nine semantic errors: `en-08 en-24 en-27 id-02 id-05 id-10 id-17 id-26 id-30`; 15 accepted with warnings, 36 accepted without detected material issue. Only changed AI label is `id-17`: English output retained Indonesian `Peron four` instead of `platform four`, confusing for English-only viewers. The classification is contestable (medium confidence); reviewers should validate rather than assume agreement. Full diagnostic summary `.agents/evidence/t10-translation-ai-provisional-recheck-60.json`.
- Outputs created for user in this ChatGPT conversation (not versioned): human-readable HTML cards/filter/search, four-sheet XLSX, machine-readable provisional CSV/JSON. They are **NOT human-review signoff** and must not be imported to `human_status` as if manually reviewed. Artifacts preserve every original source and translated output, explanation and examples separate. Workbook formula inspection found EN→ID 27/30 and ID→EN 24/30, error scan none.
- Human review remains pending; ML Kit model is not patched and cannot be declared better without rerun. Original ASR official 105/367 WER and other gates remain BLOCKED. Next: independent bilingual review if available, or advance unblocked E2E benchmark/engineering without spoofing reviewer.

### T10-TRANSLATION-USER-ACK-001 — Confirmation not a formal signed QA
- 2026-10-09: User says `sudah saya review. review saya sama dengan review ai` concerning delivered readable AI semantic audit. Capture precise provenance as `.agents/evidence/t10-translation-user-acknowledgement.json`. This supports that the user has reviewed and agrees with the AI report, but does **not** establish whether every 60 row was individually inspected or that the reviewer is independent bilingual / authenticated.
- Agreed AI provisional report remains 27/30 EN→ID, 24/30 ID→EN (9 material errors, including the extra `id-17` case compared to earlier AI draft). `human-review.csv` sign-off from `tools/t10_translation_human_qa.py` NOT_RUN/NOT_VERIFIED; no human attestation created and no CP4 pass. Source/output digest held constant; no model output regrading by code.
- T10 still BLOCKED on ID→EN translation, Base ID-clean ASR 28.61% versus 20% gate, and missing real 10min in-app video E2E thermal/resource evaluation. Next prioritize actual fix/test or E2E independent of review paperwork.


### T10-TRANSLATION-REVIEW-USER-SCOPE-002 — 60/60 explicitly self-attested
- The user explicitly clarified **"saya review 60"** and already reported agreeing with the AI audit. Mark **60/60 inspected per user self-report**, replacing earlier uncertainty of whether 9/60 or 60/60 were reviewed. Primary record updated in `.agents/evidence/t10-translation-user-acknowledgement.json`, not a new duplicate scoring source.
- Expected QA judgment unchanged: EN→ID 27/30 acceptable, ID→EN 24/30 acceptable, 9 major issues, historical earlier draft 25/30 for ID→EN retained as history. There is no evidence of `finalize` tool execution, completed signed CSV, external audit of reviewer independence, or objectively independent review of all 60; **do not claim those gates passed**.
- Review coverage recorded; formal reviewer signoff is not generated. No app/model/fixture/benchmark changes. Gate CP4 BLOCKED due ID→EN 80% vs >=90%, Base clean Indonesian WER 28.61% vs <=20%, and pending 10-min actual video E2E.


### T10-TRANS-FIDELITY-STATIC-001 — Pure Kotlin conservative translation warning signal
- `TranslationFidelityGuard.kt`: pure local diagnostic API; categories `NUMBER_TOKEN_MISMATCH`, `NEGATION_POSSIBLY_DROPPED`, `PROHIBITION_POSSIBLY_WEAKENED`, `TEMPORAL_CONTRADICTION`, `GENDER_ASSUMPTION`, `POSSIBLY_UNTRANSLATED_TERM`. Does not rewrite ML Kit output and doesn't certify semantic correctness. False positives and false negatives intentional; e.g. gender `dia` can be clear from names/context, and source numbers spelled as words are not fully parsed.
- 15 Kotlin unit test functions in `TranslationFidelityGuardTest.kt`; local independent `kotlinc` compilation with JUnit stubs executed **15/15 PASS**; a separate **real Gradle** `:engine:translation:testDebugUnitTest` was added to Android CI and must be checked for PASS on actual commit (do not equate standalone stub harness with Android CI).
- On previously archived 60 translations, the diagnostic flagged `id-01,id-02,id-09,id-10,id-17,id-24,id-30`: **four** overlap with nine material human-agreed review errors, **five** reviewed material issues missed, **three** warning-only accepted outputs flagged. Summary (derived from old known 60, not unbiased evaluation) in `.agents/evidence/t10-translation-fidelity-guard-static.json`. Does not detect subtle referent, active/passive, slower/later, quiet/calm, deliver/send, or translation into number words robustly.
- Scope adherence: no `MlKitOfflineTranslator` or instrumentation benchmark output changes; no frozen fixture edits; no signoff, CP4, model/hash, or ASR updates. A true ID→EN gain must be measured on a new predeclared unseen set and a separately recorded physical ML Kit/alternative model experiment, rather than inferring acceptance gains from warning counts.


### T10-TRANS-STRATEGY-AB-001 — Predeclared two-line offline translation A/B
- New fixture `t10_translation_strategy_ab_fixtures.json` (60 new authored source paragraphs, 30 each language, exact two nonblank newline-separated sentences). 0 identical whole-source texts against original `t10_translation_fixtures.json` when case-folded; source fixture is deliberately NOT the original CP4 gate; it is NOT an independent blind test once exposed to implementation.
- New device instrumentation `MlKitTranslationStrategyABTest`: ML Kit offline model unchanged; `whole` vs `linewise` two-call source segmentation. Exactly 60 paired outputs / 120 CSV rows / 180 ML Kit calls with AB/BA alternation. Calls remain offline after model preparation. Battery proxy initially <40C, active gate >=43C, 10min diagnostic elapsed guard. Device test raw separate and gitignored; no production Translator changes. Recorded latency per variant includes both SDK calls for candidate. Windows helper `tools/t10_translation_device_benchmark.ps1 -Phase Strategy` reuses preflight checks, unique destination (refuses overwrite), new result marker and outputs SHA.
- New `tools/t10_translation_strategy_ab_review.py`: raw/fixture fingerprint and exact source/output/strategy order checks, pairing complete, rejects original benchmark substitutions, duplicates, missing/bad timestamps, invalid battery data, changed reviewer-output columns; creates accessible browser HTML (60 side-by-side source cards, decisions blank, export/import CSV) and immutable session hashes. Reporter refuses any of 120 ungraded rows, requires rejection explanations, compares paired ACCEPT/loss, critical errors and p95 end-to-end latency. It never declares CP4 PASS, nor authenticates reviewer independence.
- 15 new Python unittest scenarios in `tools/test_t10_translation_strategy_ab_review.py`: fixture isolation, pairing, raw identity, HTML escaping, blank review, positive/negative result, added critical error, latency, tampering, thermal guard and provenance. Workflow T10 Engine Evaluation runs these and Android CI continues compiling new AndroidTest Kotlin. Device experiment and human ratings **NOT PERFORMED yet**. No quality uplift can be claimed from harness creation.
- Pre-registered thresholds: 27/30 per direction for candidate, net +3 accepted per direction, no newly created critical negative or number/name error, candidate p95 <=2.5x control p95 each direction, then follow-up truly unseen independent QA before production. `.agents/evidence/t10-translation-strategy-ab-preregistered.json`. Original 60 CP4 results and ASR WER unchanged; CP4 BLOCKED, T11 TODO.

### T10-TRANS-STRATEGY-AB-DEVICE-REPORT-001 — Physical result file fetched, not yet scored
- Received user's successful Sony experimental log: `Time: 9,188`, `OK (1 test)`, instrumentation code `-1`; ADB pull of **27,616 bytes** at original path `.t10-benchmark/translation-strategy-ab-results.csv`, local device raw SHA256 `50E612EC7EC41D37DE1E520650F1C5F90343267856BFE0C6F44AE0D27991353F`. This is user's console report, not independently fetched file; recorded evidence `.agents/evidence/t10-translation-strategy-ab-device-captured.json`.
- Next validate with `tools/t10_translation_strategy_ab_review.py init` in a new gitignored session. It rejects incomplete 120 rows or changed source/fixtures and creates local browser cards. Ask user to **upload original CSV** so assistant can perform AI-provisional 120-variant review and build a readable report, without claiming an independent human review or changing device raw, baseline labels, or CP4.
- Do not assert experimental winner or timing/safety pass beyond successful instrumented test and raw pull. Device experiment is NOT actual ten-minute video E2E. Official gates unchanged: EN→ID 27/30, ID→EN 24/30, ASR 28.61%, CP4 BLOCKED / T11 TODO. `251f9cb` Android CI and T10 Engine Evaluation both completed successfully before this device output.


### T10-TRANS-PARAGRAPH-AB-REVIEW-002 — Complete 120-row reviewer CSV received and analyzed
- Reviewed artifact SHA `516ca5d8967aefa7046db65e53fb1788ef7267bb48f7f34ada48eb72d20018a9`; content is 120 graded variant rows, 60 paired source paragraphs (30 each language), AB/BA order and call counts valid, zero error cells, every failed judgement justified. It is NOT the earlier 27,616-byte raw device CSV; historical raw SHA `50E612EC7EC41D37DE1E520650F1C5F90343267856BFE0C6F44AE0D27991353F` cannot be independently rehashed here and exact frozen NEW fixture source identity must be verified separately on raw-device export. Structural checks PASS, raw-byte provenance pending.
- Results from uploaded statuses: ID→EN whole=21 ACCEPT, linewise=21; EN→ID whole=22 ACCEPT, linewise=22. 0 wins / 0 losses, 58/60 **identical model output strings**; the 2 changed outputs `id-ab-17`/`en-ab-17` remain ACCEPT in both. 34 rejected *rows* = 17 rejected matched paragraphs, including one number/name error ID and one negation error EN in both; no candidate-only critical errors. User review status is provided but independently verified bilingual signoff was not authenticated from this CSV.
- Paired timing ID→EN medians 58.3065 vs 76.9305ms; p95 85.072 vs 97.048ms, ratio 1.1408. EN→ID medians 52.117 vs 68.8505ms; p95 76.531 vs 86.453ms, ratio 1.1296. Candidate slower on 56/60 sources. First whole run 563.170ms outlier; avoid general thermal/stability claims from 36.0°C battery proxy.
- Predeclared >=27/30 and >=+3 net ACCEPT *per direction* both NOT MET, thus **do not promote linewise**. Evidence of closed diagnostic at `.agents/evidence/t10-translation-strategy-ab-review-complete.json` (not a new independent physical benchmark, not a CP4 gate). Readable 60-card HTML/XLSX and full JSON distributed as conversation artifacts; no raw CSV or source text committed. Existing translation source/engine/code and frozen historical CP4 remain unchanged.
- Status: **T10/CP4 BLOCKED, T11 TODO**. Next real 10-minute in-app video E2E testing with thermal/RAM/crash instrumentation or a genuine new alternate offline translation engine tested on an independently authored holdout, not further repeated segmentation optimization on these 60.


### T10-VIDEO10-MEDIA-STAGE-001 — App-process real video ingest/PCM diagnostic, NOT E2E
- **Why limited:** production `SubLokaApp.kt` processing flow still demo; app does not yet perform production Whisper ASR, generated translation, subtitle layout or media export. T11–T14 are TODO while CP4 blocked. The T10 video10 harness is deliberately scoped to real app-package T09 media inspect, source fingerprint verification and full PCM decode. Never call its PASS a full-app E2E, never replace ASR resource measurement with PCM decode performance.
- New app instrumentation `RealVideoTenMinuteMediaTest` loads a real 600–900s video file placed only in its app-specific external files, uses public `AndroidMediaSource`, extracts real codec / duration / dimensions, hashes original video before and after, streams PCM without retaining raw buffers, requires last PTS within 5s of video duration and no truncation, samples memory `Debug.getPss` and Java heap, battery temperature sensor every >=2s. Requires initial battery <40C and aborts >=43C, protects 20min in-decoder wall time, records failures in metadata-only JSON even when assertions fail.
- Host `tools/t10_video10_media_device.ps1` phases Prepare/Run: builds and installs app debug/test APK, then requires airplane=1/WiFi=0 and actual MP4 file, hashes original, pushes to scoped app test dir, launches exact test with 25min host watchdog, pulls unique JSON on success OR failure, requests removal of temporarily pushed media. No raw video in repo. INSTALL -r may replace an existing debug APK; encourage backup of valuable local project state before Prepare.
- Reviewer script `tools/t10_video10_media_review.py` ties SHA host=before/after Android and size, validates exact video/audio metadata and 600-900s duration/PCM PTS, sampled peak process PSS not absolute peak, battery temperature not CPU die; outputs `MEDIA_STAGE_PASS_NOT_FULL_E2E`, always `CP4 BLOCKED`. 16 synthetic JSON validator unit tests `tools/test_t10_video10_media_review.py`, not physical device evidence. CI compile `:app:assembleDebugAndroidTest` and PowerShell parser+16 tests. Preregistered technical criteria `.agents/evidence/t10-real-video-media-stage-preregistered.json`.
- Required Sony evidence: report JSON + host-preflight JSON + test console logs + local video SHA, all stored in gitignored unique session; do not commit user's private raw video, no credential or health data. Unperformed until physical source supplied. Source SHA stable, PCM stage pass, no OOM in one run and sampled PSS provide **only media stage** facts; full E2E thermal/RAM/ASR/translation/render/export remains missing. T10 ACTIVE, CP4 BLOCKED, T11 TODO.


### T10 VIDEO10 / Windows PowerShell 5.1 encoding regression / 2026-10-10
- Native WinPS5 user parse error BEFORE Prepare: reserved `<` at 125, unterminated string at 202, cascading missing braces. Source contained one UTF-8 U+2013 en dash without BOM. PowerShell 7 parsed it but WinPS5 legacy ANSI interpretation breaks syntax; not a functional video benchmark failure.
- Replaced lone non-ASCII en dash with hyphen and verified all script characters <=ASCII 127. Added `shell: powershell` native Windows runner step to `.github/workflows/t10-engine-eval.yml` that reads bytes, fails on >=128, then calls `Parser.ParseFile` in Windows PowerShell 5.1. Evidence `.agents/evidence/t10-video10-ps51-encoding-fix.json`.
- This fix does not alter device, media model, datasets, benchmark baselines, or CP4. Physical Sony video10 Run remains pending; confirm CI Windows job before instructing user to retry.

### T10-VIDEO10-SONY-PHYSICAL-MEDIA-001 — Instrumentation PASS in user terminal, JSON verification pending
- Session `.t10-benchmark/video10-media-20261010T005735-651d8bf3`, app test `RealVideoTenMinuteMediaTest`: `Time: 45,061`, `OK (1 test)`, `INSTRUMENTATION_CODE: -1`, ADB pushed 471076143 bytes of local MP4, host file SHA `6fec4cfb23033e47144f0aed857461f32f8981072127548254cfce29ba2636bc`. ADB pulled 1418-byte JSON, SHA `935d1d90056a31e737c55c0b65e1017113b26aafd0a8adfabaaf5327cf86e272`. CLI emitted `MEDIA STAGE PASS (BUKAN full E2E/CP4)` and says staged video deleted.
- Evidence from user terminal only in `.agents/evidence/t10-real-video-media-stage-sony-console-pass.json`; not equivalent to independent direct JSON review. Validator `python tools/t10_video10_media_review.py HOST DEVICE --json SUMMARY` has yet to receive input. Need inspect `duration_us`, PCM last PTS and bytes, `decode_wall_ms`, sampled PSS/RAM, battery proxy max, video/audio codec, unchanged SHA and offline preflight from JSON; don't infer actual peak temperature/memory/video duration from the 45s test elapsed time.
- MEDIA STAGE ONLY: app T09 real file inspect/audio decode worked per harness, but full app ASR, translation, timed caption rendering/export E2E has not been run and is not yet implemented. T10 ACTIVE, CP4 BLOCKED, T11 TODO; ASR ID clean Base 105/367=28.61% and ID→EN translation 24/30 remain below gates.

### T10-VIDEO10-SONY-MEDIA-JSON-VERIFIED-001 — Real media 12min14s FULL PCM, not subtitles E2E
- Three user-uploaded JSONs read and cross-verified: host SHA `27ba63fdabcebbd7b82d64cab8afd02e046b30a51ae26dbad92fb8a68b4b64be`, device SHA `935d1d90056a31e737c55c0b65e1017113b26aafd0a8adfabaaf5327cf86e272`, summary SHA `016003c7f45a5225a3503a5d6a78a12695add621b22e4ad1c4124123db5109e0`. Summary-bound hashes, source host=device before/after, byte lengths, offline preflight, 600-900s duration, PCM/full-tail, thermal, sampled PSS and RTF checks all PASS.
- Sony SO-03L/Android 30/arm64-v8a; H.264 720x1290 video **734.570666 seconds**, AAC stereo 48k; input 471,076,143 bytes SHA `6fec4cfb23033e47144f0aed857461f32f8981072127548254cfce29ba2636bc`. Decoded PCM S16_LE 141,033,408 bytes/34,432 buffers with last PTS 734.528s (42.666ms tail gap), no truncation, unchanged video SHA after; inspect 900 ms, decode 42,758ms, total 44,537ms (0.0582 RTF decode). Battery proxy 35.2/35.5/35.5°C initial/final/peak, sampled PSS **126.463 MiB**, sampled Java heap **22.269 MiB** (not actual allocation peaks). Host device radio flags airplane=1 WiFi=0; no packet capture. Evidence `.agents/evidence/t10-real-video-media-stage-sony-json-verified.json`.
- Explicit verdict **MEDIA_STAGE_PASS_NOT_FULL_E2E** for one physical >10min MP4. No ASR or timed subtitles generated, no translation or MP4 output; production feature pipeline T11-T14 still undone. Don't use this pass as CP4 eligibility, ASR memory, CPU die thermal or multiple-codec support. ASR ID 28.61% WER and ID→EN 24/30 remain blocking. T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10-ASR-SMALL-MODEL-001 — Offline Base-vs-Small-q5_1 candidate, not CP4
- Candidate model `ggml-small-q5_1.bin` SHA256 `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`, pinned HF revision `80da2d8bfee42b0e836fc3a9890373e5defc00a6`. Approx 190-200MB download once, online **only** via `--prepare-small`; verify streamed SHA256 and final safe destination; original `ggml-base.bin` SHA `60ed5bc3dd14eea856493d334349b405782ddcaf0028d4b5df4088345fba2efe` never overwritten. No network in ADB scoring stage; `verify_environment()` requires airplane/WiFi off.
- Test protocol `tools/t10_asr_small_protocol.py` validates full 20 original FLEURS Indonesian clean + original frozen ASR CSV via `t10_asr_decode_ab.load_frozen_inputs` and existing 105/367 baseline normalization, builds AB/BA schedule (no cherry-picking), checks per-row source/model/transcript/error, recomputes paired WER and resource feasibility. `tools/t10_asr_small_ab.py` runs Android arm64 cached Whisper CLI with same `-l id -nt -ng -nfa -otxt -of result` flags; records Base vs quantized Small pair. Every run saves state to isolated `.t10-benchmark/small-model-ab-*` with model/manifest/WAV/device/binary SHA binding and can resume (default 2 new pairs per invocation).
- Physical safety: start battery <40C, stop >=43C, per-run 240-second timeout, per-invocation ~15min safety; dedicated remote `/data/local/tmp/subloka-t10-small-<uuid>` only, numeric PID validated prior to process termination, isolated cleanup. Require 600MiB available on Android `/data`. Sampled `VmRSS` (not true peak), elapsed inference/RFT and battery tracked; if RSS inaccessible, quantitative candidacy cannot be declared.
- Model-screening threshold preregistered: 20 paired clean ID runs, ≤73 Small word errors/367, ≤2.0 Small p95 RTF, RSS sampled on all small runs and sampled peak <1,600,000 kB, no OOM/thermal stop. This is a **diagnostic screen** on previously studied data; even a positive result requires fresh independently selected/unseen audio and actual app integration evaluation before any production model recommendation. 5 listener-marked AUDIO_AMBIGUOUS samples remain in original 20; do not relabel/remove based on model outcome. 21 offline Python tests verify deterministic schedule/frozen evidence/safe process scopes/missing grades, failures, download SHA and resource criteria. `.agents/evidence/t10-asr-small-model-preregistered.json`.
- Manual evidence not provided. No measurable improvement yet. Historic 105/367 ASR, translation ID→EN 24/30, CP4 BLOCKED; Sony 12m14 media-stage decoding PASS is not ASR test or full subtitle E2E.

### T10-ASR-SMALL-Q5-HTTP-404 / Source snapshot corrected
- User real Windows `--prepare-small` raised `urllib.error.HTTPError: HTTP Error 404`; root cause was nonexistent `ggml-small-q5_1.bin` at originally pinned `80da2d8bfee42b0e836fc3a9890373e5defc00a6` revision. The official Hugging Face file listing for `ggerganov/whisper.cpp` snapshot `c521a4b02f422512d734391fdf08bb08c0862f68` verifies multilingual `ggml-small-q5_1.bin` 190 MB with the *same* existing frozen SHA256 `ae85e4a935d7a567bd102fe55afc16bb595bdb618e11b2fc7591bc08120411bb`. The new fixed model source does not change pretrained weights or comparisons.
- Fix: `REVISION` in `tools/t10_asr_small_protocol.py` updated only to existing confirmed snapshot. `prepare_small` now surfaces understandable HTTP and network error and cleans .part; test suite expanded 21→23, including fixed pinned URL+hash and 404 cleanup regression. Evidence `.agents/evidence/t10-asr-small-model-download-url-fix.json`. Existing original preregistered JSON remains unchanged, followed by explicit correction.
- *Status*: No successful user model preparation after this fix and no Sony inference yet. The reported HTTP failure is not ASR performance failure. No original benchmark or CP4 change. Execute the online `--prepare-small` command after pull/CI validation; only then offline preflight and initial two-pair pilot.

### T10-ASR-SMALL-Q5-READY-001 — Model verification + device preflight (user console)
- User confirms `--prepare-small` completed after fixed HF source: `Verified small-q5_1 model (190085487 bytes)`. Hash check is performed by Python before save, but raw local model bytes were not accessible to assistant. Input model SHA pinned unchanged. `--preflight-only`: `Offline preflight PASS: SO-03L, battery=37.2C, free=2127 MiB.` Android data space exceeds 600 MiB minimum; initial battery below 40 C. Repo CI for `f6b97f3`: both Android CI and T10 Engine Evaluation completed success.
- Documentation `.agents/evidence/t10-asr-small-model-host-ready-sony-preflight.json` records user-reported provenance. No runtime ASR candidate inference or 2-pair pilot was executed yet. The only next physical action is `python tools/t10_asr_small_ab.py --max-pairs 2`; inspect returned summary for both model WER diagnostics, latency/RTF, sampled process RSS, thermal aborts before proceeding. No modifications to historical ASR/translation gates.

### T10-ASR-SMALL-Q5-SONY-PAIR-PILOT-002 — Early-stop p95 consequence, not CP4
- Sony / user CLI: `--max-pairs 2` completed 4 Android Whisper inference results in `small-model-ab-20261010T030853Z-94c149`, no runtime errors reported. For `id-clean-01`, Base 4/17 edits RTF1.05211 sampled VmRSS376968KiB, Small 5/17 edits RTF2.5069 VmRSS608612KiB. For `id-clean-02`, Base 8/18 edits RTF1.18251 VmRSS376628KiB, Small 8/18 RTF2.1602 VmRSS609308KiB. Base WER 12/35=34.29% vs Small WER 13/35=37.14% **partial only**; no full-set ASR improvement established. Battery 37.0 to 38.5C below 43C abort gate. Original user console only, not actual session hash/transcripts; see `.agents/evidence/t10-asr-small-model-two-pair-pilot-early-reject.json`.
- Preregistered Small p95 RTF <=2.0 on 20 clips uses `ceil(.95*20)=19` sorted rank; **at most ONE value >2.0** can pass. **Already TWO recorded >2** means best p95 with all remaining 18 arbitrarily fast is **2.1602**, permanently failing the fixed criterion. Stop further paired experiments for this Small-q5 screening; no reason to expose Sony to 18 further slow Small trials when intended diagnostic cannot possibly pass. This is mathematical performance rejection only, not 20-sample accuracy/independent holdout rejection.
- Analyzer now reports `EARLY_PERFORMANCE_REJECT_P95_RTF_UNRECOVERABLE_NOT_CP4` when 2 paired Small RTF violations; `--resume` checks that first and refuses further device model transfers, and live loop stops after second paired violation. Three extra regression unit tests (2 slow -> early reject; 1 slow -> still partial; 20 with 2 slow -> p95 fails). Original 20-FLEURS, original Base WER 105/367, ASR gates and trained model hashes untouched. CP4 BLOCKED, T11 TODO. Await CI confirmation before reporting code tests as PASS.

### T10-TRANSLATION-ARGOS-HOST-001 — Predeclared 10-case offline ID->EN model pilot
- Genuine candidate different from Google ML Kit: Argos Translate ID->EN `translate-id_en-1_9.argosmodel` from pinned public mirror snapshot `a69e5d5f51945c24ad8653c3255b87320af21a48`, archive SHA `b494f6109dd7ceae32cb44cc721a14039abce938dc773a70087e73301ef4fed4`. Official Argos model index confirms ID->EN language package; mirror advertises SHA and 68.7MB archive. Python runtime library `argostranslate==1.11.0` installed only with opt-in command; **additional dependencies may be much larger**, especially NLP/ML CPU wheels. No AI translation inference run yet.
- Strict upstream comparator: only exact existing user-reviewed `translation-strategy-ab-review.csv` with bytes SHA `516ca5d8967aefa7046db65e53fb1788ef7267bb48f7f34ada48eb72d20018a9`, 120 intact pairs, fixed fixture, whole reviewed ACCEPT ID 21/30 and EN 22/30. Pilot uses `id-ab-01...id-ab-10` in increasing order; control output/status copied unchanged; status for candidate output **blank** until separate review. 10-case source is **NOT a CP4 independent holdout**.
- `tools/t10_translation_argos_candidate.py prepare`: SHA-check exact model ZIP, enforce 60–90MB archive size, safe member paths/no symlinks/uncompressed bound, install in isolated gitignored workdir through `ARGOS_PACKAGES_DIR`. Offline pilot has no download calls and blocks outbound sockets during imported Argos inference. Results `pilot.csv` and `session.json` generated only on complete 10. Errors write aborted status; outputs stay local. `report` reads candidate manually reviewed file, rejects edited raw source/model/control or incomplete judgements and never returns CP4 PASS.
- Precommitted diagnostic pass = >=2 fixed whole wrong cases corrected, net >=2 ACCEPT and no newly introduced critical negation/number/name errors; passing only warrants 30-case review/new unseen set/Android integration+performance. Windows CPU speed cannot be taken as Android CPU/MLKit timing. Exactly 24 synthetic regression tests + workflow path triggers. No 2nd reviewer independence established; no current Argos results. Evidence `.agents/evidence/t10-translation-argos-id-en-host-preregistered.json`.

### T10 ARGOS HOST PILOT — OFFLINE GUARD ABORT, SAFER STANZA INITIALIZATION
- User `prepare` verified 68,650,073-byte Argos ID→EN archive/installed local Windows package. First two pilot attempts aborted before any model outputs with `Outgoing network is forbidden in offline T10 candidate inference` (new distinct aborted folders stamped `20261010T035318Z-9776740` and `20261010T035434Z-4db5ed4`). Third usage exception from literal multi-line PowerShell `>>` quoting, not actual review path. No valid pilot.csv or grading; no cloud request completed due socket blocking.
- Source audit of Argos 1.11.0 `StanzaSentencizer.lazy_pipeline` suggests (NOT independently proven for this particular model file) that its default `stanza.Pipeline` triggers resources.json download attempt on first call; Stanza supports `download_method=None` to force local cached resources only. New `t10_translation_argos_offline_sbd.py` preloads **same bundled** Stanza SBD locally with `download_method=None`, refuses missing resources, unsupported SBD, SBD outside package, unbundled MiniSBD downloads. Runner keeps socket `no_network` active through SBD initialization and translation; new session metadata records `offline_sbd_mode`. This is a safety fix, **not an output quality improvement**.
- 7 new mock unit tests for local-only Stanza, forbidden socket activity, failure messages/package path and bundled MiniSBD; total **31**, awaiting CI. Evidence: `.agents/evidence/t10-argos-offline-stanza-abort-fix.json`. Original model ZIP already installed; no reinstall/re-download is needed. After CI success, re-run pilot as single PowerShell line with existing reviewed CSV and then upload 10-row pilot.csv. T10 ACTIVE/CP4 BLOCKED/T11 TODO.

### T10 ARGOS V1.11 CACHED TRANSLATION WRAPPER — HOST ERROR & REGRESSION
- Previous 31 mock/offline tests: **PASS user console, 0.546s**. The next real offline pilot failed before any translations with `Argos direct translation lacks a local model/SBD package`. No valid `pilot.csv`.
- Upstream Argos v1.11.0 `get_installed_languages()` wraps `PackageTranslation` in `CachedTranslation`; `Language.get_translation()` returns the cached object. The local SBD helper mistakenly expected `.pkg` and `.sentencizer` on this outer cache wrapper. New strict `unwrap_local_cached_translation()` rejects non-cached/non-packaged/composite/remote/identity and wrong id→en/package path, then passes the real underlying backend to local-only SBD setup. The actual translation still uses original cached adapter.
- Five synthetic regression tests added, total **36 pending user verification**; original 31 passing tests did NOT exercise this wrapper. After `git pull --ff-only origin main`, run `python -m unittest discover -s tools -p "test_t10_translation_argos_candidate.py" -v` in existing isolated venv, then the same offline pilot if 36/36 PASS. Never disable network guard. Preserve unchanged ML Kit control and model hash; do not mark CP4 PASS. Evidence: `.agents/evidence/t10-argos-cached-direct-backend-fix.json`.
- **36-test rerun evidence, 2026-10-10:** user output `Ran 36 tests in 0.448s; FAILED (failures=1, errors=1)`; both failures from mock Argos package lacking `from_code="id"` and `to_code="en"`. `_fake_sbd` fixture now supplies these pinned values so proper 1) cached direct backend + offline SBD and 2) mismatched installed package path checks execute. No production strict validation or socket guard was changed. Rerun all 36; if PASS then retry offline pilot. No `pilot.csv` or quality verdict yet.

### T10 ARGOS HOST REAL STANZA KEYERROR AFTER 36/36 TESTS
- User-pasted Windows console: `Ran 36 tests in 0.340s OK`; real pilot aborts before any translation: `Local bundled Stanza tokenizer could not be initialized offline (KeyError); no network fallback is allowed`. Previous network and cached-wrapper blockers progressed; this exception's exact key and origin still unknown. No generated quality data.
- Previous error handler hid KeyError `args` and traceback, limiting safe diagnosis. New bounded `stanza_failure_diagnostics` reads **only** local packaged `resources.json` structural keys and names of local `id/tokenize/*.pt` files, plus safe traceback file basename/function/line. No network, no model bytes, no absolute paths or auto-repair. New two mock tests validate diagnostic redaction/fail-closed and corrupt JSON reporting; 36→**38 tests pending user Windows validation**.
- Do not rerun prepare, change ML Kit baseline or preregistered score, or disable `no_network()`. On new error, request exact sanitized `ERROR` line before changing resources or SBD options. CP4 BLOCKED / quality UNKNOWN.

### T10 ARGOS — LOCAL STANZA LEGACY DEFAULT_PROCESSORS COMPATIBILITY
- User reported `Ran 38 tests in 0.343s OK`; actual offline pilot fails `KeyError('packages')` in `Stanza common.py:add_mwt`. Packaged language resources.json has `default_processors` but no `packages`, with `gsd` tokenize resource entry and `id/tokenize/gsd.pt` present. This is an upstream schema/runtime compatibility mismatch, not a demonstrated absent tokenizer. No valid candidate quality outputs.
- `t10_translation_argos_stanza_metadata.local_stanza_metadata()`: check same isolated package hierarchy, parse existing local resources only, permit modern `packages` unchanged, or legacy adapter only when selected `default_processors.tokenize` matches declared tokenize package and local `.pt` exists; reject unsafe names or missing/mismatching model. Temporarily write revised metadata to a separate isolated temp directory and load it through Stanza's `resources_filepath` argument while retaining `download_method=None`, same original local tokenizer model, same original model package, `no_network` guard, and no overwrite of original model files. Temporary overlay cleaned after Pipeline constructor even on errors; all other defaults unchanged.
- Tests added: 5, total **43 mock tests** awaiting execution. Prior diagnostic synthetic fixtures now use a valid modern resources layout; changed expected malformed metadata fail-closed assertions. No automatic promotion, no baseline edits or Android measurements. Run the same Windows host pilot only if new 43 tests PASS, then review ten frozen cases; T10 ACTIVE / CP4 BLOCKED.

### T10 ARGOS — LEGACY STANZA TOKENIZER CHECKPOINT METADATA (43→48 MOCK TESTS)
- User reports prior 43/43 synthetic tests PASS. Real offline Argos host pilot now fails at Stanza model tokenizer load with `KeyError('feat_dropout')` (trainer.py:load:93), no valid `pilot.csv`; existing resource adapter resolved `packages` error.
- Verified upstream Stanza 1.2.3 tokenizer trainer checkpoint schema lacks `feat_dropout` and `lexicon`; Stanza 1.10.1 loader (Argos 1.11 requirement) requires these. Scoped compatibility helper creates only temporary copy, reads checkpoint with `torch.load(weights_only=True, map_location='cpu')`, adds `config.feat_dropout=0.0` and `lexicon=None` where absent, without modifying model tensors, original `gsd.pt`, original `resources.json`, or original translation model. Stanza accepts `tokenize_model_path` pointing to temp during constructor; clears temp after model loading. All calls under existing `no_network` guard and `download_method=None`, unknown formats abort. No unrestricted unpickle fallback.
- Added 5 synthetic test methods: staged legacy config and weight preservation, malformed payload rejection, weights_only strictness, modern config pass-through, temp cleanup on downstream failure, path security (see exact assertions). **48 tests awaiting user execution**, no independent physical-model compatibility proof yet.
- CI `.github/workflows/t10-engine-eval.yml` tracks new adapter; preregistered pilot selection, ML Kit frozen review, SHA, thresholds and CP4 blocked state remain unchanged.

### T10 ARGOS SBD — LEGACY ALL_CAPS FEATURE COMPATIBILITY (48→52)
- 48 mock unit tests **PASS user Windows console, 0.460s**. Real offline pilot now SBD initialized and aborts during first text with `Feature function "all_caps" is undefined.` No 10-row pilot or quality comparison.
- Verified upstream code: Stanza v1.2.3 `all_caps` = `x.isupper()`, Stanza v1.10.1 `capitalized` = `x[0].isupper()`. The newer Stanza `TokenizationDataset` normalizes input to individual characters before feature extraction. Metadata-only rename on TEMPORARY checkpoint `feat_funcs` preserves per-character output bit, vector width, model/vocab tensors and positions; no replacement tokenizer or feature dropping. Also supply absent pre-dictionary `use_dictionary=False`, preserving any existing flag.
- `tools/t10_translation_argos_stanza_checkpoint.py` implements strict feature whitelist, preserving tuple/list type; does not alter original `.pt` or resource metadata and keeps torch `weights_only=True` with `no_network` and `download_method=None`. Four new synthetic tests cover Unicode equivalence, unsupported feature rejection, dictionary flag and list-order/tuple preservation; total **52 tests** awaiting Windows rerun and real host pilot. No CP4 promotion until objective ML Kit review and separate Android proof.

### T10 ARGOS OFFLINE WINDOWS HOST PILOT — 52/52 REGRESSION PASS, 10/10 OUTPUTS
- 2026-10-10 user PowerShell: `Ran 52 tests in 0.401s OK`, Argos SBD local checkpoint setup `PACKAGED_STANZA_LEGACY_METADATA_AND_CHECKPOINT_NO_DOWNLOAD` PASS, all ten ID→EN predictions logged and persisted `HOST PILOT CSV: C:\\Users\\FLYONZ\\Documents\\GitHub\\Subloka\\.t10-benchmark\\argos-id-en-pilot-20261010T053116Z-cc3c4db\\pilot.csv`. No runtime abort; all acceptance fields remain blank per runner.
- Per-case Windows host timings (ms) in original order `id-ab-01..10`: `1094, 109, 157, 187, 156, 141, 156, 110, 109, 109`. Average 9 after first 137.111 ms; first 1094 ms; timing **not comparable to Android performance**.
- Evidence derived from user console only. Gitignored local `pilot.csv` and `session.json` not present in GitHub; do not falsely claim assistant reviewed translation meaning, schema, byte hash or acceptance. Need upload CSV and assess literal candidate outputs with independent review before `report --session ... --review ...`. `grade()` demands unmodified original candidate rows, ten filled statuses, non-empty rejection notes, raw_sha256 matches session.json, ≥2 improvements with net ≥2 and zero NEW critical errors. Successful host pilot is **NOT CP4**, T10 ACTIVE / CP4 BLOCKED.

### T10 ARGOS — UPLOADED RAW PILOT VERIFIED AND AI-ASSISTED QA DRAFT
- User-uploaded `pilot.csv` raw SHA-256 matches session `raw_sha256`: `c7ca76b9d260a95ffac7e6111104e25104eba6c866bc5b0fa0337b60de9699cf`. Verified `session.status=HOST_PILOT_COMPLETE_REVIEW_PENDING_NOT_CP4`; model SHA and original 120-row ML Kit review SHA equal preregistered pins; 10 exact sample IDs `id-ab-01..10`; column order equal `OUTPUT_COLUMNS`; all 10 translations nonempty and candidate fields initially blank. Original user-uploaded bytes were not edited.
- Human-readable AI-assisted review draft: sample ACCEPT `01,02,03,04,06,07,08,10`, sample `05 NUMBER_OR_NAME_ERROR` (Laras→Array; 'He'), `09 MAJOR_MEANING_ERROR` (gender and antecedent contradictory). Source/ML Kit / Argos comparisons performed for every case; draft annotations include marginal wording/precision issues on accepted samples, including plurals and unnatural grammar. Proposed `wins=2` (`06`, `08`), `losses=0`, `net=+2`, `new_critical_errors=[]`, baseline accepted `6/10`, candidate proposed accepted `8/10`. Protocol's threshold mathematically meets PROMISING **only provisionally**.
- Generated local chat attachment `pilot-reviewed-draft.csv` (SHA256 `2824a2442908e2eee297d3f89c5ad28cecba2096d68e641d3c39c0de1ac68157`), preserving all raw columns verbatim, adding only `candidate_review_status` and `candidate_notes`; independently re-read/checked each unchanged field. No official repository/Windows `report --session --review` run, no independent human signoff or Android inference. Next user reviews/amends draft, puts review CSV on Windows and runs reporter against immutable source session. CP4 BLOCKED even if verdict PROMISING.

### T10 ARGOS — OFFICIAL LOCAL REPORTER PROMISING, CP4 STILL BLOCKED
- User on Windows explicitly ran official reporter against original completed 10-case session and reviewed candidate copy; output: `Candidate reviewed: 8 /10; whole ML Kit: 6 /10; net 2`, `VERDICT: PROMISING_FOR_FULL_30_AND_NEW_INDEPENDENT_HOLDOUT | CP4 BLOCKED`. Prior host evidence: 52/52 unit tests PASS, offline 10/10 inference, session `argos-id-en-pilot-20261010T053116Z-cc3c4db`, original raw pilot SHA `c7ca76b9d260a95ffac7e6111104e25104eba6c866bc5b0fa0337b60de9699cf`. The reporter runs schema/hash/immutable raw field checks; actual generated Windows `review-report.json` has not been uploaded, so preserve console verdict without claiming independent report file audit.
- Official **pilot quality threshold met**, not CP4. Baseline ML Kit accepted 6/10; Argos reviewed accepted 8/10, net +2/10. Under pinned preregistered rule verdict PROMISING requires ≥2 prior rejects repaired, net≥2 and no newly introduced negation/number/name critical error. This is the authority for further full30 + unseen holdout screening, not proof Android performance.
- The present `tools/t10_translation_argos_candidate.py pilot` only generates 10 fixed rows and `report` validates exactly 10; no actual 30-sample command exists yet. Next work should design a separate FULL30 runner/report suite before asking user to run it. Follow with held-out untouched fixture screening and Android device offline acceptance. Current statuses: **T10 ACTIVE / pilot PROMISING PASSED / CP4 BLOCKED / T11 TODO**.

### T10 ARGOS — DEDICATED HOST FULL30 DESCRIPTIVE HARNESS ADDED
- Entry points: `tools/t10_translation_argos_full30.py run --review <frozen-120-row-review.csv>` and separate `report --session <completed-full30-folder> --review <30-row-reviewed-copy.csv>`; preregistered 10-case pilot still used unchanged and its official reporter verdict PROMISING remains separately preserved.
- Full30 protocol pins 30 ID→EN sample IDs `id-ab-01..id-ab-30`, same validated model archive, same 120-row ML Kit SHA, same direct CachedTranslation(PackageTranslation) validation, same fully offline SBD/legacy checkpoint, no network on all 30, new never-overwritten timestamped session and source/translation QA columns initially blank. Outputs are NOT a holdout: group `pilot_overlap_first10` = 10 reused samples; `previously_unseen_fixture_extra20` = 20 other existing frozen source fixtures, not new independent holdout. A future holdout must be created separately from untouched data.
- Strict full30 grading reads raw and rated CSV in exact original schema, checks 30 count/order, raw SHA, model SHA, frozen review SHA and immutable source/control/Argos columns; all statuses and rejection reasons required. Reports accepted/wins/losses/net/new critical for all 30, first10, extra20, but no full30 promotion threshold was preregistered, so result marked descriptive-only CP4 BLOCKED regardless of quality.
- New synthetic regression suite `tools/test_t10_translation_argos_full30.py`: 11 tests, not yet run on Windows or CI. Gate: run and verify 11/11 before real host full30; do not claim PASS until host result. CI trigger/step added.

### T10 ARGOS FULL30 — UPLOADED RAW VERIFIED, REVIEW DRAFT PENDING OFFICIAL REPORT
- Verified uploaded `full30.csv` SHA256 `fa8595768e348b4d875737631718ca91984438ee8ea7a15c425f2a4f48b6d694` matches uploaded `session.json.raw_sha256`. Session completed, all `id-ab-01..30` present in strict order, 30 nonblank outputs and positive latency, candidate statuses originally empty, error empty; original ML Kit comparison statuses 21 ACCEPT, 8 MAJOR_MEANING_ERROR, 1 NUMBER_OR_NAME_ERROR. Model SHA and frozen source review SHA match pins. Immutable original raw fields preserved verbatim in reviewer copy.
- Candidate reviewer draft `full30-reviewed-draft.csv` SHA256 `b1b39cfb73455d1e442747ef89e75d3e17997ad9ff63119572647807bdc52399`, valid 30/30 proposed statuses, nonempty notes for rejected. `full30-qa-preview.json` lists per-case rationale and borderline recheck. Score **PROVISIONAL ONLY**: full30 ML Kit 21/30, Argos 21/30, wins5, losses5, net0. Pilot overlap first10 ML Kit6/Argos8 net+2; additional existing20 ML Kit15/Argos13 net−2. Proposed critical regressions id-ab-13 (not necessarily apply→does not apply) and id-ab-25 (rupiah→rupees). New candidate wins id-ab-18,24,29 require human review (not holdout).
- Host latency from uploaded CSV: first 938ms, remaining 29 mean 138.448ms, total 30 mean 165.1ms, median 125ms. Windows CPU only; not Android throughput/performance. No official `full30-review-report.json` received yet, no independent human QA approval. Reporter `tools/t10_translation_argos_full30.py report --session <actual completed full30 dir> --review <reviewed CSV>` is next step after approval. CP4 BLOCKED, T10 ACTIVE.

### T10 ARGOS — OFFICIAL WINDOWS FULL30 REPORTER RESULTS (DESCRIPTIVE ONLY)
- Official user-pasted console on Windows: `FULL30 REVIEWED: Argos 21 /30; ML Kit 21 /30; net 0`; `ADDITIONAL 20 EXISTING FIXTURES: Argos 13 /20; ML Kit 15 /20; net -2`; `DESCRIPTIVE ONLY | INDEPENDENT HOLDOUT REQUIRED | CP4 BLOCKED`. The original pilot10 official reporter remains Argos8/10 ML Kit6/10 net+2, so first10 overlap is known; full30 21/30 means 20 additional fixtures Argos13/20 versus ML Kit15/20. Reporter was executed successfully by user; complete Windows `full30-review-report.json` not uploaded/independently re-checked.
- Frozen raw `full30.csv` SHA `fa8595768e348b4d875737631718ca91984438ee8ea7a15c425f2a4f48b6d694`; 30 exact source IDs, pinned source review/model hashes previously verified. Reporter code enforces per-field immutability, exact CSV schema, 30 reviewed labels and rejection notes. Previous user-approved draft had wins5/losses5, first10 wins2/losses0, additional20 wins3/losses5, and possible new critical regressions `id-ab-13` (negation/uncertainty) and `id-ab-25` (currency). Those detailed case labels are from original draft and are not enumerated in console; official output verifies aggregate counts, not separately each case-specific classification.
- Scientific guard: Full30 protocol declares no newly preregistered full30 pass/fail threshold and always returns DESCRIPTIVE_ONLY; do not mislabel net0 as official full30 FAIL or CP4 PASS. First10 pilot remains PROMISING, but does not generalize to existing 20. Engineering recommendation: no Argos Android promotion on current data; ML Kit stays baseline, CP4 BLOCKED; possible holdout only if further candidate advancement justified. 11 synthetic full30 tests were implemented; no explicit user-pasted unit-test report for those 11 has been received, even though actual host runner/reporter succeeded.

### T10 CP4 READINESS — FAIL-CLOSED CONSOLIDATED EVIDENCE AUDITOR
- `tools/t10_cp4_readiness.py` is read-only and uses five immutable repository T10 JSON evidence snapshots, SHA256 each file in output. It checks 20-pair default-vs-beam1 counts (105/367 vs 110/367), Small-q5_1 mathematically unrecoverable p95 RTF <=2.0, one-Sony 734.57s media decode-only JSON validation, original single-segment CP4 translation 24/30 ID→EN and 27/30 EN→ID, ML Kit paragraph strategy A/B 21/30 and 22/30, and official Argos host30 tie 21/30 each plus extra20 −2. **Does not use later paragraph/Argos counts to inflate original CP4 translation results.**
- Derived frozen threshold arithmetic: max ID-clean errors `floor(0.20 × 367) = 73`; observed 105; reduction required at least 32 edits without tampering references. Original CP4 translation acceptance min `ceil(0.9 × 30) = 27`; ID→EN 24 (gap3), EN→ID 27 (gap0). Original historical single-segment translation judgments were AI-assisted and not independently human-attested. Other ASR categories, full E2E on Android, model distribution/integration and release remain unverified; CP4 always BLOCKED by this tool.
- Includes **13 new Python unittest regression cases** including corrupted evidence refusal and no-overwrite. CI watches `t10_cp4_readiness.py`, test module and all 5 evidence files, executes test and CLI in CI; **host/CI actual PASS not yet reported**. Output optional new `.t10-benchmark/t10-cp4-readiness.json` (gitignored), never overwrite. Test mock quality metrics are not new Android measurements or permission to start T11.

### T10 CP4 AUDIT — USER VERIFIED 13 REGRESSION TESTS + REPORT
- Actual user Windows PowerShell: `Ran 13 tests in 0.131s OK`, then command `.\\.t10-benchmark\\argos-venv\\Scripts\\python.exe tools\\t10_cp4_readiness.py --json ".\\.t10-benchmark\\t10-cp4-readiness.json"` exited without ERROR. Console: `105/367 edits (28.61%); >=32 fewer edits required`, original CP4 translation ID→EN `24/30 vs 27/30` gap 3, Sony `MEDIA_STAGE_PASS` NOT E2E, Argos host Full30 `21/30 vs 21/30` net0, T10 ACTIVE/CP4 BLOCKED/T11 TODO.
- Status: **13/13 audit-unit tests PASS on user Windows host; JSON saved locally but actual bytes/hash not independently examined**. This test verifies immutable evidence parsing and anti-promotion guard only: no new ASR device results, no benchmark score modification, no Android pipeline integration. Existing 11 full30 synthetic tests were not explicitly reported as passing; don't infer they did.

### T10 ORIGINAL ML KIT HUMAN QA — NEXT EVIDENCE STAGE, NOT CLAIMED PASS
- After Windows 13/13 CP4 auditor PASS, next recommended evidence collection is a real independent bilingual reviewer of the historical 60 **single-segment original** ML Kit device outputs. The existing `tools/t10_translation_human_qa.py` verifies device raw field identity vs frozen `engine/translation/src/androidTest/assets/t10_translation_fixtures.json`, pins SHA, outputs separate 60-row `human-review.csv` with blank human decisions, and preserves AI draft as provisional only on exact-output match.
- `tools/t10_translation_device_benchmark.ps1` defaults `-OutputPath` to `.t10-benchmark/translation-results.csv` for original non-Strategy run. Before prepare, verify that exact file exists and is the original 60-row dataset; do not swap in the distinct `translation-strategy-ab-results.csv`. `finalize` is guarded by independent bilingual review attestation; no reviewer/labels may be invented and even completed human quality report cannot override ASR+full-E2E blockers. No new human-QA outcome measured at this commit.

### T10 HUMAN QA — ORIGINAL ML KIT 60-ROW SESSION PREPARE WINDOWS PASS
- User PowerShell confirms clean `git pull` to `734e66e`, original `.t10-benchmark/translation-results.csv` found, and `tools/t10_translation_human_qa.py prepare` succeeded in `.t10-benchmark/t10-human-qa-20261010T132119`. Reported original raw SHA-256 `f135ec8bf749d0609197137e54691170047d3336b2d246a9f89dd0689cb5de6a`; `AI draft exact-output match: True`.
- Source-level semantics of PASS: all 60 original source/target languages, sample IDs/text and model-result fields match the frozen fixture and local raw; AI draft digest matches those raw model outputs, but AI judgments are not independent human votes. `human_status` deliberately blank in all 60 prepared rows, `human_notes` blank, no human completed review/finalizer/signoff, no CP4 promotion. Entire local session CSV/JSON bytes have NOT been uploaded or independently SHA-audited; only the script's printed digest is observed. Do not invent any reviewer or new accepted score.
- Next: independent bilingual human fill only `human_status`/`human_notes`, preserve all original fields and `provisional_ai_*`. After truthful 60-row review, `finalize` performs checks, writes `human-reviewed.csv`, `human-quality-report.json`, `human-signoff.json` once. No shortcut to full Android E2E, ASR WER or CP4; T10 ACTIVE, CP4 BLOCKED.

### T10 HUMAN-QA UPLOADED SHEET — 60 LABELS, NOT YET VALID FOR FINALIZE
- Local attachment `human-review-reviewed.csv` SHA256 `bbee253eb6aacc07f5451d1ac3008709d5bcd3e993867a627634aa2d369f7887`, 60 unique rows in exact en01..30 + id01..30 original order and expected 11-field CSV schema. Original source→translation digest from imported records `2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c` matches repository pinned AI draft; valid nonblank positive latencies and blank error fields. Original Windows raw device and session artifacts not inspected in this turn.
- Populated counts from `human_status`: EN→ID 28 ACCEPT, 2 MAJOR; ID→EN 25 ACCEPT, 4 MAJOR, 1 NUMBER_OR_NAME. Three AI disagreements: `en-08` AI MAJOR→human ACCEPT (**missing required reviewer rationale**), `id-08` AI ACCEPT→human NUMBER_OR_NAME (**has note, borderline date grammar versus material numeral alteration**), `id-30` AI MAJOR→human ACCEPT (**missing required rationale**). All 7 rejected rows have rejection notes. **Host `validate_human_sheet` should block en-08 and id-30 missing discrepancy notes**; finalizer was NOT run.
- No evidence genuine independent human reviewer identity/attestation is established from a CSV label alone. User should have the real reviewer fill rationale; no assistant-authored or auto-copied rationales masquerading as human. Do not promote a draft 25/30 ID→EN score over frozen original 24/30 or close CP4; even 25/30 is below target 27/30, and ASR remains 105/367 WER with full E2E not run.

### T10 HUMAN-QA — READ-ONLY EXTERNAL REVIEW VALIDATION PATH
- New `tools/t10_translation_human_qa.py check` preflight validates an **external** 60-row completed review against original source device CSV, frozen fixture/AI draft SHA, per-row model evidence, schema, reviewer labels and notes, without overwriting `session/human-review.csv`. Missing override notes are reported together with sample IDs; existing `validate_human_sheet` remains final integrity validator. Output `EXTERNAL_SHEET_INTEGRITY_PASS_NOT_HUMAN_ATTESTED_NOT_CP4` cannot constitute attestation or quality gate promotion.
- Added three regression cases in `tools/test_t10_translation_human_qa.py`, now **12 tests expected**. Their Windows/CI execution is **PENDING**; don't claim PASS yet. User upload original CSV fields digest matched pinned `2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c`, but local raw session SHA/candidate immutable fields only the host check can audit. Uploader's `human-review-reviewed.csv` lacks the two explanations en-08 and id-30, so expected `check` error is correct, not a code failure.

### T10 HUMAN QA — 12/12 WINDOWS REGRESSIONS PASS, EXTERNAL SHEET CORRECTLY REJECTED
- User console: `Ran 12 tests in 0.591s OK` for `python -m unittest discover -s tools -p test_t10_translation_human_qa.py -v` (host Windows). Then original 60-sample raw, prepared QA session and reviewed external sheet supplied to `python tools/t10_translation_human_qa.py check`. Validator printed exactly `ERROR: Missing reviewer rationale for changed AI decisions: en-08, id-30`. This is **correct fail-closed behavior**: incomplete reason-giving is not proof of independent review, and no signoff artifact was written by `check`.
- Raw SHA from prior `prepare` `f135ec8bf749d0609197137e54691170047d3336b2d246a9f89dd0689cb5de6a`; source-translation digest from user upload equals pinned `2e7078978ccdcf81550f944185a263ad45479983b0e1f398b8e1446757d7d37c`; upload review byte SHA `bbee253eb6aacc07f5451d1ac3008709d5bcd3e993867a627634aa2d369f7887`. New host check stops before all fields after missing notes so no `REVIEW INTEGRITY PASS` yet, no `human-reviewed.csv`, `human-quality-report.json`, or `human-signoff.json`. Two notes needed from an actual independent bilingual reviewer; id-08 severity worth reevaluating. No CP4 change.

### T10 HUMAN QA — CORRECTED EXTERNAL REVIEW WINDOWS INTEGRITY PASS, NOT HUMAN ATTESTED
- After earlier expected missing-note rejection, user reran `tools/t10_translation_human_qa.py check` on corrected local review against `$raw` original `.t10-benchmark/translation-results.csv` and `$session` `.t10-benchmark/t10-human-qa-20261010T132119`. Console **exact:** `REVIEW INTEGRITY PASS: 60/60 labels, original evidence unchanged`; `EN->ID 27/30; ID->EN 24/30`; `NOT HUMAN-ATTESTED | CP4 BLOCKED | no files changed`. The check now passed full field immutability, source/fixture/session/AI-draft hash verification, row schema/status/notes and disagreement-note guards, unlike preceding early rejection.
- Corrected external review CSV **was not uploaded**, so its actual bytes/hash, per-case changes and note wording are not independently inspected by assistant. Do not reuse SHA from the previously uploaded review that had 28/30 and 25/30; the latter was superseded locally. Scores from terminal are not independent human QA evidence: human reviewer identity and truthfulness cannot be established from check; no `finalize`, `human-reviewed.csv`, `human-quality-report.json` or `human-signoff.json` produced by `check`. 12/12 unit tests were earlier Windows PASS. ID→EN remains 3 ACCEPT below 27/30, ID-clean ASR WER remains 28.61%, E2E untested; CP4 BLOCKED.

### T10 NEXT ID-ASR ALTERNATIVES — RESEARCH-ONLY SONY FEASIBILITY HARNESS
- Current history: 20 frozen FLEURS ID-clean Whisper Base 105/367=28.61% WER; 0.20 limit needs <=73 edits. `-bs1` 110 edits and Small-q5_1 2/2 RTF>2 early reject. No replacement engine validated. Sony 734.57s video media decode PASS only; human QA sheet integrity PASS but independently human attestation not proved.
- `tools/t10_asr_next_feasibility.py` reads three committed SHA256-audited evidence JSONs and optionally obtains **snapshot only** by ADB: precisely one ready serial, model/ABI, total RAM /proc/meminfo, free /data via `df -k`, battery temperature proxy, airplane mode and Wi-Fi status. Results are NOT peak free memory, running model usage, thermal CPU readings, or a real model inference. Fails closed on unknown output and never downloads a model, pushes files, enables network, or changes Android settings. JSON writes once under .t10-benchmark.
- Research candidate disclosures: Qwen3-ASR 0.6B INT8 ONNX 42+721+174 M listed upstream, Indonesian explicitly supported (https://k2-fsa.github.io/sherpa/onnx/qwen3-asr/pretrained.html); Wav2Vec2 Large XLSR Indonesian weight 1.26GB and self-reported Common Voice WER 14.29%, **not T10 FLEURS** (https://huggingface.co/indonesian-nlp/wav2vec2-large-xlsr-indonesian/tree/main). Vosk official model table does not list Indonesian (https://alphacephei.com/vosk/models), hence not selected. Neither artifacts pinned/downloaded/verified for exact Android redistribution; no model is chosen for inference.
- 12 new synthetic `tools/test_t10_asr_next_feasibility.py` tests added, CI step added. Host/CI outcomes currently **PENDING**. Hard guard `ready_for_model_download=false` for both until license/model-revision/SHA/size and user opt-in verified; `ready_for_sony_inference=false`, `ready_for_cp4_promotion=false`; no benchmark threshold change. T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 SONY ASR FEASIBILITY — WINDOWS 12-TEST FAILURE AND DF TOYBOX HEADER FIX
- User ran Windows unit suite on commit `1eb4734`: **12 tests: 9 ok, 3 ERROR (0.088s)**. Failed names `test_df_available_kib_strict`, `test_probe_mock_only_allowed_read_commands_and_serial`, `test_published_weight_is_not_runtime_ram_claim`. Shared exception `parse_data_free_kib` at old line 131 `ValueError("Unexpected Android df -k row")`. Input mock = `Filesystem 1K-blocks Used Available Use% Mounted on` plus `/dev/block/dm-5 55000000 52900000 2100000 97% /data`: six data fields, seven whitespace-delimited header *tokens*, but six logical columns.
- Correction in `tools/t10_asr_next_feasibility.py` collapses `Mounted on` header to one logical field; verifies exact `Filesystem/1K-blocks/Used/(Available|Avail)/Use%/Mounted` schema with a single `/data` row. More malformed data rejected: wrong mount, extra row, missing/misordered header, invalid numeric/percentage; no capacity numbers invented or model installed. Three new test methods augment prior 12 to **15**; assistant's standalone synthetic parser reproduction accepted canonical and compact headers and refused malformed rows. The FULL updated Windows suite/CI **is not yet confirmed**.
- No Sony real-device preflight results and no ASR inference; CP4/T10 quality is unchanged. Wait for 15/15 Windows PASS before running optional read-only `--probe-device` and compare actual free data vs uncertain published model weight (not runtime memory).

### T10 SONY REAL ADB FEASIBILITY — 15 SYNTHETIC TESTS PASS, DF PROBE BLOCKED
- User PowerShell output: `Ran 15 tests in 0.024s OK` after updated Android `df -k` mock parser. Actual run using `--probe-device --json <unique>` failed with `ERROR: T10 feasibility preflight failed: Unexpected Android df -k row`. This proves the synthetic header tests were good but **did NOT capture Sony's actual /data row layout**; no truthful phone free-space numbers can be extracted yet. Error originates specifically in `parse_data_free_kib` after header normalization from source, which requires one /data data row with six tokens. It does NOT prove low storage or malfunctioning device.
- New `--diagnose-df` mode in `tools/t10_asr_next_feasibility.py`: only `adb devices -l` and `adb -s <selected serial> shell df -k /data`; prints line count, token counts, redacted block-device path, remaining layout via repr; no serial, never writes a report, never modifies device, cannot combine with `--json` or `--probe-device`. 3 added synthetic regressions in `tools/test_t10_asr_next_feasibility.py` (now **18** expected), host/CI run on updated code **pending**. The user should report real sanitized df layout before modifying parser to match an unverified format. CP4/T10 unchanged.

### T10 ASR SONY DF — ACTUAL /DATA/USER/0 MOUNT DIAG AND REGRESSION
- Confirmed via user PowerShell: `Ran 18 tests in 0.025s OK`; `--diagnose-df` **successful on real Sony** with header 7 whitespace tokens (6 logical columns because `Mounted on` is a two-word column) and row 6 tokens ending **`/data/user/0`**, numeric columns `48023344 46097288 1778600 97%`. The command printed `NO DOWNLOAD | NO INFERENCE | CP4 BLOCKED`. This real report is diagnostic only; entire formal `--probe-device` had previously failed before recording verified storage and other fields.
- Root-cause revised from generic header/row mismatch to **actual row mountpoint different from `/data`**. Source now accepts only `/data` and exact empirically observed `/data/user/0` for the already fixed `df -k /data` query, keeps strict field schema, and exposes `df_reported_mountpoint` in probe JSON. Three new synthetic tests added (expected **21**), check Sony numeric shape, incorrect nested mount aliases fail, and recorded mountpoint in mocked full snapshot. Updated Windows/CI **PASS PENDING**; cannot claim verified battery/actual RAM or full feasibility yet.
- Diagnostics already indicate **97% data usage and 1778600 KiB available** for the displayed filesystem, but published model weights ≠ on-device storage overhead or inference RAM. No model downloads, no ASR runs, no frozen CP4 score adjustments. Status CP4 BLOCKED.

### T10 REAL SONY FEASIBILITY — DEVICE SNAPSHOT COMPLETE, LARGE ASR DOWNLOADS DEFERRED
- User pasted successful **read-only physical Android** `--probe-device --json` report: `SO-03L arm64-v8a RAM total MiB 5487 free /data MiB 1732 battery C 38.0`, research candidates Qwen3 ASR ONNX INT8 weights ~937 MiB, Wav2Vec2 Large XLSR Indonesian ~1202 MiB, both without verified exact artifact SHA/license/Sony quality. Tool printed `NO DOWNLOAD | NO INFERENCE | T10 ACTIVE | CP4 BLOCKED | T11 TODO`. Its completed command confirms probe did not raise errors; local output JSON was not uploaded/hashed. Real mountpoint earlier `/data/user/0`; source supports it now. Prior diagnostics showed 97% used but this *new* snapshot does not independently reprint the percentage, so treat % as previous snapshot only.
- Derived conservative storage-only heuristic from rounded stdout: two published weight copies Qwen 1874 MiB and XLSR 2404 MiB > available 1732 MiB; one copy would leave 795 MiB / 530 MiB respectively, ignoring tokenizer, downloads, archive extraction, operating-system working space, and runtime memory. **No endorsement, download, quality metric or CP4 status advancement**. 5487 MiB is total RAM not available heap; battery 38°C only instantaneous proxy, not proven thermal stability.
- Added `storage_screen_approx_only` and `estimated_mib_after_one_weight_only` report fields, concise console storage caution, and **2 new unit tests** for 1732 MiB Sony snapshot and ample-space non-promotion. New expected suite count **23**, not yet independently run; user did not paste **21-test** suite output either. CI test path already watched in `.github/workflows/t10-engine-eval.yml`. Keep false for both `ready_for_model_download` and `ready_for_sony_inference` until exact candidate evidence, explicit user opt-in and pre-registered independent holdout.

### T10 NEXT OFFLINE ID-ASR FEASIBILITY — 23/23 SYNTHETIC WINDOWS TESTS PASS
- Verified from user terminal: `Ran 23 tests in 0.030s`, `OK` for `python -m unittest discover -s tools -p "test_t10_asr_next_feasibility.py" -v`. This closes the earlier **23-test Windows PENDING** caveat for `tools/t10_asr_next_feasibility.py`: Sony exact mount alias fixture, published weight-vs-storage heuristic for 1732 MiB free, negative tests for arbitrary mounts and accidental download permissions all passed synthetically.
- Scope remains **regression-suite PASS on Windows**, **read-only Sony snapshot already reported** (SO-03L arm64-v8a, 5487 MiB total RAM, 1732 MiB /data available, battery proxy 38°C), not Android inference, translation accuracy, model artifact verification, or an end-to-end export gate. Do not claim CI PASS merely from local 23 tests. Qwen INT8 and Wav2Vec2 Large remain research candidates only; no GB-scale download justified under conservative two-weight-copy safety heuristic. T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 NEW COMPACT INDONESIAN ASR — SOURCE SHA-PINNING / NO-DOWNLOAD PROTOCOL
- Public file/blob verification completed for two publisher-provided GGML Q8_0 artifacts, **not downloaded**: Maleo Base ID 81.8MB decimal SHA256 `2ac0dc902f477389be18d8b6f6fbe97695197c12ab1392b2f4bea23732c2cfe8` (https://huggingface.co/maleo-ai/whisper-base-id/blob/main/ggml-base-id-q8_0.bin), and Maleo Tiny ID 43.5MB decimal SHA256 `423455afe438ff3b0d1f23613a223d052f34a2482a8dd8ef6433f75ccbf33a17` (https://huggingface.co/maleo-ai/whisper-tiny-id/blob/main/ggml-tiny-id-q8_0.bin). Publisher model-card license metadata Apache-2.0 for both. These compare nominally favorably to Sony ~1732MiB free data while **runtime RAM, license compliance, user permission, device inference remain unverified**.
- Publisher self-reports FLEURS ID 15.0% (base) and 19.1% (tiny); not scored under SUBLOKA normalization/20 fixed clips/actual Android, and **FLEURS is listed as a training source** in their own model cards. Cannot honestly claim data-disjoint evaluation without audit. Separate independent newly recorded/consented speech holdout and frozen transcript provenance required before inferential promotion; don't alter original clean-ID 105/367 28.61% WER control. Additional Spacewave Zipformer2 ONNX INT8 ~71MB components self-reported FLEURS 8.96%, Android engine integration missing; research only.
- `tools/t10_asr_id_compact_protocol.py` implements **no-network, no-ADB, no-inference** catalog `list`, and optional user-provided local file integrity `verify` matching publisher SHA256, publisher displayed rough size; `verify` does not declare ASR quality PASS. 12 tests in `tools/test_t10_asr_id_compact_protocol.py` added and CI configured. New Windows/CI test results **PENDING** (old Sony feasibility 23/23 Windows PASS separate); no binary staged, checksum of actual local model unverified, no CP4 promotion.

### T10 COMPACT ID GGML — WINDOWS 12/12 PASS AND CATALOG NO-DOWNLOAD PASS
- User PowerShell output: **`Ran 12 tests in 0.243s` + `OK`** for `python -m unittest discover -s tools -p test_t10_asr_id_compact_protocol.py -v`; this includes source SHA pin assertions, size/corruption rejection, synthetic checksum verification, no-overwrite and CLI no-download guards.
- User then ran `python tools/t10_asr_id_compact_protocol.py list`: displayed Base Q8_0 81.8 MB / SHA `2ac0dc902f477389be18d8b6f6fbe97695197c12ab1392b2f4bea23732c2cfe8`, Tiny Q8_0 43.5 MB / SHA `423455afe438ff3b0d1f23613a223d052f34a2482a8dd8ef6433f75ccbf33a17`, both `LICENSE CLAIM apache-2.0`. Report footer explicitly: `NO DOWNLOAD | NO ADB | NO INFERENCE | FLEURS HOLDOUT INDEPENDENCE UNVERIFIED`, `T10 ACTIVE | CP4 BLOCKED | T11 TODO`.
- **Not verified:** actual downloaded model bytes/checksums, provenance disjoint from publisher FLEURS training, model-card WER on SUBLOKA FLEURS, any heldout model evaluation, Android performance/thermal/RSS, GH Actions CI outcome, or independent human translation signoff. Keep all release gates frozen and BLOCKED. Next candidate evaluation requires genuine independent human-verified audio references and declared consent/licensing; download only with user opt-in.

### T10 ID-INDEPENDENT ASR HOLDOUT — PRIVACY/CONSENT/CHECKSUM SCHEMA PREPARED
- Created `tools/t10_id_independent_holdout.py` and accompanying `tools/t10_id_independent_holdout.md`. Private workspaces are constrained to Git-ignored `.t10-benchmark/<name>`; `init` prepares 30 **incomplete** clean/challenging Indonesian sample rows with all person-level and audio evidence blanks/false. No actual human consent/transcripts/audio present in repository; `audit` must NOT pass for this template.
- `audit` validates original WAV SHA256, mono PCM16 16 kHz/1–30 s, in-workspace relative WAV path (no symlinks), exactly 20 clean + 10 challenging ordered sample IDs, 5 pseudonymous speakers, ≥250 normalized clean transcript words using frozen `tools/t10_wer.py` normalizer, unique audio/reference hashes, real-time timezone syntax, declared fresh collection/no public datasets, actual consent and human transcript review declarations. Flags are **not independently authenticated**; a script never certifies consent, independence from Maleo training, or human identity.
- `seal`/ `verify` create/read one-time private byte lock without plaintext references, fail on post-seal audio/manifest/reference changes. Synthetic-only test `tools/test_t10_id_independent_holdout.py` adds **19 unit cases** and is watched by `.github/workflows/t10-engine-eval.yml`. **Windows/CI run for 19 cases currently PENDING.** No host/Android model inference, local model download, real ASR WER or new CP4 evidence collected. Original clean-ID ASR 105/367 WER remains 28.61%; CP4 BLOCKED, T10 ACTIVE, T11 TODO.

### T10 PRIVATE ID HOLDOUT — 19 WINDOWS TESTS, ONE TEST ASSERTION FIX PENDING RERUN
- User's 2026-10-10 Windows log: 19 synthetic `test_t10_id_independent_holdout.py` test cases completed in 9.382 s, result **FAILED (failures=1)**. Only failure was `test_private_empty_init_is_not_real_dataset_and_cannot_overwrite`: actual secure validator message `Only pseudonymous speaker/reviewer IDs permitted`; expected test regex `permission`. Empty template also lacks pseudonymous IDs, so validator correctly rejects at first guard before its consent check. The dedicated `test_missing_consent_is_rejected` covers consent when earlier fields are filled synthetically.
- Patch to **test only** changes regex to `pseudonymous speaker/reviewer IDs` and comments on fail-closed order. No change to 30-slot init, consent requirements, WAV integrity, human review or existing CP4 thresholds. Updated **19/19 Windows result remains UNCONFIRMED** until host rerun; do not label suite as PASS merely because fix was committed. No model download, ASR inference or real human speech audit.

### T10 PRIVATE INDONESIAN HOLDOUT — 19/19 WINDOWS SYNTHETIC REGRESSION PASS
- **Actual user-host report:** `Ran 19 tests in 7.496s`, `OK` for `test_t10_id_independent_holdout.py` after fixing only the expected first fail-closed pseudonym validation error. Previous `19 tests FAILED (failures=1)` is superseded by this new Windows run. Unit suite verifies synthetic path, WAV SHA, schema, blank slots, private `.t10-benchmark` location, no fabricated consent/review, one-time manifest lock and never promoting CP4.
- **Scope limitation:** Windows **unit suite PASS**, not an authentic consent audit, independent real-human speech collection, new ASR accuracy, CI verification or Android/host inference. Local actual holdout workspace initialization **not yet reported**. Original ASR 105/367 = 28.61% WER, translation reviewer sign-off pending; T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 HOLDOUT WINDOWS PRIVATE INIT — 30 EMPTY SLOTS REPORTED SUCCESS
- User host PowerShell (2026-10-10): `git pull --ff-only origin main` updated `824cd3d..5d9681b`; `python tools/t10_id_independent_holdout.py init --workspace ".\\.t10-benchmark\\t10-id-holdout-new"` returned `PRIVATE HOLDOUT TEMPLATE INITIALIZED: .t10-benchmark\\t10-id-holdout-new 30 EMPTY SLOTS`, `NO REAL AUDIO, TRANSCRIPT OR CONSENT HAS BEEN VERIFIED`, `HUMAN INDEPENDENCE NOT AUTHENTICATED | NO DOWNLOAD | NO ADB | NO INFERENCE | CP4 BLOCKED`. No exception.
- Classification **INIT SUCCESS ONLY**, not `audit` PASS or immutable `seal` PASS. Private manifest/audio have not been uploaded or independently inspected. The 30 rows are empty placeholders with `consent_declared=false`, `human_reference_reviewed=false` as prescribed by source; do not infer any real participants. Latest 19 synthetic Windows tests separately PASS (`7.496s OK`); no model installed or inference. Do not run `audit` expecting PASS until actual human data is valid; no `seal` before collected, reviewed and ethically permitted data. T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 PRIVATE ID HOLDOUT — READ-ONLY 30-SLOT QA + GIT IGNORE PASS
- Observed actual user Windows PowerShell output after private init: `Total: 30`; `Clean: 20`; `Challenging: 10`; `Empty/unverified: 30`; count-validation `throw` did not execute. Emptiness predicate explicitly checked `consent_declared -ne $true`, `human_reference_reviewed -ne $true`, blank `reference`, blank `audio_sha256` for all 30 slots. This confirms **metadata template state**, not human speech quality or permissions.
- `git check-ignore "$workspace\\manifest.json"` returned `".\\.t10-benchmark\\t10-id-holdout-new\\manifest.json"`, confirming Git ignores this private file path. Raw private data was not committed or shared. No `audit`, `seal`, transcriptions, collection, host/Android ASR, model transfer or CP4 change. Previous 19 synthetic Windows tests remain PASS; next milestone is real consented audio plus human-reviewed references and hash audit. Status T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 PRIVATE HOLDOUT TOPIC KIT — IMPLEMENTED, 12 SYNTHETIC TESTS PENDING
- After actual user Windows QA proved **30 total / 20 clean / 10 challenging / 30 empty/unverified and `git check-ignore` positive**, created metadata-only generator `tools/t10_id_collection_kit.py` for the existing gitignored workspace. Plan consists of 30 UNIQUE short Indonesian *topic cues* (not approved reference transcriptions), evenly assigned 4 clean + 2 challenging per each of five suggested pseudonymous speakers. `create` makes private `collection_plan.json` write-once, refuses sealed holdout/manifest mismatch/public directory and never edits manifest or synthetic flags. `status` counts local placeholder progress only, no transcripts/speaker names/raw WAV printed.
- Added `tools/test_t10_id_collection_kit.py` **12 test methods**: category/sample ID order, cue uniqueness, balanced speaker plan, no invented reference/consent/audio, unchanged private manifest, overwrite refusal, aggregated counts, no unauthorized PII in stdout, malformed original slots reject, public directory reject, sealed holdout reject, CLI no-download. Tests are synthetic-only, no inference/network. CI watches/runs this suite from `.github/workflows/t10-engine-eval.yml`; **Windows test PASS and CI status PENDING**.
- Existing separate `tools/test_t10_id_independent_holdout.py` 19/19 Windows PASS. Human consent, real speech, reviewer independence and training-data disjointness remain UNAUTHENTICATED; model SHA locally not verified, no host/Sony inferencing, no WER or CP4 promotion. T10 ACTIVE / CP4 BLOCKED / T11 TODO.

### T10 COLLECTION TOPIC KIT — WINDOWS 12/12 PASS AND LOCAL PLAN CREATED
- User Windows stdout: `Ran 12 tests in 0.247s`, `OK` for `test_t10_id_collection_kit.py`. A subsequent `$LASTEXITCODE` guard did not throw. **12 synthetic test suite PASS (Windows only)**; GitHub Actions CI not independently inspected.
- Local `create` successfully generated **`.t10-benchmark/t10-id-holdout-new/collection_plan.json`**, with explicit stdout `NO RECORDINGS, REAL CONSENT OR HUMAN TRANSCRIPTS CREATED` and `NO MODEL DOWNLOAD | NO ADB | NO INFERENCE | T10 ACTIVE | CP4 BLOCKED`. The script creates private metadata only; local file bytes were not shared. Do not rerun `create` (write-once).
- Local `status` verified 30 slots = 20 clean + 10 challenging; **0 WAV present, 0 references filled, 0 audio hashes, 0 declared permissions, 0 declared human reviews, 0 fully declared rows**. These are intentionally non-authenticated counts, not `audit` or `seal` PASS; zero real human data reported. No new model download, host/Sony ASR inference, WER, consent claim, or CP4 status change.
- Next stage requires real informed permission and genuine independently recorded spoken Indonesian for new holdout, transcriptions manually checked against actual audio before model outputs, with per-file hashes; preserve private storage and existing frozen FLEURS benchmarks. Status **T10 ACTIVE / CP4 BLOCKED / T11 TODO**.

### T10 PUBLIC AUDIO SOURCE TRIAGE — UPSTREAM LOCATED, 14 TESTS PENDING
- Public-source research identified [`Atika88/Indonesian-ASR-11-Class-Dataset`](https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset), CC BY 4.0 publisher label, DOI-referenced commit `c65fe8bcff0547214c34cfbea248b4045a0d867c`, 104,368 publisher-identified human WAV, 132 synthetic repair WAV (excluded because commercial redistribution/training rights are not resolved for synthesis), 16k PCM16 mono and human test split. Audio is in 11 TAR category archives (~15.6GB total); **no archive or WAV has been downloaded**. Data is read prompted speech and has overlapping scripted prompts across speakers, not a novel spontaneous audio dataset. This is **NOT** the private consent holdout and no Maleo training non-overlap guarantee exists.
- Created `tools/t10_public_id_corpus.py`: `source` has no network; `fetch-metadata` downloads public CSV metadata only over HTTPS from immutable commit with 100 MiB cap, validates required fields/creates private file once and deletes partial corrupt files; `inspect` aggregates publisher human non-synthetic test rows by category, no transcript shown; `select` writes deterministic exactly-30 selected source metadata **without obtaining audio**. Rejects train/validation, synthetic/unknown synthetic marker, nonhuman rows, unsafe audio path, unsupported WAV format, out-of-range durations, too-small/large sample, duplicate reference; requires multiple public speaker labels and sensible word totals. Raw metadata/transcripts stored in gitignored `.t10-benchmark` only. Status always `CP4 BLOCKED`.
- Added 14 synthetic-only `tools/test_t10_public_id_corpus.py` tests to CI via `.github/workflows/t10-engine-eval.yml`. **14 Windows tests and CI PASS NOT RECEIVED**; assistant execution environment cannot fetch Hugging Face bytes due DNS, so no actual upstream metadata hash, archive SHA, WAV hash or audio transcript human review proven. The tool never runs ASR; original base FLEURS WER and the separate empty 30-slot consented holdout remain frozen. T10 ACTIVE / CP4 BLOCKED / T11 TODO.
