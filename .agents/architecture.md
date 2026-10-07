# Arsitektur Aplikasi

Status: baseline diimplementasikan sampai T08 untuk frontend, domain, dan persistence lokal. Media/ASR/translation/export produksi masih mengikuti task berikutnya. Tidak ada backend server; seluruh komputasi konten dirancang lokal dan jaringan hanya untuk penyiapan model yang disetujui pengguna.

## Stack dan batas kepastian

| Komponen | Pilihan rancangan | Gate |
|---|---|---|
| UI | Kotlin, Jetpack Compose, ViewModel/StateFlow | T02, T04–T07 |
| Penyimpanan | Room 2.8.5 untuk project/caption/style; preference tambahan belum diperlukan | T08 DONE |
| Pemutar / ekspor | Media3 player dan Transformer | T09, T14 |
| Decode audio | Android extractor/decoder + konversi PCM eksplisit | T09 |
| ASR | whisper.cpp multilingual melalui JNI | T10–T11 |
| Translate | ML Kit on-device EN↔ID | T10, T12 |
| Job | Koordinator lokal, runner foreground sesuai aturan OS | T13 |

T02 menetapkan baseline: AGP 9.4.0, Gradle 9.6.0, Kotlin/Compose compiler 2.3.21, Compose BOM 2026.09.00, minSdk 26, compile/target SDK 37, Media3 1.11.1, Room 2.8.5, ML Kit Translate 17.0.3. whisper.cpp v1.9.4 menjadi kandidat evaluasi T10, bukan engine yang dianggap lulus. NDK baseline kandidat 28.2.13676358 mengikuti default AGP 9.4 saat native stage dimulai; ABI awal evaluasi arm64-v8a, perlu keputusan setelah benchmark. Sony SO-03L Android 11 dicatat sebagai perangkat uji primer yang pernah tersedia, tetapi koneksi/performa pada proyek ini belum diverifikasi.

## Struktur berdasarkan tanggung jawab

Struktur Gradle aktual sampai T08: `app` sebagai composition root; `core:domain` kontrak/model murni; `core:database` Room + persistence facade; `core:media` URI/decode/player adapter; `core:subtitle-renderer` layout subtitle; `core:designsystem` token/komponen bersama; `engine:asr` native; `engine:translation` SDK lokal. Fitur: `feature:projects`, `feature:models`, `feature:editor`, `feature:export`. Processing adalah state/job yang dipresentasikan di konteks project/editor, bukan feature destination terpisah. Nama namespace final ditetapkan T02.

Modul tidak berarti setiap folder/fungsi perlu Gradle module. Pecah lebih jauh hanya karena isolasi native, kontrak, atau alasan perubahan yang konkret. Fitur projects menangani metadata proyek; editor menangani revisi subtitle; database hanya adapter persistensi, bukan pemilik aturan editorial.

## Arah dependensi

`app` merangkai fitur, adapter, dan job coordinator. Fitur bergantung pada kontrak domain dan komponen UI/media yang diperlukan. Engine dan database mengimplementasikan kontrak domain; domain tidak mengenal Android, Room atau JNI. Fitur tidak mengakses tabel fitur lain secara langsung. Export menggunakan snapshot subtitle dan shared renderer, bukan membaca state UI yang berubah.

Kontrak utama: ProjectRepository, CaptionRepository, MediaSource, SpeechTranscriber, OfflineTranslator, ModelReadiness, SubtitleLayoutEngine, VideoExporter, JobStore. Interface dibuat hanya di batas nyata yang perlu fake atau adapter. Presentation state compact/expanded/keyboard tidak boleh masuk kontrak domain; satu state editor yang sama dikomposisikan berbeda berdasarkan ruang jendela.


## Arsitektur presentasi editor

Interaction model UI memiliki tiga workspace: `CAPTION`, `TIMING`, `STYLE`. Ini adalah state presentasi, bukan tiga domain terpisah. Translation status berasal dari domain (`MISSING/PENDING/CURRENT/STALE/FAILED`) dan dirender sebagai state/action kontekstual; jangan membuat pipeline translation bergantung pada keberadaan tab UI.

`EditorViewModel`/presenter kandidat menyatukan snapshot project, selected segment, playback position, active workspace, save feedback, dan job status melalui kontrak domain. Jangan menyimpan seluruh draft UI sebagai blob. Text draft yang belum flush boleh hidup di presentation state; commit ke repository mengikuti aturan autosave/schema.

Adaptive UI menggunakan satu sumber state:

