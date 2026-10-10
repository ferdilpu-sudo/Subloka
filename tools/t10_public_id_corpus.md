# T10 — Sumber audio Indonesia publik untuk evaluasi eksternal (bukan holdout privat)

## Kesimpulan riset sumber (2026-10-10)

Dataset yang dipilih untuk **riset dataset publik** adalah `Atika88/Indonesian-ASR-11-Class-Dataset` (https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset), sumber publik dengan DOI `10.57967/hf/10345`. Revisi DOI-pinned `c65fe8bcff0547214c34cfbea248b4045a0d867c` berasal dari September 2026, sedangkan rilis dataset pertama dilaporkan 18 Juni 2026. Halaman publik menyatakan 104.500 WAV, 104.368 rekaman manusia dan 132 synthetic repairs; metadata per-baris, transkrip, split pembicara-disjoint, 16kHz PCM16 mono; lisensi yang dinyatakan **CC BY 4.0** (atribusi wajib; kepatuhan lebih luas dan hak peserta tidak bisa otomatis diverifikasi).

SUMBER PRIMARY:
- https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset
- https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset/tree/main
- https://huggingface.co/maleo-ai/whisper-base-id (Maleo melaporkan training menggunakan Common Voice 17, FLEURS dan YODAS2, **tidak menyebut Atika**, namun ketidakberirisan sebenarnya belum diaudit)

**Batasan ilmiah:** dataset Atika adalah *prompted read speech* dan kalimat/prompts dapat berulang di seluruh partisi, sehingga tidak menguji percakapan spontan/open-vocabulary dengan baik. Dataset ini tidak boleh dimasukkan diam-diam ke manifest `t10-id-holdout-new`, karena manifest tersebut mensyaratkan rekaman baru dengan izin langsung dan reviewer manusia. Ini jalur **PUBLIC EXTERNAL DIAGNOSTIC**, tidak menggantikan FLEURS asli maupun CP4. Rekaman tetap biometrik walau ID pembicara berupa pseudonim.

**Batasan ukuran dan lisensi:** seluruh dataset ~15,6 GB dalam **11 arsip TAR per kategori**, jauh lebih besar dari target 30 WAV. Satu kategori TAR dapat mencapai skala GB. Alat baru sengaja **hanya mengunduh metadata CSV (maksimum 100 MiB)** dan menyediakan link kategori TAR dari revisi tetap setelah 30 metadata dipilih; **tidak mengunduh TAR, WAV, model ataupun menjalankan ASR**. Unduhan arsip besar memerlukan pemeriksaan ukuran, ruang penyimpanan host dan persetujuan tersendiri. **Eksklusikan baris `is_synthetic == true`** sebab hak pihak ketiga atas 132 perbaikan suara sintetis belum dipastikan di kartu dataset.

## Alur Windows

