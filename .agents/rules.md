# Aturan Implementasi

## R01 — Satu file, satu tanggung jawab

Tidak ada batas minimum/maksimum baris. Tentukan batas file dari tujuan, kohesi, dan alasan perubahan. Satu file boleh memiliki beberapa fungsi atau tipe yang bekerja untuk satu tujuan. Pisahkan UI, aturan domain, penyimpanan, dan engine jika alasan perubahannya independen. Jangan membuat wrapper atau interface tanpa batas integrasi yang nyata.

Setiap file baru harus dapat dijelaskan dalam satu kalimat spesifik. Hindari tempat penampungan seperti CommonUtils untuk fungsi yang tidak berkaitan. Jangan memecah file hanya demi panjangnya.

## R02 — Scope dan kode stabil

Perubahan harus terkait task aktif. Jangan upgrade dependency, refactor lintas fitur, mengganti formatter, atau menghapus kode stabil tanpa kebutuhan task yang tercatat. Bug di luar scope dicatat sebagai task terpisah. Lindungi perubahan pengguna dan data proyek.

## R03 — Offline sebagai kontrak

Transkripsi, terjemahan, edit, dan ekspor harus bekerja dengan jaringan mati setelah model siap. Dilarang fallback diam-diam ke API/cloud, menambahkan login, analytics cloud, atau monetisasi. Unduhan model harus eksplisit, bisa gagal dengan aman, dan tidak mengunggah media/transkrip. Izin jaringan untuk penyediaan model bukan izin memproses konten di server.

## R04 — Model dan dependency

Pin versi dependency dan revision native yang sudah dievaluasi; jangan gunakan versi dinamis. Catat sumber, lisensi, atribusi, ukuran, hash untuk model yang dikelola aplikasi, dan metode readiness untuk model yang dikelola SDK. Gunakan model ASR multilingual, bukan model English-only. Ukuran/performa tidak boleh dijanjikan sebelum benchmark. Jangan hardcode asumsi ukuran model yang belum diukur.

## R05 — Invariant subtitle

Waktu disimpan sebagai integer mikrodetik. Subtitle bilingual dalam satu segmen memiliki start/end yang sama. Identitas segmen stabil. Teks asli tidak ditimpa terjemahan. Edit asli menandai terjemahan stale; penerjemahan ulang tidak menimpa koreksi manual tanpa tindakan pengguna yang jelas. Penanganan split/merge wajib mengikuti schema.md.

## R06 — Concurrency dan lifecycle

Jangan jalankan inference/codec/I/O berat di main thread. Batasi satu job berat aplikasi aktif pada MVP. Simpan state job serta checkpoint hasil; penghentian proses tidak boleh dilaporkan sukses. Cancel harus menghentikan kerja dan membersihkan file parsial secara aman. Lifecycle Android dan aturan background execution harus diverifikasi terhadap target SDK saat implementasi.

## R07 — Media dan data pengguna

Video asli tidak dimodifikasi. Gunakan akses URI yang sah; jangan meminta akses semua berkas jika pemilih dokumen cukup. Hilangnya izin memunculkan alur tautkan ulang. File output dipublikasikan hanya setelah penulisan selesai. Hapus cache dan output parsial tanpa menghapus sumber. MVP menonaktifkan backup otomatis data sensitif aplikasi sampai kebijakan backup lokal diputuskan.

## R08 — Error dan observabilitas

Gunakan error domain terstruktur: MODEL_MISSING, MEDIA_UNAVAILABLE, NO_AUDIO, UNSUPPORTED_MEDIA, STORAGE_FULL, PROCESS_INTERRUPTED, MODEL_FAILURE, EXPORT_FAILURE. Pesan UI harus menyebut tindakan pemulihan. Log lokal secukupnya: job ID, tahap, durasi, kode error; tidak memuat teks pribadi penuh atau data biner. Retry harus idempotent dan tidak menggandakan segmen/output.

## R09 — Bukti dan status

