# Prosedur Kerja Agent

Dokumen ini mengatur bagaimana agent bekerja. Aturan kode dan UX guardrail ada di rules.md; status pengerjaan hanya di plan.md dan bukti pengujian di testing.md.

## 1. Konteks dan urutan baca

Dari root repository, baca `README.md` → `.agents/README.md` → `.agents/AGENTS.md` → `.agents/rules.md` → `.agents/prd.md` → `.agents/decisions.md` → `.agents/architecture.md` → `.agents/schema.md` → `.agents/design.md` → `.agents/plan.md` → `.agents/testing.md` sebelum memulai. Setelah itu baca kode yang terkait dengan task serta instruksi repository yang berlaku. Dokumen ini tidak mengizinkan akses, publikasi, atau perubahan di luar otorisasi pengguna.

Kebutuhan eksplisit pengguna mendahului asumsi dokumen. Jika bukti implementasi berbeda dengan dokumentasi, laporkan perbedaannya, periksa sebab, dan perbarui catatan; jangan menganggap dokumen lama sebagai bukti tes. Konflik scope yang tidak dapat diselesaikan dari instruksi pengguna ditandai BLOCKED dengan pertanyaan spesifik.

## 2. Mulai sesi

1. Periksa kondisi worktree tanpa menghapus perubahan orang lain.
2. Baca handoff terakhir dan task aktif; jangan mengulang task DONE tanpa risiko konkret.
3. Pilih satu task siap jalan, cocokkan dependensi serta checkpoint.
4. Nyatakan tujuan, file yang diperkirakan berubah, acceptance criteria, dan pengujian relevan.
5. Ubah status task menjadi IN_PROGRESS sebelum implementasi.

Satu task boleh membutuhkan banyak file. Setiap file tetap memiliki satu tanggung jawab yang kohesif, tanpa batas jumlah baris.

### 2.1 Kebersihan dokumentasi agent

- Semua catatan planning, keputusan, handoff, aturan, schema, design, dan bukti pengujian Markdown milik coding agent harus tinggal di `.agents/`.
- Jangan membuat `plan-2.md`, `notes.md`, `todo.md`, atau dokumen liar di root hanya untuk kenyamanan sesi. Perbarui source of truth yang sudah ditentukan.
- `README.md` di root tetap human-facing/project-facing dan hanya diperbarui ketika setup, milestone, atau status produk berubah.
- Bila perlu dokumen agent baru, nyatakan satu tanggung jawabnya dan tautkan dari `.agents/README.md`.

## 3. Saat implementasi

- Kerjakan perubahan dalam lingkup task; hindari pembersihan kode stabil yang tidak terkait.
- Selesaikan UI dengan fake adapter terlebih dahulu. Bedakan mode demo dari engine sungguhan; UI demo tidak boleh mengklaim transkripsi atau ekspor berhasil.
- Integrasi engine lokal menggantikan tahap backend server karena produk sepenuhnya offline.
- Perubahan kontrak data wajib disertai update schema.md dan rencana migrasi.
- Keputusan teknis atau UX baru yang mengubah interaction model dicatat di decisions.md sebelum menjadi ketergantungan task berikutnya.
- Jika pengujian yang diperlukan tidak tersedia, lanjutkan pekerjaan yang aman, tetapi catat keterbatasan dan jangan tandai task DONE.

### 3.1 Protokol UI/UX agent

Untuk task UI/UX, agent wajib bekerja dari masalah ke solusi, bukan dari selera visual ke redesign.

1. Audit kebutuhan dan flow yang sudah ada sebelum membuat layar baru.
2. Klasifikasikan temuan:
   - **Product/IA problem** — struktur atau alur salah.
   - **Usability defect** — pengguna sulit menyelesaikan tugas.
   - **Accessibility defect** — kontrol/teks/state tidak dapat diakses dengan benar.
   - **Consistency defect** — pola yang sama berperilaku/terlihat berbeda tanpa alasan.
   - **Visual polish** — hierarchy, spacing, typography, atau finishing.
   - **Aesthetic preference** — selera, bukan defect; jangan menyamar sebagai requirement.
3. Gunakan prioritas:
   - **P0** blocker/usability failure/data-risk.
   - **P1** friction besar atau interaction model tidak jelas.
   - **P2** masalah terasa tetapi tidak menghalangi task utama.
   - **P3** polish visual.