Setelah commit terbaru ada di lokal:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_public_id_corpus.py" -v
& $py tools\t10_public_id_corpus.py source
```

Jika tes baru PASS, ambil **hanya CSV metadata** via HTTPS dan revisi yang dipin; perintah ini membutuhkan koneksi internet tetapi tidak mengunduh audio. Jangan ketik ulang bila file sudah ada karena output sengaja write-once:

```powershell
& $py tools\t10_public_id_corpus.py fetch-metadata --workspace $public
& $py tools\t10_public_id_corpus.py inspect --workspace $public
```

Perintah `inspect` hanya menampilkan daftar kategori, jumlah rekaman manusia pada partisi test, dan jumlah label pembicara yang memenuhi syarat. **Output tidak menampilkan transkrip, nama, isi audio, atau materi pribadi.**

Jika kategori `Declarative` memenuhi jumlah yang ditentukan, bekukan 30 metadata `test`/human/non-synthetic dengan pilihan yang deterministik **berdasarkan path audio yang berbeda**. Karena tiap kategori memiliki sekitar 19 teks kalimat kanonis, beberapa rekaman dari pembicara berbeda mungkin membaca kalimat yang sama; pemilihan melaporkan `distinct_reference_prompts` dan `repeated_reference_prompts` secara terpisah, dan **tidak mengklaim 30 kalimat unik**:

```powershell
& $py tools\t10_public_id_corpus.py select --workspace $public --category Declarative
```

Perintah `select` membuat `$public\external_test_30_selection.json` **sekali saja** dan mencantumkan nama TAR + sumber archive URL untuk tahap pengambilan audio yang terpisah. File pilihan berisi transkrip sumber yang belum diperiksa ulang; tetap berada di folder gitignored. Jangan mengubah urutan pilihan setelah melihat hasil model. Jika kategori tidak memenuhi syarat, **jangan paksakan**; gunakan daftar `inspect` dan pilih kategori lain sebelum memilih. Pilihan dalam satu kategori meminimalkan jumlah arsip TAR besar, tetapi meningkatkan risiko keterbatasan variasi kosakata/kalimat; dataset ini hanyalah *speaker-varied scripted external diagnostic*, bukan tes unseen prompts.

**File pilihan BUKAN WAV.** Sampai arsip yang relevan berhasil didownload dengan izin, checksum arsip dan setiap WAV terverifikasi, dan referensi didengar/dikoreksi manusia, keadaan tetap `NO AUDIO LOCALLY VERIFIED`, `NO ASR EVAL`. Tidak boleh memberi label `clean/challenging` hanya dari jenis kalimat pada metadata. WER baru, bila tersedia kelak, dilaporkan sebagai **Atika external test**, bukan melewati CP4 atau mengubah baseline asli 105/367 = 28.61%.

## Alternatif sumber yang tidak dipilih

- `SEACrowd/asr_sindodusc`: 3,5 jam dan 3.296 ucapan dari 10 pembicara, tetapi lisensi CC BY-NC-ND 4.0 dan pipeline datanya melibatkan ketergantungan/halaman dataset eksternal; **tidak sebersih CC BY Atika untuk tujuan aplikasi ini**.
- `BabelSpeech/40hours_Indonesian_Colloquial_ASR_Speech_Dataset`: perlu persetujuan berbagi kontak untuk akses; **jangan melewati gate**.
- `google/fleurs`, Common Voice 17, YODAS2: tercantum dalam training Maleo; **jangan klaim independen**.

Status tidak berubah: **T10 ACTIVE / CP4 BLOCKED / T11 TODO**.

## Checkpoint Windows metadata berhasil — 2026-10-10

Berikut log hasil sebenarnya yang dilaporkan pengguna di Windows, bukan hasil simulasi: **15/15 unit tests PASS** (0,384 s), CSV metadata publik **31.362.056 byte** dengan SHA-256 **`3ba42e2261e4ef387bc15e5934ce73be8e3cf6d1700ab0d635aa9d6958f59c21`**, **15.598** rekaman manusia pada partisi `test` memenuhi filter, tersebar pada 11 kategori.

Setiap kategori memiliki **3 label pembicara pada test**, jadi dataset eksternal satu kategori ini belum memenuhi sasaran penelitian holdout privat **≥5 pembicara**. Total ukuran WAV kategori test paling kecil: `Imperative` **120.431.478 B (1.350 baris)**, `Exclamatory` **142.078.684 B (1.425 baris)**, `Negation` **148.081.252 B (1.425 baris)**. **Ini bukan ukuran unduhan TAR kategori penuh**; jangan mengambil keputusan penggunaan bandwidth berdasarkan angka tersebut.

### Pemeriksaan ukuran 11 TAR tanpa unduh audio

Ditambahkan perintah `archive-sizes` yang membaca satu daftar JSON dari API repository Hugging Face untuk revisi yang telah dipin, setelah memvalidasi metadata CSV privat yang sudah tersedia. Balasan API dibatasi **1 MB**, hanya berisi nama/ukuran arsip yang dipublikasikan, bukan audio. Perintah tidak menulis file atau mengunduh TAR/WAV/model:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_public_id_corpus.py" -v
if ($LASTEXITCODE -ne 0) { throw "Archive preflight regressions failed" }
& $py tools\t10_public_id_corpus.py archive-sizes --workspace $public
```

Jumlah tes kini **19**, karena ada **4 tes baru** untuk keamanan/keakuratan pemeriksaan metadata ukuran arsip. **Windows 19/19 PASS baru belum dilaporkan** (tes 15/15 sebelumnya sudah PASS). Perintah menampilkan kategori terurut menurut ukuran TAR yang dilaporkan server, `lfs_sha256_upstream_metadata_unverified` bila tersedia, dan `approved_for_download=false` untuk semua kategori. Belum ada checksum TAR lokal atau SHA audio yang diverifikasi.

**Jangan ulangi `fetch-metadata`**: file CSV sudah ada dan perintah sengaja menolak overwrite. Tunggu hasil `archive-sizes` sebelum memilih satu kategori dengan `select` karena pemilihan JSON juga write-once. Bila sumber API gagal atau tidak sesuai 11 kategori CSV, **stop** dan jangan menebak besar arsip atau mengunduh TAR. Pengunduhan arsip tetap perlu persetujuan terpisah setelah pemeriksaan ukuran, ruang dan lisensi.
