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

## Hasil archive-sizes nyata dan perbaikan tes — 2026-10-10

Windows berhasil memanggil API archive metadata pada revisi yang dipin, memperoleh **11 TAR dengan jumlah 15.542.917.120 byte**, tanpa mengunduh satu byte pun arsip. Empat arsip awal: Imperative 907.765.760 byte (865,7 MiB), Exclamatory 1.049.487.360 byte (1.000,9 MiB), Negation 1.094.379.520 byte (1.043,7 MiB), dan Rhetorical 1.207.500.800 byte (1.151,6 MiB). Semua SHA yang dicetak berasal dari metadata upstream dan **belum diverifikasi atas file lokal**. Total yang dipublikasikan benar-benar besar; jangan mengunduh kategori apa pun tanpa batasan ruang dan izin eksplisit.

Suite 19 tes Windows terakhir memiliki **1 FAIL + 1 ERROR**, tetapi perintah archive-sizes terhadap CSV pengguna **PASS**. Dua tes tersebut menggunakan fixture lokal berisi **kategori Declarative saja**, berlawanan dengan 11 metadata arsip yang disimulasikan. Code produksi memang harus tetap menolak mismatched kategori. **Fixture tes diperbaiki** untuk menyediakan 11 kategori pada skenario positif, ditambah satu tes baru yang memastikan metadata kategori tidak lengkap tetap ditolak. Kini **20 tes**, hasil Windows masih PENDING.

Jalankan *hanya* pengujian baru berikut setelah pull; CSV dan hasil ukuran sebelumnya tidak perlu diunduh lagi:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_public_id_corpus.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 public corpus regression FAILED" }
```

Jika **20/20 PASS**, bekukan **30 metadata sampel**, **tanpa mengunduh WAV/TAR**, untuk arsip terkecil yang diketahui:

```powershell
& $py tools\t10_public_id_corpus.py select --workspace $public --category Imperative
if ($LASTEXITCODE -ne 0) { throw "T10 public 30-case selection FAILED" }
```

Perintah select membuat satu file privat `external_test_30_selection.json` (write-once); source test dan human, 30 path WAV berbeda, tiga label pembicara test dan kemungkinan teks kalimat berulang akan dicatat. Tidak ada klaim bebas tumpang tindih model training, tidak ada Human QA atau CP4 PASS. Jika pernah memilih kategori dan file seleksi sudah ada, **jangan ulangi atau menimpa**.

Untuk mendapatkan audio secara lebih hemat dari unduhan TAR minimal 865,7 MiB, Hugging Face mendokumentasikan dukungan **HTTP byte-range requests**. Namun belum ada verifikasi range pada objek TAR Atika di host pengguna; tidak boleh diasumsikan bahwa 30 WAV dapat diambil secara acak tanpa indeks offset TAR dan byte-integrity validation. Pemeriksaan desain range, jika dilakukan, harus dibatasi beberapa byte serta meminta respons 206/Content-Range yang benar. Unduhan penuh TAR atau model harus menunggu persetujuan eksplisit setelah ukuran dan kebutuhan dataset dipastikan.

## Checkpoint Imperative terpilih + pemeriksaan byte-range — 2026-10-10

Windows menjalankan **20 unit test PASS dalam 0,342 s**, kemudian berhasil melakukan *write-once* `select --category Imperative`, menghasilkan file privat `.t10-benchmark/t10-public-atika/external_test_30_selection.json` berisi **30 pilihan metadata**, partisi `test`, dan **3 label pembicara**. Output tegas: `actual_audio_downloaded=false`, CP4 BLOCKED. **Jangan ulangi select.**

Arsip paling kecil tetap `Imperative.tar`, berukuran **907.765.760 byte (865,7 MiB)** berdasarkan metadata API penerbit; SHA-256 LFS yang diterbitkan adalah `54725d7ecd573c6fbe88cc6d43337be3910599842dc1711b8e7f5fbae88dc938`. Ini bukan SHA file lokal, dan **tidak** mengizinkan pengunduhan TAR besar.

### Pemeriksaan byte-range terbatas tanpa mengunduh TAR

Alat `tools/t10_atika_tar_range_probe.py` menjalankan **satu** HTTP GET HTTPS dengan `Range: bytes=0-511` dan `Accept-Encoding: identity` untuk URL arsip kategori Imperative pada revisi yang telah dipin. Jika server mengabaikan Range (`200 OK`), skrip **tidak membaca body apa pun** dan mengembalikan kode 2. Jika server menjawab `206 Partial Content`, skrip menuntut Content-Range persis `bytes 0-511/907765760`, Content-Length jika diberikan harus 512, membaca paling banyak **513 byte** (untuk mendeteksi overrun) dan memvalidasi checksum header TAR standar. Skrip hanya mencetak informasi umum, **bukan path member TAR, transkrip, atau audio**. Tidak ada model/ADB/inferensi/CP4 promotion. 206 yang benar hanya membuktikan kelayakan awal byte-range; indeks offset 30 WAV **belum tersedia**.

Perintah Windows:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
& $py -m unittest discover -s tools -p "test_t10_atika_tar_range_probe.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 TAR range probe tests FAILED" }
& $py tools\t10_atika_tar_range_probe.py
```

