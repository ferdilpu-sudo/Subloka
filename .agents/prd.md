# Product Requirements Document

## Tujuan dan status

Membantu kreator menghasilkan, mengoreksi, menerjemahkan, dan mengekspor subtitle bilingual Inggris–Indonesia dari satu video tanpa biaya API dan tanpa mengirim konten ke server. Kebutuhan inti dikonfirmasi pengguna pada 2026-10-06. Arah UX v0.2 mengunci produk sebagai **focused bilingual caption editor**, bukan editor video umum.

Detail model, toolchain, target perangkat, performa, dan kompatibilitas tetap harus dibuktikan melalui checkpoint.

## Pengguna dan kasus utama

Kreator vlog/mini drama mengimpor video berbahasa Indonesia, memperbaiki transkrip, menerjemahkan ke Inggris, mengoreksi timing/style bila perlu, lalu mengekspor video dengan dua bahasa. Arah Inggris ke Indonesia harus memiliki kemampuan yang setara. Pengguna dapat mengoreksi hasil AI sebelum publikasi.

Tujuan utama pengguna bukan mengedit video. Tujuan utama adalah membuat caption bilingual yang benar, sinkron, terbaca, dan siap diekspor.

## Prinsip produk

1. **Caption first:** caption adalah objek kerja utama; video adalah konteks untuk menilai timing dan layout.
2. **Offline by design:** setelah model siap, alur inti bekerja tanpa jaringan.
3. **Human in control:** hasil ASR/translation dapat dikoreksi; edit manual tidak boleh ditimpa job lama.
4. **Progressive disclosure:** tampilkan kontrol yang relevan untuk task saat ini; opsi lanjutan tidak memenuhi layar default.
5. **Calm editor:** state penting terlihat jelas tanpa badge/peringatan berlebihan.
6. **Adaptive:** UI tetap dapat digunakan pada layar compact, landscape, tablet/window besar, keyboard aktif, dan font scale besar.

## User journey utama

```text
Home / Projects
    ↓
New Project
    ↓
Pilih video + bahasa sumber
    ↓
Siapkan model bila belum siap
    ↓
Generate caption (processing state)
    ↓
Editor
  ├─ Caption (default)
  ├─ Timing
  └─ Style
    ↓
Export
```

Import, processing, dan export adalah bagian flow proyek; bukan destination global setara Home/Editor.

## Kebutuhan fungsional

| ID | Kebutuhan | Kriteria penerimaan |
|---|---|---|
| FR01 | Penyiapan model | Status model terlihat; unduhan gagal dapat diulang; proses tidak dimulai jika model belum siap; model yang sudah siap tetap digunakan tanpa jaringan; copy menjelaskan pemrosesan konten dilakukan di perangkat |
| FR02 | Proyek lokal | Home menampilkan project recent dan satu primary action New Project; buat, buka, rename, hapus proyek; hapus proyek tidak menghapus video asli; perubahan tersimpan saat layar dibuka ulang |
| FR03 | Impor video | New Project menggabungkan pilih video + source language; target language otomatis; satu sumber per proyek; durasi/rotasi terbaca; no-audio, unsupported media, URI hilang punya recovery jelas |
| FR04 | Transkripsi | Source language EN atau ID; hasil berupa source text + timing; processing ditampilkan sebagai state dengan stage/progress nyata; audio tanpa ucapan tidak menghasilkan dialog palsu yang dianggap valid |
| FR05 | Terjemahan dua arah | EN→ID dan ID→EN offline; source dipertahankan; translation status MISSING/CURRENT/STALE/FAILED terlihat secara kontekstual; bulk refresh tersedia bila ada beberapa stale segment |
| FR06 | Editor Caption | Workspace Caption menjadi default; source dan translation dapat diedit terpisah; list segmen mudah dipindai; split/merge; undo/redo dalam sesi; keyboard tidak menutup field aktif dan preview boleh mengecil |
| FR07 | Editor Timing | Timing menggunakan interval bersama untuk dua bahasa; start/end dapat diedit; drag bila tersedia memiliki alternatif input/nudge; tidak ada waktu negatif, terbalik, overlap, atau melebihi video |
| FR08 | Bilingual dan Style | Mode source-only, translation-only, dual; urutan bahasa dapat dibalik; font bundled/local, ukuran/warna per bahasa, outline/background, alignment, posisi pasangan subtitle; preview/export konsisten |
| FR09 | Ekspor MP4 | Export adalah final action; validasi mode caption jelas; output baru, subtitle sesuai mode/style/timing, audio tetap ada, orientasi benar; cancel/failure tidak menerbitkan video parsial sebagai sukses |
| FR10 | Ekspor SRT | Pilihan asli, terjemahan, atau keduanya sebagai dua file terpisah; UTF-8, nomor berurutan, timestamp valid; SRT tidak menjanjikan style/font |
| FR11 | Pemulihan | Job terputus ditandai interrupted, checkpoint dipertahankan; retry tidak menggandakan hasil; perubahan pengguna tidak ditimpa job lama; save failure terlihat dan dapat dipulihkan |
| FR12 | Privasi/offline | Semua alur setelah penyiapan lulus mode pesawat; tidak ada upload konten, login, fallback online, analytics cloud, atau API berbayar |

