# Offline Bilingual Caption — Pedoman Proyek

Versi dokumen: 0.3 • Tanggal: 2026-10-06 • Nama kerja produk: **SubLoka**.

Editor caption video Android untuk menghasilkan, mengoreksi, menerjemahkan, dan mengekspor subtitle bilingual Inggris ↔ Indonesia secara lokal. Produk ini **bukan editor video umum**. Video adalah konteks kerja; caption adalah objek utama yang diedit.

Folder `.agents/` adalah source of truth untuk spesifikasi, keputusan, rencana, pengujian, dan handoff coding agent. Kode aplikasi berada di luar folder ini; README produk tetap berada di root repository.

## Status nyata

| Aspek | Status |
|---|---|
| Kebutuhan pengguna | Android, editor caption video, offline, tanpa biaya API, subtitle bilingual EN ↔ ID dikunci |
| Arah UX | Focused bilingual caption editor; Caption/Timing/Style; processing sebagai state; adaptive layout dikunci di dokumen v0.2 |
| Dokumen | 10 dokumen agent disusun dan diperbarui; evidence berada di testing.md |
| Scaffold Android | **T04 DONE**; build dan lint frontend lulus pada GitHub Actions |
| UI demo T05–T07 | **DONE**; compile/lint dan DEVICE-001 smoke test lulus; CP3 PASS |
| Emulator / perangkat fisik | DEVICE-001 **PASS** berdasarkan smoke test manual pengguna |
| Persistence lokal T08 | **DONE**; Room v1, autosave/editor rules, reopen, revision dan schema fixture teruji |
| Media / ASR / translation engine / export nyata | Belum diintegrasikan dan belum diverifikasi |
| Akurasi, performa dan kompatibilitas | Belum diverifikasi |

Bukti teknis terbaru: `DATA-001` pada GitHub Actions run #15, revision `deb5b1ebfe87254535a5a5845fa368cb6e6c8829`; domain tests, Room integration tests, schema fixture, assemble dan lint PASS. Ini belum membuktikan media/ASR/translation/export produksi.

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

Baseline frontend: Kotlin built-in AGP + Jetpack Compose, minSdk 26, compile/target SDK 37. Room 2.8.5 persistence telah terintegrasi pada T08. Dependency fase berikutnya: Media3 1.11.1 untuk T09, ML Kit Translate 17.0.3, dan whisper.cpp v1.9.4 kandidat T10. Ukuran model, ABI final, media compatibility, dan kemampuan ekspor tetap menunggu gate teknis.

## Melanjutkan implementasi

1. Baca seluruh pedoman dan kode aktual.
2. T04–T08 dan CP3 telah selesai.
3. Next task adalah **T09: impor/pemutar/decode audio nyata**.
4. Implementasikan URI/relink, metadata/orientasi/audio-track discovery, player, decode PCM bertahap, dan error media sesuai architecture.
5. Uji file tanpa audio, rotated video, codec/input yang tidak didukung, dan pastikan video sumber tidak dimodifikasi.
6. Jangan mulai evaluasi ASR T10 sebelum T09 lulus.

GitHub Actions telah membuktikan build/lint frontend dan T08 persistence tests. Evidence terbaru berada di testing.md sebagai `DATA-001`.

## Batas versi pertama

Satu video per proyek, caption per segmen, dua bahasa EN/ID, penyimpanan lokal, pengeditan teks/timing/style, MP4 dan SRT. Bukan editor multitrack, layanan cloud, live caption, dubbing, atau editor efek video. Rincian scope dimiliki prd.md.