Tes tambahan **12 kasus sintetis**, hasil Windows **PENDING**. Bila tes lulus tetapi HTTP probe bernilai `RANGE_NOT_HONORED_NO_BODY_READ`, stop dan **jangan** meneruskan ke unduhan besar. Bila server memberikan 206 valid, evaluasi indeks TAR/berapa banyak round-trip metadata yang dibutuhkan **sebelum** mengembangkan pengambilan hanya 30 WAV. Jangan berasumsi ratusan ribu request Range ekonomis, murah, atau benar. Jika server memberi 206 namun 512 header bukan TAR yang valid, stop untuk investigasi lebih lanjut.

Dataset Atika tetap **evaluasi publik tambahan**, dengan teks bacaan yang berulang antar peserta dan hanya tiga label pembicara test/kategori; tidak boleh dimasukkan ke holdout privat rekaman baru atau dinyatakan mengatasi CP4.

## Checkpoint Range 206 PASS dan pilot header TAR berurutan (2026-10-10)

Actual Windows: `tools/test_t10_atika_tar_range_probe.py` **12/12 PASS dalam 0,006 detik**; permintaan HTTPS `Range: bytes=0-511` terhadap `Imperative.tar` pada pin revisi terbukti menghasilkan **HTTP 206**, `Content-Range` / total ukuran arsip konsisten, dan **checksum 512-byte header TAR valid**. Header pertama menunjukkan isi file pertama `91364` byte. **Belum ada satu pun WAV disalin**, 30 metadata test tetap write-once, belum ada model/ADB/inference. Terminal kemudian menampilkan `elseif : The term 'elseif' is not recognized`; ini hanya sintaks PowerShell karena `elseif` dijalankan sebagai perintah terpisah dari blok `if`, bukan kegagalan Range.

Untuk menghindari unduhan penuh 865,7 MiB sebelum menilai ongkos indexing, alat *terpisah* `tools/t10_atika_tar_header_walk.py` menelusuri **maksimal 8 header berurutan** dari offset nol. Header berikutnya dihitung dari ukuran file sebelumnya dengan kelipatan blok TAR 512 byte. Setiap header dibaca lewat satu HTTPS Range `206` persis 512 byte dan batas pembacaan 513 byte. Maksimum percobaan remote = **8 requests, 4.104 body bytes**; default 6. Tidak ada payload audio yang disimpan atau isi/path peserta yang ditampilkan. Jika server mendadak mengabaikan Range (`HTTP 200`), berhenti tanpa membaca body dan exit code 2.

Pilot membaca **snapshot seleksi privat yang sudah tersedia**, memeriksa kategori Imperative, SHA metadata publik `3ba42e...`, 30 path WAV yang unik, dan revisi pin tanpa menyalin berkas. Output hanya agregat header yang berhasil, offset lanjutan, hitungan nama yang *persis* cocok dengan 30 path metadata, dan status `CP4 BLOCKED`. Kecocokan nol tidak otomatis berarti gagal: kemungkinan path member TAR berbeda prefiks dari jalur CSV. Pilot **bukan** pengindeks seluruh arsip atau metode unduhan 30 WAV; ratusan/ribuan permintaan terpisah tidak boleh diasumsikan praktis.