Gunakan status plan.md dan format bukti testing.md. Dilarang menulis “berjalan”, “lulus”, “siap rilis”, atau “offline teruji” tanpa bukti sesuai klaim. Pisahkan sudah dibuat, sudah diuji, dan belum terverifikasi. Ketiadaan SDK/perangkat adalah keterbatasan yang harus dilaporkan, bukan alasan mengarang keberhasilan.

## R10 — Dokumentasi wajib

Task belum DONE jika docs belum sinkron. Setelah tes lulus, update plan.md, testing.md, dan dokumen spesifikasi yang berubah sebelum pindah task. Catat risiko yang tersisa secara spesifik. Dilarang menyalin status task ke banyak file hingga saling bertentangan: plan.md adalah ledger, README hanya ringkasan milestone.

## R11 — Pengujian proporsional

Uji risiko nyata: timing, data loss, migrasi, bilingual stale state, offline inference, lifecycle, render. Jangan menambah test yang hanya mengulang implementasi tanpa menguji perilaku. Perubahan dokumentasi cukup diuji dengan konsistensi scope, tautan, dependency task, aturan status, dan guardrail UX.

## R12 — Interaction model produk

MVP adalah focused caption editor, bukan general video editor. Aturan hierarki interaksi:

1. **Caption adalah pekerjaan utama.** Workspace Caption menjadi default ketika hasil tersedia.
2. **Video adalah konteks.** Preview cukup besar untuk memeriksa sinkronisasi dan posisi subtitle, tetapi tidak boleh mengambil seluruh ruang kerja pada video 9:16.
3. **Timeline bersifat kontekstual.** Timeline/detail timing hanya menjadi fokus di workspace Timing; jangan memaksa user mengedit caption melalui kotak timeline kecil pada mode default.
4. **Translation adalah state/action.** Jangan membuat workspace Translation terpisah pada MVP. Status MISSING/CURRENT/STALE/FAILED dan retranslate tampil pada segmen atau ringkasan project.
5. **Style adalah secondary tool.** Jangan menambahkan efek video, keyframe, karaoke per kata, font katalog besar, gradient, atau animasi tanpa perubahan scope tertulis.
6. **Export adalah final action.** Jangan jadikan Export sebagai bottom-nav destination.
7. **Import dan Process adalah flow/state.** Bukan area permanen yang harus ditampilkan sebagai tab global.

## R13 — UX change discipline

- Jangan redesign jika polish atau perbaikan lokal menyelesaikan masalah.
- Setiap proposal perubahan besar harus punya problem statement dan acceptance criteria.
- Pisahkan defect usability/accessibility/consistency dari preferensi estetika.
- Gunakan severity P0–P3 sesuai AGENTS.md; kerjakan P0/P1 sebelum P3.
- Satu layar harus punya hierarchy aksi yang jelas. Hindari beberapa primary action yang bersaing.
- Gunakan progressive disclosure untuk opsi jarang dipakai.
- Jangan menambah bottom navigation pada MVP tanpa ADR baru dan bukti ada ≥3 destination setara yang memang perlu perpindahan sering.

## R14 — Adaptive UI, keyboard, dan aksesibilitas

- Susunan UI mengikuti **available window size**, bukan hanya orientation flag.
- Compact: preview + workspace stacked. Expanded: preview/main pane + supporting editor pane bila ruang cukup.
- Preview memiliki maximum workspace height; video portrait tidak boleh memonopoli layar.
- Saat keyboard aktif, preview boleh menjadi compact tetapi selected caption dan field aktif harus tetap terlihat.
- Touch target interaktif rancangan minimum 48 dp kecuali ada alasan platform yang didokumentasikan.
- Status tidak boleh hanya dibedakan warna. Field bilingual selalu memakai label bahasa/role.
- Gesture presisi seperti drag timing wajib punya alternatif eksplisit, misalnya input waktu atau nudge.
- Font scale besar, TalkBack/focus order, state disabled/error, dan kontras diuji sesuai testing.md.