- compact: preview + workspace stacked;
- expanded: preview/main pane + supporting editor pane;
- keyboard active: preview dapat diperkecil tanpa menghilangkan selected editor.

Breakpoint/window-size policy adalah keputusan T03/T04 berdasarkan Compose/toolchain aktual. Domain, repository, engine, dan renderer tidak boleh bercabang berdasarkan orientation.

Processing generation dan export direpresentasikan sebagai job state. UI boleh menampilkan processing sebagai halaman/state dalam navigation flow, tetapi tidak membuat destination global permanen hanya karena implementasi job berada di modul terpisah.

## Alur pemrosesan

1. MediaSource memvalidasi URI, metadata, track audio dan izin.
2. Decoder menghasilkan PCM bertahap. Konversi sample rate/channel mengikuti input engine terpilih; verifikasi bukan sekadar mengganti header WAV.
3. ASR bekerja per chunk, membawa offset waktu absolut. Overlap antarchunk dideduplikasi; output silence dan timestamp tidak valid disaring berdasarkan kebijakan teruji.
4. Caption segmenter menyusun kalimat dan timing tanpa menciptakan ucapan baru. Hasil disimpan ke staging job, kemudian dipublikasikan sebagai revisi saat aman.
5. Translator membaca snapshot teks sumber. Hasil hanya diterapkan jika source revision dan status edit masih cocok; hasil usang ditolak.
6. Editor menyimpan transaksi lokal. Terjemahan manual tidak ditimpa secara otomatis.
7. Export membuat snapshot immutable; shared renderer menghitung teks/style menggunakan timestamp frame. Ekspor ke file sementara lalu finalisasi tujuan setelah sukses.

VAD, chunk size, overlap, dan model adalah parameter yang harus dievaluasi T10. Tidak menjanjikan timestamp per kata; karaoke di luar MVP. Terjemahan awal per segmen, dengan segmentasi kalimat yang masuk akal; jangan memakai penggabungan konteks yang menghilangkan pemetaan segmen.

## Sinkronisasi preview dan ekspor

Satu definisi layout mengubah style ternormalisasi menjadi posisi piksel pada oriented video content rectangle. Preview harus memperhitungkan letterboxing/rotasi. Export memakai waktu media mikrodetik, bukan wall clock. Cari segmen aktif dengan interval setengah terbuka [start,end). Font, line break, outline, urutan bahasa dan background mengikuti shared renderer; T14 membuktikan kesetaraan dengan frame pada boundary.

## Job, lifecycle, recovery

Koordinator mengizinkan satu pekerjaan berat pada MVP. Job menyimpan stage, progress nyata, snapshot revision, checkpoint, error, dan cancellation flag. Checkpoint ASR/translation bisa diteruskan jika versi engine/model/sumber sama; export terputus diulang dari awal kecuali dukungan resume terbukti. Jangan menjanjikan resume native di tengah chunk.

Jika proses OS mati, job RUNNING/CANCELLING menjadi INTERRUPTED setelah pemeriksaan kepemilikan job. Checkpoint terakhir tetap tersimpan. Runner foreground dan notifikasi dipilih berdasarkan aturan SDK yang diverifikasi; jangan mengandalkan loop Activity atau WorkManager sebagai janji proses tak terbatas. Kebijakan pause ketika app background merupakan fallback yang jujur jika diperlukan.

## Model dan jaringan

whisper model: manifest sumber/version/byte/hash, unduh ke temp, validasi, pindah atomik. Model ML Kit: dikelola SDK; readiness melalui API yang tersedia, tidak mengarang path/hash internal. Bebaskan model setelah job dan jangan memuat ASR serta translator bersamaan jika meningkatkan risiko RAM.

Tidak ada HTTP client untuk upload konten. Network dependency SDK harus ditinjau; lulus mode pesawat membuktikan kerja tanpa koneksi, sedangkan audit dan observasi trafik memeriksa klaim tidak mengirim konten ketika koneksi hidup. Tidak mengklaim SDK sama sekali tidak mengirim metadata tanpa pemeriksaan.

## Sumber teknis untuk implementasi

- [whisper.cpp Android](https://github.com/ggml-org/whisper.cpp/tree/master/examples/whisper.android)
- [ML Kit translation Android](https://developers.google.com/ml-kit/language/translation/android)
- [Media3 Transformer](https://developer.android.com/media/media3/transformer)

Tautan mendukung arah evaluasi, bukan bukti bahwa integrasi proyek ini telah diuji. Setiap perubahan arsitektur baru membutuhkan ADR di decisions.md dan update task terkait.