### Pengujian Windows berikutnya

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_atika_tar_header_walk.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 TAR header walk tests FAILED" }
& $py tools\t10_atika_tar_header_walk.py --workspace $public --max-headers 6
$rc = $LASTEXITCODE
if ($rc -eq 0) { Write-Host "T10 BOUNDED HEADER WALK PASS" -ForegroundColor Green }
elseif ($rc -eq 2) { Write-Host "HTTP Range ignored; no TAR downloaded" -ForegroundColor Yellow }
else { throw "TAR header walk failed ($rc)" }
```

**Catatan:** Salin blok `if/elseif/else` lengkap sekaligus ke PowerShell; jangan menjalankan `elseif` sendiri setelah sebuah `if` telah ditutup. Total **14 unit test baru**, Windows QA **belum diterima**; CI juga belum dikonfirmasi. Tidak perlu ulangi probe pertama, `fetch-metadata`, `select`, atau unduh TAR.

Jika pilot berhasil: lakukan analisis ongkos pemetaan TAR sebelum mengembangkan ekstraksi; periksa kemungkinan adanya indeks WAV kategori yang sudah dipublikasikan. Jangan mengunduh TAR besar, menjalankan scan tanpa batas, atau mengklaim WER/CP4 PASS.

## QA final 14 header-walk tests PASS — 2026-10-10
- Actual Windows rerun: `Ran 14 tests in 0.074s`, `OK`, PowerShell guard passed, `T10 HEADER WALK 14 TESTS PASS`. This supersedes the previous 14-test FAILED run and verifies the corrected numeric assertion `3 × 513 = 1539` as a synthetic regression. Live six-header network probe had already PASS earlier (6 headers, next offset 490496, 0 of 30 selected matched, zero WAV payload); don't rerun it.
- Research observation: the upstream `data/audio_shards/audio_shards_manifest.csv` is described as an **archive-level inventory** (one entry per category TAR; archive filename, file count, size and SHA). It is **not evidence of an individual WAV TAR byte-offset index**. Reference: original corpus publication at https://www.sciencedirect.com/science/article/pii/S2352340926008085 and dataset README at https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset. Avoid a naïve one-HTTP-request-per-member scan through thousands of TAR members; its network latency may be excessive and it would go beyond the current hard cap of eight.
- Existing `Imperative.tar` published size is **907765760 B (865.7 MiB)** and only 30 metadata rows are frozen. No actual WAV or TAR has been downloaded. No further code execution is necessary for the successful 14/14 check. Before any WAV acquisition, investigate whether publisher offers a genuine per-member offset index or directly hosted audio files. If not, choose a separate modest-size licensed audio source, or require explicit user approval of an 865.7 MiB archive download and available host storage. Neither strategy affects the fresh-consent private holdout or CP4 BLOCKED status.

## Pemeriksaan biaya indeks WAV offline — 2026-10-11

Kelanjutan setelah **14/14 Windows unit tests PASS** (`0.074s`) dan enam header TAR remote berhasil dibaca. Sampai saat ini hanya metadata 30 WAV `Imperative` yang dipilih; **0 WAV disimpan**. Pemeriksaan sumber resmi menunjukkan Dataset Viewer menyediakan tiga proyeksi Parquet **metadata dan transkrip**, bukan audio individual. Repository dataset menyimpan WAV dalam 11 arsip TAR; `audio_shards_manifest.csv` adalah inventaris arsip, bukan indeks posisi WAV dalam TAR. **Belum terbukti ada layanan endpoint WAV individual** pada revisi yang dibekukan. Jangan salah menyimpulkan bahwa HTTP 206 awal berarti tersedia indeks file acak.

Rujukan sumber penelitian: https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset dan https://huggingface.co/datasets/Atika88/Indonesian-ASR-11-Class-Dataset/blob/main/docs/RELEASE_EVIDENCE_AND_METHOD_BOUNDARIES.md . Lisensi yang dinyatakan adalah CC BY 4.0, tetapi **pencantuman lisensi dan label speaker pseudonim bukan autentikasi persetujuan rekaman**, hak redistribusi atau ketidakberirisan dari data latih. Dataset bersifat prompted read speech, dan publikasi menyatakan sejumlah detail metodologi/izin tidak dapat dibuktikan dari paket publik; hindari klaim legal atau penelitian yang melampaui bukti.

Dibuat `tools/t10_atika_acquisition_budget.py`, alat **offline/read-only** yang hanya membaca `upstream_metadata.csv` dan `external_test_30_selection.json` dari workspace privat. Alat memverifikasi SHA-256 lokal CSV yang sebelumnya dilaporkan Windows, revisi Hugging Face, kategori dan 30 baris yang dipilih, status `test`/human/non-synthetic, kecocokan label dan transkrip publisher, serta ukuran WAV yang dinyatakan. Output hanya agregat dan estimasi: jumlah seluruh baris kategori, kandidat human-test, total ukuran sumber terpilih, jumlah label pembicara, dan **perkiraan jumlah request jika tiap TAR member dibaca lewat satu HTTP Range header**.

**Estimasi bukan pengukuran aktual:** tanpa indeks offset, diperlukan pembacaan header sepanjang arsip. Perkiraan jumlah permintaan didasarkan pada **jumlah baris WAV kategori dalam CSV**, tidak mencakup entry direktori, PAX atau metadata lain. Tabel waktu hanya ilustrasi jika rata-rata latency 200/500/1000 ms; bukan prediksi bandwidth atau waktu yang dijamin. Pilihan terbanyak berada di posisi yang belum diketahui, jadi jangan menganggap file ke-30 bisa ditemukan dalam 8 request. Kebijakan riset ini menetapkan **maksimum 200 request header** untuk pengambilan jarak jauh; jika estimasi lebih besar, jangan melakukan scan header-per-WAV karena beban jaringan/latensi yang besar. Ini bukan batas teknis server.

### Perintah Windows berikutnya

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_atika_acquisition_budget.py" -v
if ($LASTEXITCODE -ne 0) { throw "Atika offline budget tests FAILED" }
& $py tools\t10_atika_acquisition_budget.py --workspace $public
if ($LASTEXITCODE -ne 0) { throw "Atika budget preflight FAILED" }
```

