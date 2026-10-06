# Pengujian, Gate, dan Bukti

Dokumen ini membedakan strategi yang belum dijalankan dari bukti aktual. Tanggal baseline 2026-10-06. Build dan lint Android frontend telah berhasil dijalankan melalui GitHub Actions; runtime pada emulator/perangkat fisik belum diverifikasi. Pemeriksaan statis lokal tetap dicatat terpisah agar bukti compile tidak disamakan dengan bukti usability/runtime.

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

### DEVICE-001 — Sony SO-03L Android 11 smoke test

- Task: T04–T07.
- Result: **NOT_RUN**.
- Alasan: perangkat tidak terhubung ke workspace eksekusi ini.
- Expected ketika dijalankan: install debug APK; flow Projects → New Project → Model Setup → Processing → Editor → Export; compact layout; IME; state STALE; blocked dual export; back behavior; no crash.

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
