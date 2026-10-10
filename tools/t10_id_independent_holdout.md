# T10 — Holdout ASR Bahasa Indonesia Independen (RESEARCH ONLY)

Dokumen ini adalah pedoman **pengumpulan data baru**, bukan dataset nyata. Hingga rekaman, transkrip, izin, dan peninjauan sebenarnya tersedia, **tidak ada Human QA atau CP4 PASS yang boleh diklaim**.

## Tujuan dan pemisahan dari benchmark lama

- Baseline asli SUBLOKA: Whisper Base, 20 audio clean-ID FLEURS, **105 kesalahan / 367 kata = 28,61% WER**. Jangan menulis ulang manifest/asr-results baseline atau melonggarkan target CP4.
- Model Maleo Base/Tiny-ID mencantumkan FLEURS sebagai sumber pelatihan; skor FLEURS pada kartu model **bukan bukti evaluasi independen**. Data yang akan disiapkan di sini harus berupa rekaman Bahasa Indonesia **baru** di luar korpus publik dan tidak dibuat/dipilih berdasarkan prediksi model.
- Holdout riset ini menuntut **20 clean + 10 challenging**, **≥5 pembicara berbeda** dengan ID pseudonim, dan **≥250 kata acuan clean** setelah normalisasi `tools/t10_wer.py`. Ini syarat *holdout penelitian tambahan*, **bukan perubahan gate CP4**. Penilai transkrip bekerja tanpa melihat prediksi engine dan tidak menggunakan output AI sebagai alasan mengesahkan manusia.
- Perencanaan, urutan, kategori, metode normalisasi, jumlah dan kriteria stop harus selesai **sebelum** menguji model pada audio mana pun. Jangan memilih hanya klip termudah atau mengubah referensi setelah prediksi.

## Aturan data pribadi dan sumber

Simpan **seluruh audio dan transkrip di folder lokal `.t10-benchmark` yang diabaikan Git**. Jangan commit, lampirkan ke issue, atau mengunggah rekaman pribadi tanpa izin. Setiap orang yang direkam harus mengetahui tujuan evaluasi offline dan setuju secara sukarela; patuhi perizinan tambahan bagi partisipan di bawah umur bila diperlukan. Jangan menyimpan nama asli, nomor telepon, maupun identitas sensitif dalam manifest/transkrip. Simpan bukti izin dalam penyimpanan pribadi terpisah. Apabila persetujuan dicabut, hentikan penggunaan, hapus rekaman lokal sesuai permintaan, dan anggap lock/hasil yang bergantung pada rekaman itu tidak sah.

Kolom `consent_declared=true`, `human_reference_reviewed=true`, `origin=fresh_consented_recording_not_public_corpus` adalah **pernyataan pengumpul**, bukan bukti yang bisa diautentikasi oleh program. Jangan mengubahnya menjadi `true` bila belum nyata. Rekaman sintetis pada unit test sama sekali **bukan** peserta manusia.

## Format rekaman dan transkrip

- WAV **PCM 16-bit**, **mono**, **16.000 Hz**, durasi **1–30 detik** setiap sampel, ukuran maksimal 3 MB.
- Nama file seperti `audio/id-clean-01.wav` sampai `id-clean-20.wav` (kemudian `id-challenging-01.wav` sampai `id-challenging-10.wav`). Jangan gunakan audio benchmark FLEURS/Common Voice atau audio yang mungkin menjadi bahan pelatihan kandidat.
- Acuan `reference` harus berisi kata yang benar-benar terdengar, ditinjau manusia sebelum inferensi. Gunakan `spk-01`, `spk-02`, … sebagai penanda pembicara, serta `rev-01` untuk penanda reviewer yang tidak dapat mengungkap identitas; kedua jenis ID bukan autentikasi reviewer.
- `recorded_utc` wajib ISO8601 dengan zona waktu, contoh format `2026-10-10T05:00:00Z` **hanya contoh sintaks, bukan waktu rekaman yang diklaim**.
- `audio_sha256` adalah hash dari **byte WAV lokal asli** (bukan transkrip atau nama file). `origin` harus sesuai nilai pada kode. Hindari duplikasi audio maupun teks referensi ternormalisasi.

## Langkah Windows — tidak mengunduh model

Jalankan setelah `git pull --ff-only origin main`:

```powershell
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$workspace = ".\.t10-benchmark\t10-id-holdout-new"

& $py tools\t10_id_independent_holdout.py init --workspace $workspace
notepad "$workspace\manifest.json"
```

Perintah `init` membuat **30 slot metadata belum terisi**; semua `consent_declared` dan `human_reference_reviewed` adalah `false`, nilai `reference`, `audio_sha256`, `recorded_utc`, dan ID penilai kosong. Tidak ada suara, keputusan manusia, maupun izin yang dibuat oleh AI. Rekaman sebenarnya disimpan secara lokal dalam subfolder `$workspace\audio`.

Untuk melihat SHA-256 file yang benar-benar direkam:

```powershell
Get-FileHash "$workspace\audio\id-clean-01.wav" -Algorithm SHA256
```

