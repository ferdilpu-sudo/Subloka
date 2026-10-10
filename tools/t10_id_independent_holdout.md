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
