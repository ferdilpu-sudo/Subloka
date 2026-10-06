# Kontrak Data Lokal

Status: skema logis usulan v1, belum berupa database/migrasi yang berjalan. Room schema export dan migration test dibuat pada T08. Dokumen ini memiliki kontrak data; architecture.md memiliki alur penggunaannya.

## Konvensi dan invariant

ID menggunakan UUID string; nama tabel/kolom snake_case. Waktu media integer mikrodetik (Long/INTEGER), waktu audit epoch millisecond UTC. Kode bahasa `en` atau `id`. Foreign key aktif. Enum dipetakan stabil, tidak memakai ordinal Kotlin. Video/frame/audio tidak disimpan sebagai blob dalam database.

Invariant wajib: `0 <= start_us < end_us <= duration_us`; segmen diurutkan start_us dengan urutan stabil; segmen tidak overlap pada MVP (gap boleh); interval aktif [start_us,end_us). Sumber dan terjemahan berbagi satu interval. SRT mengonversi ke millisecond dengan kebijakan pembulatan konsisten; hasil yang menjadi durasi nol harus diperbaiki atau ditolak, tidak diam-diam diekspor.

## Tabel utama

| Tabel | Field inti | Relasi / ketentuan |
|---|---|---|
| projects | id PK, title, source_uri, source_display_name, source_size_bytes nullable, source_fingerprint nullable, duration_us, width_px, height_px, rotation_degrees, source_language, target_language, content_revision, created_at_ms, updated_at_ms | target_language != source_language; metadata sumber diperbarui hanya setelah validasi |
| caption_segments | id PK, project_id FK, start_us, end_us, source_text, translated_text nullable, source_revision, translation_source_revision nullable, translation_status, translation_origin, updated_at_ms | UNIQUE tidak diperlukan untuk timestamp; overlap divalidasi dalam transaksi; INDEX(project_id,start_us) |
| caption_styles | project_id PK/FK, display_mode, source_first, font_asset_id, source_size_ratio, translation_size_ratio, source_color_argb, translation_color_argb, outline_color_argb, outline_width_ratio, background_color_argb, background_enabled, anchor_x, anchor_y, max_width_ratio, line_gap_ratio, alignment | rasio berdasarkan frame terorientasi; nilai divalidasi sebelum simpan/render |
| processing_jobs | id PK, project_id FK nullable, kind, state, stage, progress nullable, input_revision nullable, engine_version nullable, model_version nullable, checkpoint_ref nullable, error_code nullable, created_at_ms, updated_at_ms | kind=TRANSCRIBE/TRANSLATE/EXPORT; INDEX(state); snapshot bukan referensi UI mutable |
| model_assets | id PK, provider, language_pair nullable, version nullable, local_path nullable, expected_sha256 nullable, actual_sha256 nullable, size_bytes nullable, state, verified_at_ms nullable | provider=WHISPER/MLKIT; field internal ML Kit tidak diasumsikan tersedia |
| export_records | id PK, project_id FK, job_id FK, snapshot_revision, export_kind, display_mode, output_uri nullable, profile_json, state, created_at_ms | output_uri hanya final untuk hasil COMPLETE; source video tetap utuh |

`source_fingerprint` dapat berupa checksum yang diperoleh saat membaca media; metadata nama/ukuran saja tidak cukup membuktikan file pengganti identik. Bila kecocokan relink tidak terbukti, minta konfirmasi reset/review timing dan tandai proyek perlu tinjau.

Snapshot export dan checkpoint chunk disimpan sebagai file internal berversi dengan referensi path privat, ditulis atomik. Isinya menyertakan schema_version, project/revision, source identity, segmen, style, engine/model version sesuai kebutuhan. Penghapusan job/proyek harus membersihkan file miliknya dengan aman.

## Status terjemahan

`MISSING`, `PENDING`, `CURRENT`, `STALE`, `FAILED`. `translation_origin`: NONE, MACHINE, MANUAL. CURRENT mensyaratkan teks tidak kosong dan translation_source_revision == source_revision.