Setelah seluruh slot diisi sesuai bukti nyata, audit:

```powershell
& $py tools\t10_id_independent_holdout.py audit --workspace $workspace
```

Audit mungkin dan **seharusnya FAIL** selama masih ada template, izin, rekaman atau transkrip yang belum lengkap. Audit PASS hanya berarti konsistensi byte, format, metadata dan deklarasi, **bukan autentikasi independensi atau consent**.

**Sebelum kandidat Maleo digunakan terhadap holdout apa pun**, jalankan:

```powershell
& $py tools\t10_id_independent_holdout.py seal --workspace $workspace
& $py tools\t10_id_independent_holdout.py verify --workspace $workspace
```

`seal` membuat `manifest.lock.json` **sekali saja** dan menolak penimpaan. `verify` membaca ulang semua byte WAV dan manifest serta membandingkan checksum terhadap lock. Lock tidak menyimpan teks transkrip atau identitas peserta. Dokumen dan script tidak mengunduh model, menjalankan ADB, melakukan inference atau mengubah benchmark lama.

## Ketentuan evaluasi setelah dataset siap

Setelah integritas, provenance dan izin ditinjau sungguh-sungguh oleh pihak berwenang, perlu **persetujuan terpisah sebelum mengunduh model**. Verifikasi file Maleo Base Q8_0 lokal melalui `tools/t10_asr_id_compact_protocol.py verify` dan checksum yang sudah dipin. Buat aturan urutan A/B serta batas RTF/RSS/suhu sebelum evaluasi host dan Sony. Hasil holdout baru harus dilaporkan **terpisah** dari data FLEURS lama; penelitian ini tidak otomatis melewati CP4. Human QA translation juga masih memerlukan sign-off independen.

## Paket pengumpulan berbasis topik — sesudah template 30 slot siap

Bila output Windows telah menunjukkan **Total 30 / Clean 20 / Challenging 10 / Empty 30**, jangan menjalankan ulang `init`. Gunakan generator **hanya metadata dan topik**, yang tidak mengisi transkrip atau flag izin:

```powershell
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$workspace = ".\.t10-benchmark\t10-id-holdout-new"
& $py tools\t10_id_collection_kit.py create --workspace $workspace
& $py tools\t10_id_collection_kit.py status --workspace $workspace
notepad "$workspace\collection_plan.json"
```

- `create` menghasilkan `collection_plan.json` di folder privat yang sudah diabaikan Git. **Tidak menimpa** plan yang sudah ada, `manifest.json`, rekaman, maupun lock. Bila plan pernah dibuat, jalankan hanya `status`, jangan mengganti plan setelah melihat hasil model.
- Ada **30 petunjuk topik**, bukan kalimat yang harus dibaca kata demi kata. Setiap pembicara pseudonim `spk-01` sampai `spk-05` mendapat empat tugas clean dan dua tugas challenging. Setiap pembicara harus sungguh-sungguh bersedia; ID ini **hanya jadwal usulan**, bukan bukti adanya orang tersebut.
- Minta peserta berbicara **dengan kata-kata sendiri**, sekitar 15–20 kata per klip, dalam Bahasa Indonesia; variasi challenging boleh berupa jeda, angka, dan variasi tempo normal dalam suasana aman. Jangan sengaja merekam informasi pribadi atau memicu keadaan berbahaya. Nilai data ini adalah *prompted spontaneous speech*, bukan rekaman bacaan persis. Rekaman yang tidak memenuhi 1–30 detik/format harus disiapkan ulang secara sah.
- Bila pembicara masih di bawah umur, periksa kebutuhan izin orang tua/wali dan hindari pengumpulan tanpa persetujuan yang sesuai. Jangan menekan orang lain untuk berpartisipasi. Simpan dokumentasi izin secara aman di luar Git.
- **Jangan salin `topic_cue_not_reference_transcript` ke kolom `reference`**. Reviewer manusia harus mendengarkan audio, menuliskan kata yang benar-benar terucap, dan memeriksanya sebelum melihat prediksi ASR. Pelaporan kualitas mesti menyebut data ini sebagai *prompted spontaneous speech*; jangan menyamakan hasilnya dengan keseluruhan situasi pemakaian nyata.
- Perintah `status` hanya membaca metadata lokal dan menghitung isian yang ada. Hitungan bernama `*_not_verified` dan `*_not_authenticated` **tidak membuktikan akurasi audio, persetujuan maupun review**. Bahkan jika seluruh hitungan menjadi 30, gunakan `audit`, cek bukti manusia secara terpisah, dan `seal`/`verify` **sebelum** inferensi. Status tetap `CP4 BLOCKED` sampai persyaratan lain terpenuhi.
- Jumlah kata clean yang benar-benar ditranskrip harus mencapai **≥250 kata ter-normalisasi**; rencana topik ini tidak menjamin jumlah tersebut. Tidak boleh menambah kata fiktif agar lolos validator.
- Tidak ada audio, transkrip, identitas, checksum file hasil rekaman atau persetujuan nyata yang dihasilkan oleh generator, dan tidak ada pengiriman jaringan/ADB/inferensi model.