4. Jangan redesign jika masalah dapat diselesaikan dengan polish atau perbaikan lokal.
5. Pertahankan pola yang sudah familiar dan terbukti bekerja; jangan mengubah IA hanya agar terlihat baru.
6. Untuk setiap perubahan besar, tulis **masalah → alasan/bukti → solusi → dampak → acceptance criteria**.
7. Bedakan **MUST / SHOULD / COULD**; jangan menambah fitur di luar MVP hanya karena ruang UI tersedia.
8. Semua komponen interaktif harus memiliki state relevan: default, pressed/focused/selected bila berlaku, disabled, loading, error, empty, dan success/contextual feedback sesuai kebutuhan.
9. Editor harus tetap mengikuti keputusan produk: **caption = hero, video = context, timeline = contextual, translation = state/action, style = secondary tool**.
10. T03 tidak dianggap selesai hanya karena mockup terlihat rapi. Interaction flow, keyboard, adaptive layout, loading/empty/error, stale translation, dan export blocking harus dapat ditinjau.

## 4. Tiga kategori bukti wajib

| Kategori | Makna | Contoh sah |
|---|---|---|
| Sudah dibuat | Artefak/kode benar-benar ada | File importer dan test fixture tersedia |
| Sudah diuji | Pemeriksaan benar-benar dijalankan dengan hasil tercatat | Unit test importer lulus pada revision tertentu |
| Belum terverifikasi | Klaim yang belum memiliki bukti relevan | Import URI pada HP fisik belum diuji |

Build sukses bukan bukti alur pengguna sukses. Unit test bukan bukti native inference, kualitas terjemahan, atau render video berhasil di perangkat. Screenshot bukan bukti tombol bekerja. Uji yang gagal tetap dicatat sebagai telah dijalankan, dengan hasil FAIL; bukan bukti lulus.

## 5. Siklus penutupan task

Urutan wajib: implementasi → pengujian relevan → inspeksi hasil → pembaruan dokumen → pemeriksaan konsistensi → DONE.

Setelah task selesai dan teruji, agent WAJIB memperbarui:

1. **testing.md:** ID bukti, task, revision, lingkungan, perintah/langkah, expected, actual, hasil, lokasi artefak, batas verifikasi.
2. **plan.md:** status, hasil, evidence ID, blocker tersisa, task berikutnya dan handoff.
3. **Dokumen terdampak:** prd untuk kebutuhan; design untuk interaksi; architecture untuk batas integrasi; schema untuk data; decisions untuk keputusan; README untuk setup dan status milestone. Tulis “tidak berubah” pada handoff jika spesifikasi tidak berubah.

Update docs termasuk bagian Definition of Done, bukan task opsional setelah pekerjaan dianggap selesai. Bila menggunakan git, sertakan kode, pengujian, dan docs dalam changeset yang saling dapat ditelusuri. Jangan mengarang hash commit; gunakan revision yang benar-benar diuji, atau identitas working tree beserta hash/diff artefaknya.

## 6. Checkpoint dan otorisasi

Checkpoint produk, arsitektur, dan UI membutuhkan tinjauan pengguna sesuai plan.md. Jika persetujuan sudah tercatat pada sesi atau task, jangan meminta ulang. Checkpoint teknis dengan kriteria objektif bisa ditutup agent setelah ada bukti; checkpoint bukan alasan untuk berhenti pada pekerjaan yang sudah diotorisasi.

Jika harus berhenti karena checkpoint, sajikan hasil konkret, bukti, hal yang belum terverifikasi, dan satu keputusan yang dibutuhkan. Jangan menyatakan seluruh aplikasi selesai hanya karena satu fase selesai.

## 7. Handoff akhir sesi

Simpan handoff di plan.md, bukan hanya chat:

```text
Tanggal / task / revision:
Tujuan dan perubahan:
Sudah dibuat: [path nyata]
Sudah diuji: [evidence ID, hasil, lingkungan]
Belum terverifikasi: [klaim dan alasan]
Dokumen diperbarui: [file + ringkasan perubahan]
Blocker / keputusan yang dibutuhkan:
Task berikutnya yang siap: [ID + alasan dependensi terpenuhi]
```

Jangan menulis token, isi video pribadi, atau transkrip lengkap ke log serah terima. Artefak sampel untuk pengujian harus disetujui atau dibuat khusus pengujian.