- Create segmen: source_revision=1, translation MISSING.
- Edit sumber: source_revision bertambah; terjemahan lama tetap terlihat dan menjadi STALE jika ada, atau MISSING jika kosong.
- Edit terjemahan manual: simpan teks, origin MANUAL, revision mengikuti sumber yang sedang ditampilkan; validasi sumber belum berubah saat transaksi.
- Translate: ambil snapshot source_revision dan edit token/project revision; terapkan dengan compare-and-set. Jika ada edit manual atau sumber berubah selama job, jangan overwrite. Tandai hasil job dilewati/needs review.
- Split: dua ID baru, timing dibagi; teks sumber/terjemahan harus ditinjau. Pembagian teks awal hanya saran; terjemahan masing-masing STALE/MISSING sampai dikonfirmasi pengguna atau diterjemahkan ulang.
- Merge: ID baru dengan interval gabungan; gabungkan teks dengan urutan yang benar; terjemahan STALE/MISSING sampai review.
- Edit timing saja tidak membuat terjemahan stale, tetapi menaikkan content_revision proyek.

Undo/redo menyimpan command snapshot di memori sesi. Applying undo tetap menaikkan revision monotonik agar hasil job lama tidak dianggap cocok. Autosave transaksi per operasi; jangan menganggap debounced text yang belum flush sebagai saved. Saat focus keluar/back, flush atau tampilkan kegagalan.

## State job

Transisi normal: QUEUED → RUNNING → SUCCEEDED/FAILED. Cancel: QUEUED → CANCELLED atau RUNNING → CANCELLING → CANCELLED. Hilang proses: RUNNING/CANCELLING → INTERRUPTED. Retry membuat attempt/job baru dengan checkpoint valid, bukan mengubah bukti job lama menjadi sukses.

progress nullable berarti persentase belum diketahui, bukan nol. Nilai 1,0 hanya boleh bersama hasil tahap selesai; SUCCEEDED memerlukan hasil tersimpan. Penutupan proyek tidak boleh menghapus job aktif tanpa cancel. Penghapusan proyek menunggu job berhenti, lalu menghapus metadata/cache internal; output galeri dan sumber tidak ikut dihapus otomatis.

## Integritas dan konkurensi

Setiap operasi editor mengubah segmen/style dan content_revision dalam satu transaksi. Satu penulis per proyek; job menggunakan optimistic concurrency. Buat staging generation untuk transkripsi ulang; jangan menghapus caption lama sampai hasil baru valid dan penggantian diotorisasi pengguna. Indeks mencakup project_id/start_us dan status job yang digunakan untuk query pemulihan.


## State presentasi yang tidak menjadi tabel domain

Workspace aktif (`CAPTION/TIMING/STYLE`), ukuran pane, keyboard visibility, scroll position, selected control, dan expanded/compact composition adalah state presentasi. Jangan menambahkannya ke database v1 hanya untuk mempertahankan layout sementara. `selected_segment_id` atau preference UI lintas sesi hanya boleh dipersist jika T03/T04 menemukan kebutuhan pengguna yang konkret dan keputusan dicatat di decisions.md.

Readability/overflow warning dihitung dari teks, timing, style, dan ukuran frame/preview melalui validator/layout engine; bukan status terjemahan dan tidak perlu disimpan sebagai field persisten pada baseline.

## Migrasi dan backup

Mulai schema version 1 pada implementasi, ekspor schema Room ke version control. Setiap perubahan persisten membutuhkan migration path, fixture data lama, dan tes tidak kehilangan bilingual text/style. Destructive migration dilarang untuk data pengguna. Tidak ada cloud backup pada MVP; backup Android untuk database/media/transkrip dinonaktifkan melalui konfigurasi yang diuji. Ekspor proyek sebagai arsip merupakan fitur masa depan, berbeda dengan SRT.
