# Catatan Keputusan

Status keputusan: ACCEPTED = kebutuhan/keputusan telah disepakati; PROPOSED = arah rancangan menunggu tinjauan atau bukti; SUPERSEDED = diganti ADR baru, tidak dihapus. ACCEPTED tidak berarti sudah diimplementasikan/diuji. Evidence runtime berada di testing.md.

| ID | Keputusan | Status | Dasar / konsekuensi |
|---|---|---|---|
| ADR-001 | Android editor caption video | ACCEPTED | Pengguna memilih editor caption video, bukan live caption |
| ADR-002 | Seluruh proses konten offline, tanpa API berbayar | ACCEPTED | Instruksi pengguna; model disiapkan sekali, tidak ada fallback cloud |
| ADR-003 | Bilingual EN↔ID dengan timing bersama | ACCEPTED | Audio English → English+Indonesia dan sebaliknya |
| ADR-004 | Satu file satu tanggung jawab, tanpa batas baris | ACCEPTED | Struktur berdasar kohesi, bukan kuota baris |
| ADR-005 | Task/dependency/checkpoint/DoD serta docs update wajib | ACCEPTED | DONE mensyaratkan bukti dan dokumentasi sinkron |
| ADR-006 | Status dibuat, diuji, belum terverifikasi dipisah | ACCEPTED | Tidak menyamakan kode ada dengan fitur terbukti |
| ADR-007 | Native Kotlin/Compose dan Room | PROPOSED | Fokus Android, integrasi native/media lokal; versi final T02 |
| ADR-008 | whisper.cpp multilingual untuk ASR | PROPOSED | RAM, WER dan latensi wajib benchmark T10 |
| ADR-009 | ML Kit on-device EN↔ID | PROPOSED | Kualitas dialog, readiness, ketentuan SDK dan trafik perlu diperiksa |
| ADR-010 | Media3 untuk playback dan ekspor | PROPOSED | Timed bilingual overlay dan codec diuji T14 |
| ADR-011 | Tanpa akun/server, proyek lokal | ACCEPTED | Sesuai kebutuhan offline; backup cloud tidak masuk MVP |
| ADR-012 | UI lebih dahulu, lalu engine lokal, lalu integrasi | ACCEPTED | Fake UI tidak diklaim sebagai fitur AI selesai |
| ADR-013 | Satu video dan satu job berat aktif | PROPOSED | Menjaga lingkup dan RAM; batch/multitrack tidak diperlukan MVP |
| ADR-014 | Unduhan awal model diperbolehkan | ACCEPTED | User memilih offline tanpa biaya API; setup model eksplisit sebelum alur offline |
| ADR-015 | Subtitle per segmen, SRT asli/terjemahan terpisah | ACCEPTED | Dua bahasa berbagi timing; karaoke per kata/style SRT tidak dijanjikan |
| ADR-016 | Produk diarahkan sebagai focused bilingual caption editor, bukan general video editor | ACCEPTED | Audit UX + permintaan update paket; caption menjadi hero dan video hanya konteks |
| ADR-017 | Editor hanya memiliki workspace utama Caption, Timing, Style | ACCEPTED | Mengurangi beban kognitif; Caption default, timeline hanya fokus pada Timing |
| ADR-018 | Translation adalah state/action kontekstual, bukan workspace utama | ACCEPTED | Status stale/missing/current/failed melekat pada caption; menghindari mode keempat yang redundant |
| ADR-019 | Import/Processing/Export adalah flow/state project, bukan destination global | ACCEPTED | IA lebih dangkal; tidak ada kebutuhan bottom navigation pada MVP |
| ADR-020 | UI adaptif berdasarkan available window size; portrait 9:16 memiliki bounded preview | ACCEPTED | Editor harus tetap usable pada compact/expanded/keyboard; orientation saja tidak cukup |
| ADR-021 | Discipline audit UI memakai kategori defect dan severity P0–P3 | ACCEPTED | Mencegah aesthetic preference menyamar sebagai requirement dan mengutamakan blocker/friction |
| ADR-022 | Nama kerja produk **SubLoka**; applicationId sementara `app.subloka.caption` | ACCEPTED | Pendek, mudah diucapkan, mengomunikasikan subtitle + lokal; ID masih boleh berubah sebelum distribusi publik |
| ADR-023 | Baseline Android frontend memakai AGP 9.4.0 / Gradle 9.6.0 / Kotlin 2.3.21 / compile-target 37 / min 26 | ACCEPTED | Versi stabil saat eksekusi; minSdk 26 tetap mencakup perangkat uji Android 11 dan mengurangi kompatibilitas lama |
| ADR-024 | Frontend T04–T07 memakai fake adapter dan disclosure `DEMO` permanen sampai engine nyata terhubung | ACCEPTED | Memungkinkan validasi flow tanpa mengarang keberhasilan ASR/translation/export |
| ADR-025 | T10 membandingkan whisper.cpp v1.9.4 multilingual `tiny` dan `base`; synthetic smoke tidak boleh menutup CP4 | ACCEPTED | Upstream Android merekomendasikan tiny/base; model dipin dengan SHA-256; keputusan final menunggu WER/resource perangkat fisik |
| ADR-026 | T10 mengevaluasi ML Kit Translation 17.0.3 EN↔ID dengan explicit model readiness | ACCEPTED | EN/ID didukung on-device; input diproses lokal, tetapi SDK dapat melakukan model/update/metrics traffic sehingga disclosure privasi harus presisi |