Jumlah tes baru **15**, Windows QA **belum dilaporkan**, CI baru dihubungkan dan hasilnya belum diverifikasi. Kategori sumber mencakup WAV train yang dapat lebih panjang dan melebihi 3 MB; perhitungan agregat mengizinkan sampai 10 MB per baris metadata kategori, sementara **kandidat test** tetap mengikuti filter WAV maksimal 3 MB dan durasi 1–30 detik. Jalankan hanya dua perintah di atas, **jangan mengulangi** `init`, `fetch-metadata`, `select`, range probe dan six-header walk. Alat ini tidak memerlukan jaringan dan tidak menulis ke disk. Jika melaporkan `DO_NOT_SCAN_TAR_ONE_MEMBER_PER_REQUEST`, keputusan selanjutnya adalah mengutamakan sumber audio individu dengan izin penggunaan yang benar-benar sesuai atau mempertimbangkan unduh satu arsip 865,7 MiB **hanya setelah pengguna menyetujui ukuran/ruang/cakupan dan hak pemakaian**. Tidak ada download otomatis, model atau WER baru, CP4 tetap BLOCKED.


## Windows QA — 15/15 acquisition budget tests PASS (2026-10-11)
- Actual user PowerShell result at `d95e949d6a6905bee6f8d449a9e8e4ce87bca59d`: `Ran 15 tests in 0.398s`, `OK`; both test and dry-run CLI exit guards passed. This **supersedes the '15 Windows PENDING' note above** without changing its historical evidence.
- Offline actual aggregate: `Imperative` 9,500 rows; 1,350 eligible human/test; 30 pinned sample metadata, 3 public speaker labels and 16 distinct casefolded references; 2,590,936 publisher-declared bytes selected; 900,344,354 publisher-declared category WAV bytes; 907,765,760 published total TAR bytes.
- Estimated `9,500` separate one-member-per-request TAR header reads **exceeds 200 policy threshold**. Illustration only: 31.7 / 79.2 / 158.3 minutes at 200 / 500 / 1,000ms assumed serial latency. **Reject naive serial header walking**; none of these estimates establish actual member positions. Look for a verified individual-WAV TAR offset index or a small appropriately licensed alternative. If none exists, the full **865.7 MiB** archive remains **approval-gated**, including storage and provenance/reuse considerations.
- No new network, WAV, TAR, model, ADB, inference or private dataset edits; **actual WAV 0/30**; source-selection provenance and user private fresh-consent holdout unchanged. No source-audio quality or rights validation; GitHub CI not independently checked. `T10 ACTIVE / CP4 BLOCKED / T11 TODO`. Evidence: `.agents/evidence/t10-atika-acquisition-budget-windows-15-pass-2026-10-11.json`.


## TAR arithmetic preflight (implemented, Windows validation pending) — 2026-10-11
Public source audit found no verified published per-WAV offset index nor the exact construction command for `Imperative.tar`. One `Colab_ASR_A100_Training/scripts/build_colab_data_archives.sh` in the supporting repository makes **another** TAR (whole `Dataset_Balanced19` for Colab), not the category TAR; do not transfer its file order assumptions. Published `audio_shards_manifest.csv` is archive-level inventory. Metadata sizes can test the order-independent TAR byte-accounting floor, but cannot identify offsets or rule out PAX/directory/long names. Even a full TAR size match is not a valid random-access index.

