# Offline Bilingual Caption — Pedoman Proyek

Versi dokumen: 0.3 • Tanggal: 2026-10-06 • Nama kerja produk: **SubLoka**.

Editor caption video Android untuk menghasilkan, mengoreksi, menerjemahkan, dan mengekspor subtitle bilingual Inggris ↔ Indonesia secara lokal. Produk ini **bukan editor video umum**. Video adalah konteks kerja; caption adalah objek utama yang diedit.

Folder `.agents/` adalah source of truth untuk spesifikasi, keputusan, rencana, pengujian, dan handoff coding agent. Kode aplikasi berada di luar folder ini; README produk tetap berada di root repository.

## Status nyata

| Aspek | Status |
|---|---|
| Kebutuhan pengguna | Android, editor caption video, offline, tanpa biaya API, subtitle bilingual EN ↔ ID dikunci |
| Arah UX | Focused bilingual caption editor; Caption/Timing/Style; processing sebagai state; adaptive layout dikunci di dokumen v0.2 |
| Dokumen | 10 dokumen disusun dan diperbarui; pemeriksaan tercatat di testing.md |
| Kode aplikasi / APK | Frontend demo modular sudah dibuat; APK belum dibangun |
| Build / emulator / perangkat fisik | Belum terverifikasi pada eksekusi ini; Android SDK/Gradle runtime tidak tersedia di workspace |
| Akurasi, performa, ekspor dan kompatibilitas | Belum terverifikasi |

Jangan menafsirkan pilihan teknologi atau mockup sebagai bukti fitur sudah terintegrasi atau lulus uji.

## Identitas pengalaman produk

Prinsip utama:

> **Focused Offline Bilingual Caption Editor** — tenang, cepat, lokal, dan sangat jelas untuk memperbaiki caption EN ↔ ID.

Urutan mental pengguna:

```text
Pilih video → Buat caption → Perbaiki → Ekspor
```

Bukan:

```text
Masuk dashboard → pilih banyak tool → kelola timeline video → cari fitur caption → ekspor
```

Arah interaksi yang dikunci:

- Home/Projects memiliki satu primary action: **New Project**.
- New Project menggabungkan pemilihan video + bahasa sumber; bahasa target otomatis menjadi bahasa satunya.
- Processing ditampilkan sebagai state project/editor, bukan destination navigasi permanen.
- Editor hanya memiliki tiga workspace utama: **Caption**, **Timing**, **Style**.
- **Translation bukan workspace utama**; status terjemahan dan tindakan translate/retranslate muncul kontekstual pada caption.
- Timeline detail hanya muncul pada workspace Timing.
- Export adalah final action, bukan tab navigasi global.
- Tidak memakai bottom navigation pada MVP karena tidak ada beberapa destination setara yang perlu berpindah terus-menerus.
- Layout menyesuaikan ruang jendela: compact = stacked, expanded = supporting pane berdampingan.

## Pengalaman utama

1. Pilih video.
2. Pilih bahasa audio: English atau Indonesia.
3. Aplikasi memastikan model offline siap.
4. Buat caption lokal; tampilkan tahap/progress yang benar-benar diketahui.
5. Koreksi source caption pada workspace Caption.
6. Koreksi timing pada workspace Timing jika diperlukan.
7. Atur tampilan pada workspace Style jika diperlukan.
8. Perbarui translation yang stale secara kontekstual.
9. Ekspor video atau SRT.

- Audio Inggris menghasilkan teks Inggris dan terjemahan Indonesia; audio Indonesia menghasilkan teks Indonesia dan terjemahan Inggris.
- Kedua bahasa berbagi waktu kemunculan, tetapi teks dan tampilannya bisa diedit terpisah.
- Model perlu disiapkan melalui unduhan awal. Setelah model tersedia, alur utama harus berjalan tanpa jaringan.
- Tanpa login, server aplikasi, API berbayar, iklan, atau langganan pada lingkup versi pertama. Kuota unduhan awal, penyimpanan, dan daya perangkat tetap diperlukan.

## Peta dokumen dan sumber kebenaran

| File | Satu tanggung jawab |
|---|---|
| [../README.md](../README.md) | README produk di root: status implementasi, modul, dan cara build |
| [README.md](README.md) | Indeks pedoman agent dan ringkasan source of truth `.agents/` |
| [AGENTS.md](AGENTS.md) | Prosedur kerja dan serah terima agent |
| [rules.md](rules.md) | Aturan implementasi, UX guardrail, dan batas perubahan |
| [prd.md](prd.md) | Kebutuhan produk serta acceptance criteria |
| [design.md](design.md) | IA, perilaku layar, interaction model, responsive behavior, visual baseline |
| [architecture.md](architecture.md) | Batas modul, aliran proses, integrasi dan dependensi |
| [schema.md](schema.md) | Kontrak data, invariant, dan migrasi |
| [plan.md](plan.md) | Task, dependensi, checkpoint, dan ledger status |
| [testing.md](testing.md) | Strategi pengujian, gate, dan bukti aktual |
| [decisions.md](decisions.md) | Alasan keputusan, status keputusan, dan pertanyaan terbuka |

Urutan baca agent: `../README.md` → `README.md` → `AGENTS.md` → `rules.md` → `prd.md` → `decisions.md` → `architecture.md` → `schema.md` → `design.md` → `plan.md` → `testing.md`.

## Arah teknis

Baseline frontend: Kotlin built-in AGP + Jetpack Compose, minSdk 26, compile/target SDK 37. Baseline dependency produksi yang dievaluasi: Media3 1.11.1, Room 2.8.5, ML Kit Translate 17.0.3, whisper.cpp v1.9.4 kandidat T10. Engine/persistensi belum diintegrasikan; ukuran model, ABI final, dan kemampuan ekspor tetap menunggu gate teknis.

## Memulai implementasi

1. Baca seluruh pedoman, lalu periksa kode aktual jika sudah ada repository.
2. Ambil task yang dependensinya terpenuhi dari plan.md; task awal tetap T01.
3. **Jangan melompat ke visual polish atau membangun editor penuh sebelum T03/CP2.** T03 harus menghasilkan interaction specification dan wireframe state yang memenuhi design.md.
4. Selesaikan UI dengan fake adapter sebelum integrasi engine lokal. UI demo tidak boleh mengklaim inference/export nyata.
5. Catat apa yang dibuat, apa yang benar-benar diuji, serta yang belum terverifikasi.
6. Sebelum task dinyatakan DONE, perbarui plan.md, testing.md, dan spesifikasi terkait.

Project Gradle/frontend demo sudah dibuat di root repository. Target build: `./gradlew :app:assembleDebug :app:lintDebug`. Pada eksekusi ini wrapper runtime/Android SDK tidak tersedia sehingga perintah belum dapat dibuktikan berjalan; T04 tetap IMPLEMENTED, belum DONE sampai build/lint benar-benar PASS.

## Batas versi pertama

Satu video per proyek, caption per segmen, dua bahasa EN/ID, penyimpanan lokal, pengeditan teks/timing/style, MP4 dan SRT. Bukan editor multitrack, layanan cloud, live caption, dubbing, atau editor efek video. Rincian scope dimiliki prd.md.