## Rationale keputusan teknis

ADR-007: native dipilih sebagai arah karena hanya Android yang diminta dan pemrosesan memerlukan decoder, lifecycle dan JNI. Cross-platform menambah lapisan yang belum dibutuhkan. Tidak memilih versi toolchain dari ingatan; pin versi yang berhasil dibangun.

ADR-008: pilih model multilingual, karena English-only tidak memenuhi bahasa Indonesia. Kandidat model kecil dibandingkan pada dataset EN/ID, bukan langsung mengunci model besar. Jika benchmark gagal, opsi sah ialah optimasi, model lokal lain, atau penyesuaian dukungan dengan persetujuan; tidak boleh beralih ke API tanpa permintaan pengguna.

ADR-009: translation lokal harus dinilai untuk dialog informal, negasi, nama dan angka. Koreksi manual selalu tersedia. “Tanpa biaya API” bukan klaim hasil translation setara layanan cloud atau SDK bebas dari ketentuan distribusi.

ADR-010: shared layout diperlukan agar preview dan video tidak berbeda. Overlay statis saja tidak membuktikan subtitle bertiming; T14 wajib membuktikan pergantian teks per timestamp. Codec/resolusi akhir mengikuti kemampuan nyata perangkat.

ADR-012: seluruh dokumen fase boleh dirancang sekarang; implementasi mengikuti checkpoint. Untuk aplikasi ini istilah backend berarti adapter penyimpanan dan engine lokal, bukan server.

## Rationale keputusan UX v0.2

ADR-016 sampai ADR-021 adalah guardrail produk, bukan sekadar preferensi visual. Dampaknya:

- Home sederhana dengan recent project + New Project.
- Tidak ada bottom navigation pada MVP.
- New Project menggabungkan import dan language source.
- Processing ditampilkan dalam konteks project.
- Caption adalah workspace default setelah generation.
- Timeline/detail timing tidak memenuhi workspace Caption.
- Translation stale/missing/current/failed muncul di segmen dan dapat diringkas untuk bulk action.
- Style tidak berkembang menjadi editor efek video.
- T03/CP2 harus membuktikan compact, expanded, keyboard, error, empty, stale, dan export states sebelum UI produksi.

Perubahan terhadap interaction model ini memerlukan ADR pengganti, bukan improvisasi saat implementasi.

## Pertanyaan terbuka dan pemilik penyelesaian

| ID | Pertanyaan | Task | Dampak jika belum terjawab |
|---|---|---|---|
| OQ01 | Nama produk/package ID final? | T01–T02 | **Sebagian terjawab:** SubLoka dipakai sebagai nama kerja dan `app.subloka.caption` sebagai ID sementara; brand/package baru final saat release packaging |
| OQ02 | HP target, RAM/OS dan perangkat tes yang tersedia? | T01 | **Baseline:** Sony SO-03L Android 11 sebagai perangkat primer yang pernah tersedia; RAM/koneksi aktual dan perangkat tambahan masih perlu verifikasi saat device test |
| OQ03 | Durasi/resolusi video paling sering? | T01/T10 | Belum ada profil penggunaan aktual; benchmark wajib memakai fixture 30 dtk / 2 mnt / 10 mnt, 720p dan 1080p, portrait + landscape sebelum batas dukungan diklaim |
| OQ04 | Model ASR mana yang memenuhi akurasi dan resource? | T10 | Tiny/base berhasil functional smoke; pilihan final tetap terbuka sampai benchmark manusia/perangkat fisik CP4 |
| OQ05 | Apakah translation lokal memenuhi kualitas dialog EN/ID? | T10/T12 | ML Kit readiness + bidirectional smoke PASS; kualitas 30 segmen per arah masih wajib sebelum CP4 |
| OQ06 | Versi SDK/native, min SDK, ABI, runner background? | T02/T13 | Build/lifecycle harus diverifikasi sesuai versi pilihan |
| OQ07 | Input codec/HDR/VFR dan profil ekspor yang didukung? | T09/T14 | Tampilkan unsupported yang jelas; tidak menjanjikan semua format |
| OQ08 | Distribusi APK/model, lisensi/atribusi dan metadata SDK? | T10/T16 | Rilis tertahan jika kebutuhan distribusi tidak terpenuhi |
| OQ09 | Breakpoint/window size Compose final dan ukuran preview compact? | T03/T04 | Harus ditentukan lewat wireframe/prototype dan device/window test, bukan angka arbitrer |
| OQ10 | Nama produk/brand visual dan app icon? | Setelah interaction model stabil | Tidak menghalangi T01–T04; jangan mencampur branding dengan usability gate |

## Template ADR baru

```text
ID / tanggal / status:
Konteks dan masalah:
Pilihan yang dibandingkan:
Keputusan dan alasan:
Konsekuensi terhadap scope, data, UI, resource:
Task dan dokumen terdampak:
Bukti / referensi:
Persetujuan jika diperlukan:
Menggantikan ADR:
```

Keputusan lama tidak dihapus ketika berubah; tandai SUPERSEDED dan tautkan ADR pengganti. Jangan menandai PROPOSED menjadi ACCEPTED hanya karena kode telanjur ditulis.