New read-only tool `tools/t10_atika_tar_layout_budget.py` uses unchanged metadata and frozen private 30-selection; computes 512-byte record arithmetic with illustrative 10,240-byte end alignment, prints only aggregates, no network, no writes, no WAV and no model. New **12 synthetic tests Windows PENDING**, separate small CI workflow PENDING. Once pulled, run:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_atika_tar_layout_budget.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 TAR layout tests FAILED" }
& $py tools\t10_atika_tar_layout_budget.py --workspace $public
if ($LASTEXITCODE -ne 0) { throw "T10 TAR layout budget FAILED" }
```

No more `select`, `fetch-metadata`, remote header walks, big downloads, models, or inference. Do not mark CP4 PASS. Source script: https://github.com/RatnaAtika/Indonesian-ASR-11-Class-Dataset/blob/main/Colab_ASR_A100_Training/scripts/build_colab_data_archives.sh .


## Verified Windows flat TAR arithmetic, and offline order hypothesis gate — 2026-10-11
- Actual Windows console after commit `09c0020`: **27 tests PASS (0.246s)**, containing 12 layout cases + 15 reused acquisition-budget cases accidentally imported into discovery; this was corrected for future runs without changing TAR arithmetic logic. Read-only host report independently matched 9,500 WAV metadata entries and **907,765,760B TAR size** when assuming 9,500 headers, exact 512-byte WAV padding, two 512-byte end blocks and illustrative 10,240-byte TAR record rounding. The residual before final padding is **2,560B**. Do not claim this proves no directory/PAX metadata, exact WAV sizes, TAR member order, or offsets.
- Follow-on `tools/t10_atika_tar_order_hypotheses.py` only checks two **hypothetical member orders** against earlier already-observed first member WAV size 91364B and end-of-sixth-header offset 490496B. It never sends requests, creates or prints member offset tables, changes frozen 30-selection or restores WAV payloads. Return true = candidate is consistent with two small observations, **not verified**; false = candidate inconsistent. New **10 synthetic tests Windows PENDING**; corrected **12 layout tests Windows PENDING**; earlier Windows 27 PASS remains historical evidence.

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_atika_tar_layout_budget.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 layout isolated tests FAILED" }
& $py -m unittest discover -s tools -p "test_t10_atika_tar_order_hypotheses.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 order hypotheses synthetic tests FAILED" }
& $py tools\t10_atika_tar_order_hypotheses.py --workspace $public
if ($LASTEXITCODE -ne 0) { throw "T10 order hypothesis offline audit FAILED" }
```

Do not repeat archive-size reports, select, first TAR header, six-header live pilot, or acquisition budget CLI, and do not download `Imperative.tar` or any WAV. Public speaker/consent and training disjointness remain unverified. CP4 BLOCKED / T11 TODO.


## Lexical order Windows QA and bounded three-header validation pilot — 2026-10-11
Windows **12/12 layout (0.070s)** + **10/10 order hypothesis (0.086s) PASS**. Verified offline pinned metadata reports lexical file-path ordering matches prior first-member size **91364B** and sixth-next-header offset **490496B**; original CSV row ordering matches neither. **This does not prove member order or any individual offsets.**

Implemented `tools/t10_atika_tar_three_header_spotcheck.py`. **Default without opt-in flag = 100% OFFLINE**, computes three temporary hypothetical header positions at quartile member indices based on lexical order, with frozen metadata/selection and pinned digest validation. Outputs only aggregate positions (not paths/offsets) and confirms CP4 blocked. A separate, explicitly user-selected `--execute-three-headers` flag is the only remote mode: maximum three 512-byte HTTP Range header reads through the already-tested exact-206 reader. Stops on first name/size/type mismatch, HTTP Range ignored or invalid header; never downloads any WAV payload or TAR archive and never writes to workspace. Three positive matches increase confidence only at those locations; do not claim all 9500 members or 30 selected WAV offsets verified.

First run **only offline QA and preflight** after pulling main:

```powershell
cd C:\Users\FLYONZ\Documents\GitHub\Subloka
git pull --ff-only origin main
$py = ".\.t10-benchmark\argos-venv\Scripts\python.exe"
$public = ".\.t10-benchmark\t10-public-atika"
& $py -m unittest discover -s tools -p "test_t10_atika_tar_three_header_spotcheck.py" -v
if ($LASTEXITCODE -ne 0) { throw "T10 three-header synthetic tests FAILED" }
& $py tools\t10_atika_tar_three_header_spotcheck.py --workspace $public
if ($LASTEXITCODE -ne 0) { throw "T10 three-header offline preflight FAILED" }
```

The flag `--execute-three-headers` is **not** used by these commands. It authorizes three bounded remote header requests and should only be chosen deliberately after observing offline results; no infinite scan, no 865.7MiB TAR or selected WAV download. The 30 private fresh-consent holdout remains untouched; public voice provenance/disjointness still unverified, `T10 ACTIVE / CP4 BLOCKED / T11 TODO`.
