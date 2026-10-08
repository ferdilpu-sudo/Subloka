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