## Alur dan aturan editorial

1. Home tidak memakai bottom navigation pada MVP. User membuka recent project atau membuat project baru.
2. New Project meminta video dan source language. Target language otomatis menjadi bahasa satunya.
3. Bila model belum siap, user menyiapkan model sebelum generation. UI tidak memaksa user memahami nama engine internal.
4. Generation menampilkan stage aktual. Bila persentase belum diketahui, gunakan indeterminate; jangan membuat angka palsu.
5. Setelah hasil tersedia, user masuk workspace **Caption** secara default.
6. User beralih ke **Timing** hanya ketika perlu mengoreksi sinkronisasi, dan ke **Style** ketika perlu mengubah presentasi.
7. Perubahan source tidak langsung mengganti translation manual; tandai translation stale dan berikan retranslate kontekstual.
8. Mode default dual: source di atas, translation di bawah. Kedua bahasa tidak harus memiliki jumlah baris yang sama.
9. Bila translation kosong/stale/failed, user dapat memperbaiki atau mengekspor source-only; export yang membutuhkan translation diblokir sampai lengkap/current.
10. Preview layout menyesuaikan 9:16, 16:9, dan rasio lain tanpa auto-crop. Preview portrait memiliki batas tinggi sehingga editor tetap dapat digunakan.
11. Subtitle idealnya ringkas; hard maximum rancangan dua baris per bahasa. Jika hasil sulit dibaca, tampilkan warning dan tindakan seperti split segment/perkecil font, bukan memotong diam-diam.

## Target kualitas dan nonfungsional

- **NFR01 Data safety:** tidak ada data loss untuk perubahan yang sudah dikonfirmasi tersimpan; penulisan menggunakan transaksi dan feedback saving/saved/error yang tidak bising.
- **NFR02 Responsiveness:** kerja berat di luar main thread; cancel/progress tetap merespons. Angka performa ditetapkan setelah T10.
- **NFR03 Model quality:** transkrip/translation memenuhi gate testing.md; slang, musik dan overlap dievaluasi terpisah.
- **NFR04 Resource:** satu job berat aktif; video panjang diproses bertahap, bukan seluruh PCM dimuat ke RAM.
- **NFR05 Accessibility & adaptive UI:** touch target minimum rancangan 48 dp; screen-reader label/focus order benar; status tidak hanya warna; drag timing punya alternatif; compact/expanded/keyboard/font-scale diuji.
- **NFR06 Export integrity:** hasil ekspor dapat diputar ulang, tidak kosong, sinkron, dan selesai atomik sebelum ditandai berhasil.
- **NFR07 Interaction clarity:** satu primary action jelas per layar; Caption/Timing/Style memiliki tanggung jawab berbeda; timeline tidak menjadi pusat editor default; tidak ada destination global yang tidak perlu.

## Batas MVP

Termasuk: EN/ID dipilih manual, caption per segmen, satu video, koreksi bilingual, timing, style statis, MP4 H.264/AAC kandidat, SRT terpisah, autosave lokal, job recovery, adaptive editor dasar.

Sasaran ekspor awal 720p/1080p SDR sesuai kemampuan perangkat; profil final ditentukan T10/T14. Input codec, HDR, variable frame rate, dan 4K tidak dianggap otomatis didukung.

Di luar MVP: live caption, audio aplikasi lain, cloud/API translator, akun, sync, dubbing, deteksi speaker, multi-video timeline, trimming/cutting video, transition/effect video, karaoke per kata, batch proyek, subtitle impor, bahasa selain EN/ID, auto-detect code-switching, ekspor 4K/HDR terjamin, katalog font besar, gradient/animated caption. Penambahan membutuhkan perubahan scope tertulis.

## Definisi selesai produk

Seluruh FR/NFR wajib punya evidence sesuai testing.md, checkpoint rilis lulus, tidak ada bug kritis kehilangan data, interaction model T03/CP2 telah ditinjau, serta tidak ada klaim kompatibilitas tanpa perangkat yang diuji. Kualitas model, ukuran unduhan, batas video, dan waktu proses dipublikasikan berdasarkan hasil aktual.
